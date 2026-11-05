from importlib import import_module
from django.apps import apps
from django.urls import reverse
from django.test import TestCase
from . import test_portfolio as fixtures
from .models import ProjectMedia
from .portfolio import add_images
from .image_editing import edit_media


class CoverSlotTests(TestCase):
    setUpTestData=classmethod(fixtures.PortfolioTests.setUpTestData.__func__)
    setUp=fixtures.PortfolioTests.setUp
    login=fixtures.PortfolioTests.login

    def photos(self):
        return add_images(self.project.pk,[fixtures.jpeg() for _ in range(3)],'result')

    def assert_order(self,ids):
        photos=list(self.project.media.all())
        self.assertEqual([m.pk for m in photos],ids)
        self.assertEqual([m.position for m in photos],list(range(len(photos))))
        self.assertEqual([m.pk for m in photos if m.is_cover],ids[:1])

    def test_empty_slot_is_available_and_green_class_is_present(self):
        self.login()
        page=self.client.get(reverse('cabinet_edit',args=[self.project.pk]))
        self.assertContains(page,'cover-slot-empty')
        self.assertContains(page,'Добавить обложку')
        self.assertContains(self.client.get(reverse('cabinet_new')),'Место обложки')

    def test_menu_moves_cover_to_front_and_move_buttons_change_cover(self):
        first,second,third=self.photos();self.login()
        url=reverse('cabinet_media',args=[self.project.pk,third.pk])
        self.client.post(url,{'action':'cover'})
        self.assert_order([third.pk,first.pk,second.pk])
        self.client.post(url,{'action':'down'})
        self.assert_order([first.pk,third.pk,second.pk])
        self.client.post(url,{'action':'up'})
        self.assert_order([third.pk,first.pk,second.pk])

    def test_upload_as_cover_inserts_at_front(self):
        first,second,third=self.photos()
        new=add_images(self.project.pk,[fixtures.jpeg()],'result',edit={'cover':True})[0]
        self.assert_order([new.pk,first.pk,second.pk,third.pk])

    def test_editor_cover_choice_moves_photo_to_front(self):
        first,second,third=self.photos()
        edit_media(self.project.pk,third.pk,{'cover':True},third.updated_at.isoformat())
        self.assert_order([third.pk,first.pk,second.pk])

    def test_delete_cover_promotes_next_and_last_photo_restores_empty_slot(self):
        first,second,third=self.photos();self.login()
        for item,remaining in ((first,[second.pk,third.pk]),(second,[third.pk]),(third,[])):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(reverse('cabinet_media',args=[self.project.pk,item.pk]),{'action':'delete','confirm':'yes'})
            self.assert_order(remaining)
        self.assertContains(self.client.get(reverse('cabinet_edit',args=[self.project.pk])),'cover-slot-empty')

    def test_migration_preserves_selected_cover_and_remaining_order(self):
        first,second,third=self.photos()
        self.project.media.update(is_cover=False)
        ProjectMedia.objects.filter(pk=third.pk).update(is_cover=True)
        import_module('core.migrations.0011_cover_first_slot').align_covers(apps,None)
        self.assert_order([third.pk,first.pk,second.pk])
