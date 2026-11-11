"""Apply the approved 11 November editorial update without replacing article text or deleting media."""
from pathlib import Path
from django.contrib.staticfiles import finders
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Article, ArticleMedia, Project, Service
from core.portfolio import add_images
from core.site_content import NEW_SOLUTIONS


class Command(BaseCommand):
    help = "Apply approved VLICO client content from 2026-11-11 (idempotent)."

    def handle(self, **options):
        for index, item in enumerate(NEW_SOLUTIONS, 20):
            Service.objects.get_or_create(slug=item["slug"], defaults={"title": item["title"], "description": item["description"], "position": index})
        covers = [
            ("karniz-dlya-natyazhnogo-potolka-vybor", "concealed-curtains.webp", "Скрытая потолочная ниша: шторы выходят из потолка"),
            ("natiazhnoi-potolok-kak-sozdat-stilnyj-i-praktichnyi-interer", "smart-room.webp", "Современный матовый потолок с архитектурной подсветкой в гостиной"),
        ]
        for slug, filename, alt in covers:
            path = "client-updates/" + filename
            if not finders.find(path):
                raise CommandError("Missing bundled image: " + path)
            with transaction.atomic():
                article = Article.objects.select_for_update().filter(slug=slug).first()
                if not article:
                    self.stdout.write("Article not present, skipped: " + slug)
                    continue
                if article.media.filter(bundled_image=path).exists():
                    continue
                article.media.filter(is_cover=True).update(is_cover=False)
                ArticleMedia.objects.create(article=article, bundled_image=path, width=1536, height=1024, alt=alt,
                    caption="Визуализация интерьера, созданная с помощью ИИ", is_cover=True, position=0)
        project = Project.objects.filter(slug="ceiling-installation-detail").first()
        if project:
            caption = "После — установленная кухонная вытяжка"
            # Keep the supplied before image and all other existing gallery media.
            if not project.media.filter(caption=caption).exists():
                source = finders.find("client-updates/hood-after.jpg")
                if not source:
                    raise CommandError("Missing supplied hood photo")
                with open(source, "rb") as stream:
                    photo = add_images(project.pk, [File(stream, name=Path(source).name)], "result")[0]
                photo.caption = caption
                photo.alt = "Чёрная кухонная вытяжка под готовым потолком рядом с синим шкафом"
                photo.save(update_fields=["caption", "alt"])
            Project.objects.filter(pk=project.pk).update(solution="До монтажа потолка подготовили закладную конструкцию и воздуховод под кухонную вытяжку. После установки полотна смонтировали вытяжку: на фотографиях рядом показаны подготовка узла и результат.")
        self.stdout.write(self.style.SUCCESS("Client update applied."))
