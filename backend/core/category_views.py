from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .forms import CategoryForm
from .models import ProjectCategory, Project
from .portfolio import editor_required, CATEGORY_PERMISSIONS


def category_editor_required(view):
    @editor_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.has_perms(CATEGORY_PERMISSIONS):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def category_from_query(request):
    value = request.GET.get("category", "")
    if not value:
        return None
    try:
        pk = int(value)
    except (ValueError, TypeError):
        raise Http404
    return get_object_or_404(ProjectCategory, pk=pk)


@category_editor_required
@require_http_methods(["GET"])
def index(request):
    categories = ProjectCategory.objects.annotate(project_count=Count("projects", distinct=True))
    return render(request, "cabinet/categories.html", {"categories": categories})


@category_editor_required
@require_http_methods(["GET", "POST"])
def edit(request, pk=None):
    category = get_object_or_404(ProjectCategory, pk=pk) if pk else ProjectCategory()
    if request.method == "POST":
        try:
            with transaction.atomic():
                if pk:
                    category = get_object_or_404(ProjectCategory.objects.select_for_update(), pk=pk)
                form = CategoryForm(request.POST, instance=category)
                valid = form.is_valid()
                if pk and request.POST.get("revision") != category.updated_at.isoformat():
                    form.add_error(None, "Категория изменена в другой вкладке. Обновите страницу перед сохранением.")
                    valid = False
                if valid:
                    category = form.save()
                    category.projects.update(updated_at=timezone.now())
                    messages.success(request, "Категория сохранена.")
                    return redirect("cabinet_categories")
        except IntegrityError:
            if not ProjectCategory.objects.filter(title__iexact=request.POST.get("title", "").strip()).exclude(pk=pk).exists():
                raise
            form.add_error("title", "Категория с таким названием уже существует.")
    else:
        form = CategoryForm(instance=category)
    return render(request, "cabinet/category-edit.html", {"form": form, "category": category})


@category_editor_required
@require_http_methods(["GET", "POST"])
def delete(request, pk):
    with transaction.atomic():
        category = get_object_or_404(ProjectCategory.objects.select_for_update(), pk=pk)
        count = category.projects.count()
        if request.method == "POST":
            if request.POST.get("revision") != category.updated_at.isoformat():
                messages.error(request, "Категория изменилась. Проверьте её перед удалением.")
            elif request.POST.get("confirm") != "yes":
                messages.error(request, "Подтвердите удаление категории.")
            else:
                category.projects.update(updated_at=timezone.now())
                category.delete()
                messages.success(request, "Категория удалена. Проекты и фотографии сохранены.")
                return redirect("cabinet_categories")
    return render(request, "cabinet/category-delete.html", {"category": category, "project_count": count})
