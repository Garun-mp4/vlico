from hashlib import sha256
from django.conf import settings
from django.template.loader import render_to_string


def legal_context():
    return {
        "legal": settings.LEGAL_OPERATOR,
        "lead_notification_email": settings.LEAD_NOTIFICATION_EMAIL,
        "partner_notification_email": settings.PARTNER_NOTIFICATION_EMAIL,
        "lead_notification_uses_mailru": settings.EMAIL_HOST.lower() == "smtp.mail.ru",
        "lead_notification_uses_spaceweb": settings.EMAIL_HOST.lower() == "smtp.spaceweb.ru",
    }


def consent_record():
    # Preserve the accepted wording and operator details, not only a version label.
    text = render_to_string("site/consent-body.html", legal_context()).strip()
    return {"version": settings.LEGAL_VERSION, "sha256": sha256(text.encode()).hexdigest(), "text": text}


def consent_revision():
    record = consent_record()
    return record["version"] + ":" + record["sha256"]
