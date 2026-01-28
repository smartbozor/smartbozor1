import hashlib
import os
import secrets
import string

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import ForeignKey, Count, Value, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.main.models import Bazaar
from smartbozor.helpers import UploadTo, int_to_base36
from smartbozor.qrcode import generate_qr_code

ALPHABET = string.ascii_lowercase + string.digits


def generate_token(length: int = 32) -> str:
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))


class Parking(models.Model):
    BILLING_MODE_ENTER = 0
    BILLING_MODE_EXIT = 1

    bazaar = models.ForeignKey(Bazaar, on_delete=models.RESTRICT, verbose_name=_("Bozor"))
    name = models.CharField(max_length=50, verbose_name=_("Turargoh nomi/raqami"))
    billing_mode = models.SmallIntegerField(choices=(
        (BILLING_MODE_ENTER, _("Pulni kirishi bilan hisoblash")),
        (BILLING_MODE_EXIT, _("Pulni chiqishda hisoblash")),
    ), default=BILLING_MODE_EXIT)
    save_image = models.BooleanField(default=False, verbose_name=_("Rasmlarni saqlash"))

    @property
    def qr_image_file(self):
        cache_path = settings.MEDIA_ROOT / "qr-codes" / "parking" / str(self.id // 1000)
        os.makedirs(cache_path, exist_ok=True)

        cache_file = cache_path / f"{self.qr_data}.png"
        if os.path.exists(cache_file):
            return cache_file

        img = generate_qr_code("rasta-click.png", f"{settings.QR_CODE_LINK_HOST}/p/{self.qr_data}/", "AVTOTURARGOH", str(self.id))
        img.save(cache_file, format="PNG", optimize=True, compress_level=9, dpi=(300, 300))
        img.close()

        return cache_file

    @property
    def qr_data(self):
        return str(self.id)

    @classmethod
    def extract_query(cls, data):
        data_str = str(data)
        if data_str.startswith("1"):
            return int(data_str[1:])
        elif data_str.startswith("9"):
            return int_to_base36(int(data_str[1:]))

        raise ValueError

    def get_payment_amount(self, query, in_transaction=False):
        after = timezone.now().date().replace(day=1) - relativedelta(months=6)
        qs = ParkingStatus.objects.filter(
            parking=self,
            is_paid=False,
            price__gt=0,
            payment_progress=0,
            date__gte=after,
        ).order_by('id')

        if in_transaction:
            qs = qs.select_for_update()

        if isinstance(query, str):
            rows = qs.filter(number=query.upper()).all()
        else:
            rows = qs.all()[:query]

        payment_amount, selected_id, selected_rows = 0, [], []
        for row in rows:
            payment_amount += row.price
            selected_id.append(row.id)
            selected_rows.append(row)

        selected_id.sort()

        data = ",".join(map(str, selected_id)).encode("utf-8")
        digest = hashlib.sha256(data).digest()
        order_id = (self.id << 32) | int.from_bytes(digest[:4], byteorder="big", signed=False)

        return selected_rows, payment_amount, order_id

    def __str__(self):
        if hasattr(self, "display_name"):
            return self.display_name

        return f"Parking {self.name}"

    class Meta:
        verbose_name = _("Avtoturargoh")
        verbose_name_plural = _("Avtoturargohlar")


class ParkingPrice(models.Model):
    parking = models.ForeignKey(Parking, on_delete=models.RESTRICT, verbose_name=_("Avtoturargoh"))
    duration = models.IntegerField(
        default=0,
        verbose_name=_("Davomiyligi (sekundda)"),
        help_text=_(
            "Ko'rsatilgan qiymatdan o'tsa narx hisoblanadi. Masalan 3600 qo'yilsa, 1 soatdan oshsa ma'noni anglatadi."),
        validators=[MinValueValidator(0)],
    )
    price = models.IntegerField(
        verbose_name=_("Narxi"),
        help_text=_("Agar 0 qo'yilsa, tekin ekanligini anglatadi"),
        validators=[MinValueValidator(0)]
    )
    cash_receipts = models.IntegerField(default=0, verbose_name=_("Naqd cheklar soni"), editable=False)

    class Meta:
        verbose_name = _("Avtoturargoh narxi")
        verbose_name_plural = _("Avtoturargoh narxlari")


class ParkingCamera(models.Model):
    ROLE_ENTER = 0
    ROLE_EXIT = 1

    parking = ForeignKey(Parking, on_delete=models.RESTRICT, verbose_name=_("Avtoturargoh"))
    role = models.SmallIntegerField(choices=(
        (ROLE_ENTER, _("Kirish")),
        (ROLE_EXIT, _("Chiqish")),
    ), default=ROLE_ENTER, verbose_name=_("Roli"))
    mac = models.CharField(max_length=12, verbose_name=_("MAC"), null=True, blank=True, default=None)
    token = models.CharField(max_length=32, verbose_name=_("Token"), default=generate_token, editable=False,
                             unique=True)

    class Meta:
        verbose_name = _("Kamera")
        verbose_name_plural = _("Kameralar")


class ParkingStatus(models.Model):
    LICENSE_PLATE_UNKNOWN = "UNKNOWN"

    PAYMENT_PROGRESS_CLICK = 1
    PAYMENT_PROGRESS_PAYME = 2
    PAYMENT_PROGRESS_CASH = 3

    PAYMENT_PROGRESS_TITLE = {
        PAYMENT_PROGRESS_CLICK: "Click",
        PAYMENT_PROGRESS_PAYME: "Payme",
        PAYMENT_PROGRESS_CASH: _("Naqd"),
    }

    parking = models.ForeignKey(Parking, on_delete=models.RESTRICT, verbose_name=_("Avtoturargoh"))
    date = models.DateField(verbose_name=_("Sana"))
    number = models.CharField(max_length=20, verbose_name=_("Avtoraqam"))
    is_paid = models.BooleanField(default=False, verbose_name=_("To'langan"))
    payment_method = models.IntegerField(default=0, verbose_name=_("To'lov turi"))
    payment_progress = models.SmallIntegerField(default=0, verbose_name=_("To'lov jarayoni"))
    price = models.IntegerField(default=0, verbose_name=_("Narxi"))
    duration = models.IntegerField(default=0, verbose_name=_("Davomiyligi"))
    enter_count = models.IntegerField(default=0, verbose_name=_("Kirish soni"))
    leave_count = models.IntegerField(default=0, verbose_name=_("Chiqish soni"))
    enter_at = models.DateTimeField(verbose_name=_("Kirgan vaqti"))
    leave_at = models.DateTimeField(null=True, blank=True, default=None, verbose_name=_("Chiqqan vaqti"))
    paid_at = models.DateTimeField(null=True, blank=True, default=None, verbose_name=_("To'langan vaqti"))
    enter_image = models.ImageField(upload_to=UploadTo("parking/%Y-%m/enter"), null=True, blank=True, default=None,
                                    verbose_name=_("Kirish rasmi"))
    leave_image = models.ImageField(upload_to=UploadTo("parking/%Y-%m/exit"), null=True, blank=True, default=None,
                                    verbose_name=_("Chiqish rasmi"))

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

        verbose_name = _("Avtoturargoh holati")
        verbose_name_plural = _("Avtoturargoh holatlari")


class ParkingWhitelist(models.Model):
    region = models.ForeignKey("main.Region", on_delete=models.RESTRICT, verbose_name=_("Viloyat"), null=True,
                               blank=True)
    district = models.ForeignKey("main.District", on_delete=models.RESTRICT, verbose_name=_("Tuman"), null=True,
                                 blank=True)
    bazaar = models.ForeignKey("main.Bazaar", on_delete=models.RESTRICT, verbose_name=_("Bozor"), null=True, blank=True)
    pattern = models.CharField(max_length=100, verbose_name=_("Regex"))

    class Meta:
        verbose_name = _("Oq ro'yxat")
        verbose_name_plural = _("Oq ro'yxat")
