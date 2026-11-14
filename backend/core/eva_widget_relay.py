"""Relay the public Eva widget protocol through the website origin."""
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .eva_delivery import NoRedirect
from .lead_service import SubmissionError, throttle


ASSETS = {
    "widget/chat-widget.js": "application/javascript",
    "widget/style.css": "text/css",
    "widget/message.mp3": "audio/mpeg",
}
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
SOCKET_ID = re.compile(r"[A-Za-z0-9_-]{1,96}")
HEX_ID = re.compile(r"[0-9a-f]{64}")
MAX_REPLY = 2 * 1024 * 1024


def widget_route(request, path, widget_id):
    query = request.GET
    if path in ASSETS:
        return {"widgetId": widget_id, "language": "ru"}, ASSETS[path], {"GET"}
    if path == f"api/dashboard/channels/config/{widget_id}":
        return {"origin": request.build_absolute_uri("/").rstrip("/")}, "application/json", {"GET"}
    if path == f"api/dashboard/channels/hook/{widget_id}" or path == "api/dashboard/widget-message-actions":
        return {}, "application/json", {"POST"}
    if path == "api/dashboard/messages" and UUID.fullmatch(query.get("conversationId", "")):
        return {"conversationId": query["conversationId"], "limit": 10000}, "application/json", {"GET"}
    if path != "socket.io/" or query.get("EIO") != "4" or query.get("transport") != "polling":
        return None
    params = {"EIO": 4, "transport": "polling"}
    if query.get("b64") == "1":
        params["b64"] = 1
    if query.get("sid"):
        if not SOCKET_ID.fullmatch(query["sid"]):
            return None
        params["sid"] = query["sid"]
    else:
        if query.get("channelId") != widget_id or not HEX_ID.fullmatch(query.get("roomId", "")):
            return None
    for name in ("roomId", "channelId"):
        if name in query:
            if not (HEX_ID.fullmatch(query[name]) if name == "roomId" else query[name] == widget_id):
                return None
            params[name] = query[name]
    return params, "text/plain", {"GET", "POST"} if "sid" in params else {"GET"}


@csrf_exempt
def relay(request, path):
    # This endpoint has no access to cookies or credentials from the upstream.
    widget_id = settings.EVA_WIDGET_ID.lower()
    if not settings.EVA_WIDGET_ENABLED or not UUID.fullmatch(widget_id):
        return HttpResponse(status=404)
    route = widget_route(request, path, widget_id)
    if route is None:
        return HttpResponse(status=404)
    query, content_type, methods = route
    if request.method not in methods:
        return HttpResponse(status=405, headers={"Allow": ", ".join(sorted(methods))})
    origin = request.build_absolute_uri("/").rstrip("/")
    if request.headers.get("Sec-Fetch-Site") == "cross-site" or (
        request.method == "POST" and request.headers.get("Origin") != origin
    ):
        return HttpResponse(status=403)
    headers = {"Origin": origin, "Referer": origin + "/"}
    body = None
    if request.method == "POST":
        allowed_types = {"text/plain"} if path == "socket.io/" else {"application/json", "multipart/form-data"}
        if request.content_type not in allowed_types:
            return HttpResponse(status=415)
        try:
            body = request.body
        except RequestDataTooBig:
            return HttpResponse(status=413)
        if len(body) > (131072 if path == "socket.io/" else settings.DATA_UPLOAD_MAX_MEMORY_SIZE):
            return HttpResponse(status=413)
        headers["Content-Type"] = request.headers["Content-Type"]
        if path.startswith("api/dashboard/"):
            try:
                throttle(request, scope="eva-widget")
            except SubmissionError as exc:
                return HttpResponse(status=exc.status)
    upstream = Request("https://eva.bz/" + path + "?" + urlencode(query),
                       data=body, headers=headers, method=request.method)
    try:
        with build_opener(NoRedirect).open(upstream, timeout=30 if path == "socket.io/" else 12) as response:
            payload = response.read(MAX_REPLY + 1)
    except HTTPError as exc:
        code = exc.code
        exc.close()
        return HttpResponse(status=code if 400 <= code < 500 else 502)
    except (URLError, OSError):
        return HttpResponse(status=502)
    if len(payload) > MAX_REPLY:
        return HttpResponse(status=502)
    cache = "public, max-age=900" if path in ASSETS else "no-store"
    return HttpResponse(payload, content_type=content_type,
                        headers={"Cache-Control": cache, "X-Content-Type-Options": "nosniff"})
