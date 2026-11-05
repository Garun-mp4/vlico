from functools import wraps
from io import BytesIO
import warnings
import logging
from PIL import Image, ImageOps, UnidentifiedImageError
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from .models import Project, ProjectMedia

EDITOR_PERMISSIONS = ("core.view_project", "core.add_project", "core.change_project", "core.view_projectmedia", "core.add_projectmedia", "core.change_projectmedia", "core.delete_projectmedia")


CATEGORY_PERMISSIONS = ("core.view_projectcategory", "core.add_projectcategory", "core.change_projectcategory", "core.delete_projectcategory")
PROJECT_DELETE_PERMISSION = "core.delete_project"


def delete_project(project_id, revision):
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        if revision != project.updated_at.isoformat():
            raise ValidationError("Проект изменён в другой вкладке. Проверьте его ещё раз перед удалением.")
        files = {}
        for item in project.media.all():
            for field in (item.image, item.thumbnail, item.source):
                if field:
                    private = field.field.name == "source"
                    files[(private, field.name)] = field.storage
        title = project.title
        for lead in project.lead_set.select_for_update():
            if not lead.context.get("project_title"):
                lead.context = {**lead.context, "project_title": title}
                lead.save(update_fields=["context"])
        project.delete()
        # A moved photo can retain its original storage path. Delete exact files,
        # never a project directory, and keep files referenced by another record.
        removable = []
        for (private, name), storage in files.items():
            references = Q(source=name) if private else Q(image=name) | Q(thumbnail=name)
            if not ProjectMedia.objects.filter(references).exists():
                removable.append((storage, name))

        def remove_files():
            for storage, name in removable:
                try:
                    storage.delete(name)
                except OSError:
                    logging.getLogger(__name__).exception("Could not clean up a deleted project's photo")
        transaction.on_commit(remove_files, robust=True)
    return title


def is_editor(user):
    return user.is_authenticated and user.is_active and user.is_staff and user.has_perms(EDITOR_PERMISSIONS)


def editor_required(view):
    @login_required(login_url="cabinet_login")
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not is_editor(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def published_projects():
    return Project.objects.filter(status=Project.Status.PUBLISHED).prefetch_related("media", "services", "categories").order_by("position", "-published_at", "pk")


def prepared_image(upload):
    if upload.size > 12 * 1024 * 1024:
        raise ValidationError("Файл больше 12 МБ. Выберите уменьшенную копию.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValidationError("Поддерживаются только JPEG, PNG и WebP.")
                if original.width * original.height > 16_000_000 or min(original.size) < 64:
                    raise ValidationError("Размер изображения: от 64 пикселей по стороне до 16 мегапикселей.")
                original.load()
                image = ImageOps.exif_transpose(original).convert("RGB")
        image.thumbnail((2000, 2000))
        full = BytesIO()
        image.save(full, "WEBP", quality=85)
        width, height = image.size
        image.thumbnail((640, 640))
        thumb = BytesIO()
        image.save(thumb, "WEBP", quality=80)
        return ContentFile(full.getvalue(), name="image.webp"), ContentFile(thumb.getvalue(), name="thumb.webp"), width, height
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError("Не удалось прочитать фотографию. Выберите исправный JPEG, PNG или WebP.") from exc


def add_images(project_id, uploads, section, edit=None, upload_key=None):
    if not uploads or len(uploads) > 8:
        raise ValidationError("Выберите от 1 до 8 фотографий за один раз.")
    if edit is not None:
        from .image_editing import validate_edit, rendered_image, media_metadata
        if len(uploads) != 1:
            raise ValidationError("В редакторе сохраняйте по одной фотографии.")
        settings = validate_edit(edit)
        metadata = media_metadata(edit)
    prepared = [prepared_image(upload) for upload in uploads]
    written = []
    try:
        with transaction.atomic():
            project = Project.objects.select_for_update().get(pk=project_id)
            if upload_key:
                existing = ProjectMedia.objects.filter(upload_key=upload_key).first()
                if existing:
                    if existing.project_id != project_id:
                        raise ValidationError("Этот запрос загрузки уже использован.")
                    return [existing]
            media = list(project.media.all())
            if len(media) + len(prepared) > 40:
                raise ValidationError("В проекте может быть до 40 фотографий.")
            start = max((m.position for m in media), default=-1) + 1
            created = []
            for index, (full, thumb, width, height) in enumerate(prepared):
                item = ProjectMedia(project=project, position=start+index, section=section, width=width, height=height, alt=project.title, is_cover=not media and index == 0)
                if edit is not None:
                    item.source.save("source.webp", ContentFile(full.read()), save=False)
                    written.append((item.source.storage, item.source.name))
                    with item.source.open("rb") as source:
                        full, thumb, width, height = rendered_image(source, settings)
                    item.width, item.height = width, height
                    item.editing = settings
                    item.upload_key = upload_key
                    for key, value in metadata.items():
                        setattr(item, key, value)
                    if edit.get("cover"):
                        project.media.update(is_cover=False)
                        item.is_cover = True
                item.image.save(full.name, full, save=False)
                written.append((item.image.storage, item.image.name))
                item.thumbnail.save(thumb.name, thumb, save=False)
                written.append((item.thumbnail.storage, item.thumbnail.name))
                item.save()
                created.append(item)
            project.save(update_fields=["updated_at"])
        return created
    except Exception:
        for storage, name in written:
            storage.delete(name)
        raise
