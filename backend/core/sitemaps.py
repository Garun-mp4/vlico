from django.contrib.sitemaps import Sitemap
from .portfolio import published_projects
from django.urls import reverse
from .site_content import SERVICES


class PublicSitemap(Sitemap):
    def items(self):
        return ["home", "services", "partners", "contacts", "projects", "calculator"]
    def location(self, item):
        return reverse(item)


class ServiceSitemap(Sitemap):
    def items(self):
        return SERVICES
    def location(self, item):
        return reverse("service", args=[item["slug"]])

class ProjectSitemap(Sitemap):
    protocol = "https"
    def items(self):
        return published_projects()
    def lastmod(self, project):
        return project.updated_at
