import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError


QUICK_CALCULATOR_SCHEMA = "quick-v1"
OBJECT_TYPES = (
    ("apartment", "Квартира"),
    ("house", "Дом"),
    ("separate_room", "Отдельное помещение"),
)
SOLUTIONS = (
    ("classic", "Классическое"),
    ("shadow_floating", "Теневое / парящее"),
    ("designer_light", "Дизайнерское со светом"),
    ("consultation", "Нужна консультация"),
)
AREA_INPUT = re.compile(r"\d{1,5}(?:[.,]\d{1,2})?\Z")


class QuickCalculatorForm(forms.Form):
    object_type = forms.ChoiceField(
        label="Тип помещения",
        choices=OBJECT_TYPES,
        widget=forms.RadioSelect,
    )
    area_m2 = forms.CharField(
        label="Площадь потолка, м²",
        max_length=8,
        widget=forms.TextInput(attrs={
            "class": "quick-calculator__control",
            "inputmode": "decimal",
            "autocomplete": "off",
            "placeholder": "Например, 24,5",
            "pattern": r"\d{1,5}([.,]\d{1,2})?",
            "aria-describedby": "quick-area-help",
        }),
    )
    solution = forms.ChoiceField(
        label="Какое решение рассматриваете?",
        choices=SOLUTIONS,
        widget=forms.RadioSelect,
    )

    def clean_area_m2(self):
        raw = self.cleaned_data["area_m2"].strip()
        if not AREA_INPUT.fullmatch(raw):
            raise ValidationError("Введите площадь числом, например 24 или 24,5.")
        try:
            area = Decimal(raw.replace(",", "."))
        except InvalidOperation:
            raise ValidationError("Введите корректную площадь потолка.") from None
        if not area.is_finite() or area < Decimal("0.1") or area > Decimal("10000"):
            raise ValidationError("Укажите площадь от 0,1 до 10 000 м².")
        return area


def quick_snapshot(cleaned_data):
    area = cleaned_data["area_m2"]
    return {
        "schema": QUICK_CALCULATOR_SCHEMA,
        "inputs": {
            "object_type": cleaned_data["object_type"],
            "area_m2": format(area.normalize(), "f"),
            "solution": cleaned_data["solution"],
        },
    }


def quick_input_rows(inputs):
    object_type = dict(OBJECT_TYPES).get(inputs.get("object_type"), inputs.get("object_type") or "Не указано")
    solution = dict(SOLUTIONS).get(inputs.get("solution"), inputs.get("solution") or "Не указано")
    area = inputs.get("area_m2")
    try:
        area = format(Decimal(str(area)).normalize(), "f").replace(".", ",") + " м²"
    except (InvalidOperation, TypeError, ValueError):
        area = f"{area or 'Не указана'} м²" if area else "Не указана"
    return [
        ("Тип помещения", object_type),
        ("Площадь потолка", area),
        ("Рассматриваемое решение", solution),
    ]
