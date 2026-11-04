from django.db import migrations


def seed_categories(apps, schema_editor):
    Category = apps.get_model("core", "ProjectCategory")
    Project = apps.get_model("core", "Project")
    Service = apps.get_model("core", "Service")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    pairs = [("shadow", "Теневые потолки"), ("floating", "Парящие потолки"), ("light-lines", "Световые линии"), ("tracks", "Магнитные треки"), ("cornices", "Скрытые карнизы"), ("fabric", "Тканевые потолки")]
    for position, (slug, title) in enumerate(pairs):
        category, _ = Category.objects.get_or_create(title=title, defaults={"position": position})
        service = Service.objects.filter(slug=slug).first()
        if service:
            for project in Project.objects.filter(services=service):
                project.categories.add(category)
    content_type, _ = ContentType.objects.get_or_create(app_label="core", model="projectcategory")
    group, _ = Group.objects.get_or_create(name="Portfolio editors")
    for action in ("view", "add", "change", "delete"):
        permission, _ = Permission.objects.get_or_create(content_type=content_type, codename=action+"_projectcategory", defaults={"name": action+" project category"})
        group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [("core", "0004_projectcategory_project_categories"), ("auth", "0012_alter_user_first_name_max_length"), ("contenttypes", "0002_remove_content_type_name")]
    operations = [migrations.RunPython(seed_categories, migrations.RunPython.noop)]
