"""Eva Dashboard API outbox; never called by the public submission request."""
from datetime import timedelta
import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import EvaSyncJob

MAX_ATTEMPTS = 5
LEASE_SECONDS = 180


class EvaError(Exception):
    def __init__(self, code, retry=False):
        self.code, self.retry = code, retry
        super().__init__(code)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(method, resource, data=None, *, missing_ok=False):
    request = Request("https://eva.bz/api/dashboard/" + resource,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Token": settings.EVA_API_KEY, "Content-Type": "application/json", "Accept": "application/json"}, method=method)
    try:
        with build_opener(NoRedirect).open(request, timeout=15) as response:
            raw = response.read(262145)
        if len(raw) > 262144:
            raise EvaError("invalid_response", True)
        result = json.loads(raw)
    except HTTPError as exc:
        code = exc.code
        exc.close()
        if code == 404 and missing_ok:
            return None
        raise EvaError(f"http_{code}", code == 429 or code >= 500) from None
    except (URLError, OSError, ValueError):
        raise EvaError("transport_or_response", True) from None
    if not isinstance(result, dict) or type(result.get("code")) is not int:
        raise EvaError("invalid_response", True)
    code = result["code"]
    if code == 404 and missing_ok:
        return None
    if code != 200:
        raise EvaError(f"eva_{code}", code == 429 or code >= 500)
    return result


def claim():
    now = timezone.now()
    with transaction.atomic():
        # A crashed worker may have completed a remote write: next run must reconcile.
        EvaSyncJob.objects.filter(status="sending", locked_until__lt=now, error_code="write_in_progress").update(
            status="review", lease_token=None, locked_until=None, error_code="write_uncertain")
        EvaSyncJob.objects.filter(status="sending", locked_until__lt=now).update(
            status="retry", lease_token=None, locked_until=None, error_code="lease_expired")
        EvaSyncJob.objects.filter(status="retry", attempts__gte=MAX_ATTEMPTS).update(status="review", error_code="attempts_exhausted")
        item = EvaSyncJob.objects.select_for_update(skip_locked=True).filter(
            Q(next_attempt_at__lte=now) | Q(next_attempt_at__isnull=True),
            status__in=["pending", "retry"], attempts__lt=MAX_ATTEMPTS).order_by("created_at", "pk").first()
        if item:
            item.status, item.lease_token = "sending", uuid.uuid4()
            item.attempts += 1
            item.locked_until = now + timedelta(seconds=LEASE_SECONDS)
            item.save()
        return item


def mapping(lead):
    prefix = "EVA_PARTNER_" if lead.kind == "partner" else "EVA_"
    fields = {key: getattr(settings, prefix + name) for key, name in
        (("funnelId", "FUNNEL_ID"), ("statusId", "STATUS_ID"), ("userId", "EXECUTOR_ID"))}
    try:
        for value in fields.values():
            uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise EvaError("mapping_not_configured") from None
    return fields


def ensure_record(resource, record_id, fields, ownership, checkpoint=None, before_create=None):
    existing = api("GET", f"{resource}/{record_id}", missing_ok=True)
    if existing is None:
        if before_create:
            before_create()
        try:
            created = api("POST", resource, {"data": {str(record_id): fields}, "skipNotifications": True})
        except EvaError as exc:
            if exc.retry:
                raise EvaError("write_uncertain") from None
            raise
        items = created.get("items")
        if items is None:
            items = created.get("data", {}).get("items", []) if isinstance(created.get("data"), dict) else []
        if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
            raise EvaError("write_uncertain")
        try:
            record_id = uuid.UUID(items[0]["id"])
        except (ValueError, KeyError, TypeError):
            raise EvaError("write_uncertain") from None
        if checkpoint:
            checkpoint(record_id)
        existing = api("GET", f"{resource}/{record_id}", missing_ok=True)
    record = existing.get("data") if isinstance(existing, dict) else None
    if not isinstance(record, dict) or record.get("id") != str(record_id):
        raise EvaError("unconfirmed_write", True)
    if any(record.get(key) != value for key, value in ownership.items()):
        raise EvaError("remote_identity_conflict")
    return record


def deliver_eva_one():
    if not settings.EVA_SYNC_ENABLED:
        return False
    item = claim()
    if item is None:
        return False
    try:
        if not settings.EVA_API_KEY:
            raise EvaError("key_not_configured")
        lead = item.lead
        target = mapping(lead)
        reference = "vlico:" + str(lead.pk)
        def remember(field, value):
            changes = {field: value}
            if field != "error_code":
                changes["error_code"] = ""
            changed = EvaSyncJob.objects.filter(pk=item.pk, status="sending", lease_token=item.lease_token).update(**changes)
            if changed != 1:
                raise EvaError("write_uncertain")
            setattr(item, field, value)
        props = {"localleaduuid": str(lead.pk), "leadkind": lead.kind,
            "sourcepage": lead.source_page, "source": "site_form",
            **{key.replace("_", ""): value for key, value in lead.attribution.items()}}
        contact = {"name": lead.name, "externalId": reference, "props": props}
        if lead.contact.startswith("@"):
            props["telegram_username"] = lead.contact
        elif "@" in lead.contact:
            contact["email"] = lead.contact
        else:
            contact["phone"] = lead.contact
        ensure_record("contacts", item.contact_id, contact, {"externalId": reference}, lambda value: remember("contact_id", value), lambda: remember("error_code", "write_in_progress"))
        # Existing calculator snapshots are preserved; never recalculate historical quotes.
        description = json.dumps({"kind": lead.kind, "contact": lead.contact, "comment": lead.comment,
            "context": {key: value for key, value in lead.context.items() if key != "consent"},
            "calculation": lead.calculation, "source_page": lead.source_page, "attribution": lead.attribution}, ensure_ascii=False)
        fields = {**target, "contactId": str(item.contact_id), "description": description,
            "props": props}
        ensure_record("leads", item.remote_lead_id, fields, {"contactId": str(item.contact_id)}, lambda value: remember("remote_lead_id", value), lambda: remember("error_code", "write_in_progress"))
    except EvaError as exc:
        retry = exc.retry and item.attempts < MAX_ATTEMPTS
        state = "retry" if retry else "review" if exc.retry or exc.code in {"remote_identity_conflict", "write_uncertain"} else "blocked"
        changes = {"status": state, "error_code": exc.code,
            "next_attempt_at": timezone.now() + timedelta(seconds=(30, 120, 600, 1800, 3600)[item.attempts - 1])}
    else:
        changes = {"status": "sent", "error_code": "", "sent_at": timezone.now(), "next_attempt_at": None}
    EvaSyncJob.objects.filter(pk=item.pk, status="sending", lease_token=item.lease_token).update(
        **changes, lease_token=None, locked_until=None, updated_at=timezone.now())
    return True
