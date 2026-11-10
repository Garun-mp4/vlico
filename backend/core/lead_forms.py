import re
import uuid
import warnings
from hashlib import sha256
from pathlib import PurePosixPath
from django import forms
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from PIL import Image, UnidentifiedImageError
from .models import Lead, Project, Service
from .legal import consent_revision

KINDS = Lead._meta.get_field("kind").choices
TOKEN_SALT = "vlico.lead-submission.v1"
MAX_PARTNER_ATTACHMENT_SIZE = 5 * 1024 * 1024
PARTNER_ATTACHMENT_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def partner_attachment_digest(upload):
    digest = sha256()
    total = 0
    upload.seek(0)
    for chunk in upload.chunks():
        total += len(chunk)
        if total > MAX_PARTNER_ATTACHMENT_SIZE:
            upload.seek(0)
            raise ValidationError("Файл проекта не должен превышать 5 МБ.")
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()


def _valid_pdf(data):
    if not re.search(br"%PDF-(?:1\.[0-7]|2\.0)\b", data[:1024]):
        return False
    if re.search(br"/(?:JavaScript|JS|Launch|EmbeddedFile|EmbeddedFiles|RichMedia|OpenAction|AA)\b", data):
        return False
    eof = data.rfind(b"%%EOF")
    if eof < 0 or len(data) - eof > 1024:
        return False
    marker = data.rfind(b"startxref", 0, eof)
    if marker < 0:
        return False
    offset_match = re.match(br"startxref\s+(\d+)\s*$", data[marker:eof].strip())
    if not offset_match:
        return False
    offset = int(offset_match.group(1))
    if offset >= len(data):
        return False
    target = data[offset:offset + 1024].lstrip()
    if target.startswith(b"xref"):
        trailer = data.find(b"trailer", offset)
        return trailer >= 0 and b"/Root" in data[trailer:eof]
    if re.match(br"\d+\s+\d+\s+obj\b", target):
        end = data.find(b"endobj", offset)
        xref_object = data[offset:end] if end >= 0 else b""
        return bool(re.search(br"/Type\s*/XRef\b", xref_object) and b"/Root" in xref_object)
    return False


def validate_partner_attachment(upload):
    if upload.size > MAX_PARTNER_ATTACHMENT_SIZE:
        raise ValidationError("Файл проекта не должен превышать 5 МБ.")
    filename = PurePosixPath(upload.name.replace("\\", "/")).name
    extension = PurePosixPath(filename).suffix.lower()
    expected_type = PARTNER_ATTACHMENT_TYPES.get(extension)
    declared_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if not expected_type or declared_type != expected_type:
        raise ValidationError("Прикрепите проект в формате PDF, JPG или PNG.")

    upload.seek(0)
    if extension == ".pdf":
        data = upload.read()
        valid = _valid_pdf(data)
    else:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                upload.seek(0)
                with Image.open(upload) as image:
                    image_type = "image/jpeg" if image.format == "JPEG" else "image/png" if image.format == "PNG" else ""
                    valid = image_type == expected_type and image.width * image.height <= 50_000_000
                    image.verify()
        except (Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, UnidentifiedImageError):
            valid = False
    upload.seek(0)
    if not valid:
        raise ValidationError("Файл не похож на исправный PDF, JPG или PNG.")
    return upload


class LeadForm(forms.Form):
    kind = forms.ChoiceField(label="Что вас интересует", choices=KINDS)
    name = forms.CharField(label="Как к вам обращаться", min_length=2, max_length=100, widget=forms.TextInput(attrs={"autocomplete": "name"}))
    contact = forms.CharField(label="Телефон, email или Telegram", max_length=160, widget=forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "+7, email или @username"}))
    company = forms.CharField(label="Компания", required=False, max_length=160, widget=forms.TextInput(attrs={"autocomplete": "organization"}))
    attachment = forms.FileField(label="Прикрепить проект", required=False, max_length=255,
        help_text="PDF, JPG или PNG, до 5 МБ. Необязательно.",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"}))
    service = forms.ModelChoiceField(label="Решение", queryset=Service.objects.all().order_by("position", "pk"), required=False, empty_label="Нужна помощь с выбором")
    comment = forms.CharField(label="Что нужно учесть", max_length=1200, required=False, widget=forms.Textarea(attrs={"rows": 3}))
    consent = forms.BooleanField(label="Согласен на обработку имени, контакта, параметров для ответа на заявку")
    project = forms.ModelChoiceField(queryset=Project.objects.filter(status="published"), required=False, widget=forms.HiddenInput)
    interest = forms.CharField(max_length=200, required=False, widget=forms.HiddenInput)
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)
    submission_token = forms.CharField(widget=forms.HiddenInput, max_length=300)
    website = forms.CharField(required=False, max_length=200, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))
    pricing_version = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)
    legal_version = forms.CharField(widget=forms.HiddenInput, max_length=100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["legal_version"] = consent_revision()
        selected_kind = self.data.get("kind") if self.is_bound else self.initial.get("kind")
        if selected_kind == "calculator":
            self.fields["kind"].widget = forms.HiddenInput()
        elif selected_kind == "partner":
            self.fields["kind"].widget = forms.HiddenInput()
            self.fields["name"].label = "Имя"
            self.fields["contact"].label = "Телефон"
            self.fields["contact"].widget.attrs["placeholder"] = "+7 (___) ___-__-__"
        else:
            self.fields["kind"].choices = [pair for pair in KINDS if pair[0] != "calculator"]
        if not self.is_bound and not self.initial.get("idempotency_key"):
            key = uuid.uuid4()
            self.initial.update(idempotency_key=key, submission_token=signing.dumps(str(key), salt=TOKEN_SALT))

    def clean_contact(self):
        value = self.cleaned_data["contact"].strip()
        selected_kind = self.data.get("kind") if self.is_bound else self.initial.get("kind")
        if selected_kind == "partner":
            digits = re.sub(r"\D", "", value)
            if not re.fullmatch(r"[+()0-9\s.\-]+", value) or not 10 <= len(digits) <= 15:
                raise ValidationError("Укажите телефон с кодом страны, например +7 900 000-00-00.")
            return "+" + digits
        if re.fullmatch(r"@[a-zA-Z][a-zA-Z0-9_]{4,31}", value):
            return value
        if "@" in value:
            validate_email(value)
            return value
        digits = re.sub(r"\D", "", value)
        if not re.fullmatch(r"[+()0-9\s.\-]+", value) or not 10 <= len(digits) <= 15:
            raise ValidationError("Укажите телефон с кодом, email или Telegram вида @username.")
        return "+" + digits

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())

    def clean_company(self):
        return " ".join(self.cleaned_data["company"].split())

    def clean_attachment(self):
        upload = self.cleaned_data.get("attachment")
        if upload:
            return validate_partner_attachment(upload)
        return upload

    def clean_legal_version(self):
        if self.cleaned_data["legal_version"] != consent_revision():
            raise ValidationError("Условия обработки данных обновились. Обновите страницу и ознакомьтесь с согласием.")
        return self.cleaned_data["legal_version"]

    def clean(self):
        data = super().clean()
        kind = data.get("kind")
        uploaded_fields = set(self.files.keys())
        if uploaded_fields - {"attachment"}:
            self.add_error(None, "Можно прикрепить только один файл проекта.")
        if len(self.files.getlist("attachment")) > 1:
            self.add_error("attachment", "Прикрепите один файл проекта.")
        if kind != "partner" and (data.get("company") or uploaded_fields):
            self.add_error(None, "Компания и файл доступны только для заявки о сотрудничестве.")
        if kind == "partner" and not data.get("contact"):
            self.add_error("contact", "Укажите телефон для связи.")
        try:
            signed_key = signing.loads(data.get("submission_token", ""), salt=TOKEN_SALT, max_age=86400)
            if signed_key != str(data.get("idempotency_key")):
                raise signing.BadSignature
        except signing.BadSignature:
            self.add_error(None, "Форма устарела. Обновите страницу и отправьте заявку снова.")
        if data.get("website"):
            self.add_error(None, "Не удалось принять заявку. Проверьте форму.")
        return data
