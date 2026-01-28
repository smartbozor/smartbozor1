import datetime
import os
import uuid

import requests
from dateutil.relativedelta import relativedelta
from django.core.management import BaseCommand
from django.db.models import Sum, Max
from django.utils import timezone

from apps.ai.models import StallOccupation
from apps.camera.models import Camera
from apps.main.models import Bazaar


ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")


class Command(BaseCommand):
    STALL_CLASS_BAND = 0
    STALL_CLASS_BOSH = 1

    def handle(self, *args, **options):
        for bazaar in Bazaar.objects.order_by('id').all():
            print("Checking", str(bazaar), "...")
            cameras = list(Camera.objects.filter(bazaar_id=bazaar.id).order_by('id').all())
            camera_id_by_sn = {cam.device_sn: cam.id for cam in cameras}
            roi_list = set()
            for cam in cameras:
                if not isinstance(cam.roi, list):
                    continue

                for roi in cam.roi:
                    if "id" not in roi:
                        continue

                    roi_list.add((cam.id, uuid.UUID(roi["id"])))

            after = timezone.localtime() - relativedelta(month=2)
            saved = StallOccupation.objects.filter(
                camera_id__in=camera_id_by_sn.values(),
                check_at__gte=after
            ).aggregate(
                saved=Max("check_at")
            ).get('saved', "") or ""

            print("\tsave:", saved)
            url = f"http://{bazaar.server_ip}:1984/api/ai/states"
            print(f"\tpost: {url}")

            try:
                resp = requests.get(url, params={
                    "saved": saved.isoformat() if saved else "",
                }, headers={
                    "Authorization": f"Bearer {ACCESS_TOKEN}"
                }, timeout=15)
                resp.raise_for_status()
                resp = resp.json()
            except Exception as e:
                print("\terror", str(e)[:50], "...")
                print()
                continue

            min_at, max_at, rois_id, total_items_count = None, None, set(), 0
            for sn, states in resp.items():
                total_items_count += len(states)
                for state in states:
                    rois_id.add(uuid.UUID(state["roi_id"]))
                    check_at = datetime.datetime.fromisoformat(state['check_at'])
                    min_at = min(min_at or check_at, check_at)
                    max_at = max(max_at or check_at, check_at)

            if min_at is None:
                continue

            occupations = StallOccupation.objects.filter(
                camera_id__in=camera_id_by_sn.values(),
                roi_id__in=rois_id,
                check_at__gte=min_at,
                check_at__lte=max_at
            )

            exists_data = set()
            for row in occupations.all():
                exists_data.add((row.camera_id, row.roi_id, row.check_at))

            insert_data = []
            for sn, states in resp.items():
                camera_id = camera_id_by_sn[sn]
                for state in states:
                    if state["state"] != self.STALL_CLASS_BAND:
                        continue

                    roi_id = uuid.UUID(state["roi_id"])
                    if (camera_id, roi_id) not in roi_list:
                        continue

                    check_at = datetime.datetime.fromisoformat(state['check_at'])
                    if (camera_id, roi_id, check_at) in exists_data:
                        continue

                    insert_data.append(StallOccupation(
                        camera_id=camera_id,
                        roi_id=state['roi_id'],
                        state=state['state'],
                        check_at=check_at,
                    ))

            print("\ttotal data:", total_items_count)
            print("\tnew data:", len(insert_data))
            print()
            StallOccupation.objects.bulk_create(insert_data)
