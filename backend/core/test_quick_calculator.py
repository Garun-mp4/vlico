from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from .email_delivery import deliver_email_one, email_body
from .lead_forms import LeadForm
from .models import Lead, PricingVersion
from .quick_calculator import QuickCalculatorForm, quick_snapshot
from .telegram_delivery import deliver_one
from .telegram_templates import message_parts


def quick_payload(**overrides):
    lead_form = LeadForm(initial={"kind": "calculator"})
    data = {
        "kind": "calculator",
        "calculator_schema": "quick-v1",
        "object_type": "apartment",
        "area_m2": "24,50",
        "solution": "classic",
        "name": "Тестовый посетитель",
        "contact": "+7 (900) 000-00-01",
        "consent": "on",
        **lead_form.initial,
    }
    data.update(overrides)
    return data


class QuickCalculatorFormTests(TestCase):
    def test_normalizes_decimal_comma_and_accepts_consultation(self):
        form = QuickCalculatorForm({
            "object_type": "separate_room",
            "area_m2": "24,50",
            "solution": "consultation",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(quick_snapshot(form.cleaned_data), {
            "schema": "quick-v1",
            "inputs": {"object_type": "separate_room", "area_m2": "24.5", "solution": "consultation"},
        })

    def test_rejects_invalid_area_and_choice_values(self):
        for value in ("", "0", "10000.01", "Infinity", "1e2", "24.500", "-5"):
            with self.subTest(area=value):
                form = QuickCalculatorForm({"object_type": "apartment", "area_m2": value, "solution": "classic"})
                self.assertFalse(form.is_valid())
                self.assertIn("area_m2", form.errors)
        form = QuickCalculatorForm({"object_type": "warehouse", "area_m2": "20", "solution": "classic"})
        self.assertFalse(form.is_valid())
        self.assertIn("object_type", form.errors)
        form = QuickCalculatorForm({"object_type": "apartment", "area_m2": "20", "solution": "unconfirmed"})
        self.assertFalse(form.is_valid())
        self.assertIn("solution", form.errors)


class QuickCalculatorIntegrationTests(TestCase):
    def test_shared_public_form_and_no_javascript_quote_need_no_active_rates(self):
        PricingVersion.objects.update(active=False)
        for url in ("/", "/calculator/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(set(response.context["quick_form"].fields), {"object_type", "area_m2", "solution"})
            self.assertContains(response, 'name="calculator_schema" value="quick-v1"')
            self.assertNotContains(response, "data-configurator")
            self.assertNotContains(response, "calculator/controller.js")
            self.assertNotContains(response, "name=\"perimeter\"")
            self.assertNotContains(response, "₽")

        quote = self.client.post(reverse("calculator"), {
            "calculator_schema": "quick-v1", "object_type": "house", "area_m2": "130", "solution": "consultation", "action": "quote",
        })
        self.assertEqual(quote.status_code, 200)
        self.assertTrue(quote.context["quick_show_result"])
        self.assertTrue(quote.context["quick_show_contact"])
        self.assertContains(quote, "Для предварительного расчёта уточним детали")
        self.assertNotContains(quote, "₽")
        self.assertEqual(Lead.objects.count(), 0)
        self.assertFalse(PricingVersion.objects.filter(active=True).exists())

    def test_invalid_quick_answers_do_not_create_a_lead(self):
        response = self.client.post(reverse("lead_submit"), quick_payload(area_m2="10000.01"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("area_m2", response.json()["errors"])
        response = self.client.post(reverse("lead_submit"), quick_payload(solution="unconfirmed"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("solution", response.json()["errors"])
        self.assertEqual(Lead.objects.count(), 0)

    @override_settings(
        TELEGRAM_DELIVERY_ENABLED=True,
        TELEGRAM_BOT_TOKEN="test-token",
        TELEGRAM_CHAT_ID="test-chat",
        EMAIL_DELIVERY_ENABLED=True,
        LEAD_NOTIFICATION_EMAIL="partners@vlico39.ru",
        EMAIL_HOST_USER="partners@vlico39.ru",
        EMAIL_HOST_PASSWORD="test-only",
        DEFAULT_FROM_EMAIL="VLICO <partners@vlico39.ru>",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_quick_snapshot_is_idempotent_and_appears_in_both_notifications(self):
        mail.outbox = []
        PricingVersion.objects.update(active=False)
        data = quick_payload(object_type="separate_room", solution="consultation", source_page="/")
        response = self.client.post(reverse("lead_submit"), data)
        self.assertEqual(response.status_code, 201, response.content)
        lead = Lead.objects.get(pk=response.json()["reference"])
        self.assertEqual(lead.calculation, {
            "schema": "quick-v1",
            "inputs": {"object_type": "separate_room", "area_m2": "24.5", "solution": "consultation"},
        })
        self.assertIsNone(lead.pricing_version)
        self.assertEqual(lead.source_page, "/")
        self.assertEqual(self.client.post(reverse("lead_submit"), data).status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)

        altered = {**data, "area_m2": "25"}
        self.assertEqual(self.client.post(reverse("lead_submit"), altered).status_code, 409)
        self.assertEqual(Lead.objects.count(), 1)

        telegram = "\n".join(part for part, _markup in message_parts(lead))
        email = email_body(lead)
        for content in (telegram, email):
            self.assertIn("Для предварительного расчёта уточним детали", content)
            self.assertIn("Отдельное помещение", content)
            self.assertIn("24,5 м²", content)
            self.assertIn("Нужна консультация", content)
            self.assertNotIn("₽", content)

        with patch("core.telegram_delivery.api_call", return_value="telegram-test-message") as telegram_transport:
            self.assertTrue(deliver_one())
        telegram_transport.assert_called_once()
        self.assertIn("Для предварительного расчёта уточним детали", telegram_transport.call_args.args[1]["caption"])
        self.assertIn("24,5 м²", telegram_transport.call_args.args[1]["caption"])
        self.assertTrue(deliver_email_one())
        self.assertIn("Для предварительного расчёта уточним детали", mail.outbox[-1].body)
        self.assertIn("24,5 м²", mail.outbox[-1].body)
        self.assertEqual(lead.deliveries.get(channel="telegram").status, "sent")
        self.assertEqual(lead.deliveries.get(channel="email").status, "sent")

    def test_cabinet_shows_quick_answers_and_keeps_historical_v2_display(self):
        quick_response = self.client.post(reverse("lead_submit"), quick_payload())
        quick = Lead.objects.get(pk=quick_response.json()["reference"])
        legacy = Lead.objects.create(
            kind="calculator", name="Исторический расчёт", contact="legacy@example.invalid",
            calculation={
                "schema": "v2", "version_title": "Снимок старых ставок", "total": "16240.00", "complete": True,
                "warnings": [], "items": [{"title": "Полотно", "quantity": "20", "unit": "м²", "unit_price": "650", "total": "13000"}],
                "exclusions": "Дополнительные работы согласуются отдельно.", "configuration": [{"label": "Поверхность", "value": "Матовая"}],
                "inputs": {"area": "20", "material": "pvc", "edge": "standard"},
            },
        )
        user = get_user_model().objects.create_user("quick-reader", is_staff=True)
        user.user_permissions.add(Permission.objects.get(content_type__app_label="core", codename="view_lead"))
        self.client.force_login(user)

        quick_page = self.client.get(reverse("cabinet_lead", args=[quick.pk]))
        self.assertContains(quick_page, "Параметры быстрого расчёта")
        self.assertContains(quick_page, "Для предварительного расчёта уточним детали")
        self.assertContains(quick_page, "24,5 м²")
        self.assertNotContains(quick_page, "₽")

        legacy_page = self.client.get(reverse("cabinet_lead", args=[legacy.pk]))
        self.assertContains(legacy_page, "Снимок старых ставок")
        self.assertContains(legacy_page, "16240.00 ₽")
        self.assertContains(legacy_page, "Исходные параметры")
