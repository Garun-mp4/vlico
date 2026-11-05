from django.db import connection, DatabaseError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

@require_safe
def home(request):
    from .portfolio import published_projects
    from .lead_views import initial_lead_form
    from .configurator import configurator_context
    return render(request, "site/home.html", {"homepage_projects": published_projects(), "lead_form": initial_lead_form(request), **configurator_context(request)})

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
