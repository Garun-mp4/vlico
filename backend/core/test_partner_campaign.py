from datetime import datetime, timedelta, timezone
import uuid
from unittest.mock import patch

from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone as django_time

from . import partner_campaign as campaign
from .models import EvaPartnerSend
from .partner_content import first_message, photo_prompt, text_prompt
from .partner_segments import classify, DESIGNERS, BUILDERS, REVIEW


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
                self.assertIn("менеджер по партнёрствам", message)
                self.assertLessEqual(len(message.encode("utf-16-le")) // 2, 1024)

    def test_source_categories_do_not_guess_ambiguous_profiles(self):
        self.assertEqual(classify("Архитектурное бюро"), DESIGNERS)
        self.assertEqual(classify("Частная строительная бригада"), BUILDERS)
        self.assertEqual(classify("Ремонт и отделка"), BUILDERS)
        for value in ("Проектная организация", "Дизайн / строительство", "Дизайн / интерьер (уточнить профиль)", ""):
            self.assertEqual(classify(value), REVIEW)
        self.assertEqual(classify("", designer_directory=True), DESIGNERS)

    def test_personalization_changes_the_offer_and_question(self):
        designer = first_message({"partnersegment": DESIGNERS}, "whatsapp")
        builder = first_message({"partnersegment": BUILDERS}, "telegram")
        self.assertIn("эстетику проекта", designer)
        self.assertIn("согласование узлов", builder)
        self.assertNotIn("эстетику проекта", builder)
        with self.assertRaises(ValueError):
            first_message({"partnersegment": REVIEW}, "whatsapp")

    def test_photo_prompt_requires_caption_and_no_pdf(self):
        prompt = photo_prompt("Утверждённый текст", "document-id")
        self.assertIn("sendToChat", prompt)
        self.assertIn("одним сообщением", prompt)
        self.assertIn("Не отправляй PDF", prompt)
        self.assertIn("отправь этот же текст одним сообщением без вложений", prompt)
        self.assertIn("причины сбоев и пояснения клиенту не отправляй", prompt)
        self.assertNotIn("сообщи об ошибке", prompt)
        self.assertTrue(prompt.endswith("Утверждённый текст"))

    def test_text_prompt_only_allows_approved_copy(self):
        approved = "Здравствуйте!\n\n**VLICO**"
        prompt = text_prompt(approved)
        self.assertTrue(prompt.endswith(approved))
        self.assertIn("Клиенту можно отправлять только утверждённый текст", prompt)
        self.assertIn("Не прикрепляй файлы", prompt)

    def test_owner_audience_and_four_bold_spans_are_channel_specific(self):
        for channel, marker in (("whatsapp", "*"), ("telegram", "**")):
            for segment in (DESIGNERS, BUILDERS):
                text = first_message({"partnersegment": segment}, channel)
                self.assertNotIn("архитекторам", text)
                for phrase in ("VLICO", "дизайнерам и строительным компаниям",
                               "Берём на себя техническую проработку и монтаж",
                               "Бесплатно разберём потолочные решения по вашему плану или визуализации"):
                    self.assertIn(marker + phrase + marker, text)

    def test_plain_text_and_split_attachment_are_not_accepted_as_photo_caption(self):
        now = datetime(2026, 11, 18, 10, tzinfo=timezone.utc)
        row = {"taskId": "task", "createdAt": now.isoformat()}
        text = {"senderType": "assistant", "externalId": "provider-1", "text": "Подпись", "attachments": []}
        history = [({"taskId": "task"}, [(now, text)])]
        self.assertFalse(campaign.confirmed_photo(history, row, "Подпись"))
        text["attachments"] = [{"mimeType": "application/pdf"}]
        self.assertFalse(campaign.confirmed_photo(history, row, "Подпись"))
        text["attachments"] = [{"mimeType": "image/png"}]
        self.assertTrue(campaign.confirmed_photo(history, row, "Подпись"))
        self.assertFalse(campaign.confirmed_photo(history, row, "Другой текст"))


class PartnerDispatchTests(TestCase):
    @override_settings(EVA_PARTNER_MESSAGE_MODE="text", EVA_PARTNER_PHOTO_PREVIEW_VERIFIED=False)
    def test_text_mode_never_reads_or_attaches_an_image(self):
        contact = self.contact(25)
        contact["props"] = {"partnerchecked": True, "partnerconsent": True,
            "partnerconsentchannels": "whatsapp", "partnerchannel": "whatsapp",
            "partnerconsentat": "2026-11-18", "partnersegment": DESIGNERS,
            "contactpermissionbasis": "Подтверждение владельца"}
        send = campaign.reserve(contact, "whatsapp", self.task, 0, self.now)
        with patch.object(campaign, "record", return_value=contact) as read, patch.object(campaign, "api") as api:
            api.return_value = {"items": [{"id": str(uuid.uuid4()), "contactId": contact["id"]}]}
            campaign.submit(send, contact, self.now)
        read.assert_called_once_with("contacts", contact["id"])
        send.refresh_from_db()
        self.assertIsNone(send.media_document_id)
        self.assertEqual(send.status, "queued")
        self.assertIn("Только текст", api.call_args.args[2]["data"][str(send.request_id)]["prompt"])

    def test_fixed_batch_excludes_other_contacts_followups_and_stops(self):
        from .models import EvaPartnerCampaign
        contact = self.contact(26)
        with override_settings(EVA_PARTNER_BATCH_CONTACT_IDS=(contact["id"],)):
            self.assertIsNone(campaign.reserve(self.contact(27), "whatsapp", self.task, 0, self.now))
            self.assertIsNone(campaign.reserve(contact, "whatsapp", self.task, 1, self.now))
            send = campaign.reserve(contact, "whatsapp", self.task, 0, self.now)
            policy = EvaPartnerCampaign.objects.create(pk=1, enabled=True)
            with patch.object(campaign, "update") as update:
                self.assertFalse(campaign.finish_batch(policy, {"whatsapp": ["first", "repeat"]}))
                update.assert_not_called()
                send.status = "sent";send.save()
                self.assertTrue(campaign.finish_batch(policy, {"whatsapp": ["first", "repeat"]}))
            policy.refresh_from_db();self.assertFalse(policy.enabled)

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

    def test_optout_after_send_does_not_restore_daily_capacity(self):
        for number in range(20):
            send = campaign.reserve(self.contact(number), "whatsapp", self.task, 0, self.now)
            send.status, send.sent_at = "cancelled", self.now
            send.save()
        self.assertEqual(campaign.remaining_capacity("whatsapp", self.now), 0)

    @override_settings(EVA_PARTNER_PHOTO_PREVIEW_VERIFIED=True,
                       EVA_PARTNER_IMAGE_DOCUMENT_ID="00000000-0000-0000-0000-000000000001",
                       EVA_PARTNER_EXECUTOR_ID="victoria")
    def test_first_send_stores_exact_caption_and_image_instruction(self):
        contact = self.contact(11)
        contact["props"] = {
            "partnerchecked": True, "partnerconsent": True, "partnerconsentchannels": "whatsapp",
            "partnerchannel": "whatsapp", "partnerconsentat": "2026-11-18", "partnersegment": DESIGNERS,
            "contactpermissionbasis": "Подтверждение владельца",
        }
        send = campaign.reserve(contact, "whatsapp", self.task, 0, self.now)
        image = {"id": "00000000-0000-0000-0000-000000000001", "userId": "victoria",
                 "type": "image", "status": "complete", "accessMode": "sendToChat"}
        with patch.object(campaign, "record", side_effect=[contact, image]), patch.object(campaign, "api") as api:
            api.return_value = {"items": [{"id": str(uuid.uuid4()), "contactId": contact["id"]}]}
            campaign.submit(send, contact, self.now)
        saved = EvaPartnerSend.objects.get(pk=send.pk)
        self.assertEqual(saved.message_text, first_message(contact["props"], "whatsapp"))
        self.assertEqual(str(saved.media_document_id), image["id"])
        self.assertIn(saved.message_text, api.call_args.args[2]["data"][str(send.request_id)]["prompt"])
        self.assertEqual(saved.status, "queued")

    @override_settings(EVA_PARTNER_PHOTO_PREVIEW_VERIFIED=True, EVA_PARTNER_IMAGE_DOCUMENT_ID="image")
    def test_incomplete_image_blocks_submission(self):
        contact = self.contact(12)
        contact["props"] = {
            "partnerchecked": True, "partnerconsent": True, "partnerconsentchannels": "whatsapp",
            "partnerchannel": "whatsapp", "partnerconsentat": "2026-11-18", "partnersegment": BUILDERS,
            "contactpermissionbasis": "Подтверждение владельца",
        }
        send = campaign.reserve(contact, "whatsapp", self.task, 0, self.now)
        with patch.object(campaign, "record", side_effect=[contact, {"type": "image", "status": "queue"}]), patch.object(campaign, "api") as api:
            campaign.submit(send, contact, self.now)
        api.assert_not_called()
        self.assertEqual(EvaPartnerSend.objects.get(pk=send.pk).error_code, "partner_photo_not_ready")

    @override_settings(EVA_PARTNER_PHOTO_PREVIEW_VERIFIED=False)
    def test_unverified_provider_preview_blocks_an_otherwise_eligible_contact(self):
        contact = self.contact(13)
        contact["props"] = {
            "partnerchecked": True, "partnerconsent": True, "partnerconsentchannels": "whatsapp",
            "partnerchannel": "whatsapp", "partnerconsentat": "2026-11-18", "partnersegment": DESIGNERS,
            "contactpermissionbasis": "Подтверждение владельца",
        }
        send = campaign.reserve(contact, "whatsapp", self.task, 0, self.now)
        with patch.object(campaign, "record", return_value=contact), patch.object(campaign, "api") as api:
            campaign.submit(send, contact, self.now)
        api.assert_not_called()
        self.assertEqual(EvaPartnerSend.objects.get(pk=send.pk).error_code, "partner_photo_preview_unverified")


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class PartnerCabinetTests(TestCase):
    @override_settings(EVA_PARTNER_PHOTO_PREVIEW_VERIFIED=False)
    def test_launch_cannot_bypass_unverified_photo_preview(self):
        from django.contrib.auth import get_user_model
        from .models import EvaPartnerCampaign
        user = get_user_model().objects.create_superuser("media-owner", "test@example.invalid", "qa-password")
        self.client.force_login(user)
        with patch.object(campaign, "record") as read:
            response = self.client.post("/cabinet/partners/", {"action": "start"})
        read.assert_not_called()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(EvaPartnerCampaign.objects.get(pk=1).enabled)
    @override_settings(EVA_PARTNER_FUNNEL_ID="funnel", EVA_RESPONSIBLE_ID="owner")
    def test_project_and_quote_request_are_independent_metrics(self):
        from .models import EvaPartnerEvent
        lead = {"id": "lead", "contactId": str(uuid.uuid4()), "funnelId": "funnel", "statusId": "new",
                "enteredAt": "2026-11-18T10:00:00Z", "contact": {"props": {"partnerproject": True}}}
        now = datetime(2026, 11, 18, 11, tzinfo=timezone.utc)
        with patch.object(campaign, "records", return_value=[lead]):
            campaign.capture_statuses({"Новый контакт": "new"}, now)
        self.assertEqual(EvaPartnerEvent.objects.filter(kind="project_available").count(), 1)
        self.assertFalse(EvaPartnerEvent.objects.filter(kind="project_request").exists())
        lead["contact"]["props"]["partnerquoterequest"] = True
        with patch.object(campaign, "records", return_value=[lead]):
            campaign.capture_statuses({"Новый контакт": "new"}, now)
            campaign.capture_statuses({"Новый контакт": "new"}, now)
        self.assertEqual(EvaPartnerEvent.objects.filter(kind="project_request").count(), 1)

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
