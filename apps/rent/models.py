import os

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.main.models import Bazaar
from smartbozor.qrcode import generate_qr_code
from smartbozor.translation import i18n


@i18n
class Thing(models.Model):
    name_uz = models.CharField(max_length=100)

    @classmethod
    def get_qr_data(cls, bazaar, thing, number):
        return "{0}-{1}-{2}".format(
            bazaar.id,
            thing.id,
            number
        )

    @classmethod
    def get_qr_img_file(cls, bazaar, thing, number):
        cache_path = settings.MEDIA_ROOT / "qr-codes" / "rent" / str(bazaar.id // 1000)
        os.makedirs(cache_path, exist_ok=True)

        qr_data = cls.get_qr_data(bazaar, thing, number)
        cache_file = cache_path / f"{qr_data}.png"
        if os.path.exists(cache_file):
            return cache_file

        img = generate_qr_code("rasta-click.png", f"{settings.QR_CODE_LINK_HOST}/r/{qr_data}/", thing.name.upper(), str(number))
        img.save(cache_file, format="PNG", optimize=True, compress_level=9, dpi=(300, 300))
        img.close()

        return cache_file

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Buyum")
        verbose_name_plural = _("Buyumlar")


class ThingData(models.Model):
    thing = models.ForeignKey(Thing, on_delete=models.RESTRICT, verbose_name=_("Buyum"))
    bazaar = models.ForeignKey(Bazaar, on_delete=models.RESTRICT, verbose_name=_("Bozor"))
    count = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(9999)], verbose_name=_("Netcha mavjud"))
    price = models.BigIntegerField(validators=[MinValueValidator(0)], verbose_name=_("Ijara narxi"))

    def get_qr_image_file(self, number):
        return Thing.get_qr_img_file(self.bazaar, self.thing, number)

    def __str__(self):
        return f"{self.bazaar} - {self.thing}"

    class Meta:
        unique_together = ('thing', 'bazaar')
        verbose_name = _("Bozordagi buyum")
        verbose_name_plural = _("Bozordagi buyumlar")


class ThingStatus(models.Model):
    PAYMENT_PROGRESS_CLICK = 1
    PAYMENT_PROGRESS_PAYME = 2
    PAYMENT_PROGRESS_CASH = 3

    PAYMENT_PROGRESS_TITLE = {
        PAYMENT_PROGRESS_CLICK: "Click",
        PAYMENT_PROGRESS_PAYME: "Payme",
        PAYMENT_PROGRESS_CASH: _("Naqd"),
    }

    bazaar = models.ForeignKey(Bazaar, on_delete=models.RESTRICT, verbose_name=_("Bozor"))
    thing = models.ForeignKey(Thing, on_delete=models.RESTRICT, verbose_name=_("Rasta"))
    number = models.IntegerField(verbose_name=_("Buyum raqami"))
    date = models.DateField(verbose_name=_("Kun"))
    is_occupied = models.BooleanField(default=False, verbose_name=_("Band bo'lgan"))
    is_paid = models.BooleanField(default=False, verbose_name=_("To'lov qilingan"))
    payment_method = models.IntegerField(default=0, verbose_name=_("To'lov turi"))
    payment_progress = models.SmallIntegerField(default=0, verbose_name=_("To'lov jarayoni"))
    price = models.IntegerField(verbose_name=_("Narxi"))
    occupied_at = models.DateTimeField(null=True, default=None, blank=True, verbose_name=_("Band qilingan sana"))
    paid_at = models.DateTimeField(null=True, default=None, blank=True, verbose_name=_("To'lov qilingan sana"))

    @property
    def payment_progress_click(self):
        return self.payment_progress == self.PAYMENT_PROGRESS_CLICK

    @property
    def payment_progress_payme(self):
        return self.payment_progress == self.PAYMENT_PROGRESS_PAYME

    @property
    def payment_progress_cash(self):
        return self.payment_progress == self.PAYMENT_PROGRESS_CASH

    @property
    def payment_progress_title(self):
        return self.PAYMENT_PROGRESS_TITLE.get(self.payment_progress, "-")

    class Meta:
        managed = False

        verbose_name = _("Buyum holati")
        verbose_name_plural = _("Buyum holatlari")

