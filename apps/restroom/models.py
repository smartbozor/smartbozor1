from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.main.models import Bazaar


class Restroom(models.Model):
    bazaar = models.ForeignKey(Bazaar, on_delete=models.RESTRICT, verbose_name=_("Bozor"))
    number = models.CharField(max_length=50, verbose_name=_("Hojatxona raqami"))
    price = models.IntegerField(verbose_name=_("Narxi"), validators=[MinValueValidator(0)])

    def __str__(self):
        if hasattr(self, "display_name"):
            return self.display_name

        return f"Hojatxona {self.number}"

    class Meta:
        verbose_name = _("Hojatxona")
        verbose_name_plural = _("Hojatxonalar")


class RestroomStatus(models.Model):
    restroom = models.ForeignKey(Restroom, on_delete=models.RESTRICT, verbose_name=_("Hojatxona"))
    is_paid = models.BooleanField(default=False, verbose_name=_("To'langan"))
    payment_method = models.IntegerField(default=0, verbose_name=_("To'lov turi"))
    price = models.IntegerField(default=0, verbose_name=_("Narxi"))
    duration = models.IntegerField(default=0, verbose_name=_("Davomiyligi"))
    enter_at = models.DateTimeField(verbose_name=_("Kirgan vaqti"))
    leave_at = models.DateTimeField(null=True, blank=True, default=None, verbose_name=_("Chiqqan vaqti"))

    class Meta:
        managed = False

        verbose_name = _("Hojatxona holati")
        verbose_name_plural = _("Hojatxona holatlari")
