from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0021_seed_sales_offers")]
    operations = [migrations.AddField(model_name="offerpublication", name="published_revision",
                                    field=models.UUIDField(blank=True, editable=False, null=True))]
