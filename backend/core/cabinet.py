from datetime import timedelta
import hashlib
import json
import uuid
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login
from django.db import transaction
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from django.core.exceptions import ValidationError, PermissionDenied
from .forms import ProjectForm, MediaForm
from .models import Project, ProjectMedia, LoginBucket, ProjectCategory
from .portfolio import editor_required, is_editor, add_images, delete_project, PROJECT_DELETE_PERMISSION


@never_cache
@require_http_methods(["GET", "POST"])
def login(request):
    if is_editor(request.user):
        return redirect("cabinet_projects")
    form = AuthenticationForm(request, data=request.POST or None)
    limited = False
    if request.method == "POST":
        now = timezone.now()
        key = hashlib.sha256((settings.SECRET_KEY + request.META.get("REMOTE_ADDR", "")).encode()).hexdigest()
        with transaction.atomic():
            bucket, _ = LoginBucket.objects.get_or_create(key=key, defaults={"expires_at": now+timedelta(minutes=15)})
            bucket = LoginBucket.objects.select_for_update().get(pk=key)
            if bucket.expires_at <= now:
                bucket.attempts = 0
                bucket.expires_at = now+timedelta(minutes=15)
            limited = bucket.attempts >= 10
            if not limited:
                bucket.attempts += 1
            bucket.save()
        if limited:
            return render(request, "cabinet/login.html", {"form": AuthenticationForm(request), "limited": True}, status=429)
        elif form.is_valid():
            if is_editor(form.get_user()):
                auth_login(request, form.get_user())
                LoginBucket.objects.filter(key=key).delete()
                return redirect("cabinet_projects")
            form.add_error(None, "Вход недоступен. Проверьте данные и права доступа.")
    return render(request, "cabinet/login.html", {"form": form}, status=429 if limited else 200)


@require_POST
def signout(request):
    logout(request)
    return redirect("cabinet_login")


@editor_required
@require_http_methods(["GET"])
def projects(request):
    state = request.GET.get("status", "")
    from .category_views import category_from_query
    selected_category = category_from_query(request)
    items = Project.objects.prefetch_related("media", "categories").order_by("position", "-updated_at")
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "recent")
    if query:
        items = items.filter(Q(title__icontains=query) | Q(location__icontains=query))
    if selected_category:
        items = items.filter(categories=selected_category)
    counts = dict(items.order_by().values("status").annotate(total=Count("pk")).values_list("status", "total"))
    if state in Project.Status.values:
        items = items.filter(status=state)
    orders = {"recent": ("-updated_at", "pk"), "old": ("updated_at", "pk"), "title": ("title", "pk"), "position": ("position", "-published_at", "pk")}
    items = items.order_by(*orders.get(sort, orders["recent"]))
    return render(request, "cabinet/projects.html", {"projects": items, "state": state, "query": query, "sort": sort, "total": sum(counts.values()), "status_counts": [(value, label, counts.get(value, 0)) for value, label in Project.Status.choices], "categories": ProjectCategory.objects.all(), "selected_category": selected_category})


@editor_required
@require_http_methods(["GET", "POST"])
def edit(request, pk=None):
    project = get_object_or_404(Project, pk=pk) if pk else Project()
    if request.method == "POST":
        with transaction.atomic():
            if pk:
                project = Project.objects.select_for_update().get(pk=pk)
            form = ProjectForm(request.POST, instance=project)
            valid = form.is_valid()
            if pk and request.POST.get("revision") != project.updated_at.isoformat():
                form.add_error(None, "Проект изменён в другой вкладке. Скопируйте новые тексты и обновите страницу перед сохранением.")
                valid = False
            if valid:
                project = form.save()
                if request.headers.get("Accept") == "application/json":
                    return JsonResponse({"url": reverse("cabinet_edit", args=[project.pk]), "revision": project.updated_at.isoformat(), "title": project.title, "status": project.status, "created": not pk})
                messages.success(request, "Проект сохранён. Публикация выполняется отдельно.")
                return redirect("cabinet_edit", pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    media = list(project.media.all()) if project.pk else []
    if request.method == "POST" and request.headers.get("Accept") == "application/json":
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    return render(request, "cabinet/edit.html", {"project": project, "form": form, "media_forms": [(m, MediaForm(instance=m)) for m in media]})


@editor_required
@require_POST
def reorder_media(request, pk):
    with transaction.atomic():
        project = get_object_or_404(Project.objects.select_for_update(), pk=pk)
        if request.POST.get("revision") != project.updated_at.isoformat():
            return JsonResponse({"error": "Галерея изменена в другой вкладке. Обновите страницу перед перестановкой."}, status=409)
        try:
            ids = [int(value) for value in request.POST.getlist("order")]
        except ValueError:
            return JsonResponse({"error": "Некорректный порядок фотографий."}, status=400)
        media = {item.pk: item for item in project.media.all()}
        if len(ids) != len(media) or set(ids) != set(media):
            return JsonResponse({"error": "Состав галереи изменился. Обновите страницу."}, status=400)
        for position, media_id in enumerate(ids):
            media[media_id].position = position
        ProjectMedia.objects.bulk_update(media.values(), ["position"])
        project.save(update_fields=["updated_at"])
    return JsonResponse({"revision": project.updated_at.isoformat()})


@editor_required
@require_POST
def upload(request, pk):
    project = get_object_or_404(Project, pk=pk)
    section = request.POST.get("section", "result")
    if section not in {"result", "process"}:
        return HttpResponse(status=400)
    try:
        edit = json.loads(request.POST["editing"]) if "editing" in request.POST else None
        key = uuid.UUID(request.POST["upload_key"]) if "upload_key" in request.POST else None
        items = add_images(project.pk, request.FILES.getlist("images"), section, edit=edit, upload_key=key)
    except (ValidationError, ValueError, TypeError) as exc:
        error = " ".join(exc.messages) if isinstance(exc, ValidationError) else "Некорректные параметры загрузки."
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"error": error}, status=400)
        messages.error(request, error)
    else:
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"saved": [item.pk for item in items]})
        messages.success(request, "Фотографии загружены. Их описания и порядок можно изменить ниже.")
    return redirect("cabinet_edit", pk=pk)


@editor_required
@require_POST
def media_edit(request, pk, media_pk):
    with transaction.atomic():
        project = get_object_or_404(Project.objects.select_for_update(), pk=pk)
        item = get_object_or_404(ProjectMedia, project=project, pk=media_pk)
        action = request.POST.get("action")
        if action == "save":
            form = MediaForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
            else:
                messages.error(request, "Проверьте подпись и описание: не более 250 символов; выберите раздел галереи.")
                return redirect("cabinet_edit", pk=pk)
        elif action == "cover":
            project.media.update(is_cover=False)
            item.is_cover = True
            item.save(update_fields=["is_cover"])
        elif action in {"up", "down"}:
            ordered = list(project.media.all())
            index = next(i for i, m in enumerate(ordered) if m.pk == item.pk)
            target = index + (-1 if action == "up" else 1)
            if 0 <= target < len(ordered):
                ordered[index], ordered[target] = ordered[target], ordered[index]
                for position, media in enumerate(ordered):
                    media.position = position
                ProjectMedia.objects.bulk_update(ordered, ["position"])
        elif action == "delete":
            if request.POST.get("confirm") != "yes":
                messages.error(request, "Подтвердите удаление фотографии.")
                return redirect("cabinet_edit", pk=pk)
            if project.status == Project.Status.PUBLISHED and project.media.count() == 1:
                messages.error(request, "Сначала снимите проект с публикации: у опубликованного проекта должна остаться фотография.")
                return redirect("cabinet_edit", pk=pk)
            files = [(f.storage, f.name) for f in (item.image, item.thumbnail, item.source) if f]
            was_cover = item.is_cover
            item.delete()
            if was_cover:
                replacement = project.media.first()
                if replacement:
                    replacement.is_cover = True
                    replacement.save(update_fields=["is_cover"])
            transaction.on_commit(lambda: [storage.delete(name) for storage, name in files])
        else:
            return HttpResponse(status=400)
        project.save(update_fields=["updated_at"])
    messages.success(request, "Галерея обновлена.")
    return redirect("cabinet_edit", pk=pk)


@editor_required
@require_POST
def change_status(request, pk):
    with transaction.atomic():
        project = get_object_or_404(Project.objects.select_for_update(), pk=pk)
        action = request.POST.get("action")
        if action == "publish":
            if request.POST.get("confirm") != "yes":
                messages.error(request, "Подтвердите, что сведения и разрешение на публикацию проверены.")
                return redirect("cabinet_edit", pk=pk)
            if not project.solution.strip() or not project.media.filter(is_cover=True).exists():
                messages.error(request, "Для публикации добавьте описание решения и фотографию обложки.")
                return redirect("cabinet_edit", pk=pk)
            project.status = Project.Status.PUBLISHED
            project.published_at = project.published_at or timezone.now()
        elif action in {"draft", "restore"}:
            project.status = Project.Status.DRAFT
        elif action == "archive":
            if request.POST.get("confirm") != "yes":
                messages.error(request, "Подтвердите перемещение в архив.")
                return redirect("cabinet_edit", pk=pk)
            project.status = Project.Status.ARCHIVED
        else:
            return HttpResponse(status=400)
        project.save(update_fields=["status", "published_at", "updated_at"])
    messages.success(request, "Статус проекта обновлён.")
    return redirect("cabinet_edit", pk=pk)


@editor_required
@require_http_methods(["GET", "POST"])
def remove_project(request, pk):
    if not request.user.has_perm(PROJECT_DELETE_PERMISSION):
        raise PermissionDenied
    project = get_object_or_404(Project.objects.prefetch_related("media"), pk=pk)
    if request.method == "POST":
        if request.POST.get("confirm") != "yes":
            messages.error(request, "Подтвердите, что хотите удалить проект и его фотографии.")
        else:
            try:
                title = delete_project(pk, request.POST.get("revision"))
            except Project.DoesNotExist:
                return redirect("cabinet_projects")
            except ValidationError as error:
                messages.error(request, " ".join(error.messages))
                project.refresh_from_db()
            else:
                messages.success(request, f'Проект «{title}» удалён.')
                return redirect("cabinet_projects")
    return render(request, "cabinet/project-delete.html", {"project": project, "photo_count": project.media.count(), "lead_count": project.lead_set.count()})


@editor_required
@require_POST
def image_editor(request, pk, media_pk):
    from .image_editing import edit_media
    get_object_or_404(ProjectMedia, pk=media_pk, project_id=pk)
    try:
        data = json.loads(request.POST.get("editing", "{}"))
        item = edit_media(pk, media_pk, data, request.POST.get("revision"))
    except (ValidationError, ValueError, TypeError) as exc:
        error = " ".join(exc.messages) if isinstance(exc, ValidationError) else "Некорректные параметры редактирования."
        return JsonResponse({"error": error}, status=400)
    return JsonResponse({"saved": [item.pk]})
