from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.test import TestCase, Client
from django.urls import reverse
from core.models import Project, ProjectCategory
from core.portfolio import CATEGORY_PERMISSIONS
from core.test_portfolio import PortfolioTests


class CategoryTests(TestCase):
    setUpTestData = classmethod(PortfolioTests.setUpTestData.__func__)
    setUp = PortfolioTests.setUp
    login = PortfolioTests.login
    upload = PortfolioTests.upload

    def category_login(self):
        self.editor.user_permissions.add(*Permission.objects.filter(content_type__app_label="core", codename__in=[p.split(".")[1] for p in CATEGORY_PERMISSIONS]))
        self.login()

    def test_all_solution_categories_are_available(self):
        from .site_content import SERVICES
        expected = {item["title"] for item in SERVICES}
        self.assertEqual(set(ProjectCategory.objects.values_list("title", flat=True)),expected)

    def test_category_visibility_keeps_projects_and_can_be_restored(self):
        self.category_login()
        category = ProjectCategory.objects.create(title="Внутреннее направление")
        self.project.categories.add(category)
        self.upload(1)
        self.project.status = "published"
        self.project.save()
        path = reverse("cabinet_category_edit", args=[category.pk])
        self.assertContains(self.client.get(path), "Показывать категорию на сайте")
        data = {"title": category.title, "position": category.position, "revision": category.updated_at.isoformat()}
        self.assertEqual(self.client.post(path, data).status_code, 302)
        category.refresh_from_db()
        self.assertFalse(category.is_public)
        for public_path in ("/", reverse("projects"), self.project.get_absolute_url()):
            response = self.client.get(public_path)
            self.assertNotContains(response, category.title)
            self.assertContains(response, self.project.title)
        self.assertEqual(self.client.get(reverse("projects"), {"category": category.pk}).status_code, 404)
        self.assertContains(self.client.get(reverse("cabinet_projects"), {"category": category.pk}), self.project.title)
        self.assertContains(self.client.get(reverse("cabinet_categories")), "Только в кабинете")
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, "published")
        self.assertEqual(self.project.media.count(), 1)
        self.assertTrue(self.project.categories.filter(pk=category.pk).exists())
        data.update(is_public="on", revision=category.updated_at.isoformat())
        self.assertEqual(self.client.post(path, data).status_code, 302)
        self.assertContains(self.client.get(reverse("projects"), {"category": category.pk}), category.title)

    def test_category_crud_duplicate_and_stale_revision(self):
        self.category_login()
        new = reverse("cabinet_category_new")
        self.assertEqual(self.client.post(new,{"title":"", "position":0}).status_code,200)
        self.client.post(new,{"title":" Нестандартный свет ","position":7})
        category=ProjectCategory.objects.get(title="Нестандартный свет")
        response=self.client.post(new,{"title":"нестандартный свет","position":0})
        self.assertContains(response,"Категория с таким названием уже существует")
        with self.assertRaises(IntegrityError),transaction.atomic():
            ProjectCategory.objects.create(title="НЕСТАНДАРТНЫЙ СВЕТ")
        path=reverse("cabinet_category_edit",args=[category.pk])
        self.client.post(path,{"title":"Changed", "position":0,"revision":"old"})
        category.refresh_from_db();self.assertEqual(category.title,"Нестандартный свет")
        self.client.post(path,{"title":"Новая категория", "position":2,"revision":category.updated_at.isoformat()})
        category.refresh_from_db();self.assertEqual(category.title,"Новая категория")

    def test_delete_only_removes_category_not_project_or_other_categories(self):
        self.category_login()
        first, second = list(ProjectCategory.objects.all())[:2]
        self.project.categories.set([first,second])
        self.upload(1)
        self.project.status="published";self.project.save()
        path=reverse("cabinet_category_delete",args=[first.pk])
        self.assertEqual(self.client.get(path).status_code,200)
        self.assertTrue(ProjectCategory.objects.filter(pk=first.pk).exists())
        self.client.post(path,{"revision":first.updated_at.isoformat()})
        self.assertTrue(ProjectCategory.objects.filter(pk=first.pk).exists())
        self.client.post(path,{"confirm":"yes","revision":first.updated_at.isoformat()})
        self.assertFalse(ProjectCategory.objects.filter(pk=first.pk).exists())
        self.project.refresh_from_db()
        self.assertEqual(self.project.status,"published")
        self.assertEqual(self.project.media.count(),1)
        self.assertEqual(list(self.project.categories.all()),[second])
        self.assertContains(self.client.get('/'),self.project.title)

    def test_category_permissions_csrf_and_methods(self):
        path=reverse("cabinet_category_new")
        self.assertEqual(self.client.get(path).status_code,302)
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(path).status_code,403)
        self.login()
        self.assertEqual(self.client.get(path).status_code,403)
        self.category_login()
        strict=Client(enforce_csrf_checks=True);strict.force_login(self.editor)
        self.assertEqual(strict.post(path,{"title":"CSRF", "position":0}).status_code,403)
        self.assertEqual(self.client.put(path).status_code,405)

    def test_multiple_categories_are_saved_and_shown(self):
        self.category_login()
        first, second=list(ProjectCategory.objects.all())[:2]
        data={"title":"Edited project","slug":self.project.slug,"position":0,"categories":[first.pk,second.pk],"revision":self.project.updated_at.isoformat()}
        self.client.post(reverse("cabinet_edit",args=[self.project.pk]),data)
        self.project.refresh_from_db()
        self.assertEqual(self.project.categories.count(),2)
        self.project.status="published";self.project.save()
        for path in ('/',reverse('projects'),reverse('project',args=[self.project.slug])):
            response=self.client.get(path)
            self.assertContains(response,first.title);self.assertContains(response,second.title)

    def test_filters_only_expose_published_projects_and_validate_category(self):
        first, second=list(ProjectCategory.objects.all())[:2]
        self.project.categories.add(first)
        self.assertNotContains(self.client.get(reverse('projects')+'?category='+str(first.pk)),self.project.title)
        self.project.status="published";self.project.save()
        self.assertContains(self.client.get(reverse('projects')+'?category='+str(first.pk)),self.project.title)
        self.assertNotContains(self.client.get(reverse('projects')+'?category='+str(second.pk)),self.project.title)
        self.assertEqual(self.client.get(reverse('projects')+'?category=bad').status_code,404)
        self.login()
        self.assertContains(self.client.get(reverse('cabinet_projects')+'?category='+str(first.pk)),self.project.title)
        self.assertNotContains(self.client.get(reverse('cabinet_projects')+'?status=draft&category='+str(first.pk)),self.project.title)

    def test_every_published_project_appears_on_landing_without_featured_flag(self):
        self.upload(1);self.login()
        self.project.featured=False;self.project.save()
        self.client.post(reverse('cabinet_status',args=[self.project.pk]),{'action':'publish','confirm':'yes'})
        response=self.client.get('/')
        self.assertContains(response,self.project.title)
        for i in range(5):
            Project.objects.create(title='Extra '+str(i),slug='extra-'+str(i),status='published',solution='Real solution')
        response=self.client.get('/')
        self.assertContains(response,self.project.title)
        for i in range(5): self.assertContains(response,'Extra '+str(i))
        self.client.post(reverse('cabinet_status',args=[self.project.pk]),{'action':'archive','confirm':'yes'})
        self.assertNotContains(self.client.get('/'),self.project.title)

    def test_invalid_project_category_and_duplicate_slug_are_rejected(self):
        self.login()
        response=self.client.post(reverse('cabinet_new'),{'title':'Bad','slug':self.project.slug,'position':0,'categories':[999999]})
        self.assertEqual(response.status_code,200)
        self.assertEqual(Project.objects.count(),1)
