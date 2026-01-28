import uuid
from datetime import timedelta, datetime

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.camera.models import Camera
from apps.main.models import Bazaar
from smartbozor.storages import stall_storage


class StallDataSet(models.Model):
    STATUS_NEW = 0
    STATUS_MARKED = 1
    STATUS_MARKED_MODERATED = 2
    STATUS_GENERATED = 3
    STATUS_WRONG = -1

    bazaar = models.ForeignKey(Bazaar, on_delete=models.RESTRICT, verbose_name=_("Bozor"))
    camera = models.ForeignKey(Camera, on_delete=models.RESTRICT, verbose_name=_("Kamera"))
    image = models.ImageField(verbose_name="Snapshot", storage=stall_storage)
    data = models.JSONField(verbose_name="AI data")
    status = models.SmallIntegerField(default=STATUS_NEW, db_index=True)
    snapshot_at = models.DateTimeField(null=True, default=None, blank=True, verbose_name="Snapshot date")

    @classmethod
    def get_snapshot_after(cls):
        today = timezone.localtime().date()
        snapshot_after_data = today - timedelta(days=360)
        return timezone.make_aware(
            datetime(snapshot_after_data.year, snapshot_after_data.month, snapshot_after_data.day)
        )

    class Meta:
        managed = False


class StallOccupation(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.RESTRICT, verbose_name=_("Kamera"), db_index=False)
    roi_id = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name=_("Roi ID"))
    state = models.SmallIntegerField(verbose_name=_("State"), editable=False)
    check_at = models.DateTimeField(verbose_name=_("Check at"), editable=False)

    class Meta:
        managed = False
