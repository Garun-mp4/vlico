from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0012_projectcategory_is_public")]

    operations = [
        migrations.AlterField(
            model_name="lead",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "Новая"),
                    ("contacted", "В работе"),
                    ("closed", "Закрыта"),
                    ("archived", "В архиве"),
                ],
                default="new",
                max_length=12,
            ),
        ),
    ]
