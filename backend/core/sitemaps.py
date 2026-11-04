from django.contrib.sitemaps import Sitemap
from .portfolio import published_projects

class ProjectSitemap(Sitemap):
    protocol = "https"
    def items(self):
        return published_projects()
    def lastmod(self, project):
        return project.updated_at
