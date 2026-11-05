from django.conf import settings

class PreviewRobotsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/cabinet/"):
            response["Cache-Control"] = "private, no-store"
            response["X-Robots-Tag"] = "noindex, nofollow"
        if request.path.startswith(("/api/", "/request/", "/health/")) or response.status_code >= 400:
            response["X-Robots-Tag"] = "noindex, nofollow"
        if not settings.SITE_INDEXABLE:
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response
