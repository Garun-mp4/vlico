from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0025_evasyncjob_outreach_check_at_and_more")]

    operations = [
        migrations.CreateModel(
            name="EvaPartnerCampaignRun",
            fields=[
                ("queue_id", models.UUIDField(primary_key=True, serialize=False)),
                ("contact_id", models.UUIDField(db_index=True)),
                ("check_at", models.DateTimeField(db_index=True, null=True)),
                ("alert_status", models.CharField(blank=True, default="", max_length=12)),
                ("submitted_step", models.PositiveSmallIntegerField(default=0)),
                ("submitted_at", models.DateTimeField(null=True)),
            ],
        ),
    ]
