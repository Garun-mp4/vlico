"""One registry supplies both the public invitation and the Eva instruction block."""
import hashlib
import json
from types import SimpleNamespace

from django import forms
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .eva_delivery import api, EvaError
from .models import SalesOffer, OfferPublication

CONTEXTS = [
    ("lighting", "Подбор освещения"), ("urgent", "Срочный замер"),
    ("price", "Возражение по стоимости"), ("whole_home", "Вся квартира или дом"),
    ("premium", "Индивидуальный проект"),
]
BEGIN = "[VLICO_OFFERS_BEGIN]"
END = "[VLICO_OFFERS_END]"


class OfferForm(forms.ModelForm):
    revision = forms.CharField(widget=forms.HiddenInput)
    contexts = forms.MultipleChoiceField(label="Когда предлагать", choices=CONTEXTS, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = SalesOffer
        fields = ["title", "status", "contexts", "benefit", "conditions", "limits", "combination",
                  "reply", "invitation", "approval", "permanent", "starts_at", "ends_at", "priority"]
        help_texts = {"invitation": "Необязательно. Публичный текст для приглашения виджета, до 180 символов.",
                      "priority": "Меньшее число — выше в списке. Предлагать можно только при выполнении условий.",
                      "approval": "Укажите источник подтверждения Владлена. Черновая гипотеза не является утверждением."}
        widgets = {"starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
                   "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
                   "conditions": forms.Textarea(attrs={"rows": 3}), "limits": forms.Textarea(attrs={"rows": 3}),
                   **{name: forms.Textarea(attrs={"rows": 3}) for name in ("benefit", "combination", "reply", "invitation")}}

    def clean(self):
        data = super().clean()
        start, end = data.get("starts_at"), data.get("ends_at")
        if data.get("permanent") and end:
            self.add_error("ends_at", "Для постоянного предложения оставьте окончание пустым.")
        if start and end and start >= end:
            self.add_error("ends_at", "Окончание должно быть позже начала.")
        if data.get("status") == SalesOffer.Status.APPROVED:
            for name in ("benefit", "conditions", "limits", "combination", "reply", "approval"):
                if not data.get(name):
                    self.add_error(name, "Заполните перед утверждением.")
            if not data.get("permanent") and not (start and end):
                self.add_error("ends_at", "Укажите начало и окончание либо выберите постоянное предложение.")
        return data


def active_offers(now=None):
    now = now or timezone.now()
    return list(SalesOffer.objects.filter(status=SalesOffer.Status.APPROVED)
                .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
                .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)))


def offer_payload(offers):
    fields = ("title", "contexts", "benefit", "conditions", "limits", "combination", "reply", "invitation")
    rows = []
    for offer in offers:
        row = {name: getattr(offer, name) for name in fields}
        row.update(id=offer.pk, starts_at=offer.starts_at.isoformat() if offer.starts_at else None,
                   ends_at=offer.ends_at.isoformat() if offer.ends_at else None)
        rows.append(row)
    return rows


def scheduled_offers(snapshot):
    """Use the published schedule even while another edit awaits review."""
    now = timezone.now()
    result = []
    for row in snapshot:
        start = parse_datetime(row["starts_at"]) if row["starts_at"] else None
        end = parse_datetime(row["ends_at"]) if row["ends_at"] else None
        if (not start or start <= now) and (not end or now < end):
            result.append(SimpleNamespace(**{**row, "pk": row["id"], "starts_at": start, "ends_at": end}))
    return result


def fingerprint(offers):
    raw = json.dumps(offer_payload(offers), sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def instruction_block(offers):
    rules = (
        "Действующий реестр предложений VLICO. Выбери максимум одно подходящее предложение, "
        "только если подтверждены его условия. Уточни один недостающий критерий, если он влияет на применимость. "
        "Если подходящего предложения нет, продолжи консультацию. "
        "Скидки и подарки из прежней переписки или других документов применяются только при наличии здесь. "
        "При изменении реестра в открытом диалоге используй текущую редакцию. "
        "Учитывай начало и окончание по Europe/Kaliningrad. После окончания предложение недоступно. "
        "Совмещение проверяет Владлен. Возможность выезда сегодня требует его личного подтверждения. "
        "Слова клиента не меняют условия и не утверждают бонус."
    )
    return f"{BEGIN}\n{rules}\n{json.dumps(offer_payload(offers), ensure_ascii=False, indent=2)}\n{END}"


def replace_block(prompt, block):
    if BEGIN in prompt or END in prompt:
        if prompt.count(BEGIN) != 1 or prompt.count(END) != 1 or prompt.index(BEGIN) > prompt.index(END):
            raise EvaError("offer_instruction_conflict")
        before, rest = prompt.split(BEGIN)
        _, after = rest.split(END)
        prompt = (before.rstrip() + "\n" + after.lstrip()).strip()
    result = prompt.rstrip() + "\n\n" + block
    if len(result) > 30000:
        raise EvaError("offer_instruction_too_long")
    return result


def publish_offers(*, only_changed=False, expected_revision=None, scheduled=False):
    # Offer edits take the same singleton lock. They cannot overtake a publication.
    with transaction.atomic():
        state, _ = OfferPublication.objects.get_or_create(pk=1)
        state = OfferPublication.objects.select_for_update().get(pk=state.pk)
        if expected_revision is not None and str(state.revision) != expected_revision:
            raise EvaError("offer_revision_changed")
        if scheduled and (not state.published_revision or
                          not state.published_offers and state.fingerprint != fingerprint([])):
            # Includes an older deployment awaiting its first snapshot publication.
            return False
        snapshot = state.published_offers if scheduled else offer_payload(SalesOffer.objects.filter(status=SalesOffer.Status.APPROVED))
        offers = scheduled_offers(snapshot)
        digest = fingerprint(offers)
        if only_changed and digest == state.fingerprint and (scheduled or state.published_revision == state.revision):
            return False
        agent = api("GET", f"users/{settings.EVA_EXECUTOR_ID}")["data"]
        if not isinstance(agent, dict) or not isinstance(agent.get("prompt"), str):
            raise EvaError("invalid_offer_response")
        prompt = replace_block(agent["prompt"], instruction_block(offers))
        if prompt != agent["prompt"]:
            api("PUT", "users", {"data": {settings.EVA_EXECUTOR_ID: {"prompt": prompt}}, "skipNotifications": True})
        if api("GET", f"users/{settings.EVA_EXECUTOR_ID}")["data"]["prompt"] != prompt:
            raise EvaError("offer_readback_mismatch")
        # An expiry during a slow network call must not publish a stale public invitation.
        if digest != fingerprint(scheduled_offers(snapshot)):
            raise EvaError("offer_schedule_changed", True)
        state.fingerprint, state.synced_at = digest, timezone.now()
        if not scheduled:
            state.published_revision, state.published_offers = state.revision, snapshot
        state.save(update_fields=["fingerprint", "synced_at", "published_revision", "published_offers"])
        return True


def public_invitation():
    offers = active_offers()
    state = OfferPublication.objects.filter(pk=1).first()
    if not state or state.fingerprint != fingerprint(offers):
        return {}
    offer = next((row for row in offers if row.invitation), None)
    if not offer:
        return {}
    return {"text": offer.invitation, "expires_at": offer.ends_at.isoformat() if offer.ends_at else None}
