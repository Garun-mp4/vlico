from functools import wraps
import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe, require_POST, require_http_methods
from .models import Lead, LeadAttachment, Delivery, PricingVersion, EvaSyncJob
from .pricing import RatesForm, CalculationForm
from .quick_calculator import quick_input_rows, QUICK_CALCULATOR_SCHEMA
from .telegram_delivery import ERROR_LABELS

BUSINESS_PERMISSIONS = ("core.view_lead", "core.change_lead", "core.view_leadattachment", "core.view_delivery", "core.change_delivery", "core.view_pricingversion", "core.add_pricingversion")


def capability_required(permission):
    def decorate(view):
        @login_required(login_url="cabinet_login")
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_active or not request.user.is_staff or not request.user.has_perm(permission):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


@never_cache
@capability_required("core.view_lead")
@require_safe
def leads(request):
    items = Lead.objects.select_related("project", "service").prefetch_related("deliveries").order_by("-created_at")
    query = request.GET.get("q", "").strip()[:160]
    if query:
        condition = Q(name__icontains=query) | Q(contact__icontains=query)
        try:
            condition |= Q(pk=uuid.UUID(query))
        except ValueError:
            pass
        items = items.filter(condition)
    counts = dict(Lead.objects.values("status").annotate(total=Count("pk")).values_list("status", "total"))
    status_options = [(value, label, counts.get(value, 0)) for value, label in Lead._meta.get_field("status").choices]
    state = request.GET.get("status", "")
    if state in {value for value, _, _ in status_options}:
        items = items.filter(status=state)
    else:
        state = ""
    delivery_state = request.GET.get("delivery", "")
    failed_delivery_count = Delivery.objects.filter(status="failed").count()
    if delivery_state == "failed":
        items = items.filter(deliveries__status="failed").distinct()
    else:
        delivery_state = ""
    return render(request, "cabinet/leads.html", {
        "page": Paginator(items, 25).get_page(request.GET.get("page")),
        "query": query,
        "state": state,
        "status_options": status_options,
        "delivery_state": delivery_state,
        "failed_delivery_count": failed_delivery_count,
    })


@never_cache
@capability_required("core.view_lead")
@require_safe
def detail(request, pk):
    lead = get_object_or_404(Lead.objects.select_related("project", "service", "pricing_version"), pk=pk)
    deliveries = list(lead.deliveries.all())
    for delivery in deliveries:
        delivery.error_label = ERROR_LABELS.get(delivery.error_code, "Ошибка доставки" if delivery.error_code else "")
    if lead.calculation.get("schema") == QUICK_CALCULATOR_SCHEMA:
        inputs = quick_input_rows(lead.calculation.get("inputs", {}))
    else:
        inputs = []
        for name, field in CalculationForm().fields.items():
            value = lead.calculation.get("inputs", {}).get(name)
            if hasattr(field, "choices"):
                value = dict(field.choices).get(value, value)
            inputs.append((field.label, value if value is not None else "Не указан"))
    return render(request, "cabinet/lead.html", {"lead": lead, "deliveries": deliveries, "attachments": lead.attachments.all(), "calculation_inputs": inputs, "eva_sync": EvaSyncJob.objects.filter(lead=lead).first()})


@never_cache
@capability_required("core.change_lead")
@require_POST
def retry_eva(request, pk):
    with transaction.atomic():
        job = get_object_or_404(EvaSyncJob.objects.select_for_update(), lead_id=pk)
        if job.status in {"retry", "blocked", "review"} and job.error_code != "write_uncertain":
            job.status, job.attempts = "pending", 0
            job.next_attempt_at = None
            job.save(update_fields=["status", "attempts", "next_attempt_at", "updated_at"])
    return redirect("cabinet_lead", pk=pk)


@never_cache
@capability_required("core.change_lead")
@require_POST
def status(request, pk):
    with transaction.atomic():
        lead = get_object_or_404(Lead.objects.select_for_update(), pk=pk)
        if request.POST.get("revision") != lead.updated_at.isoformat():
            messages.error(request, "Заявка изменена в другой вкладке. Обновите страницу.")
        elif request.POST.get("status") in {value for value, _ in Lead._meta.get_field("status").choices}:
            lead.status = request.POST["status"]
            lead.save(update_fields=["status", "updated_at"])
            messages.success(request, "Статус заявки сохранён.")
    return redirect("cabinet_lead", pk=pk)


@never_cache
@capability_required("core.change_delivery")
@require_POST
def retry(request, pk, delivery_pk):
    with transaction.atomic():
        delivery = get_object_or_404(Delivery.objects.select_for_update(), pk=delivery_pk, lead_id=pk)
        if delivery.status not in {"failed", "pending"}:
            messages.error(request, "Повтор доступен для ожидающих и неотправленных уведомлений.")
        elif delivery.channel == "email" and not settings.EMAIL_DELIVERY_ENABLED:
            messages.error(request, "Почтовый транспорт отключён. Сначала настройте SMTP и включите отправку.")
        elif delivery.error_code == "delivery_uncertain" and request.POST.get("confirm") != "yes":
            messages.error(request, "Сначала проверьте Telegram и подтвердите повтор: сообщение могло быть доставлено.")
        else:
            delivery.status, delivery.attempts, delivery.error_code = "pending", 0, ""
            delivery.next_attempt_at = timezone.now()
            delivery.save(update_fields=["status", "attempts", "error_code", "next_attempt_at", "updated_at"])
            messages.success(request, "Уведомление поставлено в очередь. Уже подтверждённые части повторно не отправляются.")
    return redirect("cabinet_lead", pk=pk)


@never_cache
@capability_required("core.view_leadattachment")
@require_safe
def attachment(request, pk, attachment_pk):
    item = get_object_or_404(LeadAttachment, pk=attachment_pk, lead_id=pk)
    try:
        response = FileResponse(item.file.open("rb"), as_attachment=True, filename=item.original_name, content_type=item.content_type or "application/octet-stream")
    except OSError:
        raise Http404
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@never_cache
@capability_required("core.view_pricingversion")
@require_http_methods(["GET", "POST"])
def rates(request):
    version = get_object_or_404(PricingVersion, active=True)
    form = RatesForm(request.POST or None, version=version)
    if request.method == "POST":
        if not request.user.has_perm("core.add_pricingversion"):
            raise PermissionDenied
        if form.is_valid():
            with transaction.atomic():
                active = PricingVersion.objects.select_for_update().get(pk=version.pk)
                if not active.active or form.cleaned_data["revision"] != str(active.pk):
                    form.add_error(None, "Тарифы уже изменены. Обновите страницу перед сохранением.")
                else:
                    new_rates = form.rates()
                    if new_rates != active.rates or form.cleaned_data["title"] != active.title:
                        active.active = False
                        active.save(update_fields=["active", "updated_at"])
                        PricingVersion.objects.create(title=form.cleaned_data["title"], rates=new_rates, active=True)
                    messages.success(request, "Тарифы сохранены. Исторические расчёты в заявках не изменены.")
                    return redirect("cabinet_rates")
    return render(request, "cabinet/rates.html", {"form": form, "version": version, "history": PricingVersion.objects.order_by("-created_at")[:10]})
