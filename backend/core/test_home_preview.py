from django.test import TestCase
from .models import Project


class HomePreviewTests(TestCase):
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
