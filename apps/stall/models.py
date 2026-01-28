import os

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.main.models import Section
from smartbozor.qrcode import generate_qr_code


class StallManager(models.Manager):
    def get_queryset(self):
        today = timezone.localtime().date()
        return super().get_queryset().annotate(
            status_count=Count("stallstatus__id", distinct=True, filter=Q(stallstatus__date=today) & (
                    Q(stallstatus__payment_progress__gt=0) | Q(stallstatus__is_paid=True)
            ))
        )


class Stall(models.Model):
    NUMBER_PATTERN = r"^[a-z0-9]+$"

    # objects = StallManager()

    section = models.ForeignKey(Section, on_delete=models.RESTRICT, verbose_name=_("Bo'lim nomi"))
    number = models.CharField(max_length=20, verbose_name=_("Rasta raqami"), validators=[
        RegexValidator(regex=NUMBER_PATTERN)
    ])
    price = models.IntegerField(verbose_name=_("Rasta narxi"), validators=[MinValueValidator(100)])

    @property
    def qr_image_file(self):
        cache_path = settings.MEDIA_ROOT / "qr-codes" / "stall" / str(self.id // 1000)
        os.makedirs(cache_path, exist_ok=True)

        cache_file = cache_path / f"{self.qr_data}.png"
        if os.path.exists(cache_file):
            return cache_file

        img = generate_qr_code("rasta-click.png", f"{settings.QR_CODE_LINK_HOST}/s/{self.qr_data}/", "RASTA",
                               self.number)
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

    class Meta:
        unique_together = ('section', 'number')
        verbose_name = _("Rasta")
        verbose_name_plural = _("Rastalar")


class StallStatus(models.Model):
    PAYMENT_PROGRESS_CLICK = 1
    PAYMENT_PROGRESS_PAYME = 2
    PAYMENT_PROGRESS_CASH = 3

    PAYMENT_PROGRESS_TITLE = {
        PAYMENT_PROGRESS_CLICK: "Click",
        PAYMENT_PROGRESS_PAYME: "Payme",
        PAYMENT_PROGRESS_CASH: _("Naqd"),
    }

    stall = models.ForeignKey(Stall, on_delete=models.RESTRICT, verbose_name=_("Rasta"))
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

        verbose_name = _("Rasta holati")
        verbose_name_plural = _("Rasta holatlari")

# class StallGroup(models.Model):
#     number = models.CharField(max_length=20, verbose_name=_("Guruh nomi"), validators=[
#         RegexValidator(regex=r"^[a-z0-9]+$", )
#     ])
#     stalls = models.ManyToManyField(Stall, verbose_name=_("Rastalar"))
