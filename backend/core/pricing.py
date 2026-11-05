from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.core.exceptions import ValidationError
from .models import PricingVersion


# These are provisional rates selected for local review, not a confirmed VLICO price list.
RATE_DEFINITIONS = {
    "pvc": ("ПВХ-полотно и натяжка", "650", "м²", ("м²", "кв. м")),
    "fabric": ("Тканевое полотно и натяжка", "2000", "м²", ("м²", "кв. м")),
    "standard": ("Обычное примыкание", "180", "пог. м", ("пог. м", "м")),
    "shadow": ("Теневое примыкание", "850", "пог. м", ("пог. м", "м")),
    "floating": ("Парящее примыкание", "2000", "пог. м", ("пог. м", "м")),
    "light_lines": ("Световая линия", "2800", "пог. м", ("пог. м", "м")),
    "tracks": ("Магнитный трек", "3500", "пог. м", ("пог. м", "м")),
    "cornices": ("Скрытый карниз", "1500", "пог. м", ("пог. м", "м")),
    "spots": ("Монтаж световой точки с закладной", "450", "шт.", ("шт.", "точка")),
}
EXCLUSIONS = "Светильники, модули треков, блоки питания, электрика и дополнительные работы не включены. Сложная геометрия и состав оборудования уточняются после замера."


def default_rates():
    return {code: {"title": title, "amount": amount, "unit": unit} for code, (title, amount, unit, _) in RATE_DEFINITIONS.items()}


def validate_rates(rates):
    if not isinstance(rates, dict) or set(rates) != set(RATE_DEFINITIONS):
        raise ValidationError("Нужен полный набор ставок калькулятора.")
    cleaned = {}
    for code, (_, _, _, units) in RATE_DEFINITIONS.items():
        row = rates[code]
        try:
            amount = Decimal(str(row["amount"]))
            title, unit = row["title"].strip(), row["unit"]
            if not amount.is_finite() or amount < 0 or amount > 1000000 or amount != amount.quantize(Decimal(".01")):
                raise ValueError
            if not title or len(title) > 120 or unit not in units:
                raise ValueError
        except (KeyError, TypeError, ValueError, ArithmeticError, AttributeError):
            raise ValidationError("Проверьте название, единицу и неотрицательную цену каждой позиции.")
        cleaned[code] = {"title": title, "amount": str(amount.quantize(Decimal(".01"))), "unit": unit}
    return cleaned


class CalculationForm(forms.Form):
    area = forms.DecimalField(label="Площадь, м²", min_value=Decimal("0.1"), max_value=10000, max_digits=8, decimal_places=2)
    material = forms.ChoiceField(label="Материал", choices=[("pvc", "ПВХ"), ("fabric", "Ткань")])
    edge = forms.ChoiceField(label="Примыкание", choices=[("standard", "Обычное"), ("shadow", "Теневое"), ("floating", "Парящее")])
    perimeter = forms.DecimalField(label="Периметр, м", required=False, min_value=Decimal("0.1"), max_value=10000, max_digits=8, decimal_places=2,
        help_text="Если не знаете, оставьте пустым. Стоимость примыкания тогда не войдёт в сумму.")
    light_lines = forms.DecimalField(label="Световые линии, м", required=False, min_value=0, max_value=1000, max_digits=7, decimal_places=2)
    tracks = forms.DecimalField(label="Магнитные треки, м", required=False, min_value=0, max_value=1000, max_digits=7, decimal_places=2)
    cornices = forms.DecimalField(label="Скрытые карнизы, м", required=False, min_value=0, max_value=1000, max_digits=7, decimal_places=2)
    spots = forms.IntegerField(label="Световые точки, шт.", required=False, min_value=0, max_value=1000)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field, (forms.DecimalField, forms.IntegerField)):
                field.widget.attrs.update(inputmode="decimal" if name != "spots" else "numeric")
            if name in {"light_lines", "tracks", "cornices", "spots"}:
                field.widget.attrs["placeholder"] = "0"


def priced_item(code, quantity, rates):
    row = rates[code]
    total = None if quantity is None else str((Decimal(quantity) * Decimal(row['amount'])).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    return {'code': code, 'title': row['title'], 'quantity': str(quantity) if quantity is not None else None,
            'unit': row['unit'], 'unit_price': row['amount'], 'total': total}


def calculate(cleaned, version=None):
    version = version or PricingVersion.objects.get(active=True)
    rates = validate_rates(version.rates)
    selected = [(cleaned["material"], cleaned["area"]), (cleaned["edge"], cleaned.get("perimeter"))]
    selected += [(code, cleaned.get(code) or 0) for code in ("light_lines", "tracks", "cornices", "spots")]
    items = []
    for code, quantity in selected:
        if quantity is None or quantity == 0:
            continue
        items.append(priced_item(code, quantity, rates))
    return {"version": version.pk, "version_title": version.title, "currency": "RUB", "inputs": {k: str(v) if v is not None else None for k, v in cleaned.items()},
        "items": items, "total": str(sum((Decimal(item["total"]) for item in items), Decimal("0.00"))),
        "complete": cleaned.get("perimeter") is not None, "exclusions": EXCLUSIONS}


class RatesForm(forms.Form):
    revision = forms.CharField(widget=forms.HiddenInput)
    title = forms.CharField(label="Название версии", max_length=120)

    def __init__(self, *args, version, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial.update(revision=str(version.pk), title=version.title)
        for code, (title, _, _, units) in RATE_DEFINITIONS.items():
            row = version.rates[code]
            self.fields[code + "_title"] = forms.CharField(label="Название позиции", max_length=120, initial=row["title"])
            self.fields[code + "_amount"] = forms.DecimalField(label="Цена, ₽", min_value=0, max_value=1000000, max_digits=9, decimal_places=2, initial=row["amount"])
            self.fields[code + "_unit"] = forms.ChoiceField(label="Единица", choices=[(unit, unit) for unit in units], initial=row["unit"])

    def rate_rows(self):
        return [(definition[0], self[code + "_title"], self[code + "_amount"], self[code + "_unit"]) for code, definition in RATE_DEFINITIONS.items()]

    def rates(self):
        return validate_rates({code: {key: str(self.cleaned_data[code + "_" + key]) for key in ("title", "amount", "unit")} for code in RATE_DEFINITIONS})
