from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0008_alter_lead_kind")]
    operations = [migrations.AlterField(
        model_name="lead", name="kind",
        field=models.CharField(max_length=20, choices=[
            ("consultation", "Консультация"), ("measurement", "Запись на замер"),
            ("project", "Обсуждение проекта"), ("calculator", "Предварительный расчёт"),
            ("partner", "Сотрудничество"),
        ]),
    )]
