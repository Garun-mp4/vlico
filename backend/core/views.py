from django.db import connection, DatabaseError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

@require_safe
def home(request):
    from .portfolio import published_projects
    from .project_videos import PROJECT_VIDEOS
    from .lead_views import initial_lead_form, quick_calculator_context
    lead_form = initial_lead_form(request, "project")
    lead_form.fields["kind"].choices = [
        choice for choice in lead_form.fields["kind"].choices if choice[0] != "partner"
    ]
    projects = published_projects()
    homepage_projects = projects[:6]
    about_slugs = (
        "svetovye-linii-i-podvesnye-svetilniki",
        "gostinaya-s-hrustalnoy-lyustroy",
        "svetovoy-potolok-v-garderobnoy",
        "penthouse-rumyantseva",
        "russkaya-evropa-ul-molodoy-gvardii-36",
        "ul-koloskova-11",
    )
    about_by_slug = {project.slug: project for project in projects.filter(slug__in=about_slugs)}
    about_projects = [about_by_slug[slug] for slug in about_slugs if slug in about_by_slug]
    return render(request, "site/home.html", {
        "homepage_projects": homepage_projects,
        "project_videos": PROJECT_VIDEOS,
        "about_projects": about_projects or homepage_projects[:3],
        "lead_form": lead_form,
        **quick_calculator_context(request),
    })

@require_safe
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    response = JsonResponse({"status": "ok"})
    response["Cache-Control"] = "no-store"
    return response

@require_safe
def robots(request):
    from django.conf import settings
    text = "User-agent: *\nDisallow: /\n"
    if settings.SITE_INDEXABLE:
        text = "User-agent: *\nDisallow: /cabinet/\nDisallow: /api/\nDisallow: /request/\nDisallow: /health/\nSitemap: " + settings.SITE_URL + "/sitemap.xml\n"
    return HttpResponse(text, content_type="text/plain")
