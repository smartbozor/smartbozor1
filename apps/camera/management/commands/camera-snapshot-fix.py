import os

from django.conf import settings
from django.core.management import BaseCommand

from apps.camera.models import Camera
from apps.main.models import Bazaar


class Command(BaseCommand):
    def handle(self, *args, **options):
        upload_to = Camera._meta.get_field('screenshot').upload_to

        for bazaar in Bazaar.objects.prefetch_related('camera_set').order_by('id').all():
            for cam in bazaar.camera_set.all():

                subpath = os.path.join(upload_to, str(cam.bazaar_id), str(cam.id) + ".jpg")
                file_path = os.path.join(settings.MEDIA_ROOT, str(subpath))

                if os.path.exists(file_path) and os.path.getsize(file_path) < 1000 and cam.screenshot:
                    print("Fixed:", cam.id)
                    cam.screenshot = None
                    cam.save()
