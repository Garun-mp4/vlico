from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .lead_cabinet import capability_required
from .models import EvaPartnerCampaign, EvaPartnerSend, EvaPartnerReport


@never_cache
@capability_required("core.view_lead")
@require_http_methods(["GET", "POST"])
def index(request):
    campaign, _ = EvaPartnerCampaign.objects.get_or_create(pk=1)
    if request.method == "POST":
        if not request.user.has_perm("core.change_lead"):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        if request.POST.get("action") == "pause":
            with transaction.atomic():
                EvaPartnerCampaign.objects.select_for_update().get(pk=1)
                EvaPartnerCampaign.objects.filter(pk=1).update(enabled=False)
            from .partner_campaign import configuration, task_rows, update, cancel
            from .eva_delivery import EvaError
            try:
                for pair in configuration().values():
                    for task_id in pair:
                        update("tasks", task_id, enabled=False)
                        cancel(task_rows(task_id))
                messages.success(request, "Кампания приостановлена, ожидающие отправки сняты.")
            except EvaError:
                messages.error(request, "Кампания приостановлена. Отключите задачи в Eva и сверьте оставшуюся очередь.")
        elif request.POST.get("action") == "start":
            if not settings.EVA_PARTNER_PHOTO_PREVIEW_VERIFIED:
                EvaPartnerCampaign.objects.filter(pk=1).update(enabled=False)
                messages.error(request, "Кампания остаётся на паузе: фотография пока приходит файлом. Нужна проверка отображения у получателя.")
                return redirect("cabinet_partners")
            # The owner connects the channels and enables the four sender tasks in Eva.
            from .partner_campaign import configuration, record
            from .eva_delivery import EvaError
            try:
                mapping = configuration()
                for channel, ids in mapping.items():
                    for task_id in ids:
                        task = record("tasks", task_id)
                        if (not task or not task.get("enabled") or len(task.get("channels") or []) != 1
                                or task.get("autoSyncContacts") or task.get("funnelStatusId")):
                            raise EvaError("sender_not_ready")
                EvaPartnerCampaign.objects.filter(pk=1).update(enabled=True)
                messages.success(request, "Кампания включена для проверенных контактов из задачи получателей.")
            except EvaError:
                messages.error(request, "Подключите рабочие каналы и проверьте четыре задачи отправки в Eva.")
        return redirect("cabinet_partners")
    return render(request, "cabinet/partners.html", {
        "campaign": campaign, "reports": EvaPartnerReport.objects.order_by("-day", "period")[:32],
        "photo_preview_verified": settings.EVA_PARTNER_PHOTO_PREVIEW_VERIFIED,
        "exceptions": EvaPartnerSend.objects.filter(status__in=("review", "error")).order_by("-created_at")[:30],
    })
