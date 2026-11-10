from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from .configurator import ConfiguratorForm, calculate_answers
from .models import PricingVersion, Lead
from .pricing import default_rates
from .test_leads import payload
from .telegram_templates import message_parts


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

    def test_whole_apartment_uses_overall_area_without_room_dimensions(self):
        data = {"schema": "v2", "object_type": "apartment", "object_area": "82", "zones_enabled": "no",
                "material": "pvc", "edge": "standard", "lights": ["none"], "cornice": "none",
                "features": ["none"], "location": "city"}
        form = ConfiguratorForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        quote = calculate_answers(form.cleaned_data, self.version)
        self.assertEqual(quote["inputs"]["area"], "82")
        self.assertIsNotNone(quote["total"])
        self.assertIn("Вся квартира", str(quote["configuration"]))

    def test_zones_price_known_areas_and_mark_incomplete_area_honestly(self):
        data = {"schema": "v2", "object_type": "house", "object_area": "100", "zones_enabled": "yes",
                "zone_1_name": "Гостиная", "zone_1_area": "30", "zone_1_material": "pvc", "zone_1_edge": "shadow",
                "zone_2_name": "Кухня", "zone_2_area": "20", "zone_2_material": "fabric", "zone_2_edge": "standard",
                "lights": ["none"], "cornice": "none", "features": ["none"], "location": "city"}
        form = ConfiguratorForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        quote = calculate_answers(form.cleaned_data, self.version)
        self.assertFalse(quote["complete"])
        self.assertIsNotNone(quote["total"])
        self.assertEqual(len(quote["items"]), 2)
        self.assertTrue(any("Не вся площадь" in warning for warning in quote["warnings"]))
        self.assertIn("Гостиная", str(quote["configuration"]))

    def test_zones_cannot_exceed_object_area(self):
        data = {"schema": "v2", "object_type": "apartment", "object_area": "20", "zones_enabled": "yes",
                "zone_1_name": "Гостиная", "zone_1_area": "12", "zone_1_material": "pvc", "zone_1_edge": "standard",
                "zone_2_name": "Кухня", "zone_2_area": "10", "zone_2_material": "pvc", "zone_2_edge": "standard",
                "lights": ["none"], "cornice": "none", "features": ["none"], "location": "city"}
        form = ConfiguratorForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("object_area", form.errors)

    def test_v2_api_and_saved_lead_include_every_answer(self):
        data = {"schema": "v2", "object_type": "apartment", "object_area": "60", "zones_enabled": "yes",
                "zone_1_name": "Гостиная", "zone_1_area": "25", "zone_1_material": "pvc", "zone_1_edge": "shadow",
                "zone_2_name": "Кухня", "zone_2_area": "15", "zone_2_material": "fabric", "zone_2_edge": "standard",
                "lights": ["none"], "cornice": "none", "features": ["none"], "location": "city"}
        quote_page = self.client.post(reverse("estimate"), data)
        self.assertEqual(quote_page.status_code, 200)
        self.assertIn("Гостиная", str(quote_page.json()["quote"]["configuration"]))
        submission = payload("calculator", pricing_version=self.version.pk, **data)
        response = self.client.post(reverse("lead_submit"), submission)
        self.assertEqual(response.status_code, 201, response.content)
        lead = Lead.objects.get(pk=response.json()["reference"])
        self.assertEqual(lead.calculation["inputs"]["zones"][0]["name"], "Гостиная")
        self.assertEqual(lead.calculation["inputs"]["object_area"], "60")
        from .telegram_templates import message_parts
        self.assertIn("Гостиная", "\n".join(part for part, _ in message_parts(lead)))

    def test_surface_choice_keeps_material_and_texture_separate(self):
        for surface, material, texture in (("pvc", "pvc", "matte"), ("pvc_satin", "pvc", "satin"), ("pvc_gloss", "pvc", "gloss"), ("fabric", "fabric", "textile")):
            with self.subTest(surface=surface):
                quote = self.quote(material=surface)
                self.assertEqual(quote["inputs"]["material"], material)
                self.assertEqual(quote["inputs"]["texture"], texture)
                self.assertEqual(quote["inputs"]["surface"], surface)
                if texture in {"satin", "gloss"}:
                    self.assertIsNone(quote["total"])
                    self.assertEqual(quote["items"], [])
                    self.assertFalse(quote["complete"])
                    self.assertIn("стоимость выбранной фактуры уточним", " ".join(quote["warnings"]))

    def test_selected_finish_reaches_real_lead_snapshot(self):
        response = self.client.post(reverse("lead_submit"), payload("calculator", pricing_version=self.version.pk, **answers(material="pvc_gloss")))
        self.assertEqual(response.status_code, 201)
        lead = Lead.objects.get()
        quote = lead.calculation
        self.assertEqual(quote["inputs"]["material"], "pvc")
        self.assertEqual(quote["inputs"]["texture"], "gloss")
        self.assertIn("Глянцевый ПВХ", str(quote["configuration"]))
        self.assertIsNone(quote["total"])
        message = message_parts(lead)[0][0]
        self.assertIn("<b>Нужен индивидуальный расчёт</b>", message)
        self.assertIn("<b>3. Поверхность</b>\nГлянцевый ПВХ", message)
        self.assertNotIn("Расшифровка расчёта", message)

    def test_telegram_groups_answers_and_saved_price(self):
        response = self.client.post(reverse("lead_submit"), payload(
            "calculator", pricing_version=self.version.pk,
            **answers(size_mode="area", area="20", edge="shadow", lights=["spots", "tracks"], spots="6"),
        ))
        self.assertEqual(response.status_code, 201)
        message = message_parts(Lead.objects.get())[0][0]
        self.assertIn("частичная сумма", message)
        self.assertIn("Периметр неизвестен, поэтому примыкание не включено", message)
        self.assertIn("<b>5. Освещение</b>\n• Точечные светильники — 6 шт.\n• Магнитные треки — длина не указана", message)
        self.assertIn("<b>8. Расположение</b>\nКалининград", message)
        self.assertIn("<blockquote expandable><b>Расшифровка расчёта</b>", message)

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
            self.assertContains(response, "data-quick-calculator", count=1)
            self.assertContains(response, 'name="calculator_schema" value="quick-v1"')
            self.assertContains(response, 'name="object_type"')
            self.assertContains(response, 'name="area_m2"')
            self.assertContains(response, 'name="solution"')
            self.assertNotContains(response, "data-configurator")
            self.assertNotContains(response, "calculator/controller.js")
            self.assertNotContains(response, "name=\"material\"")
            self.assertNotContains(response, "₽")
        response = self.client.post("/calculator/", {
            "calculator_schema": "quick-v1", "object_type": "apartment", "area_m2": "20,5",
            "solution": "consultation", "action": "quote",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["quick_show_result"])
        self.assertTrue(response.context["quick_show_contact"])
        self.assertContains(response, "Для предварительного расчёта уточним детали")
        self.assertNotContains(response, "16240.00")
        self.assertEqual(Lead.objects.count(), 0)

    def test_quick_calculator_does_not_require_an_active_price_version(self):
        PricingVersion.objects.update(active=False)
        for url in ("/", "/calculator/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Получить предварительный расчёт")
        self.assertFalse(PricingVersion.objects.filter(active=True).exists())

    def test_quick_calculator_keeps_invalid_bound_fields_and_shows_errors(self):
        response = self.client.post('/calculator/', {
            "calculator_schema": "quick-v1", "object_type": "apartment", "area_m2": "Infinity",
            "solution": "classic", "action": "quote",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["quick_show_result"])
        self.assertEqual(response.context["quick_form"]["area_m2"].value(), "Infinity")
        self.assertIn("area_m2", response.context["quick_form"].errors)
        self.assertContains(response, "Введите площадь числом")

    def test_live_price_sequence_and_replacement(self):
        data = {'schema': 'v2', 'preview': '1', 'size_mode': 'dimensions', 'shape': 'rectangle', 'length': '5', 'width': '4', 'material': 'pvc'}
        def preview(**updates):
            data.update(updates)
            response = self.client.post(reverse('estimate'), data)
            self.assertEqual(response.status_code, 200, response.content)
            return response.json()
        first = preview()
        self.assertEqual(first['quote']['total'], '13000.00')
        self.assertEqual([i['code'] for i in first['quote']['items']], ['pvc'])
        self.assertFalse(first['quote']['complete'])
        self.assertEqual(first['options']['edge:shadow']['total'], '15300.00')
        self.assertEqual(preview(edge='standard')['quote']['total'], '16240.00')
        self.assertEqual(preview(edge='shadow')['quote']['total'], '28300.00')
        self.assertEqual(preview(lights=['spots'], spots='6')['quote']['total'], '31000.00')
        self.assertEqual(preview(lights=['spots', 'light_lines', 'tracks'], light_lines='3', tracks='2', cornice='hidden', cornices='3')['quote']['total'], '50900.00')
        self.assertEqual(preview(lights=['none'], cornice='none')['quote']['total'], '28300.00')
        self.assertEqual(preview(material='fabric')['quote']['total'], '55300.00')
        self.assertEqual(preview(width='2')['quote']['total'], '31900.00')
        self.assertIsNone(preview(material='pvc_gloss')['quote']['total'])

    def test_preview_is_partial_but_submission_and_final_estimate_stay_strict(self):
        response = self.client.post(reverse('estimate'), {'schema': 'v2', 'preview': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['quote']['total'])
        self.assertEqual(response.json()['quote']['items'], [])
        self.assertEqual(self.client.post(reverse('estimate'), {'schema': 'v2'}).status_code, 400)
        self.assertEqual(self.client.post(reverse('estimate'), {'schema': 'v2', 'preview': '1', 'size_mode': 'dimensions', 'shape': 'rectangle', 'length': 'Infinity'}).status_code, 400)

    def test_preview_matches_final_and_uses_current_version(self):
        data = answers(edge='shadow', lights=['spots'], spots='6')
        preview = self.client.post(reverse('estimate'), {**data, 'preview': '1'}).json()['quote']
        final = self.client.post(reverse('estimate'), data).json()['quote']
        self.assertEqual(preview, final)
        self.version.active = False
        self.version.save()
        rates = default_rates()
        rates['pvc']['amount'] = '700'
        current = PricingVersion.objects.create(title='Updated test rates', rates=rates, active=True)
        updated = self.client.post(reverse('estimate'), {**data, 'preview': '1'}).json()['quote']
        self.assertEqual(updated['version'], current.pk)
        self.assertEqual(updated['total'], '32000.00')
