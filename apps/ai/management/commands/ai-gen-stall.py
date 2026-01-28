import json
import os
import re
import subprocess
from pathlib import Path

from django.core.management import BaseCommand

from apps.ai.models import StallDataSet
from apps.main.models import Bazaar
from smartbozor.storages import stall_training_storage


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size (default: 100)",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        snapshot_after = StallDataSet.get_snapshot_after()
        for bazaar in Bazaar.objects.order_by('id').all():
            print("Checking", str(bazaar), "...")
            qs = StallDataSet.objects.filter(
                bazaar_id=bazaar.id,
                status=StallDataSet.STATUS_MARKED_MODERATED,
                snapshot_at__gte=snapshot_after,
            ).order_by('id').prefetch_related('camera')
            print("\tfound:", qs.count())

            ai_gen_data, processed_ids = [], []
            for row in qs.all()[:batch_size]:
                processed_ids.append(row.id)
                if not row.camera.roi:
                    continue

                occupied = {ab["id"]: ab["is_occupied"] for ab in row.data}

                from_path = row.image.path
                out_dir_tpl = stall_training_storage.path(os.path.join("train", "{0}", os.path.dirname(row.image.name)))
                file_prefix = Path(os.path.basename(from_path)).stem

                roi_data = []
                for roi in row.camera.roi:
                    if roi["type"] != 0:
                        continue

                    is_occupied = occupied.get(roi["id"], False)
                    roi_data.append({
                        "id": roi["id"],
                        "to": os.path.join(out_dir_tpl.format("band" if is_occupied else "bosh"), file_prefix + "-" + roi["id"] + "-" + str(len(roi_data)) + ".jpg"),
                        "points": roi["points"],
                    })

                ai_gen_data.append({
                    "src": from_path,
                    "clean": [
                        os.path.join(out_dir_tpl.format("band"), file_prefix + "*.jpg"),
                        os.path.join(out_dir_tpl.format("bosh"), file_prefix + "*.jpg"),
                    ],
                    "rois": roi_data,
                })

            if len(ai_gen_data) == 0:
                continue

            json_str = json.dumps(ai_gen_data)

            result = subprocess.run(
                [os.getenv("AIGEN_APP"), "--gen", "1"],
                input=json_str,
                capture_output=True,
                text=True,
            )

            print("\treturn:", result.returncode)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    print("\t->", line)

                StallDataSet.objects.filter(id__in=processed_ids).update(status=StallDataSet.STATUS_GENERATED)
