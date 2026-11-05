from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, Client
from django.urls import reverse
from .models import Project, ProjectMedia, ProjectCategory
from .portfolio import EDITOR_PERMISSIONS


class CabinetUXTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = get_user_model().objects.create_user("ux-editor", is_staff=True)
        cls.editor.user_permissions.set(Permission.objects.filter(
            content_type__app_label="core", codename__in=[p.split(".")[1] for p in EDITOR_PERMISSIONS]))

    def setUp(self):
        self.client.force_login(self.editor)
        self.project = Project.objects.create(title="Кухня", slug="kitchen", location="Калининград", solution="Результат")

    def test_search_category_status_and_counts_work_together(self):
        category = ProjectCategory.objects.create(title="Свет")
        self.project.categories.add(category)
        second = Project.objects.create(title="Ванная", slug="bath", location="Калининград", status="published")
        second.categories.add(category)
        Project.objects.create(title="Другая", slug="other")
        response = self.client.get(reverse("cabinet_projects"), {"q":"Калининград", "category":category.pk, "status":"draft"})
        self.assertEqual(list(response.context["projects"]), [self.project])
        self.assertEqual(response.context["total"], 2)
        self.assertEqual([count for _, _, count in response.context["status_counts"]], [1, 1, 0])
        self.assertContains(response, "Кухня")
        self.assertNotContains(response, "Ванная")

    def test_counts_include_every_project_of_same_status(self):
        Project.objects.create(title="Ванная", slug="bath")
        response = self.client.get(reverse("cabinet_projects"))
        self.assertEqual(response.context["total"], 2)
        self.assertEqual(response.context["status_counts"][0][2], 2)

    def test_stable_sort_and_empty_search(self):
        other = Project.objects.create(title="А", slug="first", position=2)
        response = self.client.get(reverse("cabinet_projects"), {"sort":"title"})
        self.assertEqual(list(response.context["projects"]), [other, self.project])
        response = self.client.get(reverse("cabinet_projects"), {"q":"нет совпадений"})
        self.assertContains(response, "Проекты не найдены")

    def test_json_save_returns_revision_and_preserves_stale_input(self):
        path = reverse("cabinet_edit", args=[self.project.pk])
        payload = {"title":"Новое название", "slug":"kitchen", "position":0, "revision":self.project.updated_at.isoformat()}
        response = self.client.post(path, payload, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(response.json()["revision"], self.project.updated_at.isoformat())
        payload["title"] = "Устаревший текст"
        response = self.client.post(path, payload, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("__all__", response.json()["errors"])
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Новое название")

    def test_create_generates_unique_slug_without_creating_on_get(self):
        path = reverse("cabinet_new")
        self.client.get(path)
        self.assertEqual(Project.objects.count(), 1)
        for expected in ("tenevoy-potolok", "tenevoy-potolok-2"):
            response = self.client.post(path, {"title":"Теневой потолок", "position":0}, HTTP_ACCEPT="application/json")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["created"])
            self.assertTrue(Project.objects.filter(slug=expected).exists())

    def test_reorder_is_atomic_persistent_and_rejects_stale_or_foreign_ids(self):
        first = ProjectMedia.objects.create(project=self.project, image="first.webp", is_cover=True, position=0)
        second = ProjectMedia.objects.create(project=self.project, image="second.webp", position=1)
        path = reverse("cabinet_reorder", args=[self.project.pk])
        revision = self.project.updated_at.isoformat()
        response = self.client.post(path, {"revision":revision, "order":[second.pk, first.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(self.project.media.values_list("pk", flat=True)), [second.pk, first.pk])
        first.refresh_from_db()
        self.assertFalse(first.is_cover)
        second.refresh_from_db()
        self.assertTrue(second.is_cover)
        self.assertEqual(response.json()['media_revisions'][str(second.pk)],second.updated_at.isoformat())
        self.assertEqual(self.client.post(path, {"revision":revision, "order":[first.pk, second.pk]}).status_code, 409)
        new_revision = response.json()["revision"]
        for ids in ([first.pk, first.pk], [first.pk], [first.pk, 999999], ["bad"]):
            self.assertEqual(self.client.post(path, {"revision":new_revision, "order":ids}).status_code, 400)
        self.assertEqual(list(self.project.media.values_list("pk", flat=True)), [second.pk, first.pk])

    def test_reorder_requires_editor_post_and_csrf(self):
        path = reverse("cabinet_reorder", args=[self.project.pk])
        self.assertEqual(self.client.get(path).status_code, 405)
        guest = Client()
        self.assertEqual(guest.post(path).status_code, 302)
        no_permission = get_user_model().objects.create_user("reader")
        guest.force_login(no_permission)
        self.assertEqual(guest.post(path).status_code, 403)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.editor)
        self.assertEqual(protected.post(path).status_code, 403)
