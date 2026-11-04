from datetime import timedelta
import json
import socket
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .lead_forms import KINDS
from .models import Delivery

MAX_ATTEMPTS = 5
LEASE_SECONDS = 120
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
}


class DeliveryError(Exception):
    def __init__(self, code, retryable=False, retry_after=0):
        self.code, self.retryable, self.retry_after = code, retryable, retry_after
        super().__init__(code)


class LeaseLost(Exception):
    pass


def api_call(method, fields, attachment=None):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        raise DeliveryError("not_configured")
    fields = {"chat_id": settings.TELEGRAM_CHAT_ID, **fields}
    if attachment:
        boundary = "vlico" + uuid.uuid4().hex
        body = bytearray()
        for key, value in fields.items():
            body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="plan{attachment.file.name[attachment.file.name.rfind("."):]}"\r\nContent-Type: {attachment.content_type}\r\n\r\n'.encode())
        try:
            with attachment.file.open("rb") as source:
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


def message_parts(lead):
    quote = lead.calculation
    lines = ["VLICO · Новая заявка", f"ID: {lead.pk}", f"Время: {timezone.localtime(lead.created_at):%d.%m.%Y %H:%M}",
        f"Тип: {dict(KINDS).get(lead.kind, lead.kind)}", f"Имя: {lead.name}", f"Контакт: {lead.contact}"]
    for label, value in [("Услуга", lead.context.get("service_title")), ("Интерес", lead.context.get("interest")), ("Кейс", lead.context.get("project_title")), ("Пожелания", lead.comment)]:
        if value:
            lines.append(f"{label}: {value}")
    if quote:
        lines += ["", f"Предварительный расчёт: {quote['total']} ₽", f"Тарифы: {quote['version_title']} (#{quote['version']})"]
        lines += [f"{item['title']}: {item['quantity']} {item['unit']} × {item['unit_price']} ₽ = {item['total']} ₽" for item in quote["items"]]
        if not quote["complete"]:
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


def claim_delivery():
    now = timezone.now()
    with transaction.atomic():
        # A crashed process may have sent its request before recording the answer.
        Delivery.objects.filter(status="sending", locked_until__lt=now).update(status="failed", error_code="delivery_uncertain", lease_token=None, locked_until=None)
        item = Delivery.objects.select_for_update(skip_locked=True).filter(Q(next_attempt_at__lte=now) | Q(next_attempt_at__isnull=True), channel="telegram", status="pending", attempts__lt=MAX_ATTEMPTS).order_by("next_attempt_at", "pk").first()
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


def deliver_one():
    if not settings.TELEGRAM_DELIVERY_ENABLED:
        return False
    item = claim_delivery()
    if not item:
        return False
    progress = {"messages": list(item.progress.get("messages", [])), "files": list(item.progress.get("files", []))}
    try:
        lead = item.lead
        for text in message_parts(lead)[len(progress["messages"]):]:
            progress["messages"].append(api_call("sendMessage", {"text": text, "link_preview_options": {"is_disabled": True}}))
            checkpoint(item, progress)
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
