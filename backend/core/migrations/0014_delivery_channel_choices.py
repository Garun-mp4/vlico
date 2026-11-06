from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0013_lead_archived_status")]

    operations = [
        migrations.AlterField(
            model_name="delivery",
            name="channel",
            field=models.CharField(
                choices=[("telegram", "Telegram"), ("email", "Электронная почта")],
                default="telegram",
                max_length=20,
            ),
        ),
    ]
