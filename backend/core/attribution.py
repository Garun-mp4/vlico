from datetime import timedelta
import json
from urllib.parse import urlsplit
from django.utils import timezone

UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")
ATTRIBUTION_KEYS = UTM_KEYS + ("landing_path", "referrer")


def plain(value, limit=150):
    return " ".join("".join(char for char in str(value) if ord(char) >= 32).split())[:limit]


def safe_path(value):
    try:
        path = urlsplit(plain(value, 500)).path
    except ValueError:
        return "/"
    return path[:200] if path.startswith("/") and not path.startswith("//") else "/"


def safe_referrer(value):
    try:
        parts = urlsplit(plain(value, 500))
        if parts.scheme in {"http", "https"} and parts.hostname:
            return f"{parts.scheme}://{parts.hostname}{parts.path}"[:200]
    except ValueError:
        pass
    return ""


def clean_attribution(data):
    if not isinstance(data, dict):
        return {}
    result = {key: plain(data[key]) for key in UTM_KEYS if isinstance(data.get(key), str)}
    if isinstance(data.get("landing_path"), str):
        result["landing_path"] = safe_path(data["landing_path"])
    if isinstance(data.get("referrer"), str):
        result["referrer"] = safe_referrer(data["referrer"])
    return result


def submission_attribution(request):
    result = request.session.get("lead_attribution", {}).get("data", {})
    raw = request.POST.get("attribution", "")
    if raw and len(raw) <= 3000:
        try:
            result = clean_attribution(json.loads(raw)) or result
        except (ValueError, TypeError):
            pass
    return clean_attribution(result)


class AttributionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET" and (request.path == "/" or request.path.startswith(("/projects/", "/request/", "/calculator/"))):
            now = timezone.now()
            saved = request.session.get("lead_attribution", {})
            if not saved or saved.get("expires", 0) < now.timestamp():
                data = {key: request.GET[key] for key in UTM_KEYS if request.GET.get(key)}
                data.update(landing_path=request.path, referrer=request.META.get("HTTP_REFERER", ""))
                request.session["lead_attribution"] = {"data": clean_attribution(data), "expires": (now + timedelta(days=30)).timestamp()}
        return self.get_response(request)
