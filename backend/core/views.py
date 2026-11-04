from django.db import connection, DatabaseError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

@require_safe
def home(request):
    from .portfolio import published_projects
    from .lead_views import initial_lead_form
    return render(request, "site/home.html", {"homepage_projects": published_projects(), "lead_form": initial_lead_form(request)})

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
    # Search launch and sitemap are intentionally implemented in milestone 4/5.
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")
