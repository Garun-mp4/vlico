from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

@deconstructible
class PublicMediaStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)

@deconstructible
class PrivateMediaStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PRIVATE_MEDIA_ROOT)

    def url(self, name):
        raise ValueError("Private attachments have no public URL")
