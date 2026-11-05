from django.db import migrations, models


REVIEW_CATEGORIES = ("Транспарентные потолки", "Монтажные работы")


def hide_review_categories(apps, schema_editor):
    apps.get_model("core", "ProjectCategory").objects.using(schema_editor.connection.alias).filter(title__in=REVIEW_CATEGORIES).update(is_public=False)


def restore_review_categories(apps, schema_editor):
    apps.get_model("core", "ProjectCategory").objects.using(schema_editor.connection.alias).filter(title__in=REVIEW_CATEGORIES).update(is_public=True)


class Migration(migrations.Migration):
    dependencies = [("core", "0011_cover_first_slot")]
    operations = [
        migrations.AddField(model_name="projectcategory", name="is_public", field=models.BooleanField(default=True)),
        migrations.RunPython(hide_review_categories, restore_review_categories),
    ]
