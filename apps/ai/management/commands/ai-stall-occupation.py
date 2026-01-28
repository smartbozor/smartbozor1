import uuid
from collections import defaultdict
from datetime import timedelta

from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.ai.models import StallOccupation
from apps.camera.models import Camera
from apps.main.models import Bazaar
from apps.stall.models import StallStatus, Stall


class Command(BaseCommand):
    @classmethod
    def find_best_interval(cls, states, min_gap, max_gap):
        if not states or len(states) < 2:
            return None

        t = sorted(states)
        n = len(t)

        best_check_count = -1
        best_pair = None

        j = 1
        for i in range(n):
            if j <= i:
                j = i + 1
            while j < n and t[j] - t[i] < min_gap:
                j += 1
            if j >= n:
                break

            gap = t[j] - t[i]
            if gap > max_gap:
                continue

            check_count = j - i + 1

            if check_count > best_check_count:
                best_check_count = check_count
                best_pair = (t[i], t[j], gap, check_count)

        return best_pair

    def handle(self, *args, **options):
        today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        for bazaar in Bazaar.objects.order_by('id').all():
            print("Checking ", str(bazaar), "...")
            if not bazaar.is_working_day:
                print("\tish kuni emas")
                continue

            cameras = list(Camera.objects.filter(bazaar_id=bazaar.id).order_by('id').all())
            stall_number_by_id, cameras_id = dict(), set()
            for cam in cameras:
                if not cam.roi or not isinstance(cam.roi, list):
                    continue

                cameras_id.add(cam.id)
                for roi in cam.roi:
                    if "id" not in roi or roi["type"] != 0:
                        continue

                    stall_number_by_id[(cam.id, uuid.UUID(roi["id"]))] = roi["value"]

            states = StallOccupation.objects.filter(
                camera_id__in=cameras_id,
                check_at__gte=today_start,
                check_at__lt=today_end,
            )

            roi_states = defaultdict(list)

            for row in states:
                roi_states[(row.camera_id, row.roi_id)].append(row.check_at)

            stall_occupied = set()
            for key, states in roi_states.items():
                if key not in stall_number_by_id:
                    continue

                best = self.find_best_interval(states, timedelta(hours=1), timedelta(hours=1, minutes=10))
                if best is None:
                    continue

                __, __, __, between = best
                if between < 8:
                    continue

                stall_occupied.add(stall_number_by_id[key])

            if not stall_occupied:
                continue

            with transaction.atomic():
                stalls = Stall.objects.select_for_update().filter(
                    section__area__bazaar_id=bazaar.id,
                    number__in=stall_occupied
                ).all()

                created_count = 0
                for stall in stalls:
                    ss, created = StallStatus.objects.get_or_create(
                        stall_id=stall.id,
                        date=today_start.date(),
                        defaults={
                            'is_occupied': True,
                            'price': stall.price,
                            'occupied_at': timezone.now(),
                        }
                    )

                    if not created and not ss.is_occupied:
                        ss.is_occupied = True
                        ss.occupied_at = timezone.now()
                        ss.save()

                    created_count += 1

                print("\tupdated:", created_count)
