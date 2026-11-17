from datetime import timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

from django.test import TestCase, override_settings
from django.utils import timezone

from .email_delivery import deliver_email_one
from .eva_delivery import EvaError
from .eva_outreach_monitor import ALERT_CHANNEL, monitor_one
from .models import Delivery, EvaSyncJob, Lead

TASK, CHANNEL = str(uuid4()), str(uuid4())


@override_settings(EVA_SYNC_ENABLED=True, EVA_SITE_OUTREACH_TASK_ID=TASK, EVA_SITE_OUTREACH_CHANNEL_ID=CHANNEL)
class OutreachMonitorTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        lead = Lead.objects.create(name="Test", contact="+79990000001", kind="consultation")
        self.job = EvaSyncJob.objects.create(lead=lead, status="sent", sent_at=self.now,
            outreach_status="queued", outreach_queue_id=uuid4(), outreach_check_at=self.now)
        self.conversation_id = str(uuid4())

    def remote(self, method, path, **kwargs):
        common = {"taskId": TASK, "contactId": str(self.job.contact_id), "createdAt": self.now.isoformat()}
        if path.startswith("taskcontacts/"):
            return {"data": {"status": "initial", **common}}
        if path.startswith("conversations?"):
            return {"items": [{**common, "id": self.conversation_id, "channelId": CHANNEL, "status": self.conv_status}]}
        if path.startswith("messages?"):
            return {"items": self.messages}
        self.fail(path)

    def test_confirmation_requires_outgoing_channel_message(self):
        self.conv_status = "initial"
        message = {"conversationId": self.conversation_id, "externalId": "wa-id", "createdAt": self.now.isoformat()}
        self.messages = [{**message, "senderType": "contact"}]
        with patch("core.eva_outreach_monitor.api", side_effect=self.remote):
            monitor_one()
            self.job.refresh_from_db()
            self.assertEqual(self.job.outreach_status, "queued")
            self.job.outreach_check_at = timezone.now()
            self.job.save(update_fields=["outreach_check_at"])
            self.messages.append({**message, "senderType": "assistant"})
            monitor_one()
        self.job.refresh_from_db()
        self.assertEqual(self.job.outreach_status, "sent")
        self.assertFalse(Delivery.objects.exists())

    @override_settings(EMAIL_DELIVERY_ENABLED=True, LEAD_NOTIFICATION_EMAIL="ops@example.com",
                       EMAIL_HOST_USER="test", EMAIL_HOST_PASSWORD="test", DEFAULT_FROM_EMAIL="site@example.com")
    def test_failed_send_queues_and_delivers_one_separate_alert(self):
        self.conv_status, self.messages = "error", []
        Delivery.objects.create(lead=self.job.lead, channel="email")
        with patch("core.eva_outreach_monitor.api", side_effect=self.remote):
            self.assertTrue(monitor_one())
            self.assertFalse(monitor_one())
        self.job.refresh_from_db()
        self.assertEqual(self.job.outreach_status, "failed")
        smtp = Mock()
        smtp.send_messages.return_value = 1
        with patch("core.email_delivery.get_connection", return_value=smtp):
            self.assertTrue(deliver_email_one(ALERT_CHANNEL))
            self.assertFalse(deliver_email_one(ALERT_CHANNEL))
        msg = smtp.send_messages.call_args.args[0][0]
        self.assertEqual(msg.to, ["ops@example.com"])
        self.assertIn(self.job.lead.contact, msg.body)
        self.assertIn(str(self.job.lead_id), msg.body)
        self.assertIn("ошибке отправки", msg.body)
        self.assertEqual(Delivery.objects.get(channel=ALERT_CHANNEL).status, "sent")
        self.assertEqual(Delivery.objects.get(channel="email").status, "pending")

    def test_unknown_result_has_a_bounded_wait_and_distinct_alert(self):
        self.job.sent_at -= timedelta(hours=2)
        self.job.save(update_fields=["sent_at"])
        with patch("core.eva_outreach_monitor.api", side_effect=EvaError("http_503", True)):
            monitor_one()
        self.job.refresh_from_db()
        self.assertEqual(self.job.outreach_status, "review")
        self.assertEqual(self.job.outreach_error_code, "outreach_result_unknown")
        self.assertIn("Результат неизвестен", Delivery.objects.get().progress["reason"])
