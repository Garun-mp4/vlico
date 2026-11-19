"""Release the approved Eva partner audience one verified contact per sender."""

import json
import os
import re
import tempfile
import uuid
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path


def phone_key(contact):
    number = re.sub(r"\D", "", contact.get("phone") or "")
    if len(number) == 11 and number.startswith("8"):
        return "7" + number[1:]
    return number


def pending(row):
    return row["status"] == "queue" or row["status"] == "initial" and not row.get("completeAt")


def confirmed_or_uncertain_dialogue(eva, contact_ids):
    for contact_id in contact_ids:
        for chat in eva.records("conversations", contactId=contact_id):
            if chat.get("contactId") != contact_id or chat.get("isSupportChat"):
                continue
            for message in eva.records("messages", conversationId=chat["id"]):
                if message.get("conversationId") != chat["id"]:
                    continue
                if message.get("senderType") in (None, "system", "tool", "function"):
                    continue
                if (message.get("text") or "").strip() or message.get("attachments"):
                    return True
    return False


def save_state(path, state):
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=".photo-state-", mode="w", encoding="utf-8", delete=False
    ) as output:
        temporary = Path(output.name)
        json.dump(state, output)
        output.flush()
        os.fsync(output.fileno())
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def disposition(eva, candidate, contacts, aliases, channel):
    contact = eva.record("contacts", candidate["contactId"])
    if (not contact or phone_key(contact) != candidate["phone"]
            or not eva.eligible(contact, channel)
            or (contact.get("props") or {}).get("partnersegment") != candidate["segment"]):
        return "contact_changed"
    contact_ids = aliases[candidate["phone"]] | {contact["id"]}
    if any((contacts.get(cid, {}).get("props") or {}).get("optout") for cid in contact_ids):
        return "optout"
    if confirmed_or_uncertain_dialogue(eva, sorted(contact_ids)):
        return "existing_dialogue"
    return None


def channel_ready(eva, lane, worker, document, tasks, now):
    task = tasks[lane["task"]]
    channel = eva.record("channels", lane["channel"])
    if (not channel or channel.get("userId") != worker
            or channel.get("type") != {"telegram": "telegram", "whatsapp": "whatsApp"}[lane["kind"]]
            or channel.get("status") != "online" or channel.get("enabledMode") != "enabled"):
        return False
    schedule = eva.record("schedules", task["scheduleId"]) if task.get("scheduleId") else None
    if not schedule or not schedule.get("isWorking"):
        return False
    if not eva.working(now):
        return False
    available_at = eva.timestamp(channel.get("nextTaskAt"))
    # The cron check and Eva's channel clock do not tick at the same instant.
    if available_at and available_at > now + timedelta(seconds=75):
        return False
    if document is None:
        return True
    asset = eva.record("documents", document)
    return bool(asset and asset.get("userId") == worker and asset.get("status") == "complete"
                and asset.get("type") == "image" and asset.get("accessMode") == "sendToChat")


def dispatch_lane(eva, lane, manifest, state, commit, tasks, contacts, aliases, now):
    task_id = lane["task"]
    task = tasks[task_id]
    if not task["enabled"]:
        return "paused"
    if (task.get("userId") != manifest["worker"] or task.get("channels") != [lane["channel"]]
            or task.get("autoSyncContacts") is not False or task.get("repeatDays")
            or task.get("followUpIn") or task.get("funnelStatusId")):
        raise ValueError("photo sender configuration changed")

    candidates = {row["contactId"]: row for row in lane["recipients"]}
    rows = eva.task_rows(task_id)
    state_by_contact = state[lane["kind"]]
    due = [row for row in rows if pending(row)]
    if (len(due) > 1 or any(
        row["contactId"] not in candidates
        or state_by_contact.get(row["contactId"], {}).get("outcome") not in ("submitting", "queued")
        for row in due
    )):
        eva.update("tasks", task_id, enabled=False)
        raise ValueError("photo sender paused because its queue was edited directly")

    # Preserve attempted rows across process restarts, even if the state file is lost.
    for row in rows:
        contact_id = row["contactId"]
        item = state_by_contact.get(contact_id)
        if item and item["outcome"] == "submitting":
            item["outcome"] = "queued"
            commit()
        elif not item and contact_id in candidates:
            state_by_contact[contact_id] = {"outcome": "previous_attempt"}
            commit()
    if any(item["outcome"] == "submitting" for item in state_by_contact.values()):
        return "waiting_for_uncertain_write"

    if due:
        row = due[0]
        if row["status"] == "queue":
            reason = disposition(eva, candidates[row["contactId"]], contacts, aliases, lane["kind"])
            if reason:
                eva.cancel([row])
                if not eva.record("taskcontacts", row["id"]):
                    state_by_contact[row["contactId"]]["outcome"] = reason
                    commit()
                    return reason
        return "queued_or_in_progress"

    if not channel_ready(eva, lane, manifest["worker"], manifest.get("document"), tasks, now):
        return "outside_channel_slot"
    for other in tasks.values():
        if (other["id"] != task_id and other["enabled"] and lane["channel"] in other["channels"]
                and other.get("totalContacts", 0) > other.get("completeContacts", 0)
                and any(pending(row) for row in eva.task_rows(other["id"]))):
            return "another_task_in_channel"
    day = now.astimezone(eva.KALININGRAD).date().isoformat()
    if sum(item.get("day") == day for item in state_by_contact.values()) >= 20:
        return "daily_limit"

    for candidate in candidates.values():
        contact_id = candidate["contactId"]
        if contact_id in state_by_contact:
            continue
        reason = disposition(eva, candidate, contacts, aliases, lane["kind"])
        if reason:
            state_by_contact[contact_id] = {"outcome": reason}
            commit()
            continue
        if not eva.record("tasks", task_id)["enabled"]:
            return "paused"
        request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"vlico:photo-guard:{task_id}:{contact_id}"))
        item = {"outcome": "submitting", "day": day}
        state_by_contact[contact_id] = item
        commit()
        reply = eva.api("POST", "taskcontacts", {"data": {request_id: {
            "taskId": task_id, "contactId": contact_id, "status": "queue", "prompt": candidate["prompt"],
        }}, "skipNotifications": True})
        inserted = reply.get("items") or (reply.get("data") or {}).get("items") or []
        if len(inserted) != 1 or inserted[0].get("contactId") != contact_id:
            raise ValueError("photo queue submission needs reconciliation")
        item["outcome"] = "queued"
        commit()
        return "released"
    eva.update("tasks", task_id, enabled=False)
    return "audience_finished"


def run(eva, manifest, state_path, now):
    lanes = manifest["lanes"]
    audience = [row for lane in lanes for row in lane["recipients"]]
    if (len({lane["task"] for lane in lanes}) != len(lanes)
            or len({lane["kind"] for lane in lanes}) != len(lanes)
            or len({row["contactId"] for row in audience}) != len(audience)
            or len({row["phone"] for row in audience}) != len(audience)
            or not all(row["phone"] for row in audience)):
        raise ValueError("invalid photo audience")
    tasks = {t["id"]: t for t in eva.records("tasks", page_size=50)}
    if not any(tasks[lane["task"]]["enabled"] for lane in lanes):
        return "paused"
    contacts = {c["id"]: c for c in eva.records("contacts", page_size=75)}
    aliases = defaultdict(set)
    for contact in contacts.values():
        key = phone_key(contact)
        if key:
            aliases[key].add(contact["id"])
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {
        lane["kind"]: {} for lane in lanes
    }
    lines = []
    for lane in lanes:
        kind = lane["kind"]
        result = dispatch_lane(eva, lane, manifest, state, lambda: save_state(state_path, state),
                               tasks, contacts, aliases, now)
        totals = dict(Counter(item["outcome"] for item in state[kind].values()))
        lines.append(f"{kind}: {result}; {totals}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    from django.utils import timezone
    from core import partner_campaign

    config_path = Path(sys.argv[1])
    manifest = json.loads(config_path.read_text(encoding="utf-8"))
    print(run(partner_campaign, manifest, config_path.with_suffix(".state.json"), timezone.now()))
