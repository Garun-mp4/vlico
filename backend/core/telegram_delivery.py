from datetime import timedelta
import json
from pathlib import Path
import socket
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from .lead_forms import KINDS
from .models import Delivery
from .telegram_templates import lead_title, message_parts, utf16_length

MAX_ATTEMPTS = 5
LEASE_SECONDS = 120
COVER_DIR = Path(__file__).with_name("telegram_covers")
CAPTION_LIMIT = 1024
ERROR_LABELS = {
    "not_configured": "Проверьте настройки бота и получателя",
    "telegram_401": "Telegram отклонил токен бота",
    "telegram_403": "Бот не может писать получателю",
    "telegram_400": "Telegram отклонил запрос",
    "chat_not_found": "Получатель не запустил бота или указан неверный chat_id",
    "telegram_429": "Telegram временно ограничил отправку",
    "telegram_unavailable": "Telegram временно недоступен",
    "network_unavailable": "Нет соединения с Telegram",
    "delivery_uncertain": "Результат отправки неизвестен. Проверьте Telegram перед повтором",
    "attachment_unavailable": "Файл недоступен в хранилище",
    "email_not_configured": "Не настроены параметры почтового уведомления",
    "email_auth_failed": "Почтовый сервер отклонил логин или пароль приложения",
    "email_recipient_rejected": "Почтовый сервер отклонил адрес получателя",
    "email_smtp_rejected": "Почтовый сервер отклонил письмо",
    "email_smtp_temporary": "Почтовый сервер временно не принял письмо",
}


class DeliveryError(Exception):
    def __init__(self, code, retryable=False, retry_after=0):
        self.code, self.retryable, self.retry_after = code, retryable, retry_after
        super().__init__(code)


class LeaseLost(Exception):
    pass


def api_call(method, fields, attachment=None, *, photo=None):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        raise DeliveryError("not_configured")
    fields = {"chat_id": settings.TELEGRAM_CHAT_ID, **fields}
    if attachment or photo:
        boundary = "vlico" + uuid.uuid4().hex
        body = bytearray()
        for key, value in fields.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        if photo:
            field, filename, mime_type = "photo", photo.name, "image/png"
            file = photo
        else:
            field = "document"
            filename = "plan" + Path(attachment.file.name).suffix
            mime_type = attachment.content_type
            file = attachment.file
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\nContent-Type: {mime_type}\r\n\r\n'.encode())
        try:
            with file.open("rb") as source:
                body.extend(source.read())
        except OSError:
            raise DeliveryError("attachment_unavailable")
        body.extend(f"\r\n--{boundary}--\r\n".encode())
        content_type = "multipart/form-data; boundary=" + boundary
    else:
        body = json.dumps(fields).encode()
        content_type = "application/json"
    request = Request(f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}", data=bytes(body), headers={"Content-Type": content_type}, method="POST")
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read(65536))
    except HTTPError as exc:
        retry_after = 0
        try:
            error_body = json.loads(exc.read(65536))
        except (ValueError, TypeError):
            error_body = {}
        finally:
            exc.close()
        if exc.code == 429:
            try:
                retry_after = int(error_body.get("parameters", {}).get("retry_after", 30))
            except (ValueError, TypeError, AttributeError):
                retry_after = 30
        code = "telegram_unavailable" if exc.code >= 500 else f"telegram_{exc.code}"
        if exc.code == 400 and isinstance(error_body, dict) and error_body.get("description") == "Bad Request: chat not found":
            code = "chat_not_found"
        raise DeliveryError(code, exc.code == 429 or exc.code >= 500, min(86400, max(0, retry_after))) from None
    except URLError as exc:
        if isinstance(exc.reason, (socket.gaierror, ConnectionRefusedError)):
            raise DeliveryError("network_unavailable", True) from None
        raise DeliveryError("delivery_uncertain") from None
    except (TimeoutError, OSError, ValueError):
        raise DeliveryError("delivery_uncertain") from None
    if not isinstance(result, dict) or result.get("ok") is not True or not isinstance(result.get("result"), dict) or not isinstance(result["result"].get("message_id"), int):
        raise DeliveryError("delivery_uncertain")
    return str(result["result"]["message_id"])


def legacy_message_parts(lead):
    quote = lead.calculation
    lines = ["VLICO · Новая заявка", f"ID: {lead.pk}", f"Время: {timezone.localtime(lead.created_at):%d.%m.%Y %H:%M}",
        f"Тип: {dict(KINDS).get(lead.kind, lead.kind)}", f"Имя: {lead.name}", f"Контакт: {lead.contact}"]
    for label, value in [("Услуга", lead.context.get("service_title")), ("Интерес", lead.context.get("interest")), ("Кейс", lead.context.get("project_title")), ("Пожелания", lead.comment)]:
        if value:
            lines.append(f"{label}: {value}")
    if quote:
        lines += ["", (f"Предварительный расчёт: {quote['total']} ₽" if quote["total"] is not None else "Индивидуальный расчёт: см. выбранные параметры и уточнения"), f"Тарифы: {quote['version_title']} (#{quote['version']})"]
        lines += [f"{item['title']}: {item['quantity']} {item['unit']} × {item['unit_price']} ₽ = {item['total']} ₽" for item in quote["items"]]
        if quote.get("schema") == "v2":
            lines += quote["warnings"]
            lines += [f"{row['label']}: {row['value']}" for row in quote["configuration"]]
        elif not quote["complete"]:
            lines.append("Периметр неизвестен: примыкание не включено в сумму.")
        lines.append(quote["exclusions"])
    lines += ["", "Страница: " + lead.source_page]
    lines += [f"{key}: {value}" for key, value in lead.attribution.items() if value]
    lines.append(f"Согласие: {timezone.localtime(lead.consent_at):%d.%m.%Y %H:%M}")
    text = "\n".join(lines)
    # Telegram limits text in UTF-16 units; keep user emoji intact when splitting.
    parts, current, length = [], [], 0
    for char in text:
        size = 2 if ord(char) > 0xFFFF else 1
        if length + size > 3800:
            parts.append("".join(current))
            current, length = [], 0
        current.append(char)
        length += size
    if current:
        parts.append("".join(current))
    return parts


def claim_delivery(channel="telegram"):
    now = timezone.now()
    with transaction.atomic():
        # A crashed process may have sent its request before recording the answer.
        Delivery.objects.filter(status="sending", locked_until__lt=now).update(status="failed", error_code="delivery_uncertain", lease_token=None, locked_until=None)
        item = Delivery.objects.select_for_update(skip_locked=True).filter(Q(next_attempt_at__lte=now) | Q(next_attempt_at__isnull=True), channel=channel, status="pending", attempts__lt=MAX_ATTEMPTS).order_by("next_attempt_at", "pk").first()
        if not item:
            return None
        item.status, item.lease_token = "sending", uuid.uuid4()
        item.attempts += 1
        item.locked_until = now + timedelta(seconds=LEASE_SECONDS)
        item.save(update_fields=["status", "lease_token", "attempts", "locked_until", "updated_at"])
        return item


def checkpoint(item, progress):
    changed = Delivery.objects.filter(pk=item.pk, lease_token=item.lease_token, status="sending").update(progress=progress, locked_until=timezone.now() + timedelta(seconds=LEASE_SECONDS), updated_at=timezone.now())
    if changed != 1:
        raise LeaseLost


def send_lead_message(item, progress):
    lead = item.lead
    messages = progress["messages"]
    cover_id = progress.get("cover")
    # Confirmed parts from older workers must keep their original boundaries on retry.
    legacy = bool(messages or cover_id) and not progress.get("structured")
    if legacy:
        parts = [(part, utf16_length(part)) for part in legacy_message_parts(lead)]
        formatting = {}
    else:
        progress["structured"] = True
        parts = message_parts(lead)
        url = settings.SITE_URL + reverse("cabinet_lead", kwargs={"pk": lead.pk})
        formatting = {"parse_mode": "HTML", "reply_markup": {
            "inline_keyboard": [[{"text": "Открыть заявку", "url": url}]],
        }}
    if not messages and not cover_id:
        photo = COVER_DIR / ("calculator.png" if lead.kind == "calculator" else "form.png")
        if len(parts) == 1 and parts[0][1] <= CAPTION_LIMIT:
            messages.append(api_call("sendPhoto", {"caption": parts[0][0], **formatting}, photo=photo))
            checkpoint(item, progress)
            return
        cover_id = progress["cover"] = api_call("sendPhoto", {"caption": lead_title(lead)}, photo=photo)
        checkpoint(item, progress)
    for part, _ in parts[len(messages):]:
        fields = {"text": part, "link_preview_options": {"is_disabled": True}, **formatting}
        if cover_id:
            fields["reply_parameters"] = {"message_id": int(cover_id), "allow_sending_without_reply": True}
        messages.append(api_call("sendMessage", fields))
        checkpoint(item, progress)


def deliver_one():
    if not settings.TELEGRAM_DELIVERY_ENABLED:
        return False
    item = claim_delivery()
    if not item:
        return False
    progress = {"messages": list(item.progress.get("messages", [])), "files": list(item.progress.get("files", []))}
    for key in ("cover", "structured"):
        if key in item.progress:
            progress[key] = item.progress[key]
    try:
        lead = item.lead
        send_lead_message(item, progress)
        for attachment in lead.attachments.order_by("pk"):
            if attachment.pk in progress["files"]:
                continue
            api_call("sendDocument", {"caption": f"Заявка {lead.pk}\n{attachment.original_name}"[:1000]}, attachment)
            progress["files"].append(attachment.pk)
            checkpoint(item, progress)
        Delivery.objects.filter(pk=item.pk, lease_token=item.lease_token, status="sending").update(status="sent", sent_at=timezone.now(), error_code="", external_id=progress["messages"][0], lease_token=None, locked_until=None, updated_at=timezone.now())
    except DeliveryError as exc:
        retry = exc.retryable and item.attempts < MAX_ATTEMPTS
        delay = max(exc.retry_after, (30, 120, 600, 1800, 3600)[item.attempts - 1])
        Delivery.objects.filter(pk=item.pk, lease_token=item.lease_token, status="sending").update(status="pending" if retry else "failed", error_code=exc.code,
            next_attempt_at=timezone.now() + timedelta(seconds=delay), lease_token=None, locked_until=None, updated_at=timezone.now())
    except LeaseLost:
        pass
    return True
