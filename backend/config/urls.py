from django.urls import path
from core import views, cabinet, project_views
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import ProjectSitemap
urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("robots.txt", views.robots, name="robots"),
    path("sitemap.xml", sitemap, {"sitemaps": {"projects": ProjectSitemap}}, name="sitemap"),
    path("projects/", project_views.index, name="projects"),
    path("projects/<slug:slug>/", project_views.detail, name="project"),
    path("project-media/<int:pk>/<str:variant>/", project_views.image, name="project_image"),
    path("cabinet/login/", cabinet.login, name="cabinet_login"),
    path("cabinet/logout/", cabinet.signout, name="cabinet_logout"),
    path("cabinet/", cabinet.projects, name="cabinet_projects"),
    path("cabinet/projects/new/", cabinet.edit, name="cabinet_new"),
    path("cabinet/projects/<int:pk>/", cabinet.edit, name="cabinet_edit"),
    path("cabinet/projects/<int:pk>/preview/", project_views.preview, name="cabinet_preview"),
    path("cabinet/projects/<int:pk>/status/", cabinet.change_status, name="cabinet_status"),
    path("cabinet/projects/<int:pk>/upload/", cabinet.upload, name="cabinet_upload"),
    path("cabinet/projects/<int:pk>/media/<int:media_pk>/source/", project_views.source_image, name="cabinet_image_source"),
    path("cabinet/projects/<int:pk>/media/<int:media_pk>/edit/", cabinet.image_editor, name="cabinet_image_editor"),
    path("cabinet/projects/<int:pk>/media/<int:media_pk>/", cabinet.media_edit, name="cabinet_media"),
]
