from hashlib import sha256
from django.conf import settings
from django.template.loader import render_to_string


def consent_record():
    # Preserve the accepted wording and operator details, not only a version label.
    text = render_to_string("site/consent-body.html", {"legal": settings.LEGAL_OPERATOR}).strip()
    return {"version": settings.LEGAL_VERSION, "sha256": sha256(text.encode()).hexdigest(), "text": text}


def consent_revision():
    record = consent_record()
    return record["version"] + ":" + record["sha256"]
