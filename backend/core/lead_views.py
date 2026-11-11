from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.core.exceptions import RequestDataTooBig, TooManyFilesSent
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods, require_safe
from .lead_forms import LeadForm, KINDS
from .lead_service import save_submission, throttle, SubmissionError
from .models import Project, Service, PricingVersion
from .quick_calculator import QuickCalculatorForm, QUICK_CALCULATOR_SCHEMA


def initial_lead_form(request, kind="consultation", *, auto_id="id_%s"):
    project = Project.objects.filter(slug=request.GET.get("project", ""), status="published").first()
    service = Service.objects.filter(slug=request.GET.get("service", "")).first()
    return LeadForm(initial={"kind": kind, "project": project, "service": service, "interest": request.GET.get("interest", "")[:200]}, auto_id=auto_id)


def quick_calculator_context(request, *, quick_form=None, lead_form=None, show_result=False, show_contact=False, submission_errors=None):
    source_page = request.path if request.path in {"/", "/calculator/"} else "/calculator/"
    if request.method == "POST" and request.POST.get("source_page") in {"/", "/calculator/"}:
        source_page = request.POST["source_page"]
    if lead_form is None:
        lead_form = initial_lead_form(request, "calculator", auto_id="id_quick_%s")
    return {
        "quick_form": quick_form or QuickCalculatorForm(),
        "quick_lead_form": lead_form,
        "quick_show_result": show_result,
        "quick_show_contact": show_contact,
        "quick_submission_errors": submission_errors or [],
        "quick_source_page": source_page,
    }


def accept(request, expected_kind=None):
    try:
        content_length = int(request.META.get("CONTENT_LENGTH") or 0)
        if content_length < 0 or content_length > settings.LEAD_MAX_REQUEST_SIZE:
            raise SubmissionError({"__all__": ["Форма слишком велика. Сократите текст заявки и попробуйте снова."]}, 413)
        throttle(request)
        try:
            post, files = request.POST, request.FILES
        except RequestDataTooBig:
            raise SubmissionError({"__all__": ["Форма превышает допустимый размер. Сократите текст заявки и попробуйте снова."]}, 413) from None
        except TooManyFilesSent:
            raise SubmissionError({"__all__": ["Прикрепление файлов недоступно. Отправьте заявку без вложений."]}) from None
        if expected_kind and post.get("kind") != expected_kind:
            raise SubmissionError({"kind": ["Обновите форму сотрудничества и отправьте её ещё раз."]})
        lead, created = save_submission(request, LeadForm(post, files))
        return {"ok": True, "reference": str(lead.pk), "created": created, "kind": lead.kind, "new_request_url": reverse("calculator") if lead.kind == "calculator" else reverse("request_form", args=[lead.kind]), "message": "Спасибо! Ваша заявка успешно отправлена. Наш специалист свяжется с вами в ближайшее время."}, 201 if created else 200
    except SubmissionError as exc:
        body = {"ok": False, "errors": exc.errors}
        if exc.quote:
            body["quote"] = exc.quote
        return body, exc.status


@never_cache
@require_POST
def submit(request):
    body, status = accept(request)
    response = JsonResponse(body, status=status)
    if status == 429:
        response["Retry-After"] = "900"
    return response


@never_cache
@require_http_methods(["GET", "POST"])
def request_form(request, kind="consultation"):
    if kind not in dict(KINDS):
        return HttpResponse(status=404)
    if kind == "calculator":
        return redirect("calculator")
    kind_description = ("Оставьте имя и телефон, укажите удобный способ связи. Компанию можно добавить по желанию; обсудим сотрудничество."
        if kind == "partner" else "Расскажите о помещении и оставьте удобный контакт. Обсудим потолок, освещение и следующий шаг.")
    if request.method == "POST":
        body, status = accept(request, expected_kind="partner" if kind == "partner" else None)
        if body.get("ok"):
            return render(request, "site/lead-success.html", body)
        form = initial_lead_form(request, kind) if status == 413 else LeadForm(request.POST, request.FILES)
        form.is_valid()
        return render(request, "site/request.html", {"lead_form": form, "kind_title": dict(KINDS)[kind], "kind_description": kind_description, "request_kind": kind, "submission_errors": body["errors"]}, status=status)
    return render(request, "site/request.html", {"lead_form": initial_lead_form(request, kind), "kind_title": dict(KINDS)[kind], "kind_description": kind_description, "request_kind": kind})


@never_cache
@require_http_methods(["GET", "POST"])
def calculator(request):
    quick_form = QuickCalculatorForm(request.POST if request.method == "POST" else None)
    lead_form = initial_lead_form(request, "calculator", auto_id="id_quick_%s")
    show_result = show_contact = False
    submission_errors = []
    status_code = 200
    if request.method == "POST":
        if request.POST.get("calculator_schema") != QUICK_CALCULATOR_SCHEMA:
            submission_errors = ["Версия формы изменилась. Обновите страницу и попробуйте ещё раз."]
            status_code = 409
        elif request.POST.get("action") == "quote":
            show_result = quick_form.is_valid()
            show_contact = show_result
            lead_form = _preserved_quick_lead_form(request)
        else:
            body, status = accept(request)
            if body.get("ok"):
                return render(request, "site/lead-success.html", body)
            status_code = status
            errors = body.get("errors", {})
            quick_form.is_valid()
            lead_form = LeadForm(request.POST, auto_id="id_quick_%s")
            lead_form.is_valid()
            show_result = quick_form.is_valid()
            show_contact = True
            submission_errors = [message for message in errors.get("__all__", [])]
            if not submission_errors and errors:
                submission_errors = ["Проверьте отмеченные поля формы."]
    context = quick_calculator_context(request, quick_form=quick_form, lead_form=lead_form, show_result=show_result, show_contact=show_contact, submission_errors=submission_errors)
    return render(request, "site/calculator.html", context, status=status_code)


def _preserved_quick_lead_form(request):
    names = ("name", "contact", "consent", "project", "interest", "idempotency_key", "submission_token", "legal_version", "website")
    initial = {name: request.POST.get(name, "") for name in names if name in request.POST}
    initial["kind"] = "calculator"
    return LeadForm(initial=initial, auto_id="id_quick_%s")


@never_cache
@require_POST
def estimate(request):
    preview = request.POST.get('preview') == '1' and request.POST.get('schema') == 'v2'
    from .configurator import calculation_form as answer_form, calculate_answers, ConfiguratorForm, preview_answers
    form = ConfiguratorForm(request.POST, partial=True) if preview else answer_form(request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": dict(form.errors)}, status=400)
    version = get_object_or_404(PricingVersion, active=True)
    if preview:
        quote, options = preview_answers(form, version)
        return JsonResponse({'ok': True, 'quote': quote, 'options': options})
    return JsonResponse({"ok": True, "quote": calculate_answers(form.cleaned_data, version)})


@require_safe
def privacy(request):
    return render(request, "site/privacy.html")
