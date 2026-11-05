from importlib import import_module
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db import transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from . import test_portfolio as fixtures
from .models import Project, ProjectMedia, Lead, Delivery
from .portfolio import EDITOR_PERMISSIONS, add_images, delete_project


class ProjectDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = get_user_model().objects.create_user('delete-editor', is_staff=True)
        cls.editor.user_permissions.set(Permission.objects.filter(content_type__app_label='core', codename__in=[p.split('.')[1] for p in EDITOR_PERMISSIONS]+['delete_project']))

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        context = override_settings(MEDIA_ROOT=Path(self.directory.name)/'public', PRIVATE_MEDIA_ROOT=Path(self.directory.name)/'private')
        context.enable(); self.addCleanup(context.disable)
        self.client.force_login(self.editor)
        self.project = Project.objects.create(title='Удаляемый проект', slug='delete-project', solution='Сохранённое решение')
        self.path = reverse('cabinet_project_delete', args=[self.project.pk])

    def post(self, project=None):
        project = project or self.project
        return self.client.post(reverse('cabinet_project_delete', args=[project.pk]), {'confirm':'yes','revision':project.updated_at.isoformat()})

    def test_confirmation_page_is_read_only_and_shows_consequences(self):
        add_images(self.project.pk,[fixtures.jpeg()], 'result', edit={'ratio':'3:4'})
        lead=Lead.objects.create(project=self.project,kind='project',name='Тест',contact='test@example.test')
        response=self.client.get(self.path)
        self.assertContains(response,self.project.title)
        self.assertContains(response,'Связанных обращений: 1')
        self.assertContains(response,'миниатюры и сохранённые исходники')
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())
        self.assertTrue(Lead.objects.filter(pk=lead.pk).exists())

    def test_permission_is_separate_and_csrf_is_required(self):
        guest=Client()
        self.assertEqual(guest.get(self.path).status_code,302)
        self.assertEqual(guest.post(self.path).status_code,302)
        editor=get_user_model().objects.create_user('no-delete',is_staff=True)
        editor.user_permissions.set(Permission.objects.filter(content_type__app_label='core',codename__in=[p.split('.')[1] for p in EDITOR_PERMISSIONS]))
        guest.force_login(editor)
        self.assertEqual(guest.get(reverse('cabinet_projects')).status_code,200)
        self.assertEqual(guest.get(self.path).status_code,403)
        self.assertEqual(guest.post(self.path,{'confirm':'yes','revision':self.project.updated_at.isoformat()}).status_code,403)
        self.assertNotContains(guest.get(reverse('cabinet_edit',args=[self.project.pk])),self.path)
        protected=Client(enforce_csrf_checks=True);protected.force_login(self.editor)
        self.assertEqual(protected.post(self.path,{'confirm':'yes','revision':self.project.updated_at.isoformat()}).status_code,403)
        self.assertEqual(self.client.put(self.path).status_code,405)

    def test_missing_confirmation_or_stale_revision_cannot_delete(self):
        self.client.post(self.path,{'revision':self.project.updated_at.isoformat()})
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())
        stale=self.project.updated_at.isoformat()
        self.project.title='Новая редакция';self.project.save()
        response=self.client.post(self.path,{'confirm':'yes','revision':stale})
        self.assertContains(response,'изменён в другой вкладке')
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())
        self.client.post(self.path,{'confirm':'yes'})
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_all_states_can_be_deleted_and_owned_files_are_cleaned(self):
        for state in Project.Status.values:
            with self.subTest(state=state):
                project=Project.objects.create(title=state,slug=state,solution='Решение',status=state)
                item=add_images(project.pk,[fixtures.jpeg()], 'result', edit={'ratio':'3:4'})[0]
                project.refresh_from_db()
                files=[(f.storage,f.name) for f in (item.image,item.thumbnail,item.source)]
                with self.captureOnCommitCallbacks(execute=True): response=self.post(project)
                self.assertRedirects(response,reverse('cabinet_projects'))
                self.assertFalse(Project.objects.filter(pk=project.pk).exists())
                self.assertFalse(ProjectMedia.objects.filter(pk=item.pk).exists())
                self.assertTrue(all(not storage.exists(name) for storage,name in files))
                self.assertEqual(self.client.get(reverse('project_image',args=[item.pk,'full'])).status_code,404)

    def test_related_leads_delivery_and_context_survive(self):
        lead=Lead.objects.create(project=self.project,kind='project',name='Тест',contact='test@example.test',context={'project_title':self.project.title})
        legacy=Lead.objects.create(project=self.project,kind='project',name='Тест',contact='test@example.test',context={'interest':'Замер'})
        delivery=Delivery.objects.create(lead=lead)
        self.post()
        lead.refresh_from_db();delivery.refresh_from_db()
        self.assertIsNone(lead.project_id)
        self.assertEqual(lead.context['project_title'],self.project.title)
        self.assertEqual(delivery.lead_id,lead.pk)
        legacy.refresh_from_db()
        self.assertIsNone(legacy.project_id)
        self.assertEqual(legacy.context,{'interest':'Замер','project_title':self.project.title})

    def test_shared_files_and_other_project_survive(self):
        item=add_images(self.project.pk,[fixtures.jpeg()], 'result', edit={'ratio':'3:4'})[0]
        other=Project.objects.create(title='Другой проект',slug='other')
        shared=ProjectMedia.objects.create(project=other,image=item.image.name,thumbnail=item.thumbnail.name,source=item.source.name)
        self.project.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True): self.post()
        self.assertTrue(ProjectMedia.objects.filter(pk=shared.pk).exists())
        for field in (shared.image,shared.thumbnail,shared.source): self.assertTrue(field.storage.exists(field.name))

    def test_database_rollback_does_not_remove_photo_files(self):
        item=add_images(self.project.pk,[fixtures.jpeg()], 'result', edit={'ratio':'3:4'})[0]
        self.project.refresh_from_db()
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                delete_project(self.project.pk,self.project.updated_at.isoformat())
                raise RuntimeError('Rollback verification')
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())
        for field in (item.image,item.thumbnail,item.source): self.assertTrue(field.storage.exists(field.name))

    def test_deletion_removes_public_routes_catalogue_home_and_sitemap(self):
        add_images(self.project.pk,[fixtures.jpeg()], 'result')
        self.project.refresh_from_db();self.project.status='published';self.project.save()
        url=self.project.get_absolute_url()
        self.assertContains(self.client.get('/'),self.project.title)
        self.post()
        self.assertEqual(self.client.get(url).status_code,404)
        for path in ('/','/projects/','/sitemap.xml'): self.assertNotContains(self.client.get(path),url)

    def test_standard_role_and_new_editors_receive_delete_permission(self):
        group,_=Group.objects.get_or_create(name='Portfolio editors')
        group.permissions.remove(Permission.objects.get(content_type__app_label='core',codename='delete_project'))
        unrelated=Group.objects.create(name='Custom role')
        migration=import_module('core.migrations.0010_project_delete_permission')
        migration.grant_delete_to_editor_role(apps,None)
        self.assertTrue(group.permissions.filter(codename='delete_project').exists())
        self.assertFalse(unrelated.permissions.filter(codename='delete_project').exists())
        with patch.dict('os.environ',{'VLICO_EDITOR_PASSWORD':'A-test-password-938!'}):
            call_command('create_editor',username='new-delete-editor',stdout=StringIO())
        user=get_user_model().objects.get(username='new-delete-editor')
        self.assertTrue(user.has_perms(EDITOR_PERMISSIONS))
        self.assertTrue(user.has_perm('core.delete_project'))

    def test_empty_solution_cannot_remove_published_description(self):
        self.project.status='published';self.project.save()
        data={'title':self.project.title,'slug':self.project.slug,'position':0,'solution':'   ','revision':self.project.updated_at.isoformat()}
        response=self.client.post(reverse('cabinet_edit',args=[self.project.pk]),data,HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code,400)
        self.assertIn('solution',response.json()['errors'])
        self.project.refresh_from_db();self.assertEqual(self.project.solution,'Сохранённое решение')
        self.project.status='draft';self.project.save();data['revision']=self.project.updated_at.isoformat()
        self.assertEqual(self.client.post(reverse('cabinet_edit',args=[self.project.pk]),data,HTTP_ACCEPT='application/json').status_code,200)
