"""Approved photo captions for the two VLICO partnership audiences."""
from urllib.parse import urlencode

from .partner_segments import segment_group


def partner_url(channel):
    if channel not in {"whatsapp", "telegram"}:
        raise ValueError("Unsupported partnership channel")
    return "https://vlico39.ru/partners/?" + urlencode({
        "utm_source": channel, "utm_medium": "messenger", "utm_campaign": "partner_network",
    })


def first_message(props, channel):
    group = segment_group(props.get("partnersegment"))
    if group == "designer":
        ending = ", чтобы сохранить эстетику проекта и воплотить его в деталях."
        question = "Подскажите, есть ли у вас сейчас проекты, где мы могли бы быть полезны?"
    elif group == "builder":
        ending = ", включая согласование узлов и координацию с другими работами на объекте."
        question = "Подскажите, есть ли у вас сейчас объекты, где мы могли бы быть полезны?"
    else:
        raise ValueError("Partnership audience requires review")
    marker = "*" if channel == "whatsapp" else "**"
    def bold(text):
        return marker + text + marker
    return (
        "Здравствуйте! 👋\n\n"
        f"Я Виктория, менеджер по партнёрствам студии натяжных потолков {bold('VLICO')}, Калининград.\n\n"
        f"Помогаем {bold('дизайнерам и строительным компаниям')} реализовывать потолочные решения: "
        "теневые системы, световые линии, магнитные треки и скрытые карнизы.\n\n"
        f"{bold('Берём на себя техническую проработку и монтаж')}{ending}\n\n"
        f"📐 {bold('Бесплатно разберём потолочные решения по вашему плану или визуализации')} "
        "и подберём подходящие технические узлы.\n\n"
        f"Наши проекты и возможности:\n{partner_url(channel)}\n\n{question}"
    )


def photo_prompt(content, document_id):
    return (
        f"Первое касание партнёра. Используй доступный документ «VLICO — фото первого партнёрского сообщения» "
        f"(ID {document_id}, режим sendToChat). Отправь его как одну фотографию с текстом ниже в подписи "
        "к изображению, одним сообщением. Используй инструмент отправки документа в чат. "
        "Не отправляй PDF, ссылку на файл вместо фотографии, дополнительные сообщения или другую картинку. "
        "Текст подписи передай дословно, включая абзацы и ссылку; не добавляй свои фразы. "
        "Если инструмент не поддерживает фотографию с подписью, не отправляй текст отдельно и сообщи об ошибке.\n"
        f"Текст подписи:\n{content}"
    )


FOLLOWUP = (
    "Здравствуйте! Возвращаюсь к предложению VLICO по потолкам и встроенному освещению. "
    "Если сейчас есть проект со сложным потолочным узлом, можем бесплатно разобрать его со специалистом. "
    "Актуально обсудить?"
)
