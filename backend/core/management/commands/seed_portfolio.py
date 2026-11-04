import json
from pathlib import Path
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from core.models import Project, Service, ProjectCategory
from core.portfolio import add_images

class Command(BaseCommand):
    help = "Import prepared drafts without publishing or overwriting existing projects."
    def add_arguments(self, parser):
        parser.add_argument("--source-root", type=Path)
    def handle(self, *args, **options):
        source = options["source_root"]
        services = [("shadow", "Теневые потолки"), ("floating", "Парящие потолки"), ("light-lines", "Световые линии"), ("tracks", "Магнитные треки"), ("cornices", "Скрытые карнизы"), ("fabric", "Тканевые потолки")]
        for position, (slug, title) in enumerate(services):
            Service.objects.get_or_create(slug=slug, defaults={"title": title, "position": position})
        data = json.loads((Path(__file__).resolve().parents[2]/"data"/"portfolio-drafts.json").read_text())
        for index, entry in enumerate(data):
            photos = entry.pop("photos", [])
            service_slugs = entry.pop("services", [])
            project, created = Project.objects.get_or_create(slug=entry["slug"], defaults={**entry, "position": index})
            if not created:
                continue
            project.services.set(Service.objects.filter(slug__in=service_slugs))
            project.categories.set(ProjectCategory.objects.filter(title__in=project.services.values_list("title", flat=True)))
            if source:
                for group in ("result", "process"):
                    paths = [p["path"] for p in photos if p.get("section", "result") == group]
                    uploads = []
                    for relative in paths:
                        path = (source / relative).resolve()
                        if not path.is_relative_to(source.resolve()):
                            raise CommandError("Source path escapes source root")
                        if path.is_file():
                            uploads.append(SimpleUploadedFile(path.name, path.read_bytes()))
                    if uploads:
                        add_images(project.pk, uploads, group)
            self.stdout.write("Created draft: " + project.slug)
