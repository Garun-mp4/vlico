from datetime import timedelta
from hashlib import sha256
import json
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from .attribution import safe_path, submission_attribution
from .models import Lead, Delivery, SubmissionBucket, PricingVersion
from .configurator import calculation_form, calculate_answers
from .legal import consent_record


class SubmissionError(Exception):
    def __init__(self, errors, status=400, quote=None):
        self.errors, self.status, self.quote = errors, status, quote


def throttle(request):
    key = sha256((settings.SECRET_KEY + ":lead:" + request.META.get("REMOTE_ADDR", "")).encode()).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        bucket, _ = SubmissionBucket.objects.get_or_create(key=key, defaults={"expires_at": now + timedelta(minutes=15)})
        bucket = SubmissionBucket.objects.select_for_update().get(pk=key)
        if bucket.expires_at <= now:
            bucket.attempts = 0
            bucket.expires_at = now + timedelta(minutes=15)
        if bucket.attempts >= 12:
            raise SubmissionError({"__all__": ["Слишком много попыток. Повторите через 15 минут."]}, 429)
        bucket.attempts += 1
        bucket.save()


def save_submission(request, form):
    if not form.is_valid():
        raise SubmissionError(dict(form.errors))
    data = form.cleaned_data
    if request.FILES:
        raise SubmissionError({"__all__": ["Прикрепление файлов больше не используется. Обновите страницу и отправьте заявку без вложений."]})
    answers = calculation_form(request.POST) if data["kind"] == "calculator" else None
    if answers and not answers.is_valid():
        raise SubmissionError(dict(answers.errors))
    project, service = data.get("project"), data.get("service")
    context = {"interest": data.get("interest", ""), "project_title": project.title if project else "", "service_title": service.title if service else ""}
    context["consent"] = consent_record()
    payload = {key: str(data.get(key) or "") for key in ("kind", "name", "contact", "comment", "interest", "pricing_version")}
    payload.update(project=project.pk if project else None, service=service.pk if service else None, legal_version=data["legal_version"])
    if answers:
        payload["inputs"] = {key: str(value) for key, value in answers.cleaned_data.items()}
    digest = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    existing = Lead.objects.filter(idempotency_key=data["idempotency_key"]).first()
    if existing:
        if existing.payload_hash != digest:
            raise SubmissionError({"__all__": ["Эта форма уже отправлена с другими данными. Откройте новую форму для нового обращения."]}, 409)
        return existing, False
    try:
        with transaction.atomic():
            version, quote = None, {}
            if answers:
                try:
                    version = PricingVersion.objects.select_for_update().get(active=True)
                except PricingVersion.DoesNotExist:
                    raise SubmissionError({"__all__": ["Тарифы обновились. Обновите расчёт перед отправкой."]}, 409)
                quote = calculate_answers(answers.cleaned_data, version)
                if data.get("pricing_version") != version.pk:
                    raise SubmissionError({"__all__": ["Тарифы обновились. Проверьте новый расчёт и отправьте заявку ещё раз."]}, 409, quote)
            lead = Lead.objects.create(idempotency_key=data["idempotency_key"], payload_hash=digest, kind=data["kind"], name=data["name"], contact=data["contact"],
                service=service, project=project, comment=data.get("comment", ""), context=context, source_page=safe_path(request.POST.get("source_page", "/")),
                attribution=submission_attribution(request), calculation=quote, pricing_version=version, consent_at=timezone.now())
            Delivery.objects.create(lead=lead)
            return lead, True
    except IntegrityError:
        existing = Lead.objects.filter(idempotency_key=data["idempotency_key"]).first()
        if existing:
            if existing.payload_hash == digest:
                return existing, False
            raise SubmissionError({"__all__": ["Эта форма уже отправлена с другими данными. Откройте новую форму для нового обращения."]}, 409) from None
        raise
