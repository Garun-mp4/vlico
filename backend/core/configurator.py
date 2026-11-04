"""Typed answers, conditional normalization and pricing for the one-room configurator."""
from decimal import Decimal, ROUND_HALF_UP
from django import forms
from .pricing import CalculationForm, calculate


ROOMS = [("living", "Гостиная"), ("bedroom", "Спальня"), ("kitchen", "Кухня"), ("bath", "Ванная / санузел"), ("hall", "Коридор / прихожая"), ("other", "Другое помещение")]
SHAPES = [("rectangle", "Прямоугольная"), ("l", "Г-образная"), ("complex", "Сложная"), ("unknown", "Не знаю")]
LIGHTS = [("spots", "Точечные светильники"), ("light_lines", "Световые линии"), ("tracks", "Магнитные треки"), ("chandeliers", "Люстра / подвес"), ("led", "Контурная подсветка"), ("none", "Без нового освещения"), ("unknown", "Пока не определился")]
FEATURES = [("complex", "Дополнительные углы"), ("pipes", "Трубы через потолок"), ("vents", "Вентиляция / датчики"), ("levels", "Несколько уровней"), ("tiles", "Плитка в зоне крепления"), ("height", "Сохранить высоту"), ("none", "Ничего из перечисленного"), ("unknown", "Не знаю")]
# Public surface choices map to material groups; a finish is not another tariff.
SURFACES = {
    "pvc": ("pvc", "matte", "Матовый ПВХ"),
    "pvc_satin": ("pvc", "satin", "Сатиновый ПВХ"),
    "pvc_gloss": ("pvc", "gloss", "Глянцевый ПВХ"),
    "fabric": ("fabric", "textile", "Тканевый потолок"),
    "unknown": ("unknown", "unknown", "Нужна помощь с выбором"),
}


def choice(label, choices):
    return forms.ChoiceField(label=label, choices=choices, widget=forms.RadioSelect)


def number(label, maximum=1000, integer=False):
    cls = forms.IntegerField if integer else forms.DecimalField
    opts = {} if integer else {"max_digits": 10, "decimal_places": 2}
    return cls(label=label, required=False, min_value=Decimal("0.1") if not integer else 1,
               max_value=maximum, widget=forms.TextInput(attrs={"inputmode": "numeric" if integer else "decimal", "placeholder": "Пока не знаю"}), **opts)


class ConfiguratorForm(forms.Form):
    schema = forms.CharField(initial="v2", widget=forms.HiddenInput)
    room = choice("Для какого помещения выбираете потолок?", ROOMS)
    room_other = forms.CharField(label="Что за помещение?", required=False, max_length=100)
    size_mode = choice("Как удобнее указать размеры?", [("dimensions", "Знаю длину и ширину"), ("area", "Знаю площадь"), ("unknown", "Не знаю размеры")])
    shape = choice("Форма помещения", SHAPES)
    length = number("Длина, м", 100)
    width = number("Ширина, м", 100)
    area = number("Площадь, м²", 10000)
    perimeter = number("Периметр, м", 10000)
    area_range = forms.ChoiceField(label="Примерная площадь", required=False, choices=[("", "Не знаю"), ("small", "До 10 м²"), ("medium", "10–20 м²"), ("large", "20–35 м²"), ("xl", "Более 35 м²")])
    material = choice("Какую поверхность предпочитаете?", [(code, row[2]) for code, row in SURFACES.items()])
    edge = choice("Как потолок встретится со стеной?", [("standard", "Классическое примыкание"), ("shadow", "Теневое примыкание"), ("floating", "Парящий потолок"), ("unknown", "Пока не знаю")])
    lights = forms.MultipleChoiceField(label="Какое освещение планируете?", choices=LIGHTS, widget=forms.CheckboxSelectMultiple)
    spots = number("Количество светильников", integer=True)
    light_lines = number("Общая длина световых линий, м")
    tracks = number("Общая длина треков, м")
    chandeliers = number("Количество люстр", integer=True)
    led = number("Длина контура, м")
    cornice = choice("Как оформим шторы?", [("standard", "Потолочный карниз"), ("hidden", "Скрытый карниз / ниша"), ("wall", "Карниз уже на стене"), ("none", "Карниз не нужен"), ("unknown", "Пока не определился")])
    cornices = number("Длина карниза, м")
    features = forms.MultipleChoiceField(label="Особенности монтажа", choices=FEATURES, widget=forms.CheckboxSelectMultiple)
    pipes = number("Сколько труб?", integer=True)
    vents = number("Сколько элементов вентиляции / датчиков?", integer=True)
    location = choice("Где планируется монтаж?", [("city", "Калининград"), ("region", "Калининградская область"), ("other", "Другой регион")])
    locality = forms.CharField(label="Населённый пункт", required=False, max_length=120)

    def __init__(self, *args, **kwargs):
        if args and args[0] is not None:
            data = args[0].copy()
            # Exclude stale dependent values before validation, including malformed ones.
            live = active_fields(data, data.getlist if hasattr(data, "getlist") else lambda key: data.get(key, []))
            for key in self.base_fields:
                if key not in live:
                    data.pop(key, None)
                elif isinstance(data.get(key), str) and isinstance(self.base_fields[key], forms.DecimalField):
                    data[key] = data[key].replace(",", ".")
            args = (data, *args[1:])
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if data.get("schema") != "v2":
            self.add_error("schema", "Обновите страницу калькулятора.")
        for name in ("lights", "features"):
            values = data.get(name, [])
            if len(values) > 1 and set(values) & {"none", "unknown"}:
                self.add_error(name, "Выберите конкретные варианты либо один ответ «нет / не знаю».")
        if data.get("size_mode") == "dimensions" and data.get("shape") == "rectangle":
            for name in ("length", "width"):
                if data.get(name) is None:
                    self.add_error(name, "Укажите размер или выберите другой способ ввода.")
            if data.get("length") and data.get("width"):
                data["area"] = (data["length"] * data["width"]).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
                data["perimeter"] = 2 * (data["length"] + data["width"])
                if data["area"] < Decimal(".1"):
                    self.add_error("length", "Площадь должна быть не меньше 0,1 м².")
        elif data.get("size_mode") != "unknown" and data.get("area") is None:
            self.add_error("area", "Укажите площадь или выберите «Не знаю размеры».")
        if data.get("location") in {"region", "other"} and not data.get("locality"):
            self.add_error("locality", "Укажите населённый пункт.")
        return data


def active_fields(data, getlist):
    live = {"schema", "room", "size_mode", "shape", "material", "edge", "lights", "cornice", "features", "location"}
    if data.get("room") == "other": live.add("room_other")
    if data.get("size_mode") == "unknown": live.add("area_range")
    elif data.get("size_mode") == "dimensions" and data.get("shape") == "rectangle": live.update(("length", "width"))
    else: live.update(("area", "perimeter"))
    live.update(set(getlist("lights")) & {"spots", "light_lines", "tracks", "chandeliers", "led"})
    if data.get("cornice") in {"standard", "hidden"}: live.add("cornices")
    live.update(set(getlist("features")) & {"pipes", "vents"})
    if data.get("location") in {"region", "other"}: live.add("locality")
    return live


def calculation_form(data=None, **kwargs):
    return ConfiguratorForm(data, **kwargs) if data is not None and data.get("schema") == "v2" else CalculationForm(data, **kwargs)


def calculate_answers(data, version=None):
    if data.get("schema") != "v2":
        return calculate(data, version)
    warnings = []
    material, texture, _ = SURFACES[data["material"]]
    unpriced_finish = texture in {"satin", "gloss"}
    if unpriced_finish:
        warnings.append("Доступность и стоимость выбранной фактуры уточним по образцам. Отдельная ставка пока не утверждена.")
    for name, label in (("area", "Площадь неизвестна"), ("perimeter", "Периметр неизвестен")):
        if not data.get(name): warnings.append(label)
    if data["material"] == "unknown": warnings.append("Нужно выбрать материал")
    if data["edge"] == "unknown": warnings.append("Нужно выбрать примыкание")
    if data["shape"] != "rectangle": warnings.append("Геометрия требует проверки на замере")
    if data["material"] == "fabric" and data["edge"] in {"shadow", "floating"}:
        warnings.append("Совместимость ткани и профиля подтвердит специалист")
    normalized = {"area": data.get("area") or Decimal(0), "material": material if material != "unknown" else "pvc",
                  "edge": data["edge"] if data["edge"] != "unknown" else "standard", "perimeter": data.get("perimeter") if data["edge"] != "unknown" else None}
    for code in ("spots", "light_lines", "tracks"):
        normalized[code] = data.get(code) if code in data["lights"] else 0
        if code in data["lights"] and not data.get(code): warnings.append(f"Неизвестно количество: {dict(LIGHTS)[code]}")
    normalized["cornices"] = data.get("cornices") if data["cornice"] == "hidden" else 0
    if data["cornice"] == "hidden" and not data.get("cornices"): warnings.append("Неизвестна длина скрытого карниза")
    if data["cornice"] in {"standard", "unknown"}: warnings.append("Карниз: стоимость уточняется отдельно")
    if "chandeliers" in data["lights"]: warnings.append("Монтаж люстры: отдельного тарифа нет, уточним стоимость")
    if "led" in data["lights"]:
        warnings.append("Контур парящего профиля учтён в примыкании; оборудование уточняется отдельно" if data["edge"] == "floating" else "Контурная подсветка: стоимость уточняется отдельно")
    if "unknown" in data["lights"]: warnings.append("Состав освещения ещё не выбран")
    if set(data["features"]) - {"none", "height"}: warnings.append("Особенности монтажа: стоимость уточняется после замера")
    if data["location"] != "city": warnings.append("Выезд и возможность монтажа согласуем отдельно")
    quote = calculate(normalized, version)
    unknown_base = not data.get("area") or material == "unknown" or unpriced_finish
    if unknown_base:
        quote["items"] = []
        quote["total"] = None
    quote.update(complete=not warnings, warnings=warnings, configuration=summary(data),
                 inputs={key: str(value) if isinstance(value, Decimal) else value for key, value in data.items()}, schema="v2")
    quote["inputs"].update(material=material, texture=texture, surface=data["material"])
    return quote


def summary(data):
    rows = []
    for name, field in ConfiguratorForm.base_fields.items():
        value = data.get(name)
        if name == "schema" or value is None or value == "" or value == []: continue
        if isinstance(field, forms.MultipleChoiceField): value = ", ".join(dict(field.choices)[v] for v in value)
        elif isinstance(field, forms.ChoiceField): value = dict(field.choices).get(value, value)
        rows.append({"label": field.label, "value": str(value)})
    return rows


STEP_FIELDS = [
    ("Помещение", "Для какого помещения выбираете потолок?", "Тип комнаты не меняет цену сам по себе.", ["room", "room_other"]),
    ("Размеры", "Какие размеры у помещения?", "Примерных размеров достаточно. Точные уточним на замере.", ["size_mode", "shape", "length", "width", "area", "perimeter", "area_range"]),
    ("Поверхность", "Какую поверхность предпочитаете?", "Одна комната, один ракурс — меняется только потолок. Сравните отражения и характер поверхности.", ["material"]),
    ("Примыкание", "Как потолок встретится со стеной?", "Сравните один и тот же угол комнаты: закрытый стык, теневой зазор или мягкая подсветка.", ["edge"]),
    ("Освещение", "Какое освещение планируете?", "Одна комната с разным светом. Можно выбрать несколько решений. Не знаете количество — оставьте поле пустым.", ["lights", "spots", "light_lines", "tracks", "chandeliers", "led"]),
    ("Шторы", "Как оформим шторы?", "Одна комната с разным оформлением окна. Для потолочного и скрытого карниза укажите длину, если знаете.", ["cornice", "cornices"]),
    ("Монтаж", "Что нужно учесть при монтаже?", "Особенности передадим специалисту. Доплаты без подтверждённых ставок не начисляем.", ["features", "pipes", "vents"]),
    ("Расположение", "Где планируется монтаж?", "Замер в Калининграде бесплатный. Условия выезда по области обсудим отдельно.", ["location", "locality"]),
]


def configurator_context(request, form=None, lead_form=None, quote=None, errors=None):
    from .lead_views import initial_lead_form
    from .models import PricingVersion
    form = form or ConfiguratorForm(auto_id="config_%s")
    lead_form = lead_form or initial_lead_form(request, "calculator")
    lead_form.auto_id = "calc_contact_%s"
    version = PricingVersion.objects.filter(active=True).first()
    lead_form.initial["pricing_version"] = version.pk if version else ""
    fields = {}
    for name, field in form.fields.items():
        fields[name] = {"label": field.label, "kind": "multi" if isinstance(field, forms.MultipleChoiceField) else "choice" if isinstance(field, forms.ChoiceField) else "number" if isinstance(field, (forms.DecimalField, forms.IntegerField)) else "text",
                        "choices": list(field.choices) if hasattr(field, "choices") else [], "max": getattr(field, "max_value", None), "max_length": getattr(field, "max_length", None), "integer": isinstance(field, forms.IntegerField) and not isinstance(field, forms.DecimalField)}
    # Schema is presentation metadata; bootstrap restores the quote, never lead contacts.
    return {"config_form": form, "calc_lead_form": lead_form, "calc_quote": quote, "calc_errors": errors or {}, "calculator_available": version is not None,
            "config_bootstrap": {"bound": form.is_bound, "quote": quote, "errors": {**dict(form.errors), **(errors or {})}},
            "config_schema": {"steps": [{"name": name, "title": title, "help": help_text, "fields": names} for name, title, help_text, names in STEP_FIELDS], "fields": fields},
            "config_steps": [(title, [form[name] for name in names]) for _, title, _, names in STEP_FIELDS]}
