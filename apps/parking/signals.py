from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.parking.models import ParkingWhitelist
from smartbozor.redis import REDIS_CLIENT

CACHE_VERSION_KEY = "parking_whitelist_version"


def bump_whitelist_version():
    created = REDIS_CLIENT.setnx(CACHE_VERSION_KEY, 1)
    if not created:
        REDIS_CLIENT.incr(CACHE_VERSION_KEY)


@receiver(post_save, sender=ParkingWhitelist)
def whitelist_saved(sender, **kwargs):
    bump_whitelist_version()


@receiver(post_delete, sender=ParkingWhitelist)
def whitelist_deleted(sender, **kwargs):
    bump_whitelist_version()

