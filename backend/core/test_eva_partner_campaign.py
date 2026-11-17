from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
import uuid

from django.test import SimpleTestCase

from . import eva_partner_campaign as campaign


class EvaPartnerCampaignTests(SimpleTestCase):
    start = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
    contact = "f10de41c-1f51-4588-95cd-f90915aacafc"
    statuses = {s: s for s in (
        campaign.NEW, campaign.OFFER, campaign.INTEREST, campaign.REFUSED, campaign.SILENT, campaign.ANSWER,
    )}

    def row(self, task="first", days=0, status="complete"):
        when = self.start + timedelta(days=days)
        return {"createdAt": when.isoformat(), "completeAt": when.isoformat(), "taskId": task,
                "contactId": self.contact, "status": status, "id": str(uuid.uuid4())}

    def chat(self, row):
        when = campaign.timestamp(row["createdAt"]) + timedelta(minutes=1)
        return ({"taskId": row["taskId"], "createdAt": when.isoformat(), "channelId": "channel"},
                [(when, {"senderType": "assistant", "externalId": "message-ref"})])

    def check(self, rows, history, now=None, lead_stage=campaign.NEW, props=None):
        lead = {"id": "lead", "statusId": lead_stage}
        with (patch.object(campaign, "record", return_value={"props": props or {}}),
              patch.object(campaign, "active_lead", return_value=lead),
              patch.object(campaign, "read_history", return_value=history),
              patch.object(campaign, "move") as move,
              patch.object(campaign, "cancel") as cancel,
              patch.object(campaign, "update") as update,
              patch.object(campaign, "notify_failure", return_value=True) as alert):
            lead["funnelId"] = "partners"
            when = campaign.reconcile(
                SimpleNamespace(contact_id=self.contact), rows, "victoria", "partners",
                self.statuses, now or self.start + timedelta(minutes=15),
            )
        return SimpleNamespace(
            when=when, lead=lead, move=move, cancel=cancel, update=update, alert=alert,
        )

    def test_campaign_moves_only_on_external_message(self):
        row = self.row()
        no_message = self.check([row], [])
        no_message.move.assert_not_called()
        sent = self.check([row], [self.chat(row)])
        self.assertEqual(sent.move.call_args.args[3], campaign.OFFER)
        self.assertEqual(sent.move.call_args.kwargs["partnerofferchannel"], "channel")

    def test_old_or_unrelated_external_message_does_not_count(self):
        row = self.row()
        unrelated = self.row("some-other-task")
        old = self.row(days=-1)
        self.assertIsNone(campaign.delivered(row, [self.chat(unrelated), self.chat(old)]))

    def test_failed_send_keeps_initial_stage_and_alerts(self):
        row = self.row(status="error")
        result = self.check([row], [])
        self.assertEqual(result.move.call_args.args[3], campaign.NEW)
        result.alert.assert_called_once()
        self.assertIsNone(result.when)

    def test_existing_reply_cancels_before_status_has_updated(self):
        first, repeat = self.row(), self.row("repeat", status="queue")
        other_channel = ({}, [(self.start + timedelta(minutes=2), {
            "senderType": "user", "contactId": self.contact, "text": "Спасибо, получили",
        })])
        result = self.check([first, repeat], [self.chat(first), other_channel])
        result.cancel.assert_called_once_with([first, repeat])
        result.move.assert_not_called()
        self.assertIsNotNone(result.when)

    def test_plain_optout_is_recorded_at_contact_level(self):
        row = self.row(status="queue")
        chat = ({}, [(self.start, {"senderType": "user", "contactId": self.contact,
                                  "text": "Пожалуйста, больше не пишите."})])
        result = self.check([row], [chat])
        result.update.assert_called_once_with("contacts", self.contact, props={"optout": True})
        self.assertEqual(result.move.call_args.args[3], campaign.REFUSED)

    def test_silence_waits_five_weekdays_after_last_confirmed_send(self):
        rows = [self.row(), self.row("second", 3), self.row("third", 7)]
        history = [self.chat(row) for row in rows]
        final_sent = history[-1][1][0][0]
        deadline = campaign.silence_deadline(final_sent)
        self.assertEqual(deadline.date().isoformat(), "2026-12-04")
        early = self.check(rows, history, deadline - timedelta(minutes=1), campaign.OFFER)
        early.move.assert_not_called()
        due = self.check(rows, history, deadline, campaign.OFFER)
        self.assertEqual(due.move.call_args.args[3], campaign.SILENT)

    def test_cancel_excludes_in_progress_and_completed_rows(self):
        queue, running, complete = self.row(status="queue"), self.row(status="initial"), self.row()
        with patch.object(campaign, "record", return_value=queue), patch.object(campaign, "api") as api:
            campaign.cancel([queue, running, complete])
        api.assert_called_once_with("POST", "taskcontacts/delete", {"ids": [queue["id"]]})

    def test_followup_requires_confirmed_send_and_checks_the_reply_again(self):
        first = self.row()
        history = [self.chat(first)]
        progress = [campaign.delivered(first, history)]
        task = {"enabled": True, "channels": ["channel"], "userId": "victoria", "autoSyncContacts": False}
        channel = {"id": "channel", "userId": "victoria", "enabledMode": "enabled",
                   "status": "online", "type": "whatsApp"}
        incoming = ({}, [(self.start, {"senderType": "user", "contactId": self.contact})])
        lead = {"id": "lead", "statusId": campaign.OFFER}
        run = SimpleNamespace(contact_id=self.contact, submitted_step=0, pk=first["id"])
        with (patch.object(campaign, "api") as api,
              patch.object(campaign, "task_rows", return_value=[]),
              patch.object(campaign, "active_lead", return_value=lead),
              patch.object(campaign, "read_history", return_value=[incoming]),
              patch.object(campaign, "record", side_effect=[task, task, {"props": {}}]),
              patch.object(campaign, "records", side_effect=[[], [channel]])):
            campaign.enqueue_followup(run, ["first", "second"], progress, lead, "victoria",
                                      self.statuses, self.start, self.start + timedelta(days=4))
            api.assert_not_called()

    def test_owner_pause_requires_human_message_from_confirmed_owner(self):
        chat = {"status": "complete", "id": "chat"}
        messages = [(self.start, {"senderType": "manager", "userId": "someone-else"})]
        with (patch.object(campaign, "record", return_value=chat),
              patch.object(campaign, "update", new=Mock()) as update):
            campaign.pause_for_owner([(chat, messages)], "owner", self.start)
            update.assert_not_called()
            messages.append((self.start, {"senderType": "manager", "userId": "owner"}))
            campaign.pause_for_owner([(chat, messages)], "owner", self.start)
            update.assert_called_once_with("conversations", "chat", status="disabled")
