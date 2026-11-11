from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from core.models import Project, ProjectMedia, LoginBucket
from core.portfolio import EDITOR_PERMISSIONS, add_images, prepared_image


def jpeg(name="room.jpg", size=(100, 80)):
    stream = BytesIO()
    Image.new("RGB", size, "white").save(stream, "JPEG")
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/jpeg")


class PortfolioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = get_user_model().objects.create_user("editor", password="A-test-password-938!", is_staff=True)
        cls.editor.user_permissions.set(Permission.objects.filter(content_type__app_label="core", codename__in=[p.split(".")[1] for p in EDITOR_PERMISSIONS]))
        cls.reader = get_user_model().objects.create_user("reader", password="A-test-password-938!")

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.settings_context = override_settings(MEDIA_ROOT=Path(self.directory.name)/"public", PRIVATE_MEDIA_ROOT=Path(self.directory.name)/"private")
        self.settings_context.enable()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.settings_context.disable)
        self.project = Project.objects.create(title="Real project", slug="real-project", solution="Verified solution", featured=True, editor_notes="PRIVATE EDITOR NOTES")

    def login(self):
        self.client.force_login(self.editor)

    def upload(self, count=2):
        add_images(self.project.pk, [jpeg() for _ in range(count)], "result")
        return list(self.project.media.all())

    def test_guest_and_non_editor_cannot_mutate_or_preview(self):
        paths = [reverse("cabinet_projects"), reverse("cabinet_edit", args=[self.project.pk]), reverse("cabinet_preview", args=[self.project.pk])]
        for path in paths:
            self.assertEqual(self.client.get(path).status_code, 302)
        self.client.force_login(self.reader)
        for path in paths:
            self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.post(reverse("cabinet_status", args=[self.project.pk]), {"action": "publish", "confirm": "yes"}).status_code, 403)

    def test_home_gallery_starts_with_cover_and_uses_saved_media_order(self):
        first, second, cover = self.upload(3)
        first.is_cover = False
        first.save()
        cover.is_cover = True
        cover.save()
        self.project.status = "published"
        self.project.save()
        draft = Project.objects.create(title="Private gallery", slug="private-gallery")
        private = add_images(draft.pk, [jpeg()], "result")[0]
        home = self.client.get("/")
        urls = [reverse("project_image", args=[m.pk, "thumb"]) for m in (cover, first, second)]
        html = home.content.decode()
        self.assertLess(html.index(urls[0]), html.index(urls[1]))
        self.assertLess(html.index(urls[1]), html.index(urls[2]))
        self.assertContains(home, 'data-project-carousel', count=1)
        self.assertNotContains(home, reverse("project_image", args=[private.pk, "thumb"]))
        self.assertNotContains(self.client.get(reverse("projects")), 'data-project-carousel')

    def test_home_single_photo_keeps_project_link_without_carousel(self):
        item = self.upload(1)[0]
        self.project.status = "published"
        self.project.save()
        home = self.client.get("/")
        self.assertContains(home, reverse("project_image", args=[item.pk, "thumb"]))
        self.assertContains(home, self.project.get_absolute_url())
        self.assertNotContains(home, 'data-project-carousel')

    def test_drafts_and_their_media_are_private(self):
        item = self.upload(1)[0]
        self.assertEqual(self.client.get(reverse("project", args=[self.project.slug])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("projects")), self.project.title)
        self.assertNotContains(self.client.get("/"), self.project.title)
        self.assertEqual(self.client.get(reverse("project_image", args=[item.pk, "full"])).status_code, 404)
        self.assertEqual(self.client.get("/media/"+item.image.name).status_code, 404)
        self.login()
        response = self.client.get(reverse("cabinet_preview", args=[self.project.pk]))
        self.assertContains(response, self.project.title)
        self.assertNotContains(response, self.project.editor_notes)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(self.client.get(reverse("project_image", args=[item.pk, "full"])).status_code, 200)

    def test_publication_and_unpublication_update_all_public_surfaces(self):
        item = self.upload(1)[0]
        self.login()
        path = reverse("cabinet_status", args=[self.project.pk])
        self.client.post(path, {"action": "publish"})
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, "draft")
        self.client.post(path, {"action": "publish", "confirm": "yes"})
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, "published")
        self.assertIsNotNone(self.project.published_at)
        guest = Client()
        for page in ("/", reverse("projects"), reverse("project", args=[self.project.slug])):
            response = guest.get(page)
            self.assertContains(response, self.project.title)
            self.assertNotContains(response, "PRIVATE EDITOR NOTES")
        self.assertEqual(guest.get(reverse("project_image", args=[item.pk, "thumb"])).status_code, 200)
        self.assertContains(guest.get("/sitemap.xml"), "/projects/real-project/")
        self.client.post(path, {"action": "draft"})
        self.assertEqual(guest.get(reverse("project_image", args=[item.pk, "full"])).status_code, 404)
        self.assertNotContains(guest.get(reverse("projects")), self.project.title)
        self.assertNotContains(guest.get("/sitemap.xml"), "/projects/real-project/")

    def test_publication_requires_photo_and_solution(self):
        self.login()
        self.client.post(reverse("cabinet_status", args=[self.project.pk]), {"action": "publish", "confirm": "yes"})
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, "draft")

    def test_archive_confirmation_and_restore_preserve_media(self):
        self.upload(1)
        self.login()
        path = reverse("cabinet_status", args=[self.project.pk])
        self.client.post(path, {"action": "archive"})
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, "draft")
        self.client.post(path, {"action": "archive", "confirm": "yes"})
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, "archived")
        self.client.post(path, {"action": "restore"})
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, "draft")
        self.assertEqual(self.project.media.count(), 1)

    def test_upload_is_optimized_and_strips_original_name(self):
        item = self.upload(1)[0]
        self.assertNotIn("room.jpg", item.image.name)
        self.assertEqual((item.width, item.height), (100, 80))
        for field in (item.image, item.thumbnail):
            with Image.open(field.path) as image:
                self.assertEqual(image.format, "WEBP")
                self.assertFalse(image.getexif())

    def test_responsive_srcset_uses_actual_thumbnail_and_full_widths(self):
        portrait, landscape = add_images(
            self.project.pk,
            [jpeg("portrait.jpg", (720, 1280)), jpeg("landscape.jpg", (1280, 960))],
            "result",
        )
        self.assertEqual(portrait.thumbnail_width, 360)
        self.assertEqual(landscape.thumbnail_width, 640)
        with Image.open(portrait.thumbnail.path) as thumbnail:
            self.assertEqual(thumbnail.width, portrait.thumbnail_width)

        self.project.status = Project.Status.PUBLISHED
        self.project.save()
        home = self.client.get("/")
        portrait_srcset = (
            f'{reverse("project_image", args=[portrait.pk, "thumb"])} 360w, '
            f'{reverse("project_image", args=[portrait.pk, "full"])} 720w'
        )
        self.assertContains(home, f'srcset="{portrait_srcset}"')
        self.assertContains(home, '(max-width: 1099px) calc((93.3vw - 28px) / 2), calc((100vw - clamp(40px, 6.7vw, 128px) - 56px) / 3)')
        self.assertContains(home, 'data-portrait')
        catalogue = self.client.get(reverse("projects"))
        self.assertContains(catalogue, 'sizes="(max-width: 640px) calc(100vw - 40px), (max-width: 800px) 93vw, 46vw"')
        self.assertContains(catalogue, 'data-portrait')
        detail = self.client.get(reverse("project", args=[self.project.slug]))
        self.assertContains(detail, f'srcset="{portrait_srcset}"')
        self.assertContains(detail, reverse("project_image", args=[portrait.pk, "full"]))

    def test_rejects_invalid_images_and_whole_batch(self):
        invalid = SimpleUploadedFile("fake.jpg", b"<script>alert(1)</script>", content_type="image/jpeg")
        with self.assertRaises(ValidationError):
            add_images(self.project.pk, [jpeg(), invalid], "result")
        self.assertEqual(self.project.media.count(), 0)
        self.assertEqual(list(Path(self.directory.name).rglob("*.webp")), [])
        with self.assertRaises(ValidationError):
            add_images(self.project.pk, [jpeg() for _ in range(9)], "result")
        fake = jpeg()
        fake.size = 13*1024*1024
        with self.assertRaises(ValidationError):
            prepared_image(fake)

    def test_cover_order_captions_and_delete(self):
        one, two = self.upload()
        self.login()
        path = reverse("cabinet_media", args=[self.project.pk, two.pk])
        self.client.post(path, {"action": "cover"})
        self.assertEqual(self.project.media.filter(is_cover=True).get().pk, two.pk)
        self.client.post(path, {"action": "up"})
        self.assertEqual(self.project.media.first().pk, two.pk)
        self.client.post(path, {"action": "save", "alt": "Track", "caption": "Installation", "section": "process"})
        two.refresh_from_db()
        self.assertEqual(two.section, "process")
        self.client.post(path, {"action": "delete"})
        self.assertTrue(ProjectMedia.objects.filter(pk=two.pk).exists())
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(path, {"action": "delete", "confirm": "yes"})
        self.assertFalse(ProjectMedia.objects.filter(pk=two.pk).exists())
        self.assertFalse(Path(two.image.path).exists())
        one.refresh_from_db()
        self.assertTrue(one.is_cover)

    def test_cross_project_photo_is_not_mutated(self):
        one = self.upload(1)[0]
        other = Project.objects.create(title="Other", slug="other")
        self.login()
        response = self.client.post(reverse("cabinet_media", args=[other.pk, one.pk]), {"action": "delete", "confirm": "yes"})
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ProjectMedia.objects.filter(pk=one.pk).exists())

    def test_last_published_photo_cannot_be_deleted(self):
        one = self.upload(1)[0]
        self.project.status = "published"
        self.project.save()
        self.login()
        self.client.post(reverse("cabinet_media", args=[self.project.pk, one.pk]), {"action": "delete", "confirm": "yes"})
        self.assertTrue(ProjectMedia.objects.filter(pk=one.pk).exists())

    def test_edit_rejects_stale_revision_and_bad_slug(self):
        self.login()
        payload = {"title": "Changed", "slug": "changed", "position": 0, "revision": "stale"}
        response = self.client.post(reverse("cabinet_edit", args=[self.project.pk]), payload)
        self.assertContains(response, "Проект изменён в другой вкладке")
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Real project")
        payload["revision"] = self.project.updated_at.isoformat()
        response = self.client.post(reverse("cabinet_edit", args=[self.project.pk]), payload)
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Changed")

    def test_unsafe_operations_require_csrf_and_post(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.editor)
        path = reverse("cabinet_status", args=[self.project.pk])
        self.assertEqual(strict.post(path, {"action": "publish"}).status_code, 403)
        self.assertEqual(strict.get(path).status_code, 405)
        self.assertEqual(strict.get(reverse("cabinet_logout")).status_code, 405)

    def test_login_logout_and_rate_limit(self):
        path = reverse("cabinet_login")
        response = self.client.post(path, {"username": "editor", "password": "A-test-password-938!"})
        self.assertRedirects(response, reverse("cabinet_projects"))
        self.client.post(reverse("cabinet_logout"))
        self.assertEqual(self.client.get(reverse("cabinet_projects")).status_code, 302)
        for _ in range(10):
            self.client.post(path, {"username": "missing", "password": "bad"})
        response = self.client.post(path, {"username": "editor", "password": "A-test-password-938!"})
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_new_form_and_detail_escape_html(self):
        self.login()
        self.assertContains(self.client.get(reverse("cabinet_new")), "Новый проект")
        self.project.solution = "<script>alert(1)</script>"
        self.project.status = "published"
        self.project.save()
        response = self.client.get(reverse("project", args=[self.project.slug]))
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")
