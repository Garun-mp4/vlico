from django.db import migrations, models


def separate_project_flags(apps, schema_editor):
    apps.get_model("core", "EvaPartnerEvent").objects.filter(
        kind="project_request", key__endswith=":partnerproject",
    ).update(kind="project_available")


class Migration(migrations.Migration):
    dependencies = [("core", "0027_partner_outreach_v2")]
    operations = [
        migrations.AddField("evapartnersend", "message_text", models.TextField(blank=True)),
        migrations.AddField("evapartnersend", "media_document_id", models.UUIDField(null=True)),
        migrations.RunPython(separate_project_flags, migrations.RunPython.noop),
    ]
