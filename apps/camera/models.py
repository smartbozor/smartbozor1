import os

from django.conf import settings
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from apps.main.models import Bazaar


class Camera(models.Model):
    TYPE_STALL = 0

    TYPE_TITLES = {
        TYPE_STALL: "R"
    }

    bazaar = models.ForeignKey(Bazaar, on_delete=models.RESTRICT, verbose_name=_("Bozor"), db_index=False)
    device_sn = models.CharField(_("Device SN"), max_length=100, null=True, blank=True, editable=False)
    name = models.CharField(max_length=100, verbose_name=_("Kamera nomi"))
    camera_mac = models.CharField(_("Camera MAC"), max_length=20, null=True, blank=True, default=None, editable=False)
    camera_ip = models.GenericIPAddressField(null=True, blank=True, default=None, verbose_name=_("IP"), editable=False)
    camera_port = models.PositiveSmallIntegerField(default=554, verbose_name=_("Port"))
    username = models.CharField(max_length=100, null=True, blank=True, default=None, verbose_name=_("Login"))
    password = models.CharField(max_length=100, null=True, blank=True, default=None, verbose_name=_("Parol"))
    roi = models.JSONField(null=True, blank=True, default=None, verbose_name=_("ROI"), editable=False)
    screenshot = models.ImageField(upload_to="camera/screenshot", null=True, blank=True, default=None, verbose_name=_("Screenshot"), editable=False)
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    is_online = models.BooleanField(default=False, verbose_name=_("Online"), editable=False)
    use_ai = models.BooleanField(default=False, verbose_name=_("Use AI"))

    @cached_property
    def total_info(self):
        info, total = [], self.type_total

        for typ, title in self.TYPE_TITLES.items():
            v = total.get(typ, 0)
            if v > 0:
                info.append(f"{title}: {v}")

        return ", ".join(info)

    @cached_property
    def type_total(self):
        if not self.roi:
            return dict()

        total = dict()
        for row in self.roi:
            typ = row["type"]
            total[typ] = total.get(typ, 0) + 1

        return total

    class Meta:
        indexes = [
            models.Index(fields=["bazaar", "device_sn"])
        ]
        verbose_name = _("Kamera")
        verbose_name_plural = _("Kameralar")
