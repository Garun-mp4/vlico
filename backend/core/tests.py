from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.core.files.base import ContentFile
from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase, override_settings
from .models import Project, Lead, LeadAttachment, Delivery, ProjectMedia
from .storage import PrivateMediaStorage


class FoundationTests(TestCase):
    def test_home_preserves_content_and_resolves_static(self):
        response = self.client.get("/")
        self.assertContains(response, "Потолки и свет, продуманные вместе.")
        self.assertContains(response, "Демонстрационная форма")
        self.assertContains(response, "/static/assets/hero-luxurious-geometric.")
        self.assertNotContains(response, "{%")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")

    def test_health_probes_database_and_is_not_cached(self):
        response = self.client.get("/health/")
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response["Cache-Control"], "no-store")
        with patch("core.views.connection.cursor", side_effect=DatabaseError("private details")):
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, "private details", status_code=503)

    def test_nonpublic_paths_are_not_served(self):
        for path in ("/.env", "/from-client/texts/", "/private/leads/test.pdf", "/media/test.pdf", "/admin/", "/projects/draft/"):
            self.assertEqual(self.client.get(path).status_code, 404, path)
        self.assertEqual(self.client.post("/").status_code, 405)

    def test_preview_search_is_blocked(self):
        self.assertContains(self.client.get("/robots.txt"), "Disallow: /")

    def test_new_project_is_draft_and_only_one_cover_is_allowed(self):
        project = Project.objects.create(title="Test", slug="test")
        self.assertEqual(project.status, Project.Status.DRAFT)
        ProjectMedia.objects.create(project=project, image="cover.jpg", is_cover=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectMedia.objects.create(project=project, image="second.jpg", is_cover=True)

    def test_duplicate_notification_is_prevented(self):
        lead = Lead.objects.create(name="Test", contact="test", kind="consultation")
        Delivery.objects.create(lead=lead)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Delivery.objects.create(lead=lead)

    def test_private_files_use_separate_storage_without_public_url(self):
        with TemporaryDirectory() as private, TemporaryDirectory() as public:
            with override_settings(PRIVATE_MEDIA_ROOT=Path(private), MEDIA_ROOT=Path(public)):
                storage = PrivateMediaStorage()
                name = storage.save("leads/test.txt", ContentFile(b"private"))
                self.assertTrue((Path(private) / name).exists())
                self.assertFalse((Path(public) / name).exists())
                with self.assertRaises(ValueError):
                    storage.url(name)
        self.assertIsInstance(LeadAttachment._meta.get_field("file").storage, PrivateMediaStorage)
