from django.test import TestCase
from django.template.loader import get_template
from django.urls import reverse
from .models import Project, ProjectMedia


class HomePreviewTests(TestCase):
    def test_about_section_uses_exact_copy_and_supplied_responsive_portrait(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h2 class="display-heading reveal" id="about-title">ПОТОЛОК — ОСНОВА КРАСИВОГО ИНТЕРЬЕРА</h2>', html=True)
        self.assertContains(response, '17 лет создаём премиальные потолочные системы с архитектурным освещением.')
        self.assertContains(response, 'сложные дизайнерские решения')
        self.assertContains(response, 'Владлен Гизерский')
        self.assertContains(response, '— основатель и руководитель VLICO')
        html = response.content.decode()
        self.assertRegex(html, r'vladlen-gizerskiy-portrait-640\.[a-f0-9]+\.webp')
        self.assertRegex(html, r'vladlen-gizerskiy-portrait-960\.[a-f0-9]+\.webp')
        self.assertContains(response, 'alt="Портрет Владлена Гизерского, основателя и руководителя VLICO"')
        self.assertNotContains(response, 'vladlen-gizerskiy-portrait.png')
        self.assertNotContains(response, 'Ожидается текст обращения основателя')
        self.assertNotContains(response, 'about-founder-message')
        self.assertNotContains(response, 'Сначала разбираемся в помещении и сценариях освещения')

    def test_founder_message_slot_renders_only_when_preview_context_supplies_text(self):
        public_response = self.client.get('/')
        self.assertNotContains(public_response, 'about-founder-message')
        context = {}
        for part in public_response.context:
            context.update(part.flatten())
        preview = get_template('site/home.html').render(
            {**context, 'founder_message': 'Короткий текст для предпросмотра.'},
            public_response.wsgi_request,
        )
        figure_start = preview.index('<figure class="about-founder">')
        figure_end = preview.index('</figure>', figure_start)
        quote_position = preview.index('Короткий текст для предпросмотра.')
        caption_position = preview.index('about-founder-caption', figure_start)
        self.assertLess(caption_position, quote_position)
        self.assertLess(quote_position, figure_end)
        self.assertNotIn('Ожидается текст обращения основателя', preview)
        self.assertIn('about-projects', preview)

    def test_about_gallery_remains_tied_to_published_project_media(self):
        project = Project.objects.create(title='Опубликованный объект', slug='about-gallery-case', status=Project.Status.PUBLISHED)
        cover = ProjectMedia.objects.create(
            project=project,
            image='projects/verified-cover.webp',
            width=1200,
            height=800,
            alt='Реальная обложка проекта',
            is_cover=True,
        )
        draft = Project.objects.create(title='Закрытый черновик', slug='about-gallery-draft')
        private_cover = ProjectMedia.objects.create(
            project=draft,
            image='projects/private-cover.webp',
            width=1200,
            height=800,
            is_cover=True,
        )
        response = self.client.get('/')
        self.assertContains(response, reverse('project_image', args=[cover.pk, 'thumb']))
        self.assertContains(response, project.get_absolute_url())
        self.assertNotContains(response, reverse('project_image', args=[private_cover.pk, 'thumb']))
        self.assertNotContains(response, 'Фото проекта — ожидается')

    def test_home_limits_published_projects_but_catalogue_remains_complete(self):
        projects = [Project.objects.create(title=f'Работа {i}', slug=f'preview-{i}', solution='Подтверждённое решение', status='published', position=i+1) for i in range(7)]
        Project.objects.create(title='Закрытый черновик', slug='preview-draft', position=0)
        Project.objects.create(title='Закрытый архив', slug='preview-archive', status='archived', position=0)
        home = self.client.get('/')
        self.assertEqual(list(home.context['homepage_projects']), projects[:6])
        self.assertNotContains(home, 'Работа 6')
        self.assertContains(home, 'Смотреть все проекты')
        self.assertContains(home, 'class="home-project-footer"')
        catalogue = self.client.get('/projects/')
        self.assertEqual(list(catalogue.context['projects']), projects)
        self.assertContains(catalogue, 'Работа 6')
        self.assertNotContains(catalogue, 'Закрытый черновик')
        self.assertNotContains(catalogue, 'Закрытый архив')
        projects[0].status = 'draft'; projects[0].save()
        self.assertEqual(list(self.client.get('/').context['homepage_projects']), projects[1:])
        projects[-1].position = 0; projects[-1].save()
        self.assertEqual(self.client.get('/').context['homepage_projects'][0], projects[-1])

    def test_empty_preview_keeps_helpful_empty_state(self):
        response = self.client.get('/')
        self.assertContains(response, 'Готовим подробные истории')
        self.assertNotContains(response, 'class="home-project-footer"')

    def test_home_preview_keeps_one_and_six_published_projects(self):
        for count in (1, 6):
            with self.subTest(count=count):
                Project.objects.all().delete()
                projects = [
                    Project.objects.create(
                        title=f'Портфолио {count}-{index}',
                        slug=f'portfolio-{count}-{index}',
                        solution='Подтверждённое решение',
                        status=Project.Status.PUBLISHED,
                        position=index,
                    )
                    for index in range(count)
                ]
                response = self.client.get('/')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(response.context['homepage_projects']), projects)
                self.assertContains(response, 'Смотреть все проекты')
