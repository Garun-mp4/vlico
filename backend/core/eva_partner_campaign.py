"""Reconcile Victoria's explicit campaign recipients with their Eva leads."""
from datetime import timedelta
import logging
import re
import uuid
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.db import connection
from django.utils import timezone

from .eva_delivery import EvaError, api
from .eva_outreach_monitor import timestamp
from .models import EvaPartnerCampaignRun


LOG = logging.getLogger(__name__)
KALININGRAD = ZoneInfo("Europe/Kaliningrad")
ACTIVE_DELAY = timedelta(minutes=2)
ANSWERED_DELAY = timedelta(minutes=15)
ANSWERED_WINDOW = timedelta(days=21)
REVIEW_DELAY = timedelta(hours=1)
NEW = "Новый контакт"
OFFER = "Предложение отправлено"
SILENT = "Нет ответа"
INTEREST = "Заинтересован"
NEGOTIATIONS = "Переговоры"
REFUSED = "Отказ / Запрет сообщений"
ANSWER = "Ответ"
OPT_OUT = re.compile(
    r"^(?:(?:здравствуйте|добрый день|спасибо)[,!.\s]+)?"
    r"(?:пожалуйста[,]?\s+)?(?:больше не пишите|не пишите (?:мне|нам|больше)|"
    r"прекратите (?:мне |нам )?писать|удалите (?:меня|мой номер|наш номер) из "
    r"(?:вашей )?(?:базы|рассылки)|отпишите (?:меня|нас)|стоп)[,!.\s]*$",
    re.IGNORECASE,
)


def uuid_value(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError):
        raise EvaError("partner_mapping_invalid") from None


def records(resource, **query):
    offset = 0
    while True:
        result = api("GET", resource + "?" + urlencode({
            **query, "limit": 5 if resource == "messages" else 25, "offset": offset,
            "sort": "asc", "sortColumn": "createdAt",
        }))
        rows = result.get("items")
        if not isinstance(rows, list):
            raise EvaError("partner_invalid_list", True)
        yield from rows
        offset += len(rows)
        if not rows or offset >= result["total"]:
            return


def record(resource, record_id):
    response = api("GET", f"{resource}/{uuid_value(record_id)}", missing_ok=True)
    return response["data"] if response else None


def update(resource, record_id, **fields):
    api("PUT", resource, {"append": True, "data": {uuid_value(record_id): fields}})


def task_rows(task_id):
    return [row for row in records("taskcontacts", taskId=task_id) if row.get("taskId") == task_id]


def active_lead(contact_id, executor):
    return next((row for row in records("leads", contactId=contact_id, userId=executor, archive="false")
                 if row.get("contactId") == contact_id and row.get("userId") == executor
                 and row.get("archive") is False), None)


def ensure_lead(contact_id, executor, funnel, new_status):
    current = active_lead(contact_id, executor)
    if current is None:
        # Eva permits one active lead per contact and executor. After an ambiguous
        # create, the next pass starts by looking up that same natural key.
        requested_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"vlico:victoria:{contact_id}"))
        try:
            api("POST", "leads", {"skipNotifications": True, "data": {requested_id: {
                "funnelId": funnel, "statusId": new_status, "userId": executor, "contactId": contact_id,
            }}})
        except EvaError as exc:
            if exc.code != "existing_contact_lead":
                raise
        current = active_lead(contact_id, executor)
        if current is None:
            raise EvaError("partner_unconfirmed_lead", True)
    return current if current.get("funnelId") == funnel else None


def move(lead, statuses, sources, target, **props):
    current = record("leads", lead["id"])
    if (current and current.get("archive") is False and current.get("funnelId") == lead["funnelId"]
            and current.get("statusId") in {statuses[source] for source in sources}):
        fields = {}
        if current["statusId"] != statuses[target]:
            fields["statusId"] = statuses[target]
        if props:
            saved = current.get("props") or {}
            if any(saved.get(key) != value for key, value in props.items()):
                fields["props"] = props
        if fields:
            update("leads", lead["id"], **fields)
        return True
    return False


def silence_deadline(sent):
    local = sent.astimezone(KALININGRAD)
    for _ in range(5):
        local += timedelta(days=1)
        while local.weekday() >= 5:
            local += timedelta(days=1)
    return local


def read_history(contact_id, executor, started):
    conversations = []
    for chat in records("conversations", contactId=contact_id, userId=executor):
        if (chat.get("contactId") != contact_id or chat.get("userId") != executor
                or chat.get("isSupportChat") or chat.get("groupId")):
            continue
        activity = timestamp(chat.get("lastMessageAt")) or timestamp(chat.get("createdAt"))
        if activity is None or activity >= started:
            messages = [
                (when, message) for message in records("messages", conversationId=chat["id"])
                if message.get("conversationId") == chat["id"]
                and (when := timestamp(message.get("createdAt"))) and when >= started
            ]
            conversations.append((chat, messages))
    return conversations


def delivered(row, history):
    started = timestamp(row.get("createdAt"))
    if not started:
        return None
    matching = [
        (when, chat) for chat, messages in history
        if chat.get("taskId") == row["taskId"]
        and (timestamp(chat.get("createdAt")) or started - timedelta(seconds=1)) >= started
        for when, message in messages
        if when >= started and message.get("senderType") == "assistant" and message.get("externalId")
    ]
    return min(matching, key=lambda item: item[0], default=None)


def send_error(row, history, now):
    started = timestamp(row.get("createdAt"))
    if row.get("status") == "error" or any(
        chat.get("taskId") == row["taskId"] and chat.get("status") == "error"
        and started and (timestamp(chat.get("createdAt")) or now) >= started for chat, _ in history
    ):
        return "Eva зафиксировала ошибку отправки."
    completed = timestamp(row.get("completeAt"))
    if completed and completed <= now - REVIEW_DELAY:
        return "Eva завершила задачу без подтверждённого сообщения. Проверьте историю перед повторной отправкой."
    return None


def cancel(rows):
    ids = []
    for row in rows:
        if row.get("status") != "queue":
            continue
        current = record("taskcontacts", row["id"])
        if (current and current.get("status") == "queue"
                and current.get("taskId") == row["taskId"] and current.get("contactId") == row["contactId"]):
            ids.append(uuid_value(row["id"]))
    if ids:
        api("POST", "taskcontacts/delete", {"ids": ids})


def notify_failure(run, lead, reason):
    if run.alert_status:
        return True
    if not settings.EMAIL_DELIVERY_ENABLED or not settings.PARTNER_NOTIFICATION_EMAIL:
        return False
    mail = get_connection(fail_silently=False)
    try:
        # A connection failure is safe to retry. After send begins the result
        # can be uncertain, so do not automatically duplicate the message.
        mail.open()
    except OSError:
        LOG.warning("Eva partner alert SMTP connection failed")
        return False
    try:
        if EvaPartnerCampaignRun.objects.filter(pk=run.pk, alert_status="").update(alert_status="sending"):
            link = "https://eva.bz/leads"
            if lead is None:
                link = "https://eva.bz/contacts/" + str(run.contact_id)
            mail_status = "review"
            try:
                message = EmailMessage(
                    subject="VLICO — проверьте отправку Виктории",
                    body=f"{reason}\nКонтакт в Eva: https://eva.bz/contacts/{run.contact_id}\nВоронка: {link}",
                    from_email=settings.DEFAULT_FROM_EMAIL, to=[settings.PARTNER_NOTIFICATION_EMAIL],
                )
                if mail.send_messages([message]) == 1:
                    mail_status = "sent"
            except OSError:
                LOG.warning("Eva partner alert delivery is uncertain")
            finally:
                EvaPartnerCampaignRun.objects.filter(pk=run.pk, alert_status="sending").update(alert_status=mail_status)
    finally:
        mail.close()
    return True


def enqueue_followup(run, task_ids, progress, lead, executor, statuses, started, now):
    step = len(progress)
    if step not in (1, 2) or not all(progress):
        return None
    when, chat = progress[-1]
    due = when + timedelta(days=3 if step == 1 else 5)
    if now < due:
        return due
    if run.submitted_step >= step:
        if run.submitted_at and now >= run.submitted_at + REVIEW_DELAY:
            return "Eva не подтвердила постановку повторного касания. Проверьте очередь и историю."
        return None
    task_id = task_ids[step]
    first = record("tasks", task_ids[0])
    task = record("tasks", task_id)
    channel_id = chat.get("channelId")
    if not first or not first.get("enabled") or not task or not task.get("enabled") or not channel_id:
        return None
    if (any(a.get("userId") != executor or a.get("channels") != [channel_id]
            or a.get("autoSyncContacts") is not False or a.get("funnelStatusId")
            or a.get("followUpIn") or a.get("repeatDays") for a in (first, task))
            or any(True for _ in records("taskconditions", taskId=task_id))):
        raise EvaError("partner_followup_task_not_isolated")
    channel = next((row for row in records("channels", userId=executor)
                    if row.get("id") == channel_id and row.get("userId") == executor), None)
    if not channel or channel.get("status") != "online" or channel.get("enabledMode") != "enabled":
        return None
    if channel.get("type") not in {"whatsApp", "telegram"}:
        raise EvaError("partner_followup_channel_invalid")
    contact_id = str(run.contact_id)
    if any(row.get("contactId") == contact_id for row in task_rows(task_id)):
        return None
    contact = record("contacts", contact_id)
    current = active_lead(contact_id, executor)
    if (not contact or (contact.get("props") or {}).get("optout") or not current
            or current.get("id") != lead["id"] or current.get("statusId") != statuses[OFFER]):
        return None
    if any(message.get("senderType") == "user" and message.get("contactId") == contact_id
           for _, messages in read_history(contact_id, executor, started) for _, message in messages):
        return None
    # Eva may accept a write before the response is lost. Mark the attempt
    # first and reconcile the actual remote queue on the next pass.
    if not EvaPartnerCampaignRun.objects.filter(pk=run.pk, submitted_step__lt=step).update(
        submitted_step=step, submitted_at=now,
    ):
        return None
    request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"vlico:victoria:{run.pk}:{step}"))
    api("POST", "taskcontacts", {"data": {request_id: {
        "taskId": task_id, "contactId": contact_id, "status": "queue",
    }}})
    return None


def reconcile(run, rows, executor, funnel, statuses, now, task_ids=()):
    first = rows[0]
    contact_id = str(run.contact_id)
    contact = record("contacts", contact_id)
    if contact is None:
        cancel(rows)
        return None
    lead = active_lead(contact_id, executor)
    if lead and lead.get("funnelId") != funnel:
        cancel(rows)
        return None
    started = timestamp(first.get("createdAt"))
    if not started:
        raise EvaError("partner_missing_queue_timestamp", True)
    history = read_history(contact_id, executor, started)
    incoming = [(when, message) for _, messages in history for when, message in messages
                if message.get("senderType") == "user" and message.get("contactId") == contact_id]
    opt_out = (contact.get("props") or {}).get("optout") is True or any(
        OPT_OUT.fullmatch((message.get("text") or "").strip()) for _, message in incoming
    )
    if opt_out:
        if not (contact.get("props") or {}).get("optout"):
            update("contacts", contact_id, props={"optout": True})
        cancel(rows)
        if lead:
            move(lead, statuses, (NEW, OFFER, SILENT, ANSWER, INTEREST), REFUSED,
                 nextaction="Запрет исходящих сообщений. Отменить запланированные обращения.")
        return None
    progress = [delivered(row, history) for row in rows]
    if progress[0] and lead is None:
        lead = ensure_lead(contact_id, executor, funnel, statuses[NEW])
    if incoming:
        # A response cancels outstanding sequence messages immediately, even if
        # Eva's dialogue classifier has yet to move the card.
        cancel(rows)
        return now + ANSWERED_DELAY if now < started + ANSWERED_WINDOW else None
    if lead and lead.get("statusId") not in {statuses[NEW], statuses[OFFER]}:
        cancel(rows[1:])
        return None
    if progress[0] and lead and lead.get("statusId") == statuses[NEW]:
        when, chat = progress[0]
        move(lead, statuses, (NEW,), OFFER, partnerofferat=when.isoformat(),
             partnerofferchannel=chat.get("channelId"),
             nextaction="Ожидать ответ партнёра в исходном канале.")
    for row, result in zip(rows, progress):
        if result:
            continue
        reason = send_error(row, history, now)
        if reason:
            cancel(rows[1:])
            lead = lead or ensure_lead(contact_id, executor, funnel, statuses[NEW])
            if lead:
                stage = OFFER if progress[0] else NEW
                move(lead, statuses, (stage,), stage, nextaction=reason)
            return None if notify_failure(run, lead, reason) else now + REVIEW_DELAY
    if len(rows) == 3 and all(progress) and progress[0][0] < progress[1][0] < progress[2][0] and lead:
        deadline = silence_deadline(progress[2][0])
        if now >= deadline:
            move(lead, statuses, (OFFER,), SILENT,
                 nextaction="Цепочка закончена. При позднем ответе обработать его в исходном чате.")
            return None
        return min(deadline, now + ACTIVE_DELAY)
    if task_ids and lead and [row["taskId"] for row in rows] == list(task_ids[:len(rows)]):
        next_action = enqueue_followup(run, task_ids, progress, lead, executor, statuses, started, now)
        if isinstance(next_action, str):
            move(lead, statuses, (OFFER,), OFFER, nextaction=next_action)
            return None if notify_failure(run, lead, next_action) else now + REVIEW_DELAY
        if next_action:
            return min(next_action, now + ACTIVE_DELAY)
    return now + ACTIVE_DELAY


def pause_for_owner(history, owner, since):
    if not since:
        return
    for chat, messages in history:
        if chat.get("status") not in ("initial", "inProcess", "complete"):
            continue
        if any(when >= since and m.get("senderType") == "manager" and m.get("userId") == owner
               for when, m in messages):
            fresh = record("conversations", chat["id"])
            if fresh and fresh.get("status") in ("initial", "inProcess", "complete"):
                update("conversations", chat["id"], status="disabled")


def check_handoffs(statuses, executor, funnel, owner, now):
    if not owner:
        return
    for status in (INTEREST, NEGOTIATIONS):
        for lead in records("leads", userId=executor, funnelId=funnel, statusId=statuses[status], archive="false"):
            last = lead.get("lastMessage") or {}
            updated = max(filter(None, (timestamp(lead.get("updatedAt")), timestamp(last.get("createdAt")))),
                          default=None)
            if (lead.get("funnelId") != funnel or lead.get("userId") != executor
                    or lead.get("statusId") != statuses[status] or not updated or updated < now - timedelta(days=2)
                    or not (last.get("userId") == owner or last.get("contactId") == lead.get("contactId"))):
                continue
            since = timestamp(lead.get("enteredAt"))
            if since:
                if status == NEGOTIATIONS:
                    since = max(since - timedelta(days=1), now - timedelta(days=2))
                pause_for_owner(read_history(lead["contactId"], executor, since), owner, since)


def sync():
    ids = settings.EVA_PARTNER_CAMPAIGN_TASKS
    if not ids or not settings.EVA_SYNC_ENABLED:
        return 0
    if len(ids) != 3 or len(set(ids)) != 3:
        raise EvaError("partner_campaign_requires_three_tasks")
    ids = tuple(map(uuid_value, ids))
    executor = uuid_value(settings.EVA_PARTNER_EXECUTOR_ID)
    funnel = uuid_value(settings.EVA_PARTNER_FUNNEL_ID)
    owner = settings.EVA_RESPONSIBLE_ID
    now = timezone.now()
    # SpaceWeb may start another cron invocation before this one finishes.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(665138271)")
        if not cursor.fetchone()[0]:
            return 0
        try:
            return sync_locked(ids, executor, funnel, owner, now)
        finally:
            cursor.execute("SELECT pg_advisory_unlock(665138271)")


def sync_locked(ids, executor, funnel, owner, now):
    queues = [task_rows(task_id) for task_id in ids]
    statuses = {stage["title"]: stage["id"] for stage in records("funnelstatuses", funnelId=funnel)
                if stage.get("funnelId") == funnel}
    if not {NEW, OFFER, SILENT, ANSWER, INTEREST, NEGOTIATIONS, REFUSED} <= statuses.keys():
        raise EvaError("partner_status_mapping_invalid")
    try:
        check_handoffs(statuses, executor, funnel, owner, now)
    except EvaError as exc:
        LOG.warning("Eva partner handoff check failed: %s", exc.code)
    if not any(queues):
        return 0
    first_by_id = {uuid_value(row["id"]): row for row in queues[0]}
    known = EvaPartnerCampaignRun.objects.in_bulk(first_by_id)
    EvaPartnerCampaignRun.objects.bulk_create([
        EvaPartnerCampaignRun(queue_id=row_id, contact_id=uuid_value(row["contactId"]), check_at=now)
        for row_id, row in first_by_id.items() if uuid.UUID(row_id) not in known
    ], ignore_conflicts=True)
    repeat_by_contact = {}
    for queue in queues[1:]:
        for row in queue:
            repeat_by_contact.setdefault(row["contactId"], []).append(row)
    runs = EvaPartnerCampaignRun.objects.filter(queue_id__in=first_by_id, check_at__lte=now).order_by("check_at")
    processed = 0
    for run in runs.iterator():
        first = first_by_id[str(run.queue_id)]
        started = timestamp(first.get("createdAt"))
        repeats = [row for row in repeat_by_contact.get(str(run.contact_id), [])
                   if started and (timestamp(row.get("createdAt")) or started) >= started]
        try:
            check_at = reconcile(run, [first, *repeats], executor, funnel, statuses, now, ids)
        except EvaError as exc:
            LOG.warning("Eva partner check failed: %s", exc.code)
            check_at = now + ACTIVE_DELAY
        EvaPartnerCampaignRun.objects.filter(pk=run.pk).update(check_at=check_at)
        processed += 1
    return processed
