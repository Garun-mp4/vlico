import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from .project_videos import PROJECT_VIDEOS


class ProjectVideoTests(TestCase):
    def test_home_video_section_follows_solutions_and_precedes_calculator(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertLess(html.index('id="solutions"'), html.index('id="project-videos"'))
        self.assertLess(html.index('id="project-videos"'), html.index('id="calculator"'))
        self.assertContains(response, 'Наши проекты в деталях')
        self.assertContains(response, 'Обсудить свой проект')
        self.assertEqual(html.count('data-project-video '), 7)

    def test_initial_player_has_no_source_or_autoplay(self):
        html = self.client.get('/').content.decode()
        player = re.search(r'<video\b([^>]*)>(.*?)</video>', html, re.S)
        self.assertIsNotNone(player)
        self.assertIn('controls', player[1])
        self.assertIn('playsinline', player[1])
        self.assertIn('preload="none"', player[1])
        self.assertNotIn('src=', player[1])
        self.assertNotIn('autoplay', player[1])
        self.assertNotIn('<source', player[2])

    def test_all_seven_videos_have_real_posters_and_faststart_files(self):
        root = Path(settings.BASE_DIR) / 'static/project-videos'
        for item in PROJECT_VIDEOS:
            with self.subTest(video=item['slug']):
                self.assertTrue((root / (item['slug'] + '.webp')).is_file())
                raw = (root / (item['slug'] + '.mp4')).read_bytes()
                self.assertGreater(raw.find(b'moov'), 0)
                self.assertLess(raw.find(b'moov'), raw.find(b'mdat'))

    def test_video_section_is_homepage_only(self):
        self.assertNotContains(self.client.get('/projects/'), 'data-video-dialog')
        self.assertNotContains(self.client.get('/services/'), 'data-video-dialog')
