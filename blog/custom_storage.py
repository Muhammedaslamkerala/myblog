from django.core.files.storage import FileSystemStorage
import os
from django.conf import settings

class PostImageStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        kwargs['location'] = os.path.join(settings.MEDIA_ROOT, 'post_images')
        kwargs['base_url'] = os.path.join(settings.MEDIA_URL, 'post_images')
        super().__init__(*args , **kwargs)