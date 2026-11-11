from hashlib import sha256
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Lead, Project, Service
from .site_content import SERVICES
from .portfolio import EDITOR_PERMISSIONS
from .test_leads import payload


class PublicSiteTests(TestCase):
    def test_service_catalogue_and_unique_server_rendered_pages(self):
        self.assertContains(self.client.get('/services/'), 'Потолок и свет.')
        titles = set()
        for item in SERVICES:
            response = self.client.get(reverse('service', args=[item['slug']]))
            self.assertContains(response, item['heading'])
            self.assertContains(response, item['intro'])
            self.assertContains(response, '?service=' + item['slug'])
            self.assertContains(response, 'property="og:image"')
            self.assertContains(response, 'application/ld+json')
            self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')
            titles.add(response.context['seo']['title'])
        self.assertEqual(len(titles), 9)

    def test_public_contacts_and_widgets_are_server_rendered(self):
        for path in ('/', '/contacts/'):
            response = self.client.get(path)
            self.assertContains(response, 'https://t.me/vlico_39')
            self.assertContains(response, 'https://wa.me/79097888844')
            self.assertContains(response, 'tel:+79097888844')
            self.assertContains(response, 'data-external-widget="reviews"')
            self.assertContains(response, '<iframe')
            self.assertContains(response, 'https://yandex.ru/maps-reviews-widget/164382623295?comments')
            self.assertNotContains(response, 'mc.yandex.ru/metrika/tag.js')
        self.assertContains(self.client.get('/contacts/'), 'Клубная улица, 11Б')
        self.assertContains(self.client.get('/partners/'), '/request/partner/')

    def test_partner_content_home_entry_and_primary_project_action(self):
        home = self.client.get('/')
        self.assertContains(home, 'class="partners-home-entry page-gutter"')
        self.assertContains(home, 'СОЗДАЁМ ПРОЕКТЫ ВМЕСТЕ')
        self.assertContains(home, 'class="home-hero-primary"')
        self.assertContains(home, '>Обсудить проект <span')
        self.assertNotContains(home, 'Дизайнерам и строителям')
        self.assertContains(home, 'href="/partners/"')

        response = self.client.get('/partners/')
        self.assertContains(response, 'Партнёрство, в котором продумана каждая деталь')
        self.assertContains(response, 'Сотрудничаем с дизайнерами, архитекторами и строительными компаниями. Берём на себя реализацию потолочных систем и интеграцию архитектурного освещения — от технической проработки до монтажа.')
        benefits = (
            '17 лет опыта в потолочных системах.',
            'Реализация сложных дизайнерских проектов.',
            'Техническая поддержка и согласование решений.',
            'Детальные сметы и согласованные сроки.',
        )
        markup = response.content.decode()
        positions = [markup.index(item) for item in benefits]
        self.assertEqual(positions, sorted(positions))
        steps = ('Техническая проработка', 'Согласование решений', 'Реализация проекта')
        positions = [markup.index(item) for item in steps]
        self.assertEqual(positions, sorted(positions))
        self.assertContains(response, 'action="/request/partner/"')
        self.assertContains(response, 'Обсудить сотрудничество')

    def test_only_explicitly_linked_published_projects_appear_on_services(self):
        service = Service.objects.get(slug='shadow')
        public = Project.objects.create(title='Подтверждённая работа', slug='linked-public', status='published')
        draft = Project.objects.create(title='Секретный черновик', slug='linked-draft')
        unrelated = Project.objects.create(title='Другой проект', slug='unrelated', status='published')
        public.services.add(service); draft.services.add(service)
        response = self.client.get('/services/shadow/')
        self.assertContains(response, public.title)
        self.assertNotContains(response, draft.title)
        self.assertNotContains(response, unrelated.title)
        self.assertNotContains(self.client.get('/services/fabric/'), 'Решение в наших проектах')

    def test_service_selection_is_saved_and_cleared_in_editor_form(self):
        editor = get_user_model().objects.create_user('service-editor', is_staff=True)
        editor.user_permissions.set(Permission.objects.filter(content_type__app_label='core', codename__in=[permission.split('.')[1] for permission in EDITOR_PERMISSIONS]))
        self.client.force_login(editor)
        service = Service.objects.get(slug='shadow')
        project = Project.objects.create(title='Проект', slug='editor-service')
        url = reverse('cabinet_edit', args=[project.pk])
        self.assertContains(self.client.get(url), 'Страницы услуг')
        data = {'title': project.title, 'slug': project.slug, 'position': 0, 'services': [service.pk], 'revision': project.updated_at.isoformat()}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(list(project.services.all()), [service])
        project.refresh_from_db()
        data['services'] = []
        data['revision'] = project.updated_at.isoformat()
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertFalse(project.services.exists())

    def test_service_cta_prefills_service_and_partner_interest(self):
        service = Service.objects.get(slug='shadow')
        response = self.client.get('/request/consultation/?service=shadow')
        self.assertEqual(response.context['lead_form'].initial['service'], service)
        response = self.client.get('/request/partner/', {'interest': 'Сотрудничество'})
        self.assertEqual(response.context['lead_form'].initial['interest'], 'Сотрудничество')

    @override_settings(SITE_URL='https://vlico39.ru', SITE_INDEXABLE=True)
    def test_production_seo_canonical_sitemap_and_robots(self):
        project = Project.objects.create(title='Публичный', slug='public-seo', status='published')
        Project.objects.create(title='Черновик', slug='private-seo')
        response = self.client.get('/services/shadow/?utm_source=test')
        self.assertContains(response, 'content="index,follow"')
        self.assertContains(response, 'href="https://vlico39.ru/services/shadow/"')
        self.assertNotContains(response, 'X-Robots-Tag')
        self.assertNotIn('X-Robots-Tag', response)
        partner_page = self.client.get('/partners/')
        self.assertContains(partner_page, 'content="index,follow"')
        self.assertContains(partner_page, 'href="https://vlico39.ru/partners/"')
        sitemap = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('https://vlico39.ru/partners/', sitemap)
        self.assertIn('https://vlico39.ru' + project.get_absolute_url(), sitemap)
        for item in SERVICES:
            self.assertIn('https://vlico39.ru/services/' + item['slug'] + '/', sitemap)
        for private in ('private-seo', '/cabinet/', '/api/', '/privacy/', 'testserver'):
            self.assertNotIn(private, sitemap)
        self.assertContains(self.client.get('/robots.txt'), 'Sitemap: https://vlico39.ru/sitemap.xml')
        for path in ('/missing/', '/services/unknown/', '/projects/private-seo/'):
            response = self.client.get(path)
            self.assertContains(response, 'Страница не найдена.', status_code=404)
            self.assertContains(response, 'content="noindex,nofollow"', status_code=404)
            self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')

    @override_settings(EMAIL_HOST="smtp.mail.ru", LEAD_NOTIFICATION_EMAIL="vlico_39@mail.ru")
    def test_legal_pages_forms_and_unchecked_consent(self):
        for path in ('/privacy/', '/consent/', '/cookies/'):
            self.assertContains(self.client.get(path), 'настройк' if path == '/privacy/' else 'соглас' if path == '/consent/' else 'Cookie')
        privacy = self.client.get('/privacy/').content.decode()
        consent = self.client.get('/consent/').content.decode()
        for value in ('390610984618', 'i@gizersky.ru', 'vlico_39@mail.ru', 'ООО «СпейсВэб»', '90 дней', '30 дней'):
            self.assertIn(value, privacy)
        for value in ('390610984618', 'i@gizersky.ru', 'vlico_39@mail.ru', '90 дней'):
            self.assertIn(value, consent)
        self.assertNotIn('[Указать', privacy + consent)
        self.assertNotIn('[Наименование', privacy + consent)
        for unavailable_detail in ('ОГРНИП:', 'КПП не предусмотрен', 'не предоставлен', 'не установлена', 'не указана'):
            self.assertNotIn(unavailable_detail.casefold(), (privacy + consent).casefold())
        response = self.client.get('/request/consultation/')
        self.assertContains(response, 'href="/consent/"')
        self.assertContains(response, 'name="legal_version"')
        self.assertFalse(response.context['lead_form'].fields['consent'].initial)

    @override_settings(EMAIL_HOST="smtp.spaceweb.ru", LEAD_NOTIFICATION_EMAIL="partners@vlico39.ru")
    def test_spaceweb_notification_is_disclosed_in_policy_and_consent(self):
        privacy = self.client.get("/privacy/")
        self.assertContains(privacy, "SMTP SpaceWeb")
        self.assertContains(privacy, 'href="mailto:partners@vlico39.ru"')
        self.assertNotContains(privacy, "SMTP Mail.ru")
        self.assertContains(self.client.get("/consent/"), "partners@vlico39.ru")

    @override_settings(
        EMAIL_HOST="smtp.spaceweb.ru",
        LEAD_NOTIFICATION_EMAIL="inbox@example.test",
        PARTNER_NOTIFICATION_EMAIL="partner@example.test",
    )
    def test_partner_notification_recipient_is_disclosed_separately(self):
        privacy = self.client.get("/privacy/")
        consent = self.client.get("/consent/")
        self.assertContains(privacy, 'href="mailto:inbox@example.test"')
        self.assertContains(privacy, 'href="mailto:partner@example.test"')
        self.assertContains(consent, "обычные обращения направляются на inbox@example.test")
        self.assertContains(consent, "партнёрские — на partner@example.test")

    @override_settings(PARTNER_NOTIFICATION_EMAIL="")
    def test_missing_partner_notification_route_is_disclosed_without_general_fallback(self):
        privacy = self.client.get("/privacy/")
        self.assertContains(privacy, "при его отсутствии общий адрес не используется и письмо не направляется")

    def test_success_records_exact_consent_and_rejects_stale_or_missing_acceptance(self):
        for changes in ({'legal_version': 'old'}, {'legal_version': ''}, {'consent': ''}):
            response = self.client.post('/api/leads/', payload(**changes))
            self.assertEqual(response.status_code, 400)
        self.assertFalse(Lead.objects.exists())
        response = self.client.post('/api/leads/', payload())
        self.assertEqual(response.status_code, 201, response.content)
        record = Lead.objects.get(pk=response.json()['reference']).context['consent']
        self.assertEqual(record['version'], settings.LEGAL_VERSION)
        self.assertEqual(record['sha256'], sha256(record['text'].encode()).hexdigest())
        self.assertIn('Telegram Bot API', record['text'])
        self.assertIn('приложенного файла проекта', record['text'])

    def test_local_analytics_disabled_even_if_switch_enabled(self):
        with override_settings(APP_ENV='local', ANALYTICS_ENABLED=True):
            self.assertFalse(self.client.get('/').context['site_config']['analytics_enabled'])
        with override_settings(APP_ENV='production', ANALYTICS_ENABLED=True):
            for path in ('/', '/contacts/', '/request/consultation/'):
                self.assertTrue(self.client.get(path).context['site_config']['analytics_enabled'])
            self.assertFalse(self.client.get('/missing/').context['site_config']['analytics_enabled'])

    def test_operator_change_invalidates_previously_rendered_consent(self):
        data = payload()
        changed = {**settings.LEGAL_OPERATOR, "name": "Другой оператор"}
        with override_settings(LEGAL_OPERATOR=changed):
            response = self.client.post('/api/leads/', data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('legal_version', response.json()['errors'])
        self.assertFalse(Lead.objects.exists())

    def test_private_pages_are_noindex_and_new_routes_keep_first_touch(self):
        response = self.client.get('/services/shadow/?utm_source=first')
        self.assertEqual(self.client.session['lead_attribution']['data']['utm_source'], 'first')
        self.client.get('/contacts/?utm_source=second')
        self.assertEqual(self.client.session['lead_attribution']['data']['utm_source'], 'first')
        with override_settings(SITE_INDEXABLE=True):
            self.assertEqual(self.client.get('/request/consultation/')['X-Robots-Tag'], 'noindex, nofollow')
