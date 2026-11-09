from types import SimpleNamespace
from urllib.parse import urlsplit
from django.conf import settings
from django.db.models import OuterRef, Subquery
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import json_script
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_safe
from .site_content import SERVICES, BY_SLUG, CONTACTS
from .portfolio import published_projects
from .legal import consent_revision, legal_context
from .models import ProjectCategory, ProjectMedia

INDEXABLE = {"home", "services", "service", "partners", "contacts", "projects", "project", "calculator"}


def absolute(path):
    return settings.SITE_URL + path


def project_navigation():
    covers = ProjectMedia.objects.filter(project__categories=OuterRef("pk"), project__status="published", is_cover=True).order_by("project__position", "project_id")
    categories = list(ProjectCategory.objects.filter(is_public=True).annotate(preview_pk=Subquery(covers.values("pk")[:1])))
    services = {item["title"].casefold(): item for item in SERVICES}
    for category in categories:
        service = services.get(category.title.casefold())
        category.preview_url = static(service["preview"]) if service else reverse("project_image", args=[category.preview_pk, "thumb"]) if category.preview_pk else ""
        category.preview_illustration = service["illustration"] if service else False
    return categories


def public_context(request):
    match = request.resolver_match
    name = match.url_name if match else ""
    title, description = "Потолки и свет в Калининграде", "Натяжные потолки и интегрированное освещение VLICO в Калининграде и области. Реальные проекты, выбор решений и предварительный расчёт."
    pages = {"services": ("Потолочные системы и освещение", "Шесть решений VLICO: теневые, парящие и тканевые потолки, световые линии, магнитные треки и скрытые карнизы в Калининграде."),
        "partners": ("Дизайнерам, архитекторам и строителям", "Сотрудничество с VLICO: согласование потолка и освещения по проекту, проработка узлов и обсуждение планировки со специалистом."),
        "contacts": ("Контакты студии VLICO", "Телефон, Telegram, WhatsApp и адрес VLICO. Обсудите потолок и освещение, договоритесь о замере в Калининграде."),
        "projects": ("Проекты потолков и света", "Опубликованные проекты VLICO: фотографии готовых интерьеров и процесса монтажа, потолочные и световые решения."),
        "calculator": ("Калькулятор стоимости потолка", "Выберите потолок, примыкание, свет и карнизы. Предварительная стоимость обновляется по ходу выбора, подробная смета после замера."),
        "privacy": ("Политика обработки персональных данных", "Цели, основания, сроки обработки и способы защиты данных посетителей сайта VLICO."),
        "consent": ("Согласие на обработку персональных данных", "Отдельный текст согласия на обработку данных заявки VLICO, порядок отзыва и сведения об операторе."),
        "cookies": ("Cookie и настройки приватности", "Обязательные и необязательные технологии сайта VLICO. Управление аналитикой и внешними виджетами.")}
    title, description = pages.get(name, (title, description))
    image = absolute(static("assets/hero-luxurious-geometric.webp"))
    if name == "service" and match.kwargs.get("slug") in BY_SLUG:
        content = BY_SLUG[match.kwargs["slug"]]
        title, description = content["title"] + " в Калининграде", content["description"]
        image = absolute(static(content["image"]))
    if name == "project":
        project = published_projects().filter(slug=match.kwargs.get("slug")).first()
        if project:
            title = project.title
            description = " ".join(project.solution.split())[:240] or f"Проект VLICO: {project.title}. Фотографии и выполненные решения."
            if project.cover_media:
                image = absolute(reverse("project_image", args=[project.cover_media.pk, "full"]))
    canonical = absolute(request.path)
    private = name not in INDEXABLE | {"privacy", "consent", "cookies"}
    if private:
        title = "Страница VLICO"
    if name == "request_form":
        title = {"consultation": "Обсудить потолок и освещение", "measurement": "Записаться на замер", "project": "Обсудить проект", "partner": "Обсудить сотрудничество"}.get(match.kwargs.get("kind"), title)
    data = None
    business = {"@context": "https://schema.org", "@type": "HomeAndConstructionBusiness", "@id": absolute("/#business"), "name": "VLICO", "url": settings.SITE_URL + "/",
        "telephone": CONTACTS["phone"], "email": CONTACTS["email"], "address": {"@type": "PostalAddress", "streetAddress": "Клубная улица, 11Б", "addressLocality": "посёлок Невское", "addressRegion": "Калининградская область", "addressCountry": "RU"},
        "openingHours": "Mo-Fr 09:00-18:00", "areaServed": ["Калининград", "Калининградская область"], "sameAs": [CONTACTS["yandex"], CONTACTS["telegram"], CONTACTS["instagram"]]}
    if name in {"home", "contacts"}:
        data = business
    elif name == "service" and match.kwargs.get("slug") in BY_SLUG:
        data = {"@context": "https://schema.org", "@type": "Service", "name": BY_SLUG[match.kwargs["slug"]]["title"], "url": canonical, "areaServed": "Калининградская область", "provider": {"@type": "HomeAndConstructionBusiness", "name": "VLICO", "url": settings.SITE_URL + "/"}}
    schema = mark_safe(str(json_script(data)).replace('type="application/json"', 'type="application/ld+json"')) if data else ""
    public_tracking = not private or name == "request_form"
    config = {"counter": settings.YANDEX_METRIKA_ID, "analytics_enabled": settings.ANALYTICS_ENABLED and settings.APP_ENV == "production" and public_tracking,
        "canonical": canonical, "consent_version": consent_revision()}
    navigation = project_navigation() if name in INDEXABLE | {"privacy", "consent", "cookies", "request_form"} else []
    return {**legal_context(), "service_pages": SERVICES, "company": CONTACTS, "site_origin": settings.SITE_URL, "project_navigation": navigation,
        "seo": {"title": title, "description": description, "canonical": "" if private else canonical, "image": image, "indexable": settings.SITE_INDEXABLE and name in INDEXABLE, "schema": schema}, "site_config": config}


@require_safe
def services(request):
    return render(request, "site/services.html")


@require_safe
def service(request, slug):
    if slug not in BY_SLUG:
        raise Http404
    content = BY_SLUG[slug]
    projects = published_projects().filter(services__slug=slug).distinct()
    return render(request, "site/service.html", {"service_page": content, "related_projects": projects})


@require_safe
def partners(request):
    return render(request, "site/partners.html")


@require_safe
def contacts(request):
    return render(request, "site/contacts.html")


@require_safe
def consent(request):
    return render(request, "site/consent.html")


@require_safe
def cookies(request):
    return render(request, "site/cookies.html")


@require_safe
def sitemap(request):
    from .sitemaps import PublicSitemap, ServiceSitemap, ProjectSitemap
    site = SimpleNamespace(domain=urlsplit(settings.SITE_URL).netloc)
    protocol = urlsplit(settings.SITE_URL).scheme
    urls = []
    for section in (PublicSitemap(), ServiceSitemap(), ProjectSitemap()):
        urls.extend(section.get_urls(site=site, protocol=protocol))
    return render(request, "sitemap.xml", {"urlset": urls}, content_type="application/xml")


def not_found(request, exception):
    return render(request, "site/404.html", {"seo": {"title": "Страница не найдена", "description": "Перейдите на главную или откройте опубликованные проекты VLICO.", "indexable": False}, "site_config": {"analytics_enabled": False, "consent_version": consent_revision()}}, status=404)


def csrf_failure(request, reason=""):
    return HttpResponse(render_to_string("site/form-expired.html"), status=403)
