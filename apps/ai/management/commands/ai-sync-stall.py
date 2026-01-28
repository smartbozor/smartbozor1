import datetime
import glob
import hashlib
import os
from datetime import timedelta

from django.conf import settings
from django.core.management import BaseCommand
from django.utils import timezone

from apps.ai.models import StallDataSet
from apps.camera.models import Camera
from apps.main.models import Bazaar


class Command(BaseCommand):
    def handle(self, *args, **options):
        data_dir = settings.STALL_DATASET_DIR

        snapshot_after = StallDataSet.get_snapshot_after()

        today = timezone.localtime().date()
        days = [today - timedelta(days=d) for d in range(0, 360)]

        for bazaar in Bazaar.objects.order_by('id').all():
            print("Checking", str(bazaar), "...")
            cameras = Camera.objects.filter(bazaar_id=bazaar.id).order_by('id').all()
            camera_by_hash = dict()
            for cam in cameras:
                cam_hash = hashlib.md5(str(cam.device_sn).encode('utf-8')).hexdigest().lower()
                camera_by_hash[cam_hash] = cam

            path_bazaar = os.path.join(data_dir, str(bazaar.id))
            for day in days:
                path_year = os.path.join(path_bazaar, str(day.year))
                if not os.path.exists(path_year):
                    continue

                path_month = os.path.join(path_year, str(day.month).zfill(2))
                if not os.path.exists(path_month):
                    continue

                path_day = os.path.join(path_month, str(day.day).zfill(2))
                if not os.path.exists(path_day):
                    continue

                images = [os.path.relpath(p, start=data_dir) for p in glob.glob(os.path.join(path_day, "**", "*.jpg"), recursive=True)]
                print("\t", day, len(images))

                while images:
                    selected = set(images[:20])
                    added = set(StallDataSet.objects.filter(
                        bazaar_id=bazaar.id,
                        image__in=selected,
                        snapshot_at__gte=snapshot_after
                    ).values_list('image', flat=True))
                    not_added = list(selected - added)
                    data_set = []

                    if not_added:
                        for image in not_added:
                            image_parts = image.split("/")
                            cam_hash, snapshot_date = image_parts[4], image_parts[5]
                            snapshot_at = timezone.make_aware(
                                datetime.datetime.strptime(snapshot_date.split(".")[0], "%Y-%m-%d-%H-%M-%S")
                            )
                            if cam_hash not in camera_by_hash:
                                continue

                            # roi = camera_by_hash[cam_hash].roi
                            # if not roi or len(roi) == 0:
                            #     continue

                            data_set.append(StallDataSet(
                                bazaar_id=bazaar.id,
                                camera_id=camera_by_hash[cam_hash].id,
                                image=image,
                                status=StallDataSet.STATUS_NEW,
                                snapshot_at=snapshot_at,
                            ))

                    if data_set:
                        StallDataSet.objects.bulk_create(data_set)

                    images = images[20:]

