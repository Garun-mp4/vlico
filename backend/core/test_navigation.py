import re
from django.test import TestCase
from .models import Project, ProjectCategory, ProjectMedia
from .public_site import project_navigation
from .site_content import NEW_SOLUTIONS


class NavigationTests(TestCase):
    def test_new_solution_categories_filter_projects_and_update_both_menus(self):
        for item in NEW_SOLUTIONS:
            with self.subTest(slug=item["slug"]):
                category = ProjectCategory.objects.get(title=item["title"], is_public=True)
                project = Project.objects.create(title="Проект " + item["slug"], slug="nav-" + item["slug"], status="published")
                project.categories.add(category)
                response = self.client.get("/contacts/")
                self.assertContains(response, f'href="/projects/?category={category.pk}"', count=2)
                response = self.client.get("/projects/", {"category": category.pk})
                self.assertContains(response, f"<h1>{item['title']}</h1>", html=True)
                self.assertContains(response, project.title)

    def test_solution_category_import_preserves_editorial_settings_and_assignments(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        from .models import Service
        migration = import_module("core.migrations.0017_new_solution_categories")
        category = ProjectCategory.objects.get(title=NEW_SOLUTIONS[0]["title"])
        category.title = category.title.upper()
        category.position = 101
        category.is_public = False
        category.save()
        service = Service.objects.create(slug="smart-home", title="Управление светом")
        project = Project.objects.create(title="С подключением Алисы", slug="alice-category")
        project.services.add(service)
        other = ProjectCategory.objects.first()
        project.categories.add(other)
        with connection.schema_editor() as editor:
            migration.add_solution_categories(apps, editor)
            migration.add_solution_categories(apps, editor)
        category.refresh_from_db()
        self.assertFalse(category.is_public)
        self.assertEqual(category.position, 101)
        self.assertEqual(ProjectCategory.objects.filter(title__iexact=category.title).count(), 1)
        self.assertTrue(project.categories.filter(pk=category.pk).exists())
        self.assertTrue(project.categories.filter(pk=other.pk).exists())

    def test_shared_header_on_public_routes_and_project_detail(self):
        project = Project.objects.create(title="Объект", slug="navigation-project", status="published")
        for path in ("/", "/projects/", project.get_absolute_url(), "/services/", "/services/shadow/", "/calculator/", "/contacts/", "/partners/", "/privacy/", "/consent/", "/cookies/", "/request/consultation/", "/missing/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                status = 404 if path == "/missing/" else 200
                self.assertContains(response, "data-site-header", count=1, status_code=status)
                self.assertContains(response, 'aria-controls="desktop-projects"', count=1, status_code=status)
                self.assertContains(response, 'aria-controls="mobile-projects"', count=1, status_code=status)
                self.assertContains(response, 'href="/#about"', status_code=status)
                self.assertContains(response, 'href="/calculator/"', status_code=status)

    def test_category_changes_immediately_update_both_navigation_versions(self):
        category = ProjectCategory.objects.create(title="Авторские потолки", position=100)
        for path in ("/", "/contacts/"):
            response = self.client.get(path)
            self.assertContains(response, f'href="/projects/?category={category.pk}"', count=2)
            self.assertContains(response, category.title, count=2)
        category.title = "Потолки для гостиной"
        category.save()
        self.assertContains(self.client.get("/contacts/"), category.title, count=2)
        category.delete()
        self.assertNotContains(self.client.get("/contacts/"), "Потолки для гостиной")

    def test_category_navigation_opens_only_matching_published_projects(self):
        category = ProjectCategory.objects.first()
        public = Project.objects.create(title="Работа в категории", slug="category-nav", status="published")
        private = Project.objects.create(title="Неопубликованная работа", slug="nav-draft")
        public.categories.add(category)
        private.categories.add(category)
        Project.objects.create(title="Другой объект", slug="not-in-category", status="published")
        response = self.client.get("/projects/", {"category": category.pk})
        self.assertContains(response, f"<h1>{category.title}</h1>", html=True)
        self.assertContains(response, public.title)
        self.assertNotContains(response, private.title)
        self.assertNotContains(response, "Другой объект")
        self.assertEqual(len(re.findall(rf'href="/projects/\?category={category.pk}"[^>]*aria-current="page"', response.content.decode())), 2)

    def test_custom_previews_use_only_published_covers_in_one_query(self):
        category = ProjectCategory.objects.create(title="Купольные потолки")
        private = Project.objects.create(title="Черновик", slug="private-preview")
        private.categories.add(category)
        secret = ProjectMedia.objects.create(project=private, image="private.webp", is_cover=True)
        with self.assertNumQueries(1):
            navigation = project_navigation()
        item = next(item for item in navigation if item.pk == category.pk)
        self.assertEqual(item.preview_url, "")
        public = Project.objects.create(title="Публичный", slug="public-preview", status="published")
        public.categories.add(category)
        cover = ProjectMedia.objects.create(project=public, image="public.webp", is_cover=True)
        navigation = project_navigation()
        item = next(item for item in navigation if item.pk == category.pk)
        self.assertEqual(item.preview_url, f"/project-media/{cover.pk}/thumb/")
        self.assertNotEqual(item.preview_url, f"/project-media/{secret.pk}/thumb/")
