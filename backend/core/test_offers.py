import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .eva_delivery import EvaError
from .models import OfferPublication, SalesOffer
from .offers import (BEGIN, END, OfferForm, active_offers, fingerprint, instruction_block,
                     public_invitation, publish_offers, replace_block)


@override_settings(EVA_EXECUTOR_ID="test-agent")
class OffersTests(TestCase):
    def setUp(self):
        SalesOffer.objects.all().delete()
        self.state, _ = OfferPublication.objects.update_or_create(pk=1, defaults={"fingerprint": "", "revision": uuid.uuid4()})
        self.offer = SalesOffer.objects.create(title="Подбор света", status="approved", contexts=["lighting"],
            benefit="Подбор освещения", conditions="При заказе потолков", limits="Без оборудования и монтажа",
            combination="По согласованию", reply="Поможем с подбором", invitation="Подберём освещение для вашего проекта.",
            approval="Тестовое подтверждение", permanent=True)
        self.remote_prompt = "Базовые инструкции: замер подтверждает Владлен."
        self.writes = []

    def remote(self, method, resource, data=None):
        if method == "PUT":
            self.writes.append(data)
            self.remote_prompt = data["data"]["test-agent"]["prompt"]
            return {"code": 200}
        return {"code": 200, "data": {"prompt": self.remote_prompt}}

    def form_data(self, **changes):
        data = {name: getattr(self.offer, name) for name in OfferForm.Meta.fields}
        data.update({"revision": str(self.state.revision), "starts_at": "", "ends_at": "", **changes})
        return data

    def staff(self):
        user = get_user_model().objects.create_user("offer-editor", password="test-only", is_staff=True)
        user.groups.add(Group.objects.get(name="Portfolio editors"))
        self.client.force_login(user)
        return user

    def test_seed_permissions_allow_existing_editor(self):
        user = self.staff()
        self.assertTrue(user.has_perm("core.change_salesoffer"))
        self.assertEqual(self.client.get(reverse("cabinet_offers")).status_code, 200)
        self.assertEqual(self.client.get(reverse("cabinet_offer_new")).status_code, 200)

    def test_anonymous_and_unprivileged_cannot_change_or_publish(self):
        url = reverse("cabinet_offers_publish")
        self.assertEqual(self.client.post(url).status_code, 302)
        user = get_user_model().objects.create_user("no-rights", is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(self.client.get(reverse("cabinet_offers")).status_code, 403)

    def test_csrf_and_post_required(self):
        user = self.staff()
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        self.assertEqual(client.post(reverse("cabinet_offers_publish")).status_code, 403)
        self.assertEqual(self.client.get(reverse("cabinet_offers_publish")).status_code, 405)

    def test_form_rejects_unapproved_incomplete_or_undated_offer(self):
        for changes in ({"approval": ""}, {"limits": ""}, {"permanent": False}, {"contexts": ["invented"]}):
            self.assertFalse(OfferForm(data=self.form_data(**changes), instance=self.offer).is_valid(), changes)
        self.assertTrue(OfferForm(data=self.form_data(status="draft", approval="", permanent=False), instance=self.offer).is_valid())

    def test_calendar_dates_use_kaliningrad_and_reject_reverse_interval(self):
        form = OfferForm(data=self.form_data(permanent=False, starts_at="2026-12-01T10:00", ends_at="2026-12-02T10:00"), instance=self.offer)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["starts_at"].utcoffset(), timedelta(hours=2))
        self.assertFalse(OfferForm(data=self.form_data(permanent=False, starts_at="2026-12-02T10:00", ends_at="2026-12-01T10:00"), instance=self.offer).is_valid())

    def test_start_inclusive_end_exclusive_drafts_and_disabled_excluded(self):
        now = timezone.now()
        self.offer.permanent = False
        self.offer.starts_at, self.offer.ends_at = now, now + timedelta(seconds=1)
        self.offer.save()
        self.assertEqual(active_offers(now), [self.offer])
        self.assertEqual(active_offers(now - timedelta(microseconds=1)), [])
        self.assertEqual(active_offers(now + timedelta(seconds=1)), [])
        for status in ("draft", "disabled"):
            self.offer.status = status
            self.offer.save()
            self.assertEqual(active_offers(now), [])

    def test_preview_contains_only_active_facts_not_drafts_or_internal_approval(self):
        SalesOffer.objects.create(title="Секретный черновик", status="draft", benefit="10%")
        block = instruction_block(active_offers())
        self.assertNotIn("10%", block)
        self.assertNotIn("Тестовое подтверждение", block)
        self.assertIn("При заказе потолков", block)
        self.assertIn("максимум одно", block)

    def test_public_endpoint_has_no_internal_terms_and_no_cache(self):
        with patch("core.offers.api", side_effect=self.remote):
            publish_offers()
        response = self.client.get(reverse("chat_offer"))
        self.assertEqual(response.json(), {"text": self.offer.invitation, "expires_at": None})
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("approval", response.content.decode())

    def test_unpublished_edits_expiry_and_disable_use_generic_fallback(self):
        with patch("core.offers.api", side_effect=self.remote):
            publish_offers()
        self.offer.invitation = "Изменённый текст"
        self.offer.save()
        self.assertEqual(public_invitation(), {})
        with patch("core.offers.api", side_effect=self.remote):
            publish_offers()
        self.assertEqual(public_invitation()["text"], "Изменённый текст")
        self.offer.ends_at = timezone.now() - timedelta(seconds=1)
        self.offer.save()
        self.assertEqual(public_invitation(), {})
        self.offer.ends_at, self.offer.status = None, "disabled"
        self.offer.save()
        self.assertEqual(public_invitation(), {})

    def test_publish_readback_is_idempotent_and_preserves_base_instructions(self):
        with patch("core.offers.api", side_effect=self.remote) as mock:
            self.assertTrue(publish_offers(expected_revision=str(self.state.revision)))
            self.assertTrue(publish_offers())
            mock.reset_mock()
            self.assertFalse(publish_offers(only_changed=True))
            mock.assert_not_called()
        self.assertEqual(len(self.writes), 1)
        self.assertIn("замер подтверждает Владлен", self.remote_prompt)
        self.assertEqual(self.remote_prompt.count(BEGIN), 1)
        self.state.refresh_from_db()
        self.assertEqual(self.state.fingerprint, fingerprint(active_offers()))

    def test_uncertain_write_never_exposes_unconfirmed_invitation_and_retries_safely(self):
        def uncertain(method, resource, data=None):
            result = self.remote(method, resource, data)
            if method == "PUT":
                raise EvaError("transport_or_response", True)
            return result
        with patch("core.offers.api", side_effect=uncertain), self.assertRaises(EvaError):
            publish_offers()
        self.assertEqual(public_invitation(), {})
        with patch("core.offers.api", side_effect=self.remote):
            publish_offers()
        self.assertEqual(len(self.writes), 1)
        self.assertTrue(public_invitation())

    def test_readback_mismatch_and_malformed_response_never_mark_success(self):
        with patch("core.offers.api", return_value={"data": {"prompt": "not updated"}}), self.assertRaises(EvaError):
            publish_offers()
        with patch("core.offers.api", return_value={"data": []}), self.assertRaises(EvaError):
            publish_offers()
        self.state.refresh_from_db()
        self.assertFalse(self.state.fingerprint)

    def test_schedule_change_during_network_call_requires_republish(self):
        now = timezone.now()
        self.offer.ends_at = now + timedelta(seconds=1)
        self.offer.save()
        with patch("core.offers.api", side_effect=self.remote), patch("core.offers.timezone.now", side_effect=[now, now + timedelta(seconds=2)]):
            with self.assertRaisesRegex(EvaError, "offer_schedule_changed"):
                publish_offers()
        self.state.refresh_from_db()
        self.assertFalse(self.state.fingerprint)

    def test_stale_form_and_stale_publication_do_not_overwrite(self):
        self.staff()
        data = self.form_data()
        self.state.revision = uuid.uuid4()
        self.state.save()
        response = self.client.post(reverse("cabinet_offer_edit", args=[self.offer.pk]), data)
        self.assertContains(response, "Реестр изменён")
        with patch("core.offers.api") as api:
            self.client.post(reverse("cabinet_offers_publish"), {"revision": data["revision"]})
            api.assert_not_called()

    def test_editor_can_create_change_disable_and_then_publish(self):
        self.staff()
        previous_revision = self.state.revision
        self.client.post(reverse("cabinet_offer_new"), self.form_data(title="Новое предложение", status="draft", approval=""))
        new = SalesOffer.objects.get(title="Новое предложение")
        self.state.refresh_from_db()
        self.assertNotEqual(self.state.revision, previous_revision)
        data = self.form_data(status="disabled")
        self.client.post(reverse("cabinet_offer_edit", args=[self.offer.pk]), data)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.status, "disabled")
        self.assertEqual(new.status, "draft")
        self.state.refresh_from_db()
        with patch("core.offers.api", side_effect=self.remote):
            self.client.post(reverse("cabinet_offers_publish"), {"revision": str(self.state.revision)})
        self.assertNotIn("Подбор освещения", self.remote_prompt)

    def test_expired_offer_removed_by_periodic_publication(self):
        with patch("core.offers.api", side_effect=self.remote):
            publish_offers()
            self.offer.ends_at = timezone.now() - timedelta(seconds=1)
            self.offer.save()
            publish_offers(only_changed=True)
        self.assertNotIn(self.offer.invitation, self.remote_prompt)
        self.assertNotIn(self.offer.benefit, self.remote_prompt)

    def test_scheduler_does_not_publish_unsaved_review_or_pending_edits(self):
        with patch("core.offers.api", side_effect=self.remote) as api:
            self.assertFalse(publish_offers(only_changed=True, scheduled=True))
            api.assert_not_called()
            publish_offers()
            self.state.refresh_from_db()
            self.state.revision = uuid.uuid4()
            self.state.save()
            api.reset_mock()
            self.assertFalse(publish_offers(only_changed=True, scheduled=True))
            api.assert_not_called()

    def test_expiry_still_runs_with_unpublished_edits(self):
        now = timezone.now()
        self.offer.permanent = False
        self.offer.starts_at, self.offer.ends_at = now - timedelta(days=1), now + timedelta(seconds=10)
        self.offer.save()
        with patch("core.offers.api", side_effect=self.remote):
            publish_offers()
            self.state.refresh_from_db()
            self.state.revision = uuid.uuid4()
            self.state.save()
            self.offer.benefit = "Unpublished gift"
            self.offer.ends_at = now + timedelta(days=30)
            self.offer.save()
            with patch("core.offers.timezone.now", return_value=now + timedelta(seconds=11)):
                self.assertTrue(publish_offers(only_changed=True, scheduled=True))
        self.assertNotIn("Unpublished gift", self.remote_prompt)
        self.assertNotIn("Подбор освещения", self.remote_prompt)
        self.state.refresh_from_db()
        self.assertNotEqual(self.state.published_revision, self.state.revision)

    def test_published_future_offer_starts_without_approving_later_edits(self):
        now = timezone.now()
        self.offer.starts_at = now + timedelta(seconds=10)
        self.offer.save()
        with patch("core.offers.api", side_effect=self.remote):
            publish_offers()
            self.assertNotIn(self.offer.benefit, self.remote_prompt)
            self.offer.benefit = "Unpublished gift"
            self.offer.save()
            self.state.refresh_from_db()
            self.state.revision = uuid.uuid4()
            self.state.save()
            with patch("core.offers.timezone.now", return_value=now + timedelta(seconds=11)):
                publish_offers(only_changed=True, scheduled=True)
        self.assertIn("Подбор освещения", self.remote_prompt)
        self.assertNotIn("Unpublished gift", self.remote_prompt)

    def test_conflicting_markers_and_oversized_instruction_do_not_overwrite(self):
        for prompt in (BEGIN, END, END + BEGIN, BEGIN + BEGIN + END, "a" * 30000):
            with self.assertRaises(EvaError):
                replace_block(prompt, instruction_block([]))
