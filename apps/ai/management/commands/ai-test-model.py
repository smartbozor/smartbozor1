import datetime
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management import BaseCommand

from apps.ai.models import StallDataSet


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=20,
            help="Batch size (default: 20)",
        )

    def handle(self, *args, **options):
        start_time = time.perf_counter()

        aigen_app = os.getenv("AIGEN_APP")
        workdir = os.path.dirname(aigen_app)

        batch_size = options["batch_size"]
        test_count, success_count = 0, 0

        qs = StallDataSet.objects.filter(status__in=[
            StallDataSet.STATUS_MARKED_MODERATED,
            StallDataSet.STATUS_GENERATED,
        ]).prefetch_related("camera").order_by('id')
        total = qs.count()

        def run_one(test_data):
            nonlocal test_count, success_count

            cmd = [aigen_app, "--test", "1"]
            result = subprocess.run(
                cmd,
                input=json.dumps(test_data),
                cwd=workdir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print("Error:", result.stdout)
                print("Error:", result.stderr)
                exit(1)

            test_delta, success_delta = map(int, result.stdout.strip().split())
            test_count += test_delta
            success_count += success_delta

        batch, done = [], 0
        for row in qs.iterator(chunk_size=batch_size):
            done += 1

            batch.append({
                "file": row.image.path,
                "image": False,
                "rois": row.camera.roi,
                "occupied": row.data,
            })

            if len(batch) >= batch_size:
                self.stdout.write(f"Running... {done}/{total}")
                run_one(batch)
                batch.clear()

        if batch:
            self.stdout.write(f"Running... {done}/{total}")
            run_one(batch)

        percent = round(success_count * 100 / test_count if test_count > 0 else 0, 2)
        self.stdout.write(f"Test count: {test_count}")
        self.stdout.write(f"Success count: {success_count} ({percent}%)")
        self.stdout.write()
        elapsed = time.perf_counter() - start_time
        td = datetime.timedelta(seconds=elapsed)
        self.stdout.write(f"Elapsed time: {td}")
