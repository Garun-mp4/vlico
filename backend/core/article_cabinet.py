"""Article editing in the portfolio cabinet."""

from functools import wraps
import json
import uuid

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from .article_markup import sanitize_article
from .image_editing import edit_media
from .models import Article
from .portfolio import add_images, editor_required, save_media_order

ARTICLE_PERMISSIONS = tuple(f"core.{action}_article" for action in ("view", "add", "change", "delete"))


def article_permission(action):
    def decorate(view):
        @never_cache
        @editor_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.has_perm(f"core.{action}_article"):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


class ArticleForm(forms.ModelForm):
    revision = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Article
        fields = ("title", "slug", "description", "body")
        labels = {"title": "Название", "slug": "Адрес статьи", "description": "Краткое описание", "body": "Текст статьи"}
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "body": forms.Textarea(attrs={"rows": 14, "data-article-source": ""}),
        }
        help_texts = {
            "slug": "Латинские буквы, цифры и дефисы. Адрес фиксируется после первой публикации.",
            "description": "Появляется в списке статей и в метаданных страницы. До 320 символов.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["revision"].initial = self.instance.updated_at.isoformat() if self.instance.pk else ""
        self.fields["slug"].required = False
        self.fields["slug"].disabled = bool(self.instance.published_at)
        self.fields["body"].max_length = 180_000

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        if slug:
            return slug.lower()
        title = self.cleaned_data.get("title", "")
        alphabet = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "a b v g d e yo zh z i y k l m n o p r s t u f kh ts ch sh shch - y - e yu ya".split()))
        base = slugify("".join(alphabet.get(char, char) for char in title.lower()))[:120] or "article"
        candidate, suffix = base, 2
        while Article.objects.exclude(pk=self.instance.pk).filter(slug=candidate).exists():
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    def clean_body(self):
        raw = self.cleaned_data["body"]
        if len(raw) > 180_000:
            raise ValidationError("Текст статьи слишком длинный.")
        body = sanitize_article(raw)
        if self.instance.status == Article.Status.PUBLISHED and not body:
            raise ValidationError("У опубликованной статьи должен быть текст.")
        return body


def editable_articles():
    return Article.objects.exclude(status=Article.Status.DELETED)


def revision_matches(request, article):
    return request.POST.get("revision") == article.updated_at.isoformat()


@article_permission("view")
@require_safe
def index(request):
    state = request.GET.get("status", "")
    articles = Article.objects.order_by("-updated_at")
    if state in Article.Status.values:
        articles = articles.filter(status=state)
    else:
        articles = articles.exclude(status=Article.Status.DELETED)
    query = request.GET.get("q", "").strip()[:200]
    if query:
        articles = articles.filter(title__icontains=query)
    from django.core.paginator import Paginator
    return render(request, "cabinet/articles.html", {"articles": Paginator(articles, 30).get_page(request.GET.get("page")), "state": state, "states": Article.Status.choices, "query": query})


@editor_required
@never_cache
@require_http_methods(["GET", "POST"])
def edit(request, pk=None):
    permission = "change" if pk else "add"
    if not request.user.has_perm(f"core.{permission}_article"):
        raise PermissionDenied
    article = get_object_or_404(editable_articles(), pk=pk) if pk else Article()
    if request.method == "POST":
        with transaction.atomic():
            if pk:
                article = get_object_or_404(editable_articles().select_for_update(), pk=pk)
            form = ArticleForm(request.POST, instance=article)
            valid = form.is_valid()
            if pk and not revision_matches(request, article):
                form.add_error(None, "Статья изменилась в другой вкладке. Скопируйте правки и обновите страницу.")
                valid = False
            if valid:
                try:
                    with transaction.atomic():
                        article = form.save()
                except IntegrityError:
                    form.add_error("slug", "Этот адрес уже занят.")
                else:
                    messages.success(request, "Статья сохранена." if pk else "Черновик создан. Теперь можно добавить фотографии.")
                    return redirect("cabinet_article_edit", pk=article.pk)
    else:
        form = ArticleForm(instance=article)
    editor_body = sanitize_article(str(form["body"].value() or "")[:180_000])
    media = article.media.all() if article.pk else []
    return render(request, "cabinet/article-edit.html", {"article": article, "form": form, "editor_body": editor_body, "media_forms": [(item, None) for item in media]})


@article_permission("view")
@require_safe
def preview(request, pk):
    article = get_object_or_404(editable_articles().prefetch_related("media"), pk=pk)
    return render(request, "site/blog-article.html", {"article": article, "article_preview": True})


@editor_required
@never_cache
@require_POST
def status(request, pk):
    action = request.POST.get("action")
    if action not in {"publish", "draft", "delete", "restore"}:
        return HttpResponseBadRequest()
    permission = "delete" if action in {"delete", "restore"} else "change"
    if not request.user.has_perm(f"core.{permission}_article"):
        raise PermissionDenied
    with transaction.atomic():
        article = get_object_or_404(Article.objects.select_for_update(), pk=pk)
        if (article.status == Article.Status.DELETED) != (action == "restore"):
            return HttpResponseBadRequest()
        if not revision_matches(request, article):
            messages.error(request, "Статья изменилась. Проверьте сохранённую версию перед сменой статуса.")
            return redirect("cabinet_articles" if article.status == Article.Status.DELETED else "cabinet_article_edit", **({} if article.status == Article.Status.DELETED else {"pk": pk}))
        if action == "publish" and not article.body:
            messages.error(request, "Добавьте текст статьи перед публикацией.")
            return redirect("cabinet_article_edit", pk=pk)
        if action == "delete" and request.POST.get("confirm") != "yes":
            messages.error(request, "Подтвердите перемещение статьи в корзину.")
            return redirect("cabinet_article_edit", pk=pk)
        article.status = {"publish": Article.Status.PUBLISHED, "delete": Article.Status.DELETED}.get(action, Article.Status.DRAFT)
        if action == "publish" and not article.published_at:
            article.published_at = timezone.now()
        article.save(update_fields=["status", "published_at", "updated_at"])
    messages.success(request, {"publish": "Статья опубликована.", "draft": "Статья снята с публикации.", "delete": "Статья перемещена в корзину.", "restore": "Статья восстановлена как черновик."}[action])
    return redirect("cabinet_articles" if action == "delete" else "cabinet_article_edit", **({} if action == "delete" else {"pk": pk}))


def gallery_redirect(pk):
    from django.urls import reverse
    return redirect(reverse("cabinet_article_edit", args=[pk]) + "#gallery")


@article_permission("change")
@require_POST
def upload(request, pk):
    get_object_or_404(editable_articles(), pk=pk)
    try:
        data = json.loads(request.POST["editing"]) if "editing" in request.POST else None
        key = uuid.UUID(request.POST["upload_key"]) if "upload_key" in request.POST else None
        items = add_images(pk, request.FILES.getlist("images"), None, edit=data, upload_key=key, owner_model=Article)
    except (ValidationError, ValueError, TypeError) as exc:
        message = " ".join(exc.messages) if isinstance(exc, ValidationError) else "Проверьте параметры изображения."
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"error": message}, status=400)
        messages.error(request, message)
    else:
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"saved": [item.pk for item in items]})
        messages.success(request, "Фотографии загружены.")
    return gallery_redirect(pk)


@article_permission("change")
@require_POST
def crop(request, pk, media_pk):
    article = get_object_or_404(editable_articles(), pk=pk)
    get_object_or_404(article.media, pk=media_pk)
    try:
        data = json.loads(request.POST.get("editing", "{}"))
        item = edit_media(pk, media_pk, data, request.POST.get("revision"), owner_model=Article)
    except (ValidationError, ValueError, TypeError) as exc:
        return JsonResponse({"error": " ".join(exc.messages) if isinstance(exc, ValidationError) else "Проверьте параметры изображения."}, status=400)
    return JsonResponse({"saved": [item.pk]})


@article_permission("change")
@require_POST
def reorder(request, pk):
    with transaction.atomic():
        article = get_object_or_404(editable_articles().select_for_update(), pk=pk)
        if not revision_matches(request, article):
            return JsonResponse({"error": "Галерея изменилась. Обновите страницу."}, status=409)
        items = {item.pk: item for item in article.media.all()}
        try:
            order = [int(value) for value in request.POST.getlist("order")]
        except ValueError:
            return JsonResponse({"error": "Некорректный порядок фотографий."}, status=400)
        if len(order) != len(items) or set(order) != set(items):
            return JsonResponse({"error": "Состав галереи изменился. Обновите страницу."}, status=409)
        save_media_order(article, [items[pk] for pk in order])
        article.save(update_fields=["updated_at"])
    return JsonResponse({"revision": article.updated_at.isoformat(), "media_revisions": {item.pk: item.updated_at.isoformat() for item in items.values()}})


@article_permission("change")
@require_POST
def media(request, pk, media_pk):
    with transaction.atomic():
        article = get_object_or_404(editable_articles().select_for_update(), pk=pk)
        item = get_object_or_404(article.media, pk=media_pk)
        action = request.POST.get("action")
        ordered = list(article.media.all())
        if action == "save":
            fields = {key: request.POST.get(key, "").strip() for key in ("alt", "caption")}
            if any(len(value) > 250 for value in fields.values()):
                messages.error(request, "Описание и подпись могут содержать до 250 символов.")
                return gallery_redirect(pk)
            for key, value in fields.items():
                setattr(item, key, value)
            item.save(update_fields=["alt", "caption", "updated_at"])
        elif action == "cover":
            save_media_order(article, [item] + [photo for photo in ordered if photo.pk != item.pk])
        elif action in {"up", "down"}:
            position = next(i for i, photo in enumerate(ordered) if photo.pk == item.pk)
            target = position + (-1 if action == "up" else 1)
            if 0 <= target < len(ordered):
                ordered[position], ordered[target] = ordered[target], ordered[position]
                save_media_order(article, ordered)
        elif action == "delete" and request.POST.get("confirm") == "yes":
            files = [(field.storage, field.name) for field in (item.image, item.thumbnail, item.source) if field]
            item.delete()
            save_media_order(article, list(article.media.all()))
            transaction.on_commit(lambda: [storage.delete(name) for storage, name in files], robust=True)
        else:
            return HttpResponseBadRequest()
        article.save(update_fields=["updated_at"])
    messages.success(request, "Галерея обновлена.")
    return gallery_redirect(pk)
