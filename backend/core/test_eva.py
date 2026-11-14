import uuid
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import close_old_connections
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.urls import reverse
from django.templatetags.static import static
from django.utils import timezone
from .models import Lead, EvaSyncJob, Delivery, PricingVersion
from .test_leads import payload
from .eva_delivery import deliver_eva_one, EvaError, claim, api


@override_settings(EVA_CAPTURE_ENABLED=True, EVA_SYNC_ENABLED=True, EVA_API_KEY="test-only",
    EVA_FUNNEL_ID=str(uuid.uuid4()), EVA_STATUS_ID=str(uuid.uuid4()), EVA_EXECUTOR_ID=str(uuid.uuid4()),
    EVA_PARTNER_FUNNEL_ID=str(uuid.uuid4()), EVA_PARTNER_STATUS_ID=str(uuid.uuid4()), EVA_PARTNER_EXECUTOR_ID=str(uuid.uuid4()))
class EvaTests(TestCase):
    def submit(self, kind="consultation"):
        data = payload(kind)
        if kind == "calculator":
            data.update(area="20", material="pvc", edge="shadow", perimeter="18", pricing_version=PricingVersion.objects.get(active=True).pk)
        response = self.client.post(reverse("lead_submit"), data)
        self.assertEqual(response.status_code, 201, response.content)
        return EvaSyncJob.objects.get(lead_id=response.json()["reference"]), data

    def test_all_forms_and_duplicate_keep_one_job_and_deliveries(self):
        for kind in ("consultation", "measurement", "project", "calculator", "partner"):
            job, data = self.submit(kind)
            count = Delivery.objects.filter(lead=job.lead).count()
            self.assertEqual(self.client.post(reverse("lead_submit"), data).status_code, 200)
            self.assertEqual(EvaSyncJob.objects.filter(lead=job.lead).count(), 1)
            self.assertEqual(Delivery.objects.filter(lead=job.lead).count(), count)

    @override_settings(EVA_CAPTURE_ENABLED=False)
    def test_capture_disabled(self):
        self.assertEqual(self.client.post(reverse("lead_submit"), payload()).status_code, 201)
        self.assertFalse(EvaSyncJob.objects.exists())

    @override_settings(EVA_SYNC_ENABLED=False)
    @patch("core.eva_delivery.api")
    def test_send_disabled(self, api):
        self.submit()
        self.assertFalse(deliver_eva_one())
        api.assert_not_called()

    def test_reconcile_existing_records_never_posts(self):
        job, _ = self.submit()
        def read(method, path, *args, **kwargs):
            self.assertEqual(method, "GET")
            return {"code": 200, "data": {"id": path.split("/")[-1],
                "phone": job.lead.contact, "contactId": str(job.contact_id),
                "props": {"localleaduuid": str(job.lead_id)}}}
        with patch("core.eva_delivery.api", side_effect=read):
            self.assertTrue(deliver_eva_one())
        job.refresh_from_db()
        self.assertEqual(job.status, "sent")

    def test_partial_write_and_lost_response_reconciles(self):
        job, _ = self.submit()
        records = {}
        lost = [True]
        def remote(method, path, data=None, **kwargs):
            if method == "GET":
                return {"code": 200, "data": records[path]} if path in records else None
            key, fields = next(iter(data["data"].items()))
            records[path + "/" + key] = {"id": key, **fields}
            if path == "leads" and lost.pop():
                raise EvaError("transport_or_response", True)
            return {"code": 200, "data": {"items": [records[path + "/" + key]]}}
        with patch("core.eva_delivery.api", side_effect=remote):
            deliver_eva_one()
            job.refresh_from_db()
            self.assertEqual(job.status, "review")
            self.assertEqual(job.error_code, "write_uncertain")
        job.refresh_from_db()
        self.assertEqual(job.status, "review")
        self.assertEqual(len(records), 2)

    def test_auth_and_temporary_failures(self):
        for code, retry, state in (("eva_401", False, "blocked"), ("eva_402", False, "blocked"), ("http_429", True, "retry"), ("http_500", True, "retry")):
            with self.subTest(code=code):
                job, _ = self.submit()
                with patch("core.eva_delivery.api", side_effect=EvaError(code, retry)):
                    deliver_eva_one()
                job.refresh_from_db()
                self.assertEqual(job.status, state)

    def test_expired_final_lease_requires_review(self):
        job, _ = self.submit()
        EvaSyncJob.objects.filter(pk=job.pk).update(status="sending", attempts=5, locked_until=timezone.now()-timedelta(seconds=1))
        self.assertIsNone(claim())
        job.refresh_from_db()
        self.assertEqual(job.status, "review")

    def test_identity_conflict_is_not_overwritten(self):
        job, _ = self.submit()
        with patch("core.eva_delivery.api", return_value={"code": 200, "data": {"id": str(job.contact_id), "externalId": "other"}}) as api:
            deliver_eva_one()
        job.refresh_from_db()
        self.assertEqual(job.status, "review")
        self.assertEqual(api.call_count, 1)

    def test_server_allocated_ids_are_persisted_and_reused(self):
        job, _ = self.submit()
        job.lead.attribution = {"utm_source": "test_campaign"}
        job.lead.save(update_fields=["attribution"])
        records, posts = {}, []
        def remote(method, path, data=None, **kwargs):
            if method == "GET":
                return {"code": 200, "data": records[path]} if path in records else None
            self.assertTrue(data["skipNotifications"])
            fields = next(iter(data["data"].values()))
            self.assertNotIn("skipNotifications", fields)
            if path == "leads":
                self.assertEqual(fields["props"]["utmsource"], "test_campaign")
                self.assertEqual(fields["props"]["source"], "site_form")
            allocated = str(uuid.uuid4())
            records[path + "/" + allocated] = {"id": allocated, **fields}
            posts.append(path)
            return {"code": 200, "items": [records[path + "/" + allocated]]}
        with patch("core.eva_delivery.api", side_effect=remote):
            deliver_eva_one()
        job.refresh_from_db()
        self.assertEqual(job.status, "sent")
        self.assertIn("contacts/" + str(job.contact_id), records)
        self.assertIn("leads/" + str(job.remote_lead_id), records)
        self.assertEqual(posts, ["contacts", "leads"])

    def test_crash_during_write_never_reposts(self):
        job, _ = self.submit()
        EvaSyncJob.objects.filter(pk=job.pk).update(status="sending", attempts=1, error_code="write_in_progress", locked_until=timezone.now()-timedelta(seconds=1))
        self.assertIsNone(claim())
        job.refresh_from_db()
        self.assertEqual(job.status, "review")
        self.assertEqual(job.error_code, "write_uncertain")

    def test_eva_can_reuse_one_phone_contact_for_two_distinct_leads(self):
        first, _ = self.submit("consultation")
        second, _ = self.submit("measurement")
        contact_id = str(uuid.uuid4())
        records = {}

        def remote(method, path, data=None, **kwargs):
            if method == "GET":
                return {"code": 200, "data": records[path]} if path in records else None
            fields = next(iter(data["data"].values()))
            allocated = contact_id if path == "contacts" else str(uuid.uuid4())
            records.setdefault(path + "/" + allocated, {"id": allocated, **fields})
            return {"code": 200, "items": [{"id": allocated}]}

        with patch("core.eva_delivery.api", side_effect=remote):
            self.assertTrue(deliver_eva_one())
            self.assertTrue(deliver_eva_one())
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.status, second.status), ("sent", "sent"))
        self.assertEqual(first.contact_id, second.contact_id)
        self.assertNotEqual(first.remote_lead_id, second.remote_lead_id)

    @patch("core.eva_delivery.build_opener")
    def test_http_success_with_json_error_is_not_success(self, opener):
        response = opener.return_value.open.return_value.__enter__.return_value
        response.read.return_value = b'{"code":402}'
        with self.assertRaises(EvaError) as caught:
            api("GET", "contacts/test")
        self.assertEqual(caught.exception.code, "eva_402")

    @patch("core.eva_delivery.build_opener")
    def test_eva_existing_lead_rejection_is_distinguished_from_other_validation_errors(self, opener):
        opener.return_value.open.return_value.__enter__.return_value.read.return_value = (
            b'{"code":422,"validationErrors":{"temp":{"userId":["Parameters are not unique"]}}}'
        )
        with self.assertRaises(EvaError) as caught:
            api("POST", "leads", {})
        self.assertEqual(caught.exception.code, "existing_contact_lead")
        self.assertFalse(caught.exception.retry)

    @patch("core.eva_delivery.build_opener")
    def test_invalid_response_is_retryable_read_failure(self, opener):
        opener.return_value.open.return_value.__enter__.return_value.read.return_value = b'not json'
        with self.assertRaises(EvaError) as caught:
            api("GET", "contacts/test")
        self.assertTrue(caught.exception.retry)

    @override_settings(EVA_WIDGET_ENABLED=True, EVA_WIDGET_ID="6da2fe48-d1ff-4935-856e-d1cfff9d1d38")
    def test_widget_in_both_layouts_and_no_server_key(self):
        for url in ("/", "/calculator/", "/partners/", "/contacts/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            html = response.content.decode()
            self.assertEqual(html.count('src="/widget/chat-widget.js?widgetId=6da2fe48-d1ff-4935-856e-d1cfff9d1d38&amp;language=ru"'), 1)
            self.assertEqual(html.count(f'src="{static("eva-widget.js")}"'), 1)
            self.assertNotIn("test-only", html)
            self.assertNotIn('containerId=', html)

    @override_settings(EVA_WIDGET_ENABLED=True, EVA_WIDGET_ID="invalid")
    def test_invalid_widget_id_does_not_load(self):
        response = self.client.get("/")
        self.assertNotContains(response, '/widget/chat-widget.js')
        self.assertNotContains(response, static("eva-widget.js"))

    def test_requeue_is_protected_and_uncertain_write_cannot_be_replayed(self):
        job, _ = self.submit()
        url = reverse("cabinet_eva_retry", args=[job.lead_id])
        self.assertEqual(self.client.post(url).status_code, 302)
        user = get_user_model().objects.create_user("eva-test-operator", password="test-password-long-219!", is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.post(url).status_code, 403)
        user.user_permissions.add(Permission.objects.get(codename="change_lead", content_type__app_label="core"))
        self.assertEqual(self.client.get(url).status_code, 405)
        EvaSyncJob.objects.filter(pk=job.pk).update(status="review", error_code="write_uncertain")
        self.assertEqual(self.client.post(url).status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.status, "review")
        EvaSyncJob.objects.filter(pk=job.pk).update(status="blocked", error_code="eva_401")
        self.client.post(url)
        job.refresh_from_db()
        self.assertEqual(job.status, "pending")


class EvaConcurrencyTests(TransactionTestCase):
    def test_only_one_worker_claims_a_job(self):
        lead = Lead.objects.create(name="VLICO_TEST", contact="nobody@example.test", kind="consultation")
        job = EvaSyncJob.objects.create(lead=lead)
        barrier = Barrier(2)
        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                result = claim()
                return result.pk if result else None
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        self.assertEqual(results.count(job.pk), 1)
        self.assertEqual(results.count(None), 1)
