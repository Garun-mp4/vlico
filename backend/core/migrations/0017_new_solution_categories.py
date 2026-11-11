from django.db import migrations
from django.db.models import Max


SOLUTION_CATEGORIES = (
    ("smart-home", "Умный дом с Алисой"),
    ("electric-cornices", "Электрокарнизы"),
    ("teqtum", "Пожаробезопасные полотна TEQTUM КМ1 / КМ2"),
)


def add_solution_categories(apps, schema_editor):
    database = schema_editor.connection.alias
    Category = apps.get_model("core", "ProjectCategory")
    Project = apps.get_model("core", "Project")
    categories = Category.objects.using(database)
    last_position = categories.aggregate(last=Max("position"))["last"]
    next_position = 0 if last_position is None else last_position + 1
    for slug, title in SOLUTION_CATEGORIES:
        category, created = categories.get_or_create(
            title__iexact=title,
            defaults={"title": title, "position": next_position, "is_public": True},
        )
        if created:
            next_position += 1
        for project in Project.objects.using(database).filter(services__slug=slug):
            project.categories.add(category)


class Migration(migrations.Migration):
    dependencies = [("core", "0016_import_article_cover_media")]
    # Keep editorial categories and their assignments when rolling code back.
    operations = [migrations.RunPython(add_solution_categories, migrations.RunPython.noop)]
