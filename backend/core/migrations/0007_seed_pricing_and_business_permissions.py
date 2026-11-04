from django.db import migrations


def seed(apps, schema_editor):
    Pricing = apps.get_model("core", "PricingVersion")
    rows = [
        ("pvc", "ПВХ-полотно и натяжка", "650.00", "м²"),
        ("fabric", "Тканевое полотно и натяжка", "2000.00", "м²"),
        ("standard", "Обычное примыкание", "180.00", "пог. м"),
        ("shadow", "Теневое примыкание", "850.00", "пог. м"),
        ("floating", "Парящее примыкание", "2000.00", "пог. м"),
        ("light_lines", "Световая линия", "2800.00", "пог. м"),
        ("tracks", "Магнитный трек", "3500.00", "пог. м"),
        ("cornices", "Скрытый карниз", "1500.00", "пог. м"),
        ("spots", "Монтаж световой точки с закладной", "450.00", "шт."),
    ]
    if not Pricing.objects.filter(active=True).exists():
        Pricing.objects.create(title="Стартовые цены для согласования", active=True, rates={code: {"title": title, "amount": amount, "unit": unit} for code, title, amount, unit in rows})
    Service = apps.get_model("core", "Service")
    for position, (slug, title) in enumerate([("shadow", "Теневые потолки"), ("floating", "Парящие потолки"), ("light-lines", "Световые линии"), ("tracks", "Магнитные треки"), ("cornices", "Скрытые карнизы"), ("fabric", "Тканевые потолки")]):
        Service.objects.get_or_create(slug=slug, defaults={"title": title, "position": position})
    ContentType, Permission, Group = [apps.get_model(app, model) for app, model in [("contenttypes", "ContentType"), ("auth", "Permission"), ("auth", "Group")]]
    group, _ = Group.objects.get_or_create(name="Portfolio editors")
    for model, actions in [("lead", ("view", "change")), ("leadattachment", ("view",)), ("delivery", ("view", "change")), ("pricingversion", ("view", "add"))]:
        content_type, _ = ContentType.objects.get_or_create(app_label="core", model=model)
        for action in actions:
            permission, _ = Permission.objects.get_or_create(content_type=content_type, codename=f"{action}_{model}", defaults={"name": f"{action} {model}"})
            group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [("core", "0006_submissionbucket_delivery_lease_token_and_more")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
