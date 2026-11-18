"""Consent-gated, rate-limited partnership dispatch and reporting."""
from datetime import datetime, time, timedelta
import hashlib
import json
import re

from django.conf import settings
from django.db import connection, transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone

from .eva_delivery import EvaError
from .eva_partner_campaign import (
    api, records, record, update, cancel, task_rows, read_history, delivered, timestamp,
    ensure_lead, active_lead, move, KALININGRAD, OPT_OUT, NEW, OFFER, SILENT, INTEREST, REFUSED,
)
from .models import EvaPartnerCampaign, EvaPartnerSend, EvaPartnerEvent, EvaPartnerReport
from .partner_content import first_message, FOLLOWUP


def business_day_after(sent, days):
    value = sent.astimezone(KALININGRAD)
    for _ in range(days):
        value += timedelta(days=1)
        while value.weekday() >= 5:
            value += timedelta(days=1)
    return value


def working(now):
    local = now.astimezone(KALININGRAD)
    return local.weekday() < 5 and 10 <= local.hour < 18


def configuration():
    try:
        data = json.loads(settings.EVA_PARTNER_SEND_TASKS)
        if set(data) != {"whatsapp", "telegram"} or any(len(value) != 2 for value in data.values()):
            raise ValueError()
        if len({str(item) for values in data.values() for item in values}) != 4:
            raise ValueError()
    except (ValueError, TypeError):
        raise EvaError("partner_dispatch_not_configured") from None
    return data


def eligible(contact, channel):
    props = contact.get("props") or {}
    permitted = {v.strip().casefold() for v in str(props.get("partnerconsentchannels") or "").split(",")}
    return (
        props.get("partnerchecked") is True and props.get("partnerconsent") is True
        and bool(props.get("contactpermissionbasis")) and bool(props.get("partnerconsentat"))
        and channel in permitted and not props.get("optout") and not props.get("testrecord")
        and bool(props.get("partnersegment")) and props.get("partnerchannel") == channel
    )


def identity(contact):
    phone = re.sub(r"\D", "", contact.get("phone") or "")
    if len(phone) == 11 and phone.startswith("8"):
        phone = "7" + phone[1:]
    key = phone or (contact.get("email") or "").strip().casefold() or (
        (contact.get("props") or {}).get("telegramusername") or str(contact["id"]))
    return hashlib.sha256(key.encode()).hexdigest()


def event(key, kind, when, contact_id=None, channel="", **details):
    EvaPartnerEvent.objects.get_or_create(key=key, defaults={
        "kind": kind, "occurred_at": when, "contact_id": contact_id,
        "channel_type": channel, "details": details,
    })


def remaining_capacity(channel, now):
    today = now.astimezone(KALININGRAD).date()
    start = timezone.make_aware(datetime.combine(today, time()), KALININGRAD)
    # Pending or ambiguous submissions from earlier days consume a place until reconciled.
    used = EvaPartnerSend.objects.filter(channel_type=channel).filter(
        Q(reserved_day=today) | Q(sent_at__gte=start, sent_at__lt=start + timedelta(days=1))
        | Q(status__in=("reserved", "submitting", "queued", "review")),
    ).exclude(status="cancelled", sent_at__isnull=True).count()
    return max(0, 20 - used)


def reserve(contact, channel, task, step, now):
    if step not in (0, 1) or not working(now) or not remaining_capacity(channel, now):
        return None
    try:
        with transaction.atomic():
            return EvaPartnerSend.objects.create(
                contact_id=contact["id"], identity=identity(contact), channel_type=channel,
                channel_id=task["channels"][0], task_id=task["id"], step=step,
                reserved_day=now.astimezone(KALININGRAD).date(),
            )
    except IntegrityError:
        return None


def submit(send, contact, now):
    fresh = record("contacts", str(send.contact_id))
    if not fresh or not eligible(fresh, send.channel_type):
        send.status = "cancelled"
        send.save(update_fields=["status"])
        return
    # Check all Victoria conversations immediately before an unsolicited follow-up.
    if send.step:
        original = EvaPartnerSend.objects.get(contact_id=send.contact_id, step=0)
        history = read_history(str(send.contact_id), settings.EVA_PARTNER_EXECUTOR_ID, original.created_at)
        if any(m.get("senderType") == "user" for _, messages in history for _, m in messages):
            send.status = "cancelled"
            send.save(update_fields=["status"])
            return
    content = FOLLOWUP if send.step else first_message(fresh.get("props") or {}, send.channel_type)
    send.status = "submitting"
    send.save(update_fields=["status"])
    try:
        response = api("POST", "taskcontacts", {"data": {str(send.request_id): {
            "taskId": str(send.task_id), "contactId": str(send.contact_id), "status": "queue",
            "prompt": f"Отправь дословно одно сообщение. Не добавляй приветствий или вопросов. Текст сообщения:\n{content}",
        }}})
        items = response.get("items") or []
        if len(items) != 1 or items[0].get("contactId") != str(send.contact_id):
            raise EvaError("partner_queue_unconfirmed")
        send.queue_id, send.status = items[0]["id"], "queued"
    except EvaError as exc:
        send.status, send.error_code = "review", exc.code
    send.save(update_fields=["queue_id", "status", "error_code"])


def submit_if_running(send, contact, now):
    # Pause takes the same lock. An already accepted request finishes before
    # pause cancels queues, so it cannot appear afterwards as a new submission.
    with transaction.atomic():
        policy = EvaPartnerCampaign.objects.select_for_update().get(pk=1)
        if policy.enabled:
            submit(send, contact, now)
        else:
            send.status = "cancelled"
            send.save(update_fields=["status"])


def reconcile(send, statuses, now):
    contact_id = str(send.contact_id)
    contact = record("contacts", contact_id)
    if contact is None:
        return
    first = EvaPartnerSend.objects.filter(contact_id=send.contact_id, step=0).first()
    since = first.created_at if first else send.created_at
    history = read_history(contact_id, settings.EVA_PARTNER_EXECUTOR_ID, since)
    incoming = [(when, m) for _, messages in history for when, m in messages
                if m.get("senderType") == "user" and m.get("contactId") == contact_id]
    forbidden = (contact.get("props") or {}).get("optout") or any(
        OPT_OUT.fullmatch((m.get("text") or "").strip()) for _, m in incoming
    )
    row = record("taskcontacts", str(send.queue_id)) if send.queue_id else None
    if send.status in ("submitting", "review") and row is None:
        found = [r for r in task_rows(str(send.task_id)) if r.get("contactId") == contact_id
                 and (timestamp(r.get("createdAt")) or now) >= send.created_at]
        if len(found) == 1:
            row = found[0]
            send.queue_id = row["id"]
            send.save(update_fields=["queue_id"])
    sent = delivered(row, history) if row else None
    if sent and not send.sent_at:
        send.sent_at, send.status = sent[0], "sent"
        send.save(update_fields=["sent_at", "status"])
        event(f"sent:{send.pk}", "sent", sent[0], send.contact_id, send.channel_type, step=send.step)
        ensure_lead(contact_id, settings.EVA_PARTNER_EXECUTOR_ID, settings.EVA_PARTNER_FUNNEL_ID, statuses[NEW])
    lead = active_lead(contact_id, settings.EVA_PARTNER_EXECUTOR_ID)
    if lead and lead.get("funnelId") != settings.EVA_PARTNER_FUNNEL_ID:
        return
    if forbidden:
        update("contacts", contact_id, props={"optout": True})
    if incoming or forbidden:
        if row and row.get("status") == "queue":
            cancel([row])
            send.status = "cancelled"
            send.save(update_fields=["status"])
        for when, message in incoming:
            event("reply:" + message["id"], "reply", when, send.contact_id, send.channel_type)
        if forbidden and lead:
            move(lead, statuses, (NEW, OFFER, "Ответ", SILENT, INTEREST), REFUSED)
        if send.sent_at:
            send.status = "answered" if incoming and not forbidden else "cancelled"
            send.save(update_fields=["status"])
        return
    if row and row.get("status") == "error" and not sent:
        send.status, send.error_code = "error", "provider_error"
        send.save(update_fields=["status", "error_code"])
        event(f"error:{send.pk}", "error", now, send.contact_id, send.channel_type)
        if lead:
            update("leads", lead["id"], props={"nextaction": "Ошибка исходящего сообщения. Проверить историю и связаться вручную."})
        return
    if lead and send.step == 0 and sent:
        move(lead, statuses, (NEW,), OFFER)
    if row and row.get("status") == "complete" and not sent:
        completed = timestamp(row.get("completeAt"))
        if completed and now >= completed + timedelta(hours=1):
            send.status, send.error_code = "review", "message_unconfirmed"
            send.save(update_fields=["status", "error_code"])
    if lead and send.step == 1 and send.sent_at and now >= business_day_after(send.sent_at, 5):
        move(lead, statuses, (OFFER,), SILENT)
        send.status = "closed"
        send.save(update_fields=["status"])


def capture_statuses(statuses, now):
    for lead in records("leads", funnelId=settings.EVA_PARTNER_FUNNEL_ID, archive="false"):
        if lead.get("funnelId") != settings.EVA_PARTNER_FUNNEL_ID:
            continue
        title = next((n for n, value in statuses.items() if value == lead.get("statusId")), "")
        kind = {
            INTEREST: "interest", "Переговоры": "negotiation", "Первый объект": "project",
            "Активный партнёр": "partner", REFUSED: "refusal",
        }.get(title)
        entered = timestamp(lead.get("enteredAt"))
        if kind and entered:
            event(f"stage:{lead['id']}:{lead['statusId']}:{entered.isoformat()}", kind,
                  entered, lead["contactId"])
        assigned = {item.get("id") if isinstance(item, dict) else item for item in lead.get("users", [])}
        if title == INTEREST and entered and settings.EVA_RESPONSIBLE_ID in assigned:
            event(f"handoff:{lead['id']}:{entered.isoformat()}", "handoff", entered, lead["contactId"])
        props = (lead.get("contact") or {}).get("props") or {}
        for key, metric in (("partnerproject", "project_request"), ("partnercomplaint", "complaint")):
            if props.get(key) and entered:
                event(f"flag:{lead['id']}:{key}", metric, entered, lead["contactId"])


def capture_checks():
    for contact in records("contacts", page_size=50):
        props = contact.get("props") or {}
        if props.get("partnerchecked") is not True:
            continue
        raw = str(props.get("partnercheckedat") or "")
        checked = timestamp(raw)
        if len(raw) == 10:
            try:
                checked = timezone.make_aware(datetime.fromisoformat(raw), KALININGRAD)
            except ValueError:
                checked = None
        if checked:
            event(f"checked:{contact['id']}", "checked", checked, contact["id"])


def refresh_reports(now):
    local = now.astimezone(KALININGRAD)
    daily = local.date() if local.hour >= 18 else local.date() - timedelta(days=1)
    monday = local.date() - timedelta(days=local.weekday())
    for period, day, days in (("daily", daily, 1), ("weekly", monday - timedelta(days=7), 7)):
        start = timezone.make_aware(datetime.combine(day, time()), KALININGRAD)
        metrics = {}
        items = EvaPartnerEvent.objects.filter(occurred_at__gte=start, occurred_at__lt=start + timedelta(days=days))
        for kind in ("checked", "sent", "reply", "interest", "project_request", "handoff",
                     "refusal", "complaint", "negotiation", "project", "partner", "click", "error"):
            subset = items.filter(kind=kind)
            metrics[kind] = subset.values("contact_id").distinct().count() if kind in {
                "checked", "reply", "interest", "handoff", "refusal", "project_request", "project", "partner",
            } else subset.count()
        metrics["sent_whatsapp"] = items.filter(kind="sent", channel_type="whatsapp").count()
        metrics["sent_telegram"] = items.filter(kind="sent", channel_type="telegram").count()
        metrics["delivered"] = None  # Provider acceptance does not establish delivery to the device.
        EvaPartnerReport.objects.update_or_create(period=period, day=day, defaults={"metrics": metrics})


def sync():
    if not settings.EVA_SYNC_ENABLED or not settings.EVA_PARTNER_INTAKE_TASK_ID:
        return 0
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(665138271)")
        if not cursor.fetchone()[0]:
            return 0
        try:
            return sync_locked(timezone.now())
        finally:
            cursor.execute("SELECT pg_advisory_unlock(665138271)")


def sync_locked(now):
    mapping = configuration()
    statuses = {s["title"]: s["id"] for s in records("funnelstatuses", funnelId=settings.EVA_PARTNER_FUNNEL_ID)}
    if not {NEW, OFFER, INTEREST, SILENT, REFUSED} <= statuses.keys():
        raise EvaError("partner_stages_invalid")
    # Reconcile active submissions regardless of launch state, so replies still cancel pending sends.
    for send in EvaPartnerSend.objects.exclude(status__in=("error", "cancelled", "answered", "closed")).filter(
        created_at__gte=now - timedelta(days=45), check_at__lte=now,
    ).order_by("check_at")[:20]:
        reconcile(send, statuses, now)
        next_check = now + timedelta(minutes=2)
        if send.status == "sent" and send.sent_at:
            due = business_day_after(send.sent_at, 3 if send.step == 0 else 5)
            next_check = max(now + timedelta(minutes=15), due)
        EvaPartnerSend.objects.filter(pk=send.pk).update(check_at=next_check)
    policy, _ = EvaPartnerCampaign.objects.get_or_create(pk=1)
    if not policy.next_scan_at or policy.next_scan_at <= now:
        capture_statuses(statuses, now)
        capture_checks()
        policy.next_scan_at = now + timedelta(minutes=15)
        policy.save(update_fields=["next_scan_at"])
    refresh_reports(now)
    if not policy.enabled or not working(now):
        return 0
    intake = record("tasks", settings.EVA_PARTNER_INTAKE_TASK_ID)
    if not intake or intake.get("enabled") or intake.get("channels"):
        raise EvaError("partner_intake_must_stay_disabled")
    candidates = task_rows(settings.EVA_PARTNER_INTAKE_TASK_ID)
    count = 0
    for channel, ids in mapping.items():
        if not remaining_capacity(channel, now):
            continue
        # Keep only one in-flight submission per channel to avoid unattended backlog.
        if EvaPartnerSend.objects.filter(channel_type=channel, status__in=("reserved", "submitting", "queued", "review")).exists():
            continue
        tasks = [record("tasks", value) for value in ids]
        if any(not t or not t.get("enabled") or t.get("autoSyncContacts") or t.get("funnelStatusId")
               or len(t.get("channels") or []) != 1 or t.get("repeatDays") or t.get("followUpIn") for t in tasks):
            continue
        if tasks[0]["channels"] != tasks[1]["channels"]:
            raise EvaError("partner_channel_pair_mismatch")
        if not tasks[0].get("scheduleId") or tasks[1].get("scheduleId") != tasks[0]["scheduleId"]:
            raise EvaError("partner_schedule_missing")
        connected = record("channels", tasks[0]["channels"][0])
        expected_type = "whatsApp" if channel == "whatsapp" else "telegram"
        if not connected or connected.get("type") != expected_type or connected.get("userId") != settings.EVA_PARTNER_EXECUTOR_ID:
            continue
        if connected.get("enabledMode") != "enabled" or connected.get("status") != "online":
            continue
        source_ids = {row["contactId"] for row in candidates if row.get("status") == "queue"}
        originals = EvaPartnerSend.objects.filter(channel_type=channel, step=0, status="sent", contact_id__in=source_ids)
        due = next((s for s in originals if s.sent_at and now >= business_day_after(s.sent_at, 3)
                    and not EvaPartnerSend.objects.filter(contact_id=s.contact_id, step=1).exists()), None)
        if due:
            contact = record("contacts", str(due.contact_id))
            lead = active_lead(str(due.contact_id), settings.EVA_PARTNER_EXECUTOR_ID)
            history = read_history(str(due.contact_id), settings.EVA_PARTNER_EXECUTOR_ID, due.created_at)
            if (contact and eligible(contact, channel) and lead and lead.get("statusId") == statuses[OFFER]
                    and not any(m.get("senderType") == "user" for _, messages in history for _, m in messages)):
                send = reserve(contact, channel, tasks[1], 1, now)
                if send:
                    submit_if_running(send, contact, now)
                    count += 1
                    continue
        for candidate in candidates:
            if candidate.get("status") != "queue" or EvaPartnerSend.objects.filter(contact_id=candidate["contactId"]).exists():
                continue
            contact = record("contacts", candidate["contactId"])
            if not contact or not eligible(contact, channel):
                continue
            send = reserve(contact, channel, tasks[0], 0, now)
            if send:
                event(f"checked:{contact['id']}", "checked", now, contact["id"], channel)
                submit_if_running(send, contact, now)
                count += 1
                break
    return count
