from django.db import migrations
from django.utils import timezone


def align_covers(apps, schema_editor):
    Project = apps.get_model('core', 'Project')
    Media = apps.get_model('core', 'ProjectMedia')
    for project in Project.objects.all():
        items = list(Media.objects.filter(project=project).order_by('position','pk'))
        if not items:
            continue
        cover = next((item for item in items if item.is_cover),items[0])
        ordered = [cover]+[item for item in items if item.pk!=cover.pk]
        if all(item.position==index and item.is_cover==(index==0) for index,item in enumerate(ordered)):
            continue
        Media.objects.filter(project=project,is_cover=True).update(is_cover=False)
        for index,item in enumerate(ordered):
            item.position=index
            item.is_cover=index==0
        Media.objects.bulk_update(ordered,['position','is_cover'])
        Project.objects.filter(pk=project.pk).update(updated_at=timezone.now())


class Migration(migrations.Migration):
    dependencies=[('core','0010_project_delete_permission')]
    operations=[migrations.RunPython(align_covers,migrations.RunPython.noop)]
