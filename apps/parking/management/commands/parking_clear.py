import datetime

from django.core.management import BaseCommand
from django.utils import timezone

from apps.parking.models import ParkingStatus


class Command(BaseCommand):
    def handle(self, *args, **options):
        yesterday = timezone.localtime().date() - datetime.timedelta(days=1)

        ParkingStatus.objects.filter(
            data=yesterday,
            leave_at__isnull=True,
        ).delete()

