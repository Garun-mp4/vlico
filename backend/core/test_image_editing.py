import json
import uuid
from io import BytesIO
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.test import Client, TestCase
from PIL import Image
from core.test_portfolio import PortfolioTests, jpeg
from core.portfolio import add_images
from core.image_editing import rendered_image, validate_edit, edit_media


class ImageEditorTests(TestCase):
    setUpTestData = classmethod(PortfolioTests.setUpTestData.__func__)
    setUp = PortfolioTests.setUp
    login = PortfolioTests.login
    upload = PortfolioTests.upload
    # Inherit the common persistence/authentication fixtures, not the existing tests.
    def test_crop_geometry_and_position(self):
        source = Image.new("RGB", (200,100), "red")
        for x in range(100,200):
            for y in range(100): source.putpixel((x,y),(0,0,255))
        stream=BytesIO();source.save(stream,"PNG");stream.seek(0)
        full, thumb, w, h = rendered_image(stream, validate_edit({"zoom":2,"x":100,"y":50}))
        self.assertAlmostEqual(w/h,4/3,places=1)
        image=Image.open(full)
        self.assertGreater(image.getpixel((w//2,h//2))[2],200)

    def test_invalid_settings(self):
        for data in ({"zoom":0},{"zoom":float("nan")},{"x":-1},{"y":101},{"rotation":45},{"mode":"script"}):
            with self.assertRaises(ValidationError): validate_edit(data)

    def test_upload_preserves_source_and_prevents_retry_duplicate(self):
        key=uuid.uuid4(); data={"alt":"Ceiling","caption":"Caption","section":"process","cover":True,"zoom":1.5}
        one=add_images(self.project.pk,[jpeg()],"result",edit=data,upload_key=key)[0]
        two=add_images(self.project.pk,[jpeg()],"result",edit=data,upload_key=key)[0]
        self.assertEqual(one.pk,two.pk)
        self.assertEqual(self.project.media.count(),1)
        self.assertTrue(one.source)
        self.assertEqual(one.section,"process")
        self.assertEqual(one.caption,"Caption")
        self.assertAlmostEqual(one.width/one.height,4/3,places=1)

    def test_reedit_uses_original_and_checks_revision(self):
        item=add_images(self.project.pk,[jpeg()],"result",edit={"zoom":2})[0]
        with item.source.open("rb") as stream: source_bytes=stream.read()
        revision=item.updated_at.isoformat()
        item=edit_media(self.project.pk,item.pk,{"mode":"fit","rotation":90},revision)
        self.assertEqual(item.editing["zoom"],1)
        with item.source.open("rb") as stream: self.assertEqual(stream.read(),source_bytes)
        with self.assertRaises(ValidationError): edit_media(self.project.pk,item.pk,{},revision)

    def test_editor_endpoint_and_source_are_protected(self):
        item=self.upload(1)[0]
        source=reverse("cabinet_image_source",args=[self.project.pk,item.pk])
        edit=reverse("cabinet_image_editor",args=[self.project.pk,item.pk])
        self.assertEqual(self.client.get(source).status_code,302)
        self.login()
        self.assertEqual(self.client.get(source).status_code,200)
        result=self.client.post(edit,{"editing":json.dumps({"caption":"Edited","rotation":90}),"revision":item.updated_at.isoformat()})
        self.assertEqual(result.status_code,200)
        item.refresh_from_db();self.assertEqual(item.caption,"Edited")
        self.assertTrue(item.source)
        self.assertEqual(Client().get('/private/'+item.source.name).status_code,404)

    def test_ajax_upload_validation_and_idempotency(self):
        self.login();path=reverse("cabinet_upload",args=[self.project.pk]);key=str(uuid.uuid4())
        for _ in range(2):
            response=self.client.post(path,{"images":jpeg(),"upload_key":key,"editing":json.dumps({"alt":"Photo","zoom":1.2})},HTTP_ACCEPT="application/json")
            self.assertEqual(response.status_code,200)
        self.assertEqual(self.project.media.count(),1)
        response=self.client.post(path,{"images":jpeg(),"editing":json.dumps({"caption":4})},HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.project.media.count(),1)

    def test_capacity_limit_and_image_source_isolation(self):
        from core.models import ProjectMedia
        ProjectMedia.objects.bulk_create([ProjectMedia(project=self.project,image="placeholder.webp",position=i) for i in range(40)])
        with self.assertRaises(ValidationError): add_images(self.project.pk,[jpeg()],"result")
        self.assertEqual(self.project.media.count(),40)

    def test_source_files_stay_inside_test_storage(self):
        from pathlib import Path
        from django.conf import settings
        item=add_images(self.project.pk,[jpeg()],"result",edit={})[0]
        self.assertTrue(Path(item.source.path).is_relative_to(Path(self.directory.name)))
        self.assertTrue(Path(item.source.path).is_relative_to(settings.PRIVATE_MEDIA_ROOT))
