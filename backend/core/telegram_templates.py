from decimal import Decimal
from html import escape
from django import forms

from django.utils import timezone

from .configurator import ConfiguratorForm, FEATURES, LIGHTS, STEP_FIELDS
from .lead_forms import KINDS
from .pricing import CalculationForm
from .quick_calculator import QUICK_CALCULATOR_SCHEMA, quick_input_rows


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
    output = []
    quantities = {"spots": ("шт.", "количество не указано"), "light_lines": ("м", "длина не указана"),
                  "tracks": ("м", "длина не указана"), "chandeliers": ("шт.", "количество не указано"),
                  "led": ("м", "длина не указана")}
    for index, (name, title, _help, fields) in enumerate(STEP_FIELDS, 1):
        values = []
        for key in fields:
            value = inputs.get(key)
            if value in (None, "", []):
                continue
            field = ConfiguratorForm.base_fields[key]
            if isinstance(field, forms.MultipleChoiceField):
                options = []
                for item in value:
                    text = dict(field.choices).get(item, item)
                    if item in quantities:
                        unit, missing = quantities[item]
                        text += f" — {measured(inputs.get(item), unit, missing)}"
                    options.append(text)
                value = "\n".join(f"• {item}" for item in options) if len(options) > 1 else options[0]
            elif isinstance(field, forms.ChoiceField):
                selected = inputs.get("surface") if key == "material" and inputs.get("surface") else value
                value = dict(field.choices).get(selected, selected)
            if key in {"material", "lights", "features", "location"}:
                values.append(value)
                continue
            label = field.label
            if key.endswith("_area") or key in {"area", "object_area"}:
                value = f"{number(value)} м²"
            values.append(f"{label}: {value}")
        if values:
            output.append((f"{index}. {name}", "\n".join(values)))
    return output


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
        for key, label in (("company", "Компания"), ("contact_method", "Способ связи"), ("interest", "Интерес"), ("project_title", "Кейс")):
            if lead.context.get(key):
                contact.append(f"{label}: {lead.context[key]}")
    add(lead_title(lead), "\n".join(contact))

    quote = lead.calculation
    if quote:
        if quote.get("schema") == QUICK_CALCULATOR_SCHEMA:
            add("Для предварительного расчёта уточним детали", "Сумма не определяется по трём ответам.")
            for label, value in quick_input_rows(quote.get("inputs", {})):
                add(label, value)
        else:
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

    if quote and quote.get("schema") != QUICK_CALCULATOR_SCHEMA and quote["items"]:
        rows = []
        for item in quote["items"]:
            price = f"{number(item['unit_price'])} ₽ за {item['unit']}"
            amount = (f"{number(item['quantity'])} {item['unit']} × {number(item['unit_price'])} ₽ = {number(item['total'])} ₽"
                      if item["total"] is not None else f"{price} · количество не указано")
            rows.append(f"• {item['title']}: {amount}")
        add("Расшифровка расчёта", "\n".join([*rows, "", quote["exclusions"]]), "blockquote expandable")
    elif quote and quote.get("schema") != QUICK_CALCULATOR_SCHEMA:
        add("Что не входит в расчёт", quote["exclusions"])

    source = "Калькулятор" if lead.kind == "calculator" else ("Главная" if lead.source_page in {"", "/"} else lead.source_page)
    add(body=f"{source} · {timezone.localdate(lead.created_at):%d.%m.%Y}", style="i")
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
