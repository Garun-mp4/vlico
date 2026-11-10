from django.db import migrations, models


def import_cover_media(apps, schema_editor):
    Article = apps.get_model("core", "Article")
    ArticleMedia = apps.get_model("core", "ArticleMedia")
    database = schema_editor.connection.alias
    articles = Article.objects.using(database).exclude(legacy_cover="").filter(media__isnull=True)
    ArticleMedia.objects.using(database).bulk_create([
        ArticleMedia(
            article_id=article.pk,
            bundled_image=article.legacy_cover,
            width=article.legacy_width,
            height=article.legacy_height,
            alt=article.legacy_cover_alt,
            editing={"ratio": "original"},
            is_cover=True,
        )
        for article in articles
    ])


def restore_legacy_covers(apps, schema_editor):
    ArticleMedia = apps.get_model("core", "ArticleMedia")
    ArticleMedia.objects.using(schema_editor.connection.alias).exclude(bundled_image="").filter(image="").delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0015_article_cabinet")]
    operations = [
        migrations.AddField(
            model_name="articlemedia",
            name="bundled_image",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RunPython(import_cover_media, restore_legacy_covers),
    ]
