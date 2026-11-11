from io import StringIO
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Article, ArticleMedia, Lead, Project
from .email_delivery import email_body
from .telegram_delivery import message_parts
from .test_leads import payload


@override_settings(EMAIL_DELIVERY_ENABLED=False, TELEGRAM_DELIVERY_ENABLED=False)
class ClientUpdateTests(TestCase):
    def test_services_metadata_includes_new_solutions(self):
        response = self.client.get('/services/')
        description = response.context['seo']['description']
        self.assertNotIn('Шесть решений', description)
        self.assertIn('Алисой', description)
        self.assertIn('TEQTUM', description)

    def test_repeated_update_preserves_edited_installation_description(self):
        project = Project.objects.create(slug='ceiling-installation-detail', title='Монтажный узел потолка', status='published')
        call_command('apply_client_update_20261111', stdout=StringIO())
        project.refresh_from_db()
        self.assertIn('подготовили закладную конструкцию', project.solution)
        self.assertEqual(project.media.filter(caption='После — установленная кухонная вытяжка').count(), 1)
        count = project.media.count()
        project.solution = 'Уточнённое заказчиком описание результата.'
        project.save()
        call_command('apply_client_update_20261111', stdout=StringIO())
        project.refresh_from_db()
        self.assertEqual(project.solution, 'Уточнённое заказчиком описание результата.')
        self.assertEqual(project.media.count(), count)

    def test_modern_interior_cover_preserves_article_title_and_body(self):
        article, _ = Article.objects.update_or_create(slug='natiazhnoi-potolok-kak-sozdat-stilnyj-i-praktichnyi-interer', defaults={'title': 'Натяжной потолок: как создать стильный и практичный интерьер', 'body': '<p>Согласованный текст о потолках.</p>'})
        call_command('apply_client_update_20261111', stdout=StringIO())
        article.refresh_from_db()
        self.assertEqual(article.title, 'Натяжной потолок: как создать стильный и практичный интерьер')
        self.assertEqual(article.body, '<p>Согласованный текст о потолках.</p>')
        self.assertEqual(article.cover_media.bundled_image, 'client-updates/smart-room.webp')

    def test_partner_preference_is_saved_notified_and_part_of_idempotency(self):
        data = payload('partner', company='Design Studio', contact_method='whatsapp')
        response = self.client.post(reverse('lead_submit'), data)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['message'], 'Спасибо! Ваша заявка успешно отправлена. Наш специалист свяжется с вами в ближайшее время.')
        self.assertEqual(response.json()['new_request_url'], '/request/partner/')
        lead = Lead.objects.get(pk=response.json()['reference'])
        self.assertEqual(lead.context['contact_method'], 'WhatsApp')
        self.assertIn('Способ связи: WhatsApp', email_body(lead))
        self.assertIn('WhatsApp', '\n'.join(part for part, length in message_parts(lead)))
        self.assertEqual(self.client.post(reverse('lead_submit'), data).status_code, 200)
        data['contact_method'] = 'phone'
        self.assertEqual(self.client.post(reverse('lead_submit'), data).status_code, 409)

    def test_unknown_contact_preference_is_rejected(self):
        response = self.client.post(reverse('lead_submit'), payload('partner', contact_method='invalid'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('contact_method', response.json()['errors'])

    def test_editorial_update_preserves_text_old_media_and_is_idempotent(self):
        slug = 'karniz-dlya-natyazhnogo-potolka-vybor'
        article = Article.objects.filter(slug=slug).first()
        if not article:
            article = Article.objects.create(slug=slug, title='Согласованный заголовок', body='<p>Исходный текст</p>')
        title, body = article.title, article.body
        old = article.cover_media
        call_command('apply_client_update_20261111', stdout=StringIO())
        article.refresh_from_db()
        self.assertEqual((article.title, article.body), (title, body))
        cover = article.cover_media
        self.assertEqual(cover.bundled_image, 'client-updates/concealed-curtains.webp')
        if old:
            self.assertTrue(ArticleMedia.objects.filter(pk=old.pk).exists())
        count = article.media.count()
        call_command('apply_client_update_20261111', stdout=StringIO())
        self.assertEqual(article.media.count(), count)
        self.assertEqual(article.media.filter(is_cover=True).count(), 1)
