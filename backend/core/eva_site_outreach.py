"""Trusted, form-specific first replies for the Eva WhatsApp task."""
import re

from .quick_calculator import OBJECT_TYPES, SOLUTIONS


TASK_REPLIES = {
    "consultation": "Получил вашу заявку на консультацию с сайта. Подскажите, какой вопрос хотите обсудить в первую очередь?",
    "measurement": "Получил вашу заявку на замер с сайта. Подскажите, в каком районе находится объект и когда вам обычно удобно принять специалиста?",
    "project": "Получил вашу заявку на обсуждение проекта с сайта. Если у вас уже есть план помещения или примеры потолка и света, можете прислать их сюда.",
    "calculator": "Получил ваши данные из калькулятора на сайте. Подскажите, в каком районе находится объект? Это поможет уточнить условия расчёта.",
}


def first_message(lead):
    greeting = "Здравствуйте! Я Артём, ИИ-помощник VLICO."
    reply = TASK_REPLIES[lead.kind]
    if lead.kind == "calculator":
        inputs = lead.calculation.get("inputs", {})
        area = str(inputs.get("area_m2", ""))
        if re.fullmatch(r"\d{1,5}(?:\.\d{1,2})?", area):
            details = [dict(OBJECT_TYPES).get(inputs.get("object_type")), f"{area.replace('.', ',')} м²"]
            solution = dict(SOLUTIONS).get(inputs.get("solution"))
            if solution and inputs.get("solution") != "consultation":
                details.append(solution)
            summary = ", ".join(detail for detail in details if detail)
            reply = f"Получил ваш расчёт с сайта ({summary}). Подскажите, в каком районе находится объект?"
    elif lead.kind == "project" and lead.context.get("project_title"):
        project = " ".join(lead.context["project_title"].split())[:100]
        reply = f"Получил вашу заявку по проекту «{project}». Подскажите, что из этого проекта вы хотели бы повторить у себя?"
    elif lead.kind == "consultation" and lead.context.get("service_title"):
        service = " ".join(lead.context["service_title"].split())[:100]
        reply = f"Получил вашу заявку по услуге «{service}». Подскажите, что хотите уточнить в первую очередь?"
    if lead.comment.strip():
        reply = reply.split(". ", 1)[0] + ". Вижу ваш комментарий к заявке. Если хотите что-то добавить, напишите здесь."
    return f"{greeting} {reply}"
