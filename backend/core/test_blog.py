from tempfile import TemporaryDirectory
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Article
from .portfolio import EDITOR_PERMISSIONS
from .test_portfolio import jpeg


@override_settings(SITE_URL="https://vlico39.ru", SITE_INDEXABLE=True)
class BlogArchiveTests(TestCase):
    def test_published_article_urls_remain_available_and_indexed(self):
        index = self.client.get(reverse("blog"))
        sitemap = self.client.get(reverse("sitemap"))
        articles = Article.objects.filter(status=Article.Status.PUBLISHED)
        self.assertEqual(articles.count(), 10)
        for article in articles:
            with self.subTest(slug=article.slug):
                path = reverse("blog_article", args=[article.slug])
                self.assertContains(index, path)
                self.assertContains(sitemap, "https://vlico39.ru" + path)
                page = self.client.get(path)
                self.assertContains(page, article.title)
                self.assertContains(page, 'rel="canonical" href="https://vlico39.ru' + path + '"')
                self.assertNotContains(page, 'content="noindex,nofollow"')

    def test_original_covers_redirect_only_when_they_exist(self):
        article = Article.objects.exclude(original_cover="").first()
        path = reverse("blog_cover", args=[article.original_cover])
        response = self.client.get(path)
        self.assertEqual(response.status_code, 301)
        self.assertIn("/static/blog/", response["Location"])
        self.assertEqual(self.client.get(reverse("blog_cover", args=["unknown.jpg"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("blog_article", args=["unknown"])).status_code, 404)


class ArticleCabinetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.editor = users.objects.create_superuser("blog-editor")
        cls.portfolio_only = users.objects.create_user("portfolio-editor", is_staff=True)
        cls.portfolio_only.user_permissions.set(Permission.objects.filter(
            content_type__app_label="core", codename__in=[name.split(".")[1] for name in EDITOR_PERMISSIONS],
        ))

    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        private = override_settings(PRIVATE_MEDIA_ROOT=directory.name)
        private.enable()
        self.addCleanup(private.disable)
        self.client.force_login(self.editor)

    def change_status(self, article, action, **data):
        response = self.client.post(reverse("cabinet_article_status", args=[article.pk]), {
            "action": action, "revision": article.updated_at.isoformat(), **data,
        })
        article.refresh_from_db()
        return response

    def test_cabinet_requires_permission_and_csrf(self):
        path = reverse("cabinet_article_new")
        self.assertEqual(Client().get(path).status_code, 302)
        self.client.force_login(self.portfolio_only)
        self.assertEqual(self.client.get(path).status_code, 403)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.editor)
        self.assertEqual(protected.post(path, {"title": "Без токена"}).status_code, 403)

    def test_imported_cover_is_editable_and_stays_in_gallery_after_upload(self):
        article = Article.objects.exclude(legacy_cover="").first()
        cover = article.media.get(is_cover=True)
        edit = reverse("cabinet_article_edit", args=[article.pk])
        page = self.client.get(edit)
        self.assertContains(page, 'class="gallery-count">1 / 40 фото')
        self.assertContains(page, reverse("blog_image", args=[cover.pk, "thumb"]))
        self.assertNotContains(page, "Добавить обложку")
        source = reverse("blog_image", args=[cover.pk, "source"])
        response = self.client.get(source)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")
        self.assertTrue(b"".join(response.streaming_content).startswith(b"RIFF"))

        crop = reverse("cabinet_article_crop", args=[article.pk, cover.pk])
        self.assertEqual(self.client.post(crop, {
            "editing": '{"rotation":90,"ratio":"original","cover":true}',
            "revision": cover.updated_at.isoformat(),
        }).status_code, 200)
        upload = reverse("cabinet_article_upload", args=[article.pk])
        uploaded = self.client.post(upload, {"images": [jpeg()]}, HTTP_ACCEPT="application/json")
        new_photo, = uploaded.json()["saved"]
        self.assertEqual(article.cover_media.pk, cover.pk)
        self.assertEqual(list(article.media.values_list("pk", flat=True)), [cover.pk, new_photo])
        self.assertContains(self.client.get(edit), 'class="gallery-count">2 / 40 фото')

        for pk in (cover.pk, new_photo):
            remove = reverse("cabinet_article_media", args=[article.pk, pk])
            self.assertEqual(self.client.post(remove, {"action": "delete", "confirm": "yes"}).status_code, 302)
        self.assertContains(self.client.get(edit), "Добавить обложку")
        self.assertNotContains(Client().get(reverse("blog_article", args=[article.slug])), 'class="blog-cover"')

    @override_settings(SITE_INDEXABLE=True)
    def test_article_lifecycle_preserves_published_address_and_draft_privacy(self):
        response = self.client.post(reverse("cabinet_article_new"), {
            "title": "Как выбрать свет", "description": "Советы студии",
            "body": (
                '<h2>Свет</h2><script>discard-me</script><p><strong>Текст</strong></p>'
                '<ol start="3" class="external"><li><code>LED</code></li></ol><pre><code>3000 K</code></pre>'
            ),
        })
        article = Article.objects.get(title="Как выбрать свет")
        edit = reverse("cabinet_article_edit", args=[article.pk])
        public = reverse("blog_article", args=[article.slug])
        preview = reverse("cabinet_article_preview", args=[article.pk])
        self.assertRedirects(response, edit)
        self.assertEqual(article.slug, "kak-vybrat-svet")
        self.assertEqual(article.body,
            '<h2>Свет</h2><p><strong>Текст</strong></p>'
            '<ol start="3"><li><code>LED</code></li></ol><pre><code>3000 K</code></pre>',
        )
        self.assertEqual(Client().get(public).status_code, 404)
        self.assertContains(self.client.get(preview), 'content="noindex,nofollow"')
        self.change_status(article, "publish")
        self.assertContains(Client().get(public), "<strong>Текст</strong>", html=True)
        self.assertContains(Client().get(reverse("sitemap")), public)
        form = {"title": "Как выбрать свет в кухне", "body": "<p>Новый текст</p>", "slug": "new-address"}
        self.assertContains(self.client.post(edit, {**form, "revision": "stale"}), "в другой вкладке")
        self.assertRedirects(self.client.post(edit, {**form, "revision": article.updated_at.isoformat()}), edit)
        article.refresh_from_db()
        self.assertEqual(article.slug, "kak-vybrat-svet")
        self.assertContains(Client().get(public), "Новый текст")
        self.change_status(article, "delete")
        self.assertEqual(article.status, Article.Status.PUBLISHED)
        self.change_status(article, "delete", confirm="yes")
        self.assertEqual(Client().get(public).status_code, 404)
        self.assertNotContains(Client().get(reverse("sitemap")), public)
        self.assertContains(self.client.get(reverse("cabinet_articles"), {"status": "deleted"}), article.title)
        self.change_status(article, "restore")
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertEqual(Client().get(public).status_code, 404)

    def test_repeated_upload_crop_reorder_and_public_media_visibility(self):
        article = Article.objects.create(title="Галерея", slug="gallery-check", body="<p>Текст</p>")
        upload = reverse("cabinet_article_upload", args=[article.pk])
        invalid = self.client.post(upload, {"images": [jpeg()], "editing": '{"mode":[]}'}, HTTP_ACCEPT="application/json")
        self.assertEqual(invalid.status_code, 400)
        data = {"editing": '{"caption":"Гостиная","ratio":"1:1"}', "upload_key": uuid4()}
        first = self.client.post(upload, {**data, "images": [jpeg()]}, HTTP_ACCEPT="application/json").json()["saved"]
        self.assertEqual(self.client.post(upload, {**data, "images": [jpeg()]}, HTTP_ACCEPT="application/json").json()["saved"], first)
        second, third = self.client.post(upload, {"images": [jpeg(), jpeg()]}, HTTP_ACCEPT="application/json").json()["saved"]
        first_photo = article.media.get(pk=first[0])
        source = reverse("blog_image", args=[first_photo.pk, "source"])
        full = reverse("blog_image", args=[first_photo.pk, "full"])
        self.assertEqual(Client().get(full).status_code, 404)
        self.assertEqual(self.client.get(source).status_code, 200)
        crop = reverse("cabinet_article_crop", args=[article.pk, first_photo.pk])
        self.assertEqual(self.client.post(crop, {
            "editing": '{"rotation":90}', "revision": first_photo.updated_at.isoformat(),
        }).status_code, 200)
        article.refresh_from_db()
        order = [second, first_photo.pk, third]
        response = self.client.post(reverse("cabinet_article_reorder", args=[article.pk]), {
            "order": order, "revision": article.updated_at.isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(article.media.values_list("pk", flat=True)), order)
        self.assertEqual(article.cover_media.pk, second)
        article.refresh_from_db()
        self.change_status(article, "publish")
        page = Client().get(reverse("blog_article", args=[article.slug]))
        self.assertContains(page, "data-project-carousel")
        self.assertEqual(Client().get(full).status_code, 200)
        self.assertEqual(Client().get(source).status_code, 404)
        self.change_status(article, "draft")
        self.assertEqual(Client().get(full).status_code, 404)
