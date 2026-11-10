from datetime import timedelta
from email.utils import make_msgid
import smtplib
import socket

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.core.validators import validate_email
from django.urls import reverse
from django.utils import timezone

from .lead_forms import KINDS
from .models import Delivery
from .telegram_delivery import DeliveryError, MAX_ATTEMPTS, claim_delivery
from .quick_calculator import QUICK_CALCULATOR_SCHEMA, quick_input_rows


def email_body(lead):
    lines = [
        "VLICO · Новая заявка",
        f"Номер: {lead.pk}",
        f"Дата: {timezone.localtime(lead.created_at):%d.%m.%Y %H:%M}",
        f"Тип: {dict(KINDS).get(lead.kind, lead.kind)}",
        f"Имя: {lead.name}",
        f"Контакт: {lead.contact}",
    ]
    for label, value in (
        ("Услуга", lead.context.get("service_title")),
        ("Компания", lead.context.get("company")),
        ("Интерес", lead.context.get("interest")),
        ("Проект", lead.context.get("project_title")),
        ("Комментарий", lead.comment),
    ):
        if value:
            lines.append(f"{label}: {value}")
    attachment_count = lead.attachments.count()
    if attachment_count:
        lines.append(f"Файлы проекта: {attachment_count} · скачивание в кабинете")
    if lead.calculation:
        quote = lead.calculation
        if quote.get("schema") == QUICK_CALCULATOR_SCHEMA:
            lines.extend(["", "Для предварительного расчёта уточним детали."])
            lines.extend(f"{label}: {value}" for label, value in quick_input_rows(quote.get("inputs", {})))
        else:
            total = quote.get("total")
            lines.extend(["", f"Расчёт: {total} ₽" if total is not None else "Расчёт: требуется уточнение"])
            for item in quote.get("items", []):
                lines.append(f"{item['title']}: {item['quantity']} {item['unit']} × {item['unit_price']} ₽ = {item['total']} ₽")
            lines.extend(quote.get("warnings", []))
            if quote.get("exclusions"):
                lines.append(quote["exclusions"])
    lines.extend([
        "",
        f"Страница: {lead.source_page}",
        "Заявка в кабинете: " + settings.SITE_URL + reverse("cabinet_lead", kwargs={"pk": lead.pk}),
    ])
    return "\n".join(lines)


def _mark_failure(item, code, *, retryable=False):
    retry = retryable and item.attempts < MAX_ATTEMPTS
    delay = (30, 120, 600, 1800, 3600)[min(item.attempts - 1, 4)]
    Delivery.objects.filter(pk=item.pk, lease_token=item.lease_token, status="sending").update(
        status="pending" if retry else "failed",
        error_code=code,
        next_attempt_at=timezone.now() + timedelta(seconds=delay),
        lease_token=None,
        locked_until=None,
        updated_at=timezone.now(),
    )


def deliver_email_one():
    if not settings.EMAIL_DELIVERY_ENABLED:
        return False
    item = claim_delivery("email")
    if not item:
        return False
    recipient = settings.PARTNER_NOTIFICATION_EMAIL if item.lead.kind == "partner" else settings.LEAD_NOTIFICATION_EMAIL
    if item.lead.kind == "partner" and not recipient:
        _mark_failure(item, "email_partner_not_configured")
        return True
    try:
        validate_email(recipient or "")
    except ValidationError:
        _mark_failure(item, "email_partner_recipient_invalid" if item.lead.kind == "partner" else "email_recipient_invalid")
        return True
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD or not settings.DEFAULT_FROM_EMAIL:
        _mark_failure(item, "email_not_configured")
        return True

    contact = item.lead.contact
    try:
        validate_email(contact)
    except ValidationError:
        reply_to = []
    else:
        reply_to = [contact]

    message_id = make_msgid()
    message = EmailMessage(
        subject=f"VLICO — {dict(KINDS).get(item.lead.kind, item.lead.kind)}",
        body=email_body(item.lead),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        reply_to=reply_to,
        headers={"Message-ID": message_id},
    )
    connection = get_connection(fail_silently=False)
    try:
        connection.open()
    except smtplib.SMTPAuthenticationError:
        _mark_failure(item, "email_auth_failed")
        return True
    except smtplib.SMTPRecipientsRefused:
        _mark_failure(item, "email_recipient_rejected")
        return True
    except smtplib.SMTPResponseException as exc:
        temporary = 400 <= exc.smtp_code < 500
        _mark_failure(item, "email_smtp_temporary" if temporary else "email_smtp_rejected", retryable=temporary)
        return True
    except (socket.timeout, TimeoutError, OSError):
        _mark_failure(item, "email_smtp_temporary", retryable=True)
        return True

    try:
        sent = connection.send_messages([message])
        if sent != 1:
            raise DeliveryError("delivery_uncertain")
    except smtplib.SMTPAuthenticationError:
        _mark_failure(item, "email_auth_failed")
    except smtplib.SMTPRecipientsRefused:
        _mark_failure(item, "email_recipient_rejected")
    except smtplib.SMTPResponseException as exc:
        if 400 <= exc.smtp_code < 500:
            _mark_failure(item, "email_smtp_temporary", retryable=True)
        else:
            _mark_failure(item, "email_smtp_rejected")
    except DeliveryError:
        _mark_failure(item, "delivery_uncertain")
    except (smtplib.SMTPServerDisconnected, socket.timeout, TimeoutError, OSError):
        _mark_failure(item, "delivery_uncertain")
    else:
        Delivery.objects.filter(pk=item.pk, lease_token=item.lease_token, status="sending").update(
            status="sent",
            sent_at=timezone.now(),
            external_id=message_id,
            error_code="",
            lease_token=None,
            locked_until=None,
            updated_at=timezone.now(),
        )
    finally:
        connection.close()
    return True
