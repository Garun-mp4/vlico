import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0018_evasyncjob")]

    operations = [
        migrations.AlterField(
            model_name="evasyncjob",
            name="contact_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
