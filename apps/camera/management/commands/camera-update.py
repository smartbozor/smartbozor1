import os

from django.core.management import BaseCommand
from django.db import transaction

from apps.camera.tasks import sync_cameras
from apps.main.models import Bazaar
from smartbozor.security import switch_to_www_data


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update snapshots',
        )

        parser.add_argument(
            '--id',
            type=int,
            default=0,
            help='Force update snapshots',
        )

    def handle(self, *args, **options):
        switch_to_www_data()

        force = options.get('force')
        bazaar_id = options.get('id')

        with (transaction.atomic()):
            qs = Bazaar.objects.select_for_update().order_by('id')
            if bazaar_id > 0:
                qs = qs.filter(id=bazaar_id)

            for bazaar in qs.all():
                if not bazaar.server_ip:
                    continue

                print()
                print("-" * 30)
                print(bazaar, "checking ...")

                sync_cameras(bazaar.id, force_update=force)
