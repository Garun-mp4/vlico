import hashlib
import json
from pathlib import Path
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Project
from core.portfolio import add_images, prepared_image

class Command(BaseCommand):
    help = "Apply client-confirmed photo grouping; preserve drafts, edits and existing media."
    def add_arguments(self, parser):
        parser.add_argument("--source-root", type=Path, required=True)
    def handle(self, *args, **options):
        root = options["source_root"].resolve()
        for old_slug, target_slug in (("room-magnetic-track", "leonova-55"), ("ceiling-assembly", "kholmogorovka-process")):
            with transaction.atomic():
                target = Project.objects.select_for_update().get(slug=target_slug)
                old = Project.objects.select_for_update().filter(slug=old_slug).first()
                if old:
                    has_cover = target.media.filter(is_cover=True).exists()
                    offset = target.media.count()
                    for index, item in enumerate(old.media.all()):
                        item.project = target
                        item.position = offset+index
                        item.is_cover = not has_cover and index == 0
                        item.save()
                    old.status = "archived"
                    old.editor_notes = "Фотографии перенесены в подтверждённый объект: " + target.title
                    old.save()
        entries = json.loads((Path(__file__).resolve().parents[2]/"data"/"portfolio-drafts.json").read_text())
        for entry in entries:
            slug = entry["slug"]
            if slug not in {"leonova-55", "kholmogorovka-process", "residential-shadow-details", "bathroom-contour-light", "ceiling-installation-detail"}:
                continue
            defaults = {k:v for k,v in entry.items() if k not in {"photos", "services", "slug"}}
            project, _ = Project.objects.get_or_create(slug=slug, defaults=defaults)
            for field in ("task", "solution"):
                if not getattr(project, field):
                    setattr(project, field, entry.get(field, ""))
            if entry.get("editor_notes") not in project.editor_notes:
                project.editor_notes += "\n" + entry.get("editor_notes", "")
            project.save()
            known = set()
            for item in project.media.all():
                with (item.source or item.image).open("rb") as stream:
                    known.add(hashlib.sha256(stream.read()).hexdigest())
            for photo in entry.get("photos", []):
                path = (root/photo["path"]).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    raise CommandError("Missing source inside source root: " + photo["path"])
                content = path.read_bytes()
                upload = SimpleUploadedFile(path.name, content)
                digest = hashlib.sha256(prepared_image(upload)[0].read()).hexdigest()
                if digest not in known:
                    add_images(project.pk, [SimpleUploadedFile(path.name, content)], photo.get("section", "result"))
                    known.add(digest)
            self.stdout.write(project.slug + ": " + str(project.media.count()) + " photos")
