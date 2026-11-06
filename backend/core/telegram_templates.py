from decimal import Decimal
from html import escape

from django.utils import timezone

from .configurator import ConfiguratorForm, FEATURES, LIGHTS, STEP_FIELDS
from .lead_forms import KINDS
from .pricing import CalculationForm


def lead_title(lead):
    label = "Калькулятор" if lead.kind == "calculator" else dict(KINDS).get(lead.kind, lead.kind)
    return f"Новая заявка №{str(lead.pk)[:8]} · {label}"


def number(value):
    whole, _, fraction = f"{Decimal(value):,f}".partition(".")
    fraction = fraction.rstrip("0")
    return whole.replace(",", " ") + (f",{fraction}" if fraction else "")


def measured(value, unit, missing):
    return f"{number(value)} {unit}" if value is not None else missing


def calculator_steps(inputs):
    def label(key):
        return dict(ConfiguratorForm.base_fields[key].choices).get(inputs[key], inputs[key])

    room = label("room")
    if inputs.get("room_other"):
        room += f" — {inputs['room_other']}"

    dimensions = [f"Форма: {label('shape').lower()}"]
    if inputs.get("length") is not None and inputs.get("width") is not None:
        dimensions.append(f"Длина × ширина: {number(inputs['length'])} × {number(inputs['width'])} м")
    if inputs.get("area") is None:
        dimensions.append(f"Примерная площадь: {label('area_range')}" if inputs.get("area_range") else "Размеры неизвестны")
    else:
        dimensions.append(f"Площадь: {number(inputs['area'])} м²")
        dimensions.append(f"Периметр: {measured(inputs.get('perimeter'), 'м', 'не указан')}")

    def options(key, choices, quantities):
        lines = []
        for code in inputs[key]:
            title = dict(choices)[code]
            if code in quantities:
                unit, missing = quantities[code]
                title += f" — {measured(inputs.get(code), unit, missing)}"
            lines.append(title)
        return "\n".join(f"• {line}" for line in lines) if len(lines) > 1 else lines[0]

    lighting = options("lights", LIGHTS, {
        "spots": ("шт.", "количество не указано"),
        "light_lines": ("м", "длина не указана"),
        "tracks": ("м", "длина не указана"),
        "chandeliers": ("шт.", "количество не указано"),
        "led": ("м", "длина не указана"),
    })
    curtains = label("cornice")
    if inputs["cornice"] in {"standard", "hidden"}:
        curtains += f" — {measured(inputs.get('cornices'), 'м', 'длина не указана')}"
    installation = options("features", FEATURES, {
        "pipes": ("шт.", "количество не указано"),
        "vents": ("шт.", "количество не указано"),
    })
    location = label("location")
    if inputs.get("locality"):
        location += f" · {inputs['locality']}"

    surface = dict(ConfiguratorForm.base_fields["material"].choices)[inputs["surface"]]
    answers = (room, "\n".join(dimensions), surface, label("edge"), lighting, curtains, installation, location)
    return [(f"{index}. {step[0]}", answer)
            for index, (step, answer) in enumerate(zip(STEP_FIELDS, answers, strict=True), 1)]


def saved_estimate_steps(inputs):
    lines = []
    for key, field in CalculationForm.base_fields.items():
        value = inputs.get(key)
        if value is not None:
            value = dict(field.choices).get(value, value) if hasattr(field, "choices") else number(value)
            lines.append(f"{field.label}: {value}")
    return [("Параметры расчёта", "\n".join(lines))]


def message_blocks(lead):
    # Each block carries its plain text so splitting uses Telegram's length after markup parsing.
    blocks = []

    def add(title="", body="", style=""):
        plain = "\n".join(filter(None, (title, body)))
        html = "\n".join(filter(None, (f"<b>{escape(title)}</b>" if title else "", escape(body))))
        if style:
            html = f"<{style}>{html}</{style.split()[0]}>"
        blocks.append((plain, html))

    contact = [f"Клиент: {lead.name}", f"Контакт: {lead.contact}"]
    if lead.kind != "calculator":
        contact.append(f"Решение: {lead.context.get('service_title') or 'Нужна помощь с выбором'}")
        for key, label in (("interest", "Интерес"), ("project_title", "Кейс")):
            if lead.context.get(key):
                contact.append(f"{label}: {lead.context[key]}")
    add(lead_title(lead), "\n".join(contact))

    quote = lead.calculation
    if quote:
        total = quote["total"]
        warnings = list(quote.get("warnings", []))
        if "Периметр неизвестен" in warnings and quote["inputs"].get("edge") != "unknown":
            warnings[warnings.index("Периметр неизвестен")] = "Периметр неизвестен, поэтому примыкание не включено в сумму."
        if total is None:
            title = "Нужен индивидуальный расчёт"
        else:
            title = f"Предварительный расчёт: {number(total)} ₽"
            if not quote["complete"]:
                title += " · частичная сумма"
        if quote.get("schema") != "v2" and not quote["complete"]:
            warnings.append("Периметр неизвестен, поэтому примыкание не включено в сумму.")
        add(title, "\n".join(f"• {warning}" for warning in warnings))
        steps = calculator_steps(quote["inputs"]) if quote.get("schema") == "v2" else saved_estimate_steps(quote["inputs"])
        for heading, answer in steps:
            add(heading, answer)
    if lead.comment:
        add("Что нужно учесть", lead.comment)

    if quote and quote["items"]:
        rows = []
        for item in quote["items"]:
            price = f"{number(item['unit_price'])} ₽ за {item['unit']}"
            amount = (f"{number(item['quantity'])} {item['unit']} × {number(item['unit_price'])} ₽ = {number(item['total'])} ₽"
                      if item["total"] is not None else f"{price} · количество не указано")
            rows.append(f"• {item['title']}: {amount}")
        add("Расшифровка расчёта", "\n".join([*rows, "", quote["exclusions"]]), "blockquote expandable")
    elif quote:
        add("Что не входит в расчёт", quote["exclusions"])

    source = "Калькулятор" if lead.kind == "calculator" else ("Главная" if lead.source_page in {"", "/"} else lead.source_page)
    add(body=f"{source} · {timezone.localtime(lead.created_at):%d.%m.%Y, %H:%M}", style="i")
    return blocks


def utf16_length(text):
    return len(text.encode("utf-16-le")) // 2


def message_parts(lead):
    parts = []
    current, length = [], 0
    for plain, html in message_blocks(lead):
        size = utf16_length(plain)
        if current and length + 2 + size > 3800:
            parts.append(("\n\n".join(current), length))
            current, length = [], 0
        length += size + (2 if current else 0)
        current.append(html)
    parts.append(("\n\n".join(current), length))
    return parts
