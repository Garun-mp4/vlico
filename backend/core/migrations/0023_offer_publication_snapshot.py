from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0022_offer_publication_revision")]
    operations = [migrations.AddField(model_name="offerpublication", name="published_offers",
                                    field=models.JSONField(default=list, editable=False))]
