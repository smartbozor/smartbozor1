import time

from django.core.management import BaseCommand
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--id", type=int)

    def handle(self, *args, **options):
        t = TOTPDevice.objects.get(id=options.pop('id'))
        totp = TOTP(t.bin_key, t.step, t.t0, t.digits, t.drift)
        totp.time = time.time()

        print(totp.token())
