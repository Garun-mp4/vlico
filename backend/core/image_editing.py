import math
from io import BytesIO
from PIL import Image, ImageOps
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from .models import Project, ProjectMedia


RATIOS = {"4:3": 4/3, "3:4": 3/4, "16:9": 16/9, "9:16": 9/16, "1:1": 1, "original": None}


def validate_edit(data):
    if not isinstance(data, dict):
        raise ValidationError("Некорректные параметры изображения.")
    result = {}
    for key, default, low, high in (("zoom", 1, 1, 3), ("x", 50, 0, 100), ("y", 50, 0, 100)):
        try:
            value = float(data.get(key, default))
        except (TypeError, ValueError):
            raise ValidationError("Проверьте масштаб и положение кадра.")
        if not math.isfinite(value) or not low <= value <= high:
            raise ValidationError("Масштаб и положение кадра выходят за допустимые границы.")
        result[key] = value
    rotation = data.get("rotation", 0)
    if rotation not in (0, 90, 180, 270):
        raise ValidationError("Допустим поворот на 0, 90, 180 или 270 градусов.")
    result["rotation"] = rotation
    result["mode"] = data.get("mode", "crop")
    if result["mode"] not in {"crop", "fit"}:
        raise ValidationError("Выберите кадрирование или сохранение фотографии целиком.")
    ratio = data.get("ratio", "4:3")
    if not isinstance(ratio, str) or ratio not in RATIOS:
        raise ValidationError("Выберите допустимый формат фотографии.")
    result["ratio"] = ratio
    return result


def rendered_image(source, edit):
    image = Image.open(source).convert("RGB")
    if edit["rotation"]:
        image = image.rotate(-edit["rotation"], expand=True)
    width, height = image.size
    ratio = RATIOS[edit.get("ratio", "4:3")] or width/height
    if edit["mode"] == "fit":
        frame_width = max(width, height*ratio)
        frame_height = frame_width/ratio
        scale = min(1, 1600/max(frame_width, frame_height))
        size = (max(1, round(frame_width*scale)), max(1, round(frame_height*scale)))
        image = ImageOps.pad(image, size, color="#f2f1e9", method=Image.Resampling.LANCZOS)
    else:
        crop_w = min(width, height*ratio) / edit["zoom"]
        crop_h = crop_w/ratio
        left = (width-crop_w)*edit["x"]/100
        top = (height-crop_h)*edit["y"]/100
        scale = min(1, 1600/max(crop_w, crop_h))
        size = (max(1, round(crop_w*scale)), max(1, round(crop_h*scale)))
        image = image.resize(size, Image.Resampling.LANCZOS, box=(left, top, left+crop_w, top+crop_h))
    full = BytesIO()
    image.save(full, "WEBP", quality=85)
    dimensions = image.size
    image.thumbnail((640, 640), Image.Resampling.LANCZOS)
    thumb = BytesIO()
    image.save(thumb, "WEBP", quality=80)
    return ContentFile(full.getvalue(), name="image.webp"), ContentFile(thumb.getvalue(), name="thumb.webp"), *dimensions


def media_metadata(data):
    if not all(isinstance(data.get(key, ""), str) for key in ("alt", "caption", "section")) or not isinstance(data.get("cover", False), bool):
        raise ValidationError("Некорректные подписи или параметры обложки.")
    alt = data.get("alt", "").strip()
    caption = data.get("caption", "").strip()
    section = data.get("section", "result")
    if len(alt) > 250 or len(caption) > 250 or section not in {"result", "process"}:
        raise ValidationError("Описание и подпись: до 250 символов. Выберите раздел галереи.")
    return {"alt": alt, "caption": caption, "section": section}


def edit_media(project_id, media_id, data, revision):
    edit = validate_edit(data)
    meta = media_metadata(data)
    written = []
    old = []
    try:
        with transaction.atomic():
            project = Project.objects.select_for_update().get(pk=project_id)
            item = ProjectMedia.objects.select_for_update().get(pk=media_id, project=project)
            if revision != item.updated_at.isoformat():
                raise ValidationError("Фото изменено в другой вкладке. Обновите страницу и откройте редактор снова.")
            if not item.source:
                with item.image.open("rb") as stream:
                    item.source.save("source.webp", ContentFile(stream.read()), save=False)
                written.append((item.source.storage, item.source.name))
            with item.source.open("rb") as source:
                full, thumb, width, height = rendered_image(source, edit)
            old = [(f.storage, f.name) for f in (item.image, item.thumbnail) if f]
            for field, content in ((item.image, full), (item.thumbnail, thumb)):
                field.save(content.name, content, save=False)
                written.append((field.storage, field.name))
            item.width, item.height = width, height
            item.editing = edit
            for key, value in meta.items():
                setattr(item, key, value)
            if data.get("cover"):
                project.media.exclude(pk=item.pk).update(is_cover=False)
                item.is_cover = True
            item.save()
            if data.get("cover"):
                from .portfolio import save_media_order
                save_media_order(project, [item] + list(project.media.exclude(pk=item.pk)))
            project.save(update_fields=["updated_at"])
            transaction.on_commit(lambda: [storage.delete(name) for storage, name in old], robust=True)
        return item
    except Exception:
        for storage, name in written:
            storage.delete(name)
        raise
