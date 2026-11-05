import re
import uuid
from django import forms
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .models import Lead, Project, Service
from .legal import consent_revision

KINDS = Lead._meta.get_field("kind").choices
TOKEN_SALT = "vlico.lead-submission.v1"


class LeadForm(forms.Form):
    kind = forms.ChoiceField(label="Что вас интересует", choices=KINDS)
    name = forms.CharField(label="Как к вам обращаться", min_length=2, max_length=100, widget=forms.TextInput(attrs={"autocomplete": "name"}))
    contact = forms.CharField(label="Телефон, email или Telegram", max_length=160, widget=forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "+7, email или @username"}))
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
        else:
            self.fields["kind"].choices = [pair for pair in KINDS if pair[0] != "calculator"]
        if not self.is_bound and not self.initial.get("idempotency_key"):
            key = uuid.uuid4()
            self.initial.update(idempotency_key=key, submission_token=signing.dumps(str(key), salt=TOKEN_SALT))

    def clean_contact(self):
        value = self.cleaned_data["contact"].strip()
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

    def clean_legal_version(self):
        if self.cleaned_data["legal_version"] != consent_revision():
            raise ValidationError("Условия обработки данных обновились. Обновите страницу и ознакомьтесь с согласием.")
        return self.cleaned_data["legal_version"]

    def clean(self):
        data = super().clean()
        try:
            signed_key = signing.loads(data.get("submission_token", ""), salt=TOKEN_SALT, max_age=86400)
            if signed_key != str(data.get("idempotency_key")):
                raise signing.BadSignature
        except signing.BadSignature:
            self.add_error(None, "Форма устарела. Обновите страницу и отправьте заявку снова.")
        if data.get("website"):
            self.add_error(None, "Не удалось принять заявку. Проверьте форму.")
        return data
