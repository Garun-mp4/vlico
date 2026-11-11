from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe
from django.views.decorators.cache import never_cache
from .models import Project, ProjectMedia, ProjectCategory
from django.db.models import Count, Q
from .portfolio import editor_required, is_editor, published_projects


def project_context(project):
    media = list(project.media.all())
    comparison = None
    if project.slug == "ceiling-installation-detail":
        before = next((m for m in media if m.section == "process"), None)
        after = next((m for m in media if m.section == "result"), None)
        if before and after:
            comparison = {"before": before, "after": after}
    return {"installation_comparison": comparison, "project": project, "cover": next((m for m in media if m.is_cover), None), "results": [m for m in media if m.section == "result" and not m.is_cover], "process": [m for m in media if m.section == "process" and not m.is_cover]}


@require_safe
def index(request):
    from .category_views import category_from_query
    selected_category = category_from_query(request, public=True)
    projects = published_projects()
    if selected_category:
        projects = projects.filter(categories=selected_category)
    categories = ProjectCategory.objects.filter(is_public=True).annotate(project_count=Count("projects", filter=Q(projects__status=Project.Status.PUBLISHED), distinct=True))
    return render(request, "site/projects.html", {"projects": projects, "categories": categories, "selected_category": selected_category})


@require_safe
def detail(request, slug):
    return render(request, "site/project.html", project_context(get_object_or_404(published_projects(), slug=slug)))


@never_cache
@editor_required
@require_safe
def preview(request, pk):
    context = project_context(get_object_or_404(Project.objects.prefetch_related("media", "services", "categories"), pk=pk))
    context["preview"] = True
    response = render(request, "site/project.html", context)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@require_safe
def image(request, pk, variant):
    if variant not in {"thumb", "full"}:
        raise Http404
    item = get_object_or_404(ProjectMedia.objects.select_related("project"), pk=pk)
    if item.project.status != Project.Status.PUBLISHED and not is_editor(request.user):
        raise Http404
    field = item.thumbnail if variant == "thumb" and item.thumbnail else item.image
    try:
        stream = field.open("rb")
    except (OSError, ValueError):
        raise Http404
    response = FileResponse(stream, content_type="image/webp")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    if item.project.status != Project.Status.PUBLISHED:
        response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@editor_required
@require_safe
def source_image(request, pk, media_pk):
    item = get_object_or_404(ProjectMedia, pk=media_pk, project_id=pk)
    try:
        stream = (item.source or item.image).open("rb")
    except (OSError, ValueError):
        raise Http404
    response = FileResponse(stream, content_type="image/webp")
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
