from django.contrib.sitemaps import Sitemap
from .portfolio import published_projects
from django.urls import reverse
from .models import Article
from .site_content import SERVICES


class PublicSitemap(Sitemap):
    def items(self):
        return ["home", "services", "partners", "contacts", "projects", "calculator", "blog"]
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


class BlogSitemap(Sitemap):
    def items(self):
        return Article.objects.filter(status=Article.Status.PUBLISHED)

    def location(self, article):
        return reverse("blog_article", args=[article.slug])
