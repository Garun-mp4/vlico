"""Owner-approved partnership messaging, 18 November 2026."""
from urllib.parse import urlencode


def partner_url(channel):
    return "https://vlico39.ru/partners/?" + urlencode({
        "utm_source": channel, "utm_medium": "messenger", "utm_campaign": "partner_network",
    })


def first_message(props, channel):
    segment = props.get("partnersegment", "").casefold()
    opening = "Здравствуйте! Я Виктория, виртуальный менеджер студии потолочных решений VLICO."
    company = " ".join(str(props.get("partnercompany") or "").split())[:120]
    if company:
        opening += f" Обращаюсь по сотрудничеству с компанией «{company}»."
    if "дизайн" in segment:
        pitch = ("Помогаем дизайнерам реализовывать теневые потолки, световые линии, треки и скрытые карнизы. "
                 "Можем бесплатно посмотреть чертёж сложного потолка и предложить вариант исполнения.")
        question = "Интересен такой формат сотрудничества?"
    elif "прораб" in segment or "бригад" in segment:
        pitch = ("Выполняем современные натяжные потолки в Калининграде и области. "
                 "Можем подключаться к вашим объектам как профильный подрядчик по потолкам и свету.")
        question = "Актуально для вас сотрудничество по потолкам?"
    else:
        pitch = ("Берём потолочную часть строительных и отделочных проектов — от технических решений до монтажа. "
                 "Если есть текущий проект, можем бесплатно разобрать потолочный узел и предложить вариант исполнения.")
        question = "Было бы интересно обсудить сотрудничество?"
    return f"{opening}\n\n{pitch}\n\nПримеры работ: {partner_url(channel)}\n\n{question}"


FOLLOWUP = (
    "Здравствуйте! Возвращаюсь к предложению VLICO по потолкам и встроенному освещению. "
    "Если сейчас есть проект со сложным потолочным узлом, можем бесплатно разобрать его со специалистом. "
    "Актуально обсудить?"
)
