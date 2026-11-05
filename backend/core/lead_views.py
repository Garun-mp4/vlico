from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods, require_safe
from .lead_forms import LeadForm, KINDS
from .lead_service import save_submission, throttle, SubmissionError
from .models import Project, Service, PricingVersion
from .configurator import calculation_form as answer_form, calculate_answers, configurator_context


def initial_lead_form(request, kind="consultation"):
    project = Project.objects.filter(slug=request.GET.get("project", ""), status="published").first()
    service = Service.objects.filter(slug=request.GET.get("service", "")).first()
    return LeadForm(initial={"kind": kind, "project": project, "service": service, "interest": request.GET.get("interest", "")[:200]})


def accept(request):
    try:
        if int(request.META.get("CONTENT_LENGTH") or 0) > 2 * 1024 * 1024:
            raise SubmissionError({"__all__": ["Сообщение получилось слишком длинным. Сократите его и попробуйте отправить снова."]}, 413)
        throttle(request)
        lead, created = save_submission(request, LeadForm(request.POST))
        return {"ok": True, "reference": str(lead.pk), "created": created, "kind": lead.kind, "message": "Заявка принята. Мы свяжемся с вами по указанному контакту."}, 201 if created else 200
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
    if request.method == "POST":
        body, status = accept(request)
        if body.get("ok"):
            return render(request, "site/lead-success.html", body)
        form = LeadForm(request.POST)
        form.is_valid()
        return render(request, "site/request.html", {"lead_form": form, "kind_title": dict(KINDS)[kind], "request_kind": kind, "submission_errors": body["errors"]}, status=status)
    return render(request, "site/request.html", {"lead_form": initial_lead_form(request, kind), "kind_title": dict(KINDS)[kind], "request_kind": kind})


@never_cache
@require_http_methods(["GET", "POST"])
def calculator(request):
    version = get_object_or_404(PricingVersion, active=True)
    quote, errors = None, {}
    calculation_form = answer_form(request.POST or None)
    lead_form = initial_lead_form(request, "calculator")
    if request.method == "POST":
        preserved = {name: request.POST.get(name, "") for name in lead_form.fields}
        preserved["kind"], preserved["pricing_version"] = "calculator", version.pk
        lead_form = LeadForm(initial=preserved)
        if request.POST.get("action") == "quote":
            if calculation_form.is_valid():
                quote = calculate_answers(calculation_form.cleaned_data, version)
        else:
            body, status = accept(request)
            if body.get("ok"):
                return render(request, "site/lead-success.html", body)
            errors = body["errors"]
            if calculation_form.is_valid():
                quote = calculate_answers(calculation_form.cleaned_data, version)
    lead_form.initial["pricing_version"] = version.pk
    from .configurator import ConfiguratorForm
    context = configurator_context(request, form=calculation_form if isinstance(calculation_form, ConfiguratorForm) else None, lead_form=lead_form, quote=quote, errors=errors)
    return render(request, "site/calculator.html", context)


@never_cache
@require_POST
def estimate(request):
    preview = request.POST.get('preview') == '1' and request.POST.get('schema') == 'v2'
    from .configurator import ConfiguratorForm, preview_answers
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
