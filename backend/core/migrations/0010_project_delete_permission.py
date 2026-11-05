from django.db import migrations


def grant_delete_to_editor_role(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    group = Group.objects.filter(name="Portfolio editors").first()
    if group:
        content_type, _ = ContentType.objects.get_or_create(app_label="core", model="project")
        permission, _ = Permission.objects.get_or_create(content_type=content_type, codename="delete_project", defaults={"name":"Can delete project"})
        group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [("core", "0009_discuss_project_without_files")]
    operations = [migrations.RunPython(grant_delete_to_editor_role, migrations.RunPython.noop)]
