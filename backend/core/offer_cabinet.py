import uuid
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST, require_safe
from .lead_cabinet import capability_required
from .models import SalesOffer, OfferPublication
from .eva_delivery import EvaError
from .offers import OfferForm, active_offers, fingerprint, publish_offers, public_invitation


@never_cache
@capability_required("core.view_salesoffer")
@require_safe
def index(request):
    state, _ = OfferPublication.objects.get_or_create(pk=1)
    offers = active_offers()
    return render(request, "cabinet/offers.html", {
        "offers": SalesOffer.objects.all(), "state": state,
        "published": state.fingerprint == fingerprint(offers) and state.published_revision == state.revision, "active_offers": offers,
    })


@never_cache
@capability_required("core.change_salesoffer")
@require_http_methods(["GET", "POST"])
def edit(request, pk=None):
    if pk is None and not request.user.has_perm("core.add_salesoffer"):
        raise PermissionDenied
    state, _ = OfferPublication.objects.get_or_create(pk=1)
    offer = get_object_or_404(SalesOffer, pk=pk) if pk else SalesOffer()
    form = OfferForm(request.POST if request.method == "POST" else None, instance=offer,
                     initial={"revision": str(state.revision)})
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            locked = OfferPublication.objects.select_for_update().get(pk=1)
            if str(locked.revision) != form.cleaned_data["revision"]:
                form.add_error(None, "Реестр изменён в другой вкладке. Скопируйте ваши правки и обновите страницу.")
            else:
                form.save()
                locked.revision = uuid.uuid4()
                locked.save(update_fields=["revision"])
                messages.success(request, "Сохранено. Проверьте предпросмотр и опубликуйте реестр в Eva.")
                return redirect("cabinet_offers")
    return render(request, "cabinet/offer.html", {"form": form, "offer": offer})


@never_cache
@capability_required("core.change_salesoffer")
@require_POST
def publish(request):
    try:
        publish_offers(expected_revision=request.POST.get("revision", ""))
    except (EvaError, KeyError, TypeError) as exc:
        if getattr(exc, "code", "") == "offer_revision_changed":
            messages.error(request, "Реестр изменён. Проверьте актуальную редакцию перед публикацией.")
        else:
            messages.error(request, "Eva не подтвердила публикацию. Проверьте связь и повторите публикацию после сверки. В Eva может действовать предыдущая редакция.")
    else:
        messages.success(request, "Реестр опубликован и проверен в Eva. Приглашение сайта использует эту редакцию.")
    return redirect("cabinet_offers")


@never_cache
@require_safe
def invitation(request):
    return JsonResponse(public_invitation())
