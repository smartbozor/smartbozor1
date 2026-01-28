from django.core.management.base import BaseCommand
from apps.main.models import Bazaar
import subprocess

class Command(BaseCommand):
    help = "Ping asosida barcha bozorlarni tekshirib, online/offline statusini yangilaydi"

    def handle(self, *args, **options):
        for bazaar in Bazaar.check_online(True):
            status = "🟢 ONLINE" if bazaar.is_online else "🔴 OFFLINE"
            self.stdout.write(f"{bazaar.name} [{bazaar.server_ip}]: {status}")
