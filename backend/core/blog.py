"""Public article pages and image delivery."""

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_safe
from .models import Article, ArticleMedia
from .portfolio import is_editor


def published_articles():
    return Article.objects.filter(status=Article.Status.PUBLISHED).prefetch_related("media")


def cover_url(article):
    photo = article.cover_media
    if photo:
        return reverse("blog_image", args=[photo.pk, "full"])
    return ""


@require_safe
def index(request):
    return render(request, "site/blog.html", {"articles": published_articles()})


@require_safe
def detail(request, slug):
    article = get_object_or_404(published_articles(), slug=slug)
    request.blog_article = article
    return render(request, "site/blog-article.html", {"article": article})


@require_safe
def original_cover(request, filename):
    article = get_object_or_404(Article, original_cover=filename, status=Article.Status.PUBLISHED)
    if not article.legacy_cover:
        raise Http404
    return redirect(static(article.legacy_cover), permanent=True)


@require_safe
def image(request, pk, variant):
    if variant not in {"thumb", "full", "source"}:
        raise Http404
    photo = get_object_or_404(ArticleMedia.objects.select_related("article"), pk=pk)
    if variant == "source" or photo.article.status != Article.Status.PUBLISHED:
        if not is_editor(request.user) or not request.user.has_perm("core.view_article"):
            raise Http404
    try:
        stream = photo.open_variant(variant)
    except (OSError, ValueError):
        raise Http404
    response = FileResponse(stream, content_type="image/webp")
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex" if variant == "source" or photo.article.status != Article.Status.PUBLISHED else "all"
    return response
