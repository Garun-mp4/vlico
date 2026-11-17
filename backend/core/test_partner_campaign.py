from datetime import datetime, timedelta, timezone
import uuid
from unittest.mock import patch

from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone as django_time

from . import partner_campaign as campaign
from .models import EvaPartnerSend
from .partner_content import first_message


class PartnerRulesTests(SimpleTestCase):
    def test_consent_is_channel_specific_and_requires_evidence(self):
        contact = {"props": {
            "partnerchecked": True, "partnerconsent": True, "partnerconsentchannels": "whatsapp",
            "partnerchannel": "whatsapp", "partnerconsentat": "2026-11-18", "partnersegment": "Дизайнеры",
            "contactpermissionbasis": "Подтверждение владельца",
        }}
        self.assertTrue(campaign.eligible(contact, "whatsapp"))
        self.assertFalse(campaign.eligible(contact, "telegram"))
        contact["props"]["optout"] = True
        self.assertFalse(campaign.eligible(contact, "whatsapp"))
        contact["props"].pop("optout")
        contact["props"].pop("contactpermissionbasis")
        self.assertFalse(campaign.eligible(contact, "whatsapp"))

    def test_weekend_is_excluded_from_followup_interval(self):
        friday = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
        self.assertEqual(campaign.business_day_after(friday, 3).date().isoformat(), "2026-11-25")
        self.assertFalse(campaign.working(friday + timedelta(days=1)))
        self.assertTrue(campaign.working(datetime(2026, 11, 18, 8, tzinfo=timezone.utc)))
        self.assertFalse(campaign.working(datetime(2026, 11, 18, 16, tzinfo=timezone.utc)))

    def test_segment_messages_use_channel_attribution_without_commission(self):
        for segment in ("Дизайнеры", "Прорабы", "Строительные компании"):
            for channel in ("whatsapp", "telegram"):
                message = first_message({"partnersegment": segment}, channel)
                self.assertIn("utm_source=" + channel, message)
                self.assertNotIn("%", message.replace("%D", ""))
                self.assertIn("виртуальный менеджер", message)


class PartnerDispatchTests(TestCase):
    now = datetime(2026, 11, 18, 10, tzinfo=timezone.utc)

    def setUp(self):
        self.task = {"id": str(uuid.uuid4()), "channels": [str(uuid.uuid4())]}

    def contact(self, number):
        return {"id": str(uuid.uuid4()), "phone": f"+7900000{number:04d}", "props": {}}

    def test_twenty_reservations_maximum_per_channel(self):
        for number in range(20):
            self.assertIsNotNone(campaign.reserve(self.contact(number), "whatsapp", self.task, 0, self.now))
        self.assertIsNone(campaign.reserve(self.contact(99), "whatsapp", self.task, 0, self.now))
        self.assertIsNotNone(campaign.reserve(self.contact(99), "telegram", self.task, 0, self.now))

    def test_same_phone_cannot_be_contacted_on_second_channel(self):
        first = self.contact(42)
        self.assertIsNotNone(campaign.reserve(first, "whatsapp", self.task, 0, self.now))
        other = {**first, "id": str(uuid.uuid4()), "phone": "89000000042"}
        self.assertIsNone(campaign.reserve(other, "telegram", self.task, 0, self.now))

    def test_pending_previous_day_consumes_daily_capacity(self):
        for number in range(20):
            campaign.reserve(self.contact(number), "whatsapp", self.task, 0, self.now - timedelta(days=1))
        self.assertIsNone(campaign.reserve(self.contact(50), "whatsapp", self.task, 0, self.now))

    def test_revoked_permission_cancels_without_api_submission(self):
        contact = self.contact(42)
        send = campaign.reserve(contact, "whatsapp", self.task, 0, self.now)
        with patch.object(campaign, "record", return_value=contact), patch.object(campaign, "api") as api:
            campaign.submit(send, contact, self.now)
        api.assert_not_called()
        self.assertEqual(EvaPartnerSend.objects.get(pk=send.pk).status, "cancelled")

    def test_twelve_isolated_contacts_are_checked_without_sending(self):
        for number in range(12):
            contact = self.contact(number)
            send = campaign.reserve(contact, "whatsapp", self.task, 0, self.now)
            with patch.object(campaign, "record", return_value=contact), patch.object(campaign, "api") as api:
                campaign.submit(send, contact, self.now)
            api.assert_not_called()
        self.assertEqual(EvaPartnerSend.objects.filter(status="cancelled").count(), 12)

    def test_second_followup_is_rejected(self):
        self.assertIsNone(campaign.reserve(self.contact(1), "whatsapp", self.task, 2, self.now))

    def test_yesterdays_queue_sent_today_counts_toward_today(self):
        for number in range(20):
            send = campaign.reserve(self.contact(number), "whatsapp", self.task, 0, self.now - timedelta(days=1))
            send.status, send.sent_at = "sent", self.now
            send.save()
        self.assertIsNone(campaign.reserve(self.contact(50), "whatsapp", self.task, 0, self.now))


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class PartnerCabinetTests(TestCase):
    def test_reports_generated_and_visible_to_staff(self):
        from django.contrib.auth import get_user_model
        from .models import EvaPartnerReport
        user = get_user_model().objects.create_superuser("partner-owner", "test@example.invalid", "qa-password")
        campaign.refresh_reports(datetime(2026, 11, 18, 17, tzinfo=timezone.utc))
        self.assertEqual(EvaPartnerReport.objects.count(), 2)
        self.client.force_login(user)
        response = self.client.get("/cabinet/partners/")
        self.assertContains(response, "Кампания приостановлена")
        self.assertContains(response, "Нет данных провайдера")

    def test_anonymous_report_is_protected(self):
        response = self.client.get("/cabinet/partners/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/cabinet/login/"))

    def test_partner_page_records_campaign_source(self):
        from .models import EvaPartnerEvent
        response = self.client.get("/partners/?utm_source=telegram&utm_campaign=partner_network")
        self.assertContains(response, "Бесплатно разберём задачу")
        self.assertEqual(EvaPartnerEvent.objects.filter(kind="click", channel_type="telegram").count(), 1)
