"""Reconcile WhatsApp outcomes and enqueue a single operator alert per form."""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .eva_delivery import EvaError, api
from .models import Delivery, EvaSyncJob

CHECK_INTERVAL = timedelta(minutes=2)
REVIEW_AFTER = timedelta(hours=1)
ALERT_CHANNEL = "email_outreach"


def timestamp(value):
    try:
        parsed = parse_datetime(value or "")
    except (TypeError, ValueError):
        return None
    return parsed if parsed and timezone.is_aware(parsed) else None


def observed_outcome(job):
    queue = api("GET", f"taskcontacts/{job.outreach_queue_id}", missing_ok=True)
    row = (queue or {}).get("data") or {}
    task_id = row.get("taskId")
    queue_time = timestamp(row.get("createdAt"))
    if (task_id != settings.EVA_SITE_OUTREACH_TASK_ID or row.get("contactId") != str(job.contact_id)
            or not queue_time):
        return None
    if row.get("status") == "queue":
        return None
    result = api("GET", f"conversations?taskId={task_id}&contactId={job.contact_id}&limit=10&sort=desc&sortColumn=createdAt")
    candidates = []
    for conversation in result.get("items") or []:
        created = timestamp(conversation.get("createdAt"))
        if (created and created >= queue_time and conversation.get("taskId") == task_id
                and conversation.get("contactId") == str(job.contact_id)
                and conversation.get("channelId") == settings.EVA_SITE_OUTREACH_CHANNEL_ID):
            candidates.append(conversation)
    for conversation in candidates:
        conversation_id = conversation["id"]
        messages = api("GET", f"messages?conversationId={conversation_id}&limit=20")
        for message in messages.get("items") or []:
            sent = timestamp(message.get("createdAt"))
            if (sent and sent >= queue_time and message.get("conversationId") == conversation_id
                    and message.get("senderType") == "assistant" and message.get("externalId")):
                return "sent", "", ""
    if row.get("status") == "error" or (len(candidates) == 1 and candidates[0].get("status") == "error"):
        return "failed", "outreach_send_error", "Eva сообщила об ошибке отправки в WhatsApp."
    return None


def monitor_one():
    if not settings.EVA_SYNC_ENABLED:
        return False
    now = timezone.now()
    with transaction.atomic():
        job = (EvaSyncJob.objects.select_for_update(skip_locked=True)
            .filter(status="sent", outreach_status__in=("queued", "review"), outreach_check_at__lte=now)
            .order_by("outreach_check_at", "pk").first())
        if not job:
            return False
        # Reserve the next check while allowing another worker to handle unrelated leads.
        lease = now + CHECK_INTERVAL
        job.outreach_check_at = lease
        job.save(update_fields=["outreach_check_at"])

    if job.outreach_status == "review":
        if job.outreach_error_code in ("write_uncertain", "unconfirmed_write"):
            reason = "Eva не подтвердила постановку сообщения в очередь. Результат неизвестен."
        else:
            reason = "Заявка сохранена, но поставить первое сообщение в очередь WhatsApp не удалось."
        outcome = "review", job.outreach_error_code, reason
    else:
        try:
            outcome = observed_outcome(job)
        except EvaError:
            outcome = None
        if outcome is None and job.sent_at <= now - REVIEW_AFTER:
            outcome = "review", "outreach_result_unknown", "За час Eva не подтвердила отправку WhatsApp. Результат неизвестен."
    if outcome is None:
        return True

    state, code, reason = outcome
    with transaction.atomic():
        changed = EvaSyncJob.objects.filter(pk=job.pk, outreach_check_at=lease,
            outreach_status=job.outreach_status).update(outreach_status=state, outreach_error_code=code, outreach_check_at=None)
        if changed and reason and job.lead.status == "new":
            Delivery.objects.get_or_create(lead_id=job.lead_id, channel=ALERT_CHANNEL, defaults={"progress": {
                "reason": reason, "eva_contact": str(job.contact_id), "eva_lead": str(job.remote_lead_id)}})
    return True
