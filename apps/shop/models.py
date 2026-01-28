import os

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.main.models import Section
from smartbozor.qrcode import generate_qr_code


class Shop(models.Model):
    NUMBER_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"

    section = models.ForeignKey(Section, on_delete=models.RESTRICT, verbose_name=_("Bo'lim nomi"))
    owner = models.CharField(max_length=200, verbose_name=_("Tadbirkor"), null=True, blank=True, default=None)
    number = models.CharField(max_length=20, verbose_name=_("Magazin raqami"), validators=[
        RegexValidator(regex=NUMBER_PATTERN)
    ])
    rent_price = models.BigIntegerField(verbose_name=_("Ijara narxi"), validators=[
        MinValueValidator(0)
    ])
    is_active = models.BooleanField(default=True, verbose_name=_("Ishlayaptimi?"))

    @property
    def qr_image_file(self):
        cache_path = settings.MEDIA_ROOT / "qr-codes" / "shop" / str(self.id // 1000)
        os.makedirs(cache_path, exist_ok=True)

        cache_file = cache_path / f"{self.qr_data}.png"
        if os.path.exists(cache_file):
            return cache_file

        img = generate_qr_code("rasta-click.png", f"{settings.QR_CODE_LINK_HOST}/m/{self.qr_data}/", "DO'KON", self.number)
        img.save(cache_file, format="PNG", optimize=True, compress_level=9, dpi=(300, 300))
        img.close()

        return cache_file

    @property
    def qr_data(self):
        return "{0}-{1}-{2}-{3}".format(
            self.section.area.bazaar_id,
            self.section.area.id,
            self.section.id,
            self.number
        )

    def __str__(self):
        return f"Shop {self.number} ({self.id})"

    class Meta:
        unique_together = ('section', 'number')
        verbose_name = _("Magazin")
        verbose_name_plural = _("Magazinlar")


class ShopPayment(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.RESTRICT, verbose_name=_("Magazin"))
    date = models.DateField(verbose_name=_("Kun"))
    nonce = models.BigIntegerField(default=0, editable=False)
    payment_method = models.IntegerField(default=0, verbose_name=_("To'lov turi"))
    amount = models.IntegerField(verbose_name=_("Narxi"))
    paid_at = models.DateTimeField(null=True, default=None, blank=True, verbose_name=_("To'lov qilingan sana"))

    class Meta:
        managed = False

        verbose_name = _("Magazin to'lovi")
        verbose_name_plural = _("Magazin to'lovlari")


class ShopStatus(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.RESTRICT, verbose_name=_("Magazin"))
    date = models.DateField(verbose_name=_("Kun"))
    is_occupied = models.BooleanField(default=False, verbose_name=_("Ochilgan"))
    rent_price = models.BigIntegerField(verbose_name=_("Ijara narxi"), validators=[
        MinValueValidator(0)
    ])
    occupied_at = models.DateTimeField(null=True, default=None, blank=True, verbose_name=_("Sana"))

    class Meta:
        managed = False

        verbose_name = _("Magazin holati")
        verbose_name_plural = _("Magazin holatlari")
