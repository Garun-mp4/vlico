from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.test import Client, RequestFactory, SimpleTestCase, override_settings
from django.urls import path
from django.views.defaults import server_error
from config.urls import urlpatterns as public_urls


def fail(request, kind):
    raise {"denied": PermissionDenied, "invalid": SuspiciousOperation, "failed": RuntimeError}[kind]("private diagnostic detail")


urlpatterns = [path("<str:kind>/", fail), *public_urls]


class PublicErrorCopyTests(SimpleTestCase):
    @override_settings(DEBUG=False, ROOT_URLCONF=__name__)
    def test_errors_show_recovery_without_private_diagnostics(self):
        client = Client(raise_request_exception=False)
        for kind, status, message in (
            ("denied", 403, "Доступ к этой странице ограничен."),
            ("invalid", 400, "Проверьте адрес страницы"),
            ("failed", 500, "Не удалось загрузить страницу."),
        ):
            with self.subTest(kind=kind):
                response = client.get(f"/{kind}/")
                self.assertContains(response, message, status_code=status)
                self.assertNotContains(response, "private diagnostic detail", status_code=status)
                self.assertContains(response, "Связаться с VLICO", status_code=status)

    def test_csrf_protection_is_preserved_with_readable_recovery(self):
        response = Client(enforce_csrf_checks=True).post("/api/leads/", {})
        self.assertContains(response, "Не удалось отправить форму.", status_code=403)
        self.assertContains(response, "обновите страницу", status_code=403)
        self.assertNotContains(response, "CSRF", status_code=403)

    def test_server_error_renders_without_database_access(self):
        response = server_error(RequestFactory().get("/"))
        self.assertContains(response, "Не удалось загрузить страницу.", status_code=500)
