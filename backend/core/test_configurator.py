from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from .configurator import ConfiguratorForm, calculate_answers
from .models import PricingVersion, Lead
from .pricing import default_rates
from .test_leads import payload


def answers(**changes):
    return {"schema": "v2", "room": "living", "size_mode": "dimensions", "shape": "rectangle", "length": "5", "width": "4", "material": "pvc", "edge": "standard", "lights": ["none"], "cornice": "none", "features": ["none"], "location": "city", **changes}


class ConfiguratorTests(TestCase):
    def setUp(self):
        PricingVersion.objects.filter(active=True).update(active=False)
        self.version = PricingVersion.objects.create(title="Control rates", rates=default_rates(), active=True)

    def quote(self, **changes):
        form = ConfiguratorForm(answers(**changes))
        self.assertTrue(form.is_valid(), form.errors)
        return calculate_answers(form.cleaned_data, self.version)

    def test_rectangle_and_multiple_systems_preserve_control_prices(self):
        q = self.quote()
        self.assertEqual(q["total"], "16240.00")
        self.assertEqual(q["inputs"]["area"], "20.00")
        self.assertEqual(q["inputs"]["perimeter"], "18")
        q = self.quote(edge="shadow", lights=["spots", "light_lines", "tracks"], spots="6", light_lines="3", tracks="2", cornice="hidden", cornices="3")
        self.assertEqual(q["total"], "50900.00")
        self.assertEqual(len(q["items"]), 6)

    def test_comma_and_fabric(self):
        self.assertEqual(self.quote(length="5,5", width="4")["inputs"]["area"], "22.00")
        self.assertEqual(self.quote(material="fabric")["total"], "43240.00")
        self.assertIn("Совместимость", " ".join(self.quote(material="fabric", edge="shadow")["warnings"]))

    def test_unknown_area_material_and_perimeter_are_honest(self):
        q = self.quote(size_mode="area", area="20", perimeter="")
        self.assertEqual(q["total"], "13000.00")
        self.assertFalse(q["complete"])
        for changes in ({"size_mode": "unknown", "area_range": "medium"}, {"material": "unknown"}):
            q = self.quote(**changes)
            self.assertIsNone(q["total"])
            self.assertEqual(q["items"], [])

    def test_complex_shape_never_uses_rectangle_formula(self):
        q = self.quote(shape="l", area="25", perimeter="30")
        self.assertEqual(q["inputs"]["area"], "25")
        self.assertEqual(q["inputs"]["perimeter"], "30")
        self.assertFalse(q["complete"])

    def test_deselected_dependent_fields_are_ignored_even_if_malformed(self):
        q = self.quote(spots="NaN", cornices="-9", pipes="oops", area="700", perimeter="999")
        self.assertEqual(q["total"], "16240.00")
        self.assertIsNone(q["inputs"]["spots"])
        self.assertIsNone(q["inputs"]["cornices"])

    def test_unknown_quantities_and_unpriced_options(self):
        q = self.quote(lights=["spots", "chandeliers"], spots="", chandeliers="2", cornice="standard", cornices="3", features=["pipes", "levels"], pipes="2", location="region", locality="Зеленоградск")
        self.assertEqual(q["total"], "16240.00")
        self.assertGreaterEqual(len(q["warnings"]), 5)
        self.assertIn("Зеленоградск", str(q["configuration"]))

    def test_floating_led_is_not_charged_twice(self):
        q = self.quote(edge="floating", lights=["led"], led="18")
        self.assertEqual(q["total"], "49000.00")
        self.assertEqual([i["code"] for i in q["items"]], ["pvc", "floating"])

    def test_validation_rejects_invalid_numbers_and_exclusive_answers(self):
        for changes in ({"length": "0"}, {"length": "NaN"}, {"width": "-1"}, {"length": "101"}, {"length": ".1", "width": ".1"}, {"lights": ["spots", "none"]}, {"features": ["tiles", "unknown"]}, {"location": "region"}, {"size_mode": "area", "area": ""}, {"lights": ["spots"], "spots": "1.5"}):
            form = ConfiguratorForm(answers(**changes))
            self.assertFalse(form.is_valid(), changes)

    def test_api_and_submission_snapshot_and_replay(self):
        data = answers(lights=["tracks"], tracks="2", features=["pipes"], pipes="1")
        q = self.client.post(reverse("estimate"), data)
        self.assertEqual(q.status_code, 200)
        submission = payload("calculator", pricing_version=self.version.pk, **data)
        response = self.client.post(reverse("lead_submit"), submission)
        self.assertEqual(response.status_code, 201, response.content)
        lead = Lead.objects.get(pk=response.json()["reference"])
        self.assertEqual(lead.calculation["inputs"]["pipes"], 1)
        self.assertEqual(lead.calculation["total"], q.json()["quote"]["total"])
        self.assertEqual(self.client.post(reverse("lead_submit"), submission).status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)

    def test_unknown_base_can_be_submitted_without_fake_price(self):
        response = self.client.post(reverse("lead_submit"), payload("calculator", pricing_version=self.version.pk, **answers(size_mode="unknown", material="unknown")))
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(Lead.objects.get().calculation["total"])

    def test_v2_stale_rates_require_review_and_keep_snapshot(self):
        data = payload("calculator", pricing_version=self.version.pk, **answers())
        self.version.active = False
        self.version.save()
        rates = default_rates()
        rates["pvc"]["amount"] = "700"
        current = PricingVersion.objects.create(title="Updated", rates=rates, active=True)
        response = self.client.post(reverse("lead_submit"), data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["quote"]["total"], "17240.00")
        self.assertEqual(Lead.objects.count(), 0)
        data["pricing_version"] = current.pk
        self.assertEqual(self.client.post(reverse("lead_submit"), data).status_code, 201)
        self.assertEqual(Lead.objects.get().calculation["schema"], "v2")

    def test_same_module_home_and_standalone_and_no_js_post(self):
        for url in ("/", "/calculator/"):
            response = self.client.get(url)
            self.assertContains(response, "data-configurator", count=1)
            self.assertContains(response, 'id="calc_contact_name"')
        response = self.client.post("/calculator/", {**answers(), "action": "quote"})
        self.assertContains(response, "16240.00")
        self.assertContains(response, "Ваш предварительный расчёт готов")
