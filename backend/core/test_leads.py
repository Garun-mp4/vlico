from datetime import timedelta
from decimal import Decimal
from io import BytesIO
import smtplib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.db import IntegrityError
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.db import close_old_connections, connections
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.urls import reverse
from django.utils import timezone
from .lead_cabinet import BUSINESS_PERMISSIONS
from .email_delivery import deliver_email_one
from .lead_forms import LeadForm
from .lead_service import save_submission
from .models import Lead, LeadAttachment, Delivery, PricingVersion, Project, SubmissionBucket
from .pricing import CalculationForm, calculate, default_rates, validate_rates
from .telegram_delivery import deliver_one, DeliveryError, claim_delivery, message_parts, api_call


def pdf(name="plan.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4\n% Historical attachment fixture\n%%EOF", content_type="application/pdf")


def payload(kind="consultation", **overrides):
    form = LeadForm(initial={"kind": kind})
    data = {"kind": kind, "name": "Тестовый посетитель", "contact": "+7 (900) 000-00-01", "consent": "on", **form.initial}
    data.update(overrides)
    return data


class LeadTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        settings = override_settings(PRIVATE_MEDIA_ROOT=Path(self.temp.name)/"private")
        settings.enable(); self.addCleanup(settings.disable)
        self.editor = get_user_model().objects.create_user("lead-editor", password="Test-password-937!", is_staff=True)
        self.editor.user_permissions.add(*Permission.objects.filter(content_type__app_label="core", codename__in=[name.split(".")[1] for name in BUSINESS_PERMISSIONS]))
        self.version = PricingVersion.objects.get(active=True)

    def test_every_kind_saves_and_queues_without_files(self):
        for kind in ("consultation", "measurement", "partner", "project", "calculator"):
            data = payload(kind)
            if kind == "calculator": data.update(area="20", material="pvc", edge="shadow", perimeter="18", pricing_version=self.version.pk)
            response = self.client.post(reverse("lead_submit"), data)
            self.assertEqual(response.status_code, 201, response.content)
            lead = Lead.objects.get(pk=response.json()["reference"])
            self.assertEqual(lead.contact, "+79000000001")
            self.assertIsNotNone(lead.consent_at)
            self.assertEqual(lead.deliveries.count(), 1)
        self.assertFalse(LeadAttachment.objects.exists())

    @override_settings(EMAIL_DELIVERY_ENABLED=True)
    def test_email_notification_is_queued_separately_and_keeps_lead(self):
        response = self.client.post(reverse("lead_submit"), payload("project"))
        self.assertEqual(response.status_code, 201)
        lead = Lead.objects.get(pk=response.json()["reference"])
        self.assertEqual(set(lead.deliveries.values_list("channel", flat=True)), {"telegram", "email"})
        self.assertEqual(lead.deliveries.get(channel="email").status, "pending")

    def test_public_forms_have_no_upload_controls(self):
        for path in ('/', '/calculator/', '/request/consultation/', '/request/measurement/', '/request/project/', '/request/partner/'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'type="file"')
            self.assertNotContains(response, 'name="attachments"')
            self.assertNotContains(response, 'multipart/form-data')

    def test_project_request_without_javascript_accepts_no_file(self):
        response = self.client.post(reverse('request_form', args=['project']), payload('project'))
        self.assertContains(response, 'Заявка принята')
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(Delivery.objects.count(), 1)
        self.assertFalse(LeadAttachment.objects.exists())

    def test_repeat_is_idempotent_and_modified_replay_is_rejected(self):
        data = payload()
        first = self.client.post(reverse("lead_submit"), data)
        second = self.client.post(reverse("lead_submit"), data)
        self.assertEqual((first.status_code, second.status_code), (201, 200))
        self.assertEqual(first.json()["reference"], second.json()["reference"])
        changed = self.client.post(reverse("lead_submit"), {**data, "contact": "new@example.com"})
        self.assertEqual(changed.status_code, 409)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(Delivery.objects.count(), 1)

    def test_bad_contact_missing_consent_honeypot_token_and_private_project(self):
        draft = Project.objects.create(title="Private", slug="private")
        for values in ({"contact": "no"}, {"contact": "invalid"}, {"consent": ""}, {"website": "spam"}, {"submission_token": "forged"}, {"project": draft.pk}):
            response = self.client.post(reverse("lead_submit"), payload(**values))
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)
        self.assertEqual(self.client.get(reverse("lead_submit")).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post(reverse("lead_submit"), payload()).status_code, 403)

    def test_server_throttle_and_expiry(self):
        for _ in range(12):
            self.assertEqual(self.client.post(reverse("lead_submit"), payload()).status_code, 201)
        response = self.client.post(reverse("lead_submit"), payload())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "900")
        SubmissionBucket.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.client.post(reverse("lead_submit"), payload()).status_code, 201)

    def test_public_uploads_are_rejected_for_every_field_name(self):
        invalid = [payload("project", attachments=pdf()), payload(other_file=pdf()), payload(attachments=[pdf() for _ in range(4)]),
            payload(attachments=SimpleUploadedFile("fake.pdf", b"%PDF-fake\n%%EOF")),
            payload(attachments=SimpleUploadedFile("script.jpg", b"<script>alert(1)</script>")),
            payload(attachments=SimpleUploadedFile("bad.exe", b"MZ"))]
        for data in invalid:
            self.assertEqual(self.client.post(reverse("lead_submit"), data).status_code, 400)
        oversized = self.client.post(reverse("lead_submit"), payload(attachments=SimpleUploadedFile("large.pdf", b"x"*(2*1024*1024+1))))
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(Lead.objects.count(), 0)
        self.assertEqual(LeadAttachment.objects.count(), 0)

    def test_failed_queue_creation_rolls_back_lead(self):
        with patch("core.lead_service.Delivery.objects.create", side_effect=RuntimeError("test failure")):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("lead_submit"), payload("project"))
        self.assertEqual(Lead.objects.count(), 0)
        self.assertEqual(LeadAttachment.objects.count(), 0)
        self.assertEqual(list(Path(self.temp.name).rglob("*.pdf")), [])

    def test_source_survives_navigation_and_private_fields_do_not_reach_public_pages(self):
        self.client.get("/?utm_source=test&utm_campaign=ceiling")
        project = Project.objects.create(title="Published", slug="published", status="published")
        form_page = self.client.get(reverse("request_form", args=["consultation"])+"?project=published")
        self.assertEqual(form_page.context["lead_form"].initial["project"], project)
        response = self.client.post(reverse("lead_submit"), payload(project=project.pk, source_page="/request/consultation/?contact=secret"))
        lead = Lead.objects.get(pk=response.json()["reference"])
        self.assertEqual(lead.attribution["utm_source"], "test")
        self.assertEqual(lead.source_page, "/request/consultation/")
        self.assertEqual(lead.context["project_title"], "Published")
        self.assertNotContains(self.client.get("/"), lead.contact)

    def test_control_prices_partial_and_unsupported_or_nonfinite_parameters(self):
        data = {"area":"20", "material":"pvc", "edge":"shadow", "perimeter":"18", "light_lines":"3", "tracks":"2", "cornices":"3", "spots":"6"}
        form = CalculationForm(data); self.assertTrue(form.is_valid())
        self.assertEqual(calculate(form.cleaned_data)["total"], "50900.00")
        form = CalculationForm({**data, "perimeter":"", "light_lines":"0", "tracks":"0", "cornices":"0", "spots":"0"})
        self.assertTrue(form.is_valid()); quote=calculate(form.cleaned_data)
        self.assertEqual(quote["total"], "13000.00");self.assertFalse(quote["complete"])
        for values in ({"area":"NaN"}, {"area":"-1"}, {"material":"other"}, {"spots":"1.2"}, {"tracks":"1001"}):
            self.assertFalse(CalculationForm({**data, **values}).is_valid())

    def test_changed_rates_do_not_change_history_and_stale_quote_needs_review(self):
        data = payload("calculator", area="20", material="pvc", edge="standard", perimeter="18", pricing_version=self.version.pk)
        response = self.client.post(reverse("lead_submit"), data)
        lead = Lead.objects.get(pk=response.json()["reference"])
        self.assertEqual(lead.calculation["total"], "16240.00")
        self.version.active=False;self.version.save()
        rates=default_rates();rates["pvc"]["amount"]="1000"
        current=PricingVersion.objects.create(title="New", rates=rates, active=True)
        stale = self.client.post(reverse("lead_submit"), payload("calculator", area="20", material="pvc", edge="standard", perimeter="18", pricing_version=self.version.pk))
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["quote"]["version"], current.pk)
        self.assertEqual(lead.calculation["total"], "16240.00")
        self.assertEqual(self.client.post(reverse("lead_submit"), data).status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)

    def test_cabinet_permissions_private_download_status_and_retry(self):
        response = self.client.post(reverse("lead_submit"), payload("project"))
        lead=Lead.objects.get(pk=response.json()["reference"]); delivery=lead.deliveries.get()
        attachment=LeadAttachment.objects.create(lead=lead, original_name="plan.pdf", file=pdf(), content_type="application/pdf", size=50)
        paths=[reverse("cabinet_leads"),reverse("cabinet_lead",args=[lead.pk]),reverse("cabinet_rates"),reverse("cabinet_lead_attachment",args=[lead.pk,attachment.pk])]
        for path in paths: self.assertEqual(self.client.get(path).status_code,302)
        reader=get_user_model().objects.create_user("reader")
        self.client.force_login(reader)
        for path in paths: self.assertEqual(self.client.get(path).status_code,403)
        self.client.force_login(self.editor)
        for path in paths:
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            if response.streaming:
                b"".join(response.streaming_content)
        file_response=self.client.get(paths[-1]);self.assertIn("attachment",file_response["Content-Disposition"]);self.assertEqual(file_response["Cache-Control"],"private, no-store")
        b"".join(file_response.streaming_content)
        self.assertEqual(self.client.get(reverse("cabinet_lead_attachment",args=[lead.pk,attachment.pk+100])).status_code,404)
        self.client.post(reverse("cabinet_lead_status",args=[lead.pk]),{"status":"contacted","revision":lead.updated_at.isoformat()})
        lead.refresh_from_db();self.assertEqual(lead.status,"contacted")
        self.client.post(reverse("cabinet_lead_status",args=[lead.pk]),{"status":"archived","revision":lead.updated_at.isoformat()})
        lead.refresh_from_db();self.assertEqual(lead.status,"archived")
        archived=self.client.get(reverse("cabinet_leads"),{"status":"archived"})
        self.assertEqual(list(archived.context["page"].object_list),[lead])
        self.assertContains(archived,"В архиве")
        delivery.status="failed";delivery.error_code="delivery_uncertain";delivery.save()
        path=reverse("cabinet_delivery_retry",args=[lead.pk,delivery.pk])
        self.client.post(path);delivery.refresh_from_db();self.assertEqual(delivery.status,"failed")
        self.client.post(path,{"confirm":"yes"});delivery.refresh_from_db();self.assertEqual(delivery.status,"pending")

    def test_rate_edit_is_versioned_rejects_stale_and_invalid_units(self):
        self.client.force_login(self.editor)
        data={"title":"Updated", "revision":str(self.version.pk)}
        for code,row in self.version.rates.items():
            data.update({f"{code}_{key}":value for key,value in row.items()})
        data["pvc_amount"]="700.50"
        self.assertEqual(self.client.post(reverse("cabinet_rates"),data).status_code,302)
        active=PricingVersion.objects.get(active=True);self.assertNotEqual(active.pk,self.version.pk)
        self.version.refresh_from_db();self.assertEqual(self.version.rates["pvc"]["amount"],"650.00")
        self.assertContains(self.client.post(reverse("cabinet_rates"),data),"Тарифы уже изменены")
        data["revision"]=str(active.pk);data["pvc_unit"]="шт."
        self.client.post(reverse("cabinet_rates"),data)
        self.assertEqual(PricingVersion.objects.get(active=True).pk,active.pk)

    def test_non_javascript_calculator_preserves_contact_and_submits(self):
        data=payload("calculator",area="20",material="pvc",edge="standard",perimeter="18",pricing_version=self.version.pk,action="quote")
        response=self.client.post(reverse("calculator"),data)
        self.assertContains(response,"16240.00")
        self.assertContains(response,"Тестовый посетитель")
        self.assertEqual(Lead.objects.count(),0)
        data["action"]="submit"
        self.assertContains(self.client.post(reverse("calculator"),data),"Заявка принята")
        self.assertEqual(Lead.objects.count(),1)

    def test_attribution_ignores_bad_shapes_and_control_characters(self):
        import json
        response=self.client.post(reverse("lead_submit"),payload(source_page="http://[",attribution=json.dumps({"utm_source":"source\u0000", "referrer":"http://[", "landing_path":"/hello?contact=private", "phone":"private"})))
        self.assertEqual(response.status_code,201)
        lead=Lead.objects.get(pk=response.json()["reference"])
        self.assertEqual(lead.attribution["utm_source"],"source")
        self.assertEqual(lead.attribution["landing_path"],"/hello")
        self.assertNotIn("phone",lead.attribution)


@override_settings(TELEGRAM_DELIVERY_ENABLED=True)
class DeliveryTests(TestCase):
    def setUp(self):
        self.lead=Lead.objects.create(kind="consultation",name="Тест",contact="test@example.com",consent_at=timezone.now())
        self.delivery=Delivery.objects.create(lead=self.lead)

    def test_success_and_no_second_send(self):
        with patch("core.telegram_delivery.api_call",return_value="42") as api:
            self.assertTrue(deliver_one());self.assertFalse(deliver_one())
        self.delivery.refresh_from_db();self.assertEqual(self.delivery.status,"sent");self.assertEqual(api.call_count,1)
        self.assertEqual(api.call_args.args[0], "sendPhoto")
        self.assertIn(self.lead.contact, api.call_args.args[1]["caption"])
        self.assertEqual(api.call_args.kwargs["photo"].name, "form.png")
        self.assertEqual(api.call_args.args[1]["parse_mode"], "HTML")
        button = api.call_args.args[1]["reply_markup"]["inline_keyboard"][0][0]
        self.assertTrue(button["url"].endswith(reverse("cabinet_lead", args=[self.lead.pk])))

    def test_long_calculator_message_retries_without_resending_cover(self):
        self.lead.kind = "calculator"
        self.lead.comment = "😀" * 600
        self.lead.save()
        with patch("core.telegram_delivery.api_call", side_effect=["42", DeliveryError("telegram_429", True)]) as api:
            self.assertTrue(deliver_one())
        cover, text = api.call_args_list
        self.assertEqual(cover.args[0], "sendPhoto")
        self.assertEqual(cover.kwargs["photo"].name, "calculator.png")
        self.assertEqual(text.args[0], "sendMessage")
        self.assertEqual(text.args[1]["reply_parameters"]["message_id"], 42)
        self.assertIn(self.lead.comment, text.args[1]["text"])

        Delivery.objects.filter(pk=self.delivery.pk).update(next_attempt_at=timezone.now())
        with patch("core.telegram_delivery.api_call", return_value="43") as api:
            self.assertTrue(deliver_one())
        api.assert_called_once_with(*text.args, **text.kwargs)
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, "sent")

    def test_temporary_failure_retries_with_limit_and_keeps_lead(self):
        with patch("core.telegram_delivery.api_call",side_effect=DeliveryError("telegram_unavailable",True)):
            for attempt in range(5):
                self.assertTrue(deliver_one());self.delivery.refresh_from_db()
                self.assertEqual(self.delivery.attempts,attempt+1)
                if attempt<4:
                    self.assertEqual(self.delivery.status,"pending")
                    Delivery.objects.filter(pk=self.delivery.pk).update(next_attempt_at=timezone.now())
        self.delivery.refresh_from_db();self.assertEqual(self.delivery.status,"failed");self.assertEqual(Lead.objects.count(),1)

    def test_uncertain_result_and_expired_lease_require_manual_review(self):
        with patch("core.telegram_delivery.api_call",side_effect=DeliveryError("delivery_uncertain")):
            deliver_one()
        self.delivery.refresh_from_db();self.assertEqual(self.delivery.status,"failed")
        self.delivery.status="sending";self.delivery.locked_until=timezone.now()-timedelta(seconds=1);self.delivery.save()
        with patch("core.telegram_delivery.api_call") as api:
            self.assertFalse(deliver_one());api.assert_not_called()
        self.delivery.refresh_from_db();self.assertEqual(self.delivery.error_code,"delivery_uncertain")

    def test_partial_attachment_retry_does_not_resend_confirmed_parts(self):
        first=LeadAttachment.objects.create(lead=self.lead,original_name="1.pdf",file="one.pdf")
        second=LeadAttachment.objects.create(lead=self.lead,original_name="2.pdf",file="two.pdf")
        with patch("core.telegram_delivery.api_call",side_effect=["10","11",DeliveryError("telegram_unavailable",True)]):
            deliver_one()
        self.delivery.refresh_from_db();self.assertEqual(self.delivery.progress["files"],[first.pk])
        Delivery.objects.filter(pk=self.delivery.pk).update(next_attempt_at=timezone.now())
        with patch("core.telegram_delivery.api_call",return_value="12") as api:
            deliver_one()
        self.assertEqual(api.call_count,1);self.assertEqual(api.call_args.args[2].pk,second.pk)
        self.delivery.refresh_from_db();self.assertEqual(self.delivery.status,"sent")

    def test_message_contains_context_and_respects_utf16_limits(self):
        self.lead.comment = "<b>Тест</b> & " + "😀" * 1100
        self.lead.context = {"project_title": "Кейс", "service_title": "Свет"}
        parts = message_parts(self.lead)
        html = "\n".join(part for part, _ in parts)
        self.assertIn("Кейс", html)
        self.assertIn(str(self.lead.pk)[:8], html)
        self.assertIn("&lt;b&gt;Тест&lt;/b&gt; &amp;", html)
        for _, size in parts:
            self.assertLessEqual(size, 3800)

    def test_legacy_retry_does_not_resend_confirmed_notification(self):
        self.delivery.progress = {"messages": ["42"], "files": []}
        self.delivery.save()
        with patch("core.telegram_delivery.api_call") as api:
            self.assertTrue(deliver_one())
        api.assert_not_called()
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, "sent")

    @override_settings(TELEGRAM_BOT_TOKEN="placeholder-for-transport-test", TELEGRAM_CHAT_ID="123")
    def test_transport_rate_limit_permanent_error_and_ambiguous_timeout(self):
        errors=[(HTTPError("https://example.invalid",429,"rate",{},BytesIO(b'{"parameters":{"retry_after":90}}')),"telegram_429",True),
            (HTTPError("https://example.invalid",400,"bad",{},BytesIO(b'{"description":"Bad Request: chat not found"}')),"chat_not_found",False),
            (HTTPError("https://example.invalid",403,"blocked",{},BytesIO(b"{}")),"telegram_403",False),
            (TimeoutError(),"delivery_uncertain",False)]
        for failure,code,retryable in errors:
            with patch("core.telegram_delivery.urlopen",side_effect=failure):
                with self.assertRaises(DeliveryError) as caught:api_call("sendMessage",{"text":"Test"})
            self.assertEqual(caught.exception.code,code);self.assertEqual(caught.exception.retryable,retryable)
            self.assertNotIn("placeholder",str(caught.exception))


@override_settings(
    EMAIL_DELIVERY_ENABLED=True,
    LEAD_NOTIFICATION_EMAIL="inbox@example.test",
    EMAIL_HOST_USER="sender@example.test",
    EMAIL_HOST_PASSWORD="test-app-password",
    DEFAULT_FROM_EMAIL="sender@example.test",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class EmailDeliveryTests(TestCase):
    def setUp(self):
        self.lead = Lead.objects.create(
            kind="consultation", name="Посетитель", contact="+79000000000",
            comment="Нужен расчёт", consent_at=timezone.now(),
        )
        self.delivery = Delivery.objects.create(lead=self.lead, channel="email")

    def test_email_is_sent_once_and_marked_delivered(self):
        mail.outbox = []
        self.assertTrue(deliver_email_one())
        self.assertFalse(deliver_email_one())
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["inbox@example.test"])
        self.assertIn(self.lead.contact, mail.outbox[0].body)
        self.assertIn(self.lead.comment, mail.outbox[0].body)
        self.assertIn(str(self.lead.pk), mail.outbox[0].body)
        self.assertTrue(self.delivery.external_id.startswith("<"))

    def test_unknown_send_result_requires_manual_review(self):
        with patch("core.email_delivery.get_connection") as get_connection:
            get_connection.return_value.send_messages.side_effect = smtplib.SMTPServerDisconnected()
            self.assertTrue(deliver_email_one())
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, "failed")
        self.assertEqual(self.delivery.error_code, "delivery_uncertain")


class ConcurrentLeadTests(TransactionTestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        settings=override_settings(PRIVATE_MEDIA_ROOT=Path(self.temp.name)/"private")
        settings.enable();self.addCleanup(settings.disable)

    def test_concurrent_replay_saves_one_lead_without_files_and_one_delivery(self):
        data=payload("project")
        barrier=Barrier(2)
        def send(index):
            close_old_connections()
            try:
                client=Client(REMOTE_ADDR=f"192.0.2.{index+1}")
                barrier.wait(timeout=10)
                return client.post(reverse("lead_submit"),data).status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(send,range(2)))
        self.assertEqual(sorted(results),[200,201])
        self.assertEqual((Lead.objects.count(),LeadAttachment.objects.count(),Delivery.objects.count()),(1,0,1))
        self.assertEqual(len(list(Path(self.temp.name).rglob("*.pdf"))),0)

    def test_concurrent_workers_only_claim_a_delivery_once(self):
        lead=Lead.objects.create(kind="consultation",name="Test",contact="test@example.com",consent_at=timezone.now())
        Delivery.objects.create(lead=lead)
        barrier=Barrier(2)
        def claim(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10);item=claim_delivery();return item.pk if item else None
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(claim,range(2)))
        self.assertEqual(len([value for value in results if value]),1)
        self.assertEqual(Delivery.objects.get().attempts,1)

    def test_concurrent_different_payloads_with_same_key_report_conflict(self):
        data=payload();barrier=Barrier(2)
        def send(index):
            close_old_connections()
            try:
                client=Client(REMOTE_ADDR=f"192.0.2.{index+1}")
                barrier.wait(timeout=10)
                return client.post(reverse("lead_submit"),{**data,"name":f"Visitor {index}"}).status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(send,range(2)))
        self.assertEqual(sorted(results),[201,409])
        self.assertEqual((Lead.objects.count(),Delivery.objects.count()),(1,1))
