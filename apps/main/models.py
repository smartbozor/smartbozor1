import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from smartbozor.translation import i18n

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")

@i18n
class Region(models.Model):
    name_uz = models.CharField(max_length=100, verbose_name=_("Viloyat nomi"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Viloyat")
        verbose_name_plural = _("Viloyatlar")


@i18n
class District(models.Model):
    region = models.ForeignKey(Region, on_delete=models.RESTRICT)
    name_uz = models.CharField(max_length=100, verbose_name=_("Tuman nomi"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Tuman")
        verbose_name_plural = _("Tumanlar")


@i18n
class Bazaar(models.Model):
    PAYMENT_METHOD_CASH = 1 << 0
    PAYMENT_METHOD_CLICK = 1 << 1
    PAYMENT_METHOD_PAYME = 1 << 2

    PAYMENT_METHOD_CHOICES = (
        (PAYMENT_METHOD_CASH, _("Naqd")),
        (PAYMENT_METHOD_CLICK, _("Click")),
        (PAYMENT_METHOD_PAYME, _("Payme")),
    )

    PAYMENT_METHOD_DICT = {
        a: b for a, b in PAYMENT_METHOD_CHOICES
    }

    MONDAY = 1 << 0
    TUESDAY = 1 << 1
    WEDNESDAY = 1 << 2
    THURSDAY = 1 << 3
    FRIDAY = 1 << 4
    SATURDAY = 1 << 5
    SUNDAY = 1 << 6

    DAY_CHOICES = (
        (MONDAY, _("Dushanba")),
        (TUESDAY, _("Seshanba")),
        (WEDNESDAY, _("Chorshanba")),
        (THURSDAY, _("Payshanba")),
        (FRIDAY, _("Juma")),
        (SATURDAY, _("Shanba")),
        (SUNDAY, _("Yakshanba")),
    )

    district = models.ForeignKey(District, on_delete=models.RESTRICT, verbose_name=_("Bozor joylashgan tuman"))
    name_uz = models.CharField(max_length=100, verbose_name=_("Bozor nomi"))
    working_days = models.IntegerField(default=0, verbose_name=_("Ish kunlari"))
    payment_methods = models.IntegerField(default=0, verbose_name=_("To'lov turlari"))
    payme_merchant = models.CharField(max_length=50, verbose_name=_("Payme merchant id"), null=True, blank=True,
                                      default=None)
    payme_username = models.CharField(max_length=50, verbose_name=_("Payme login"), null=True, blank=True, default=None)
    payme_password = models.CharField(max_length=50, verbose_name=_("Payme parol"), null=True, blank=True, default=None)
    click_merchant_id = models.BigIntegerField(null=True, blank=True, default=None)
    click_merchant_user_id = models.BigIntegerField(null=True, blank=True, default=None)
    click_service_id = models.BigIntegerField(null=True, blank=True, default=None)
    click_secret_key = models.CharField(max_length=50, null=True, blank=True, default=None)
    slug = models.CharField(max_length=30, unique=True, verbose_name=_("Slug"))
    server_user = models.CharField(max_length=50, null=True, blank=True, default=None)
    server_ip = models.GenericIPAddressField(null=True, blank=True, default=None)
    server_port = models.PositiveSmallIntegerField(default=22)
    is_online = models.BooleanField(default=False, verbose_name=_("Online"), editable=False)
    app_version = models.CharField(max_length=50, default='-', editable=False)
    stall_pdf = models.FileField(null=True, blank=True, default=None, editable=False, max_length=255)
    shop_pdf = models.FileField(null=True, blank=True, default=None, editable=False, max_length=255)
    rent_pdf = models.FileField(null=True, blank=True, default=None, editable=False, max_length=255)
    parking_pdf = models.FileField(null=True, blank=True, default=None, editable=False, max_length=255)
    vat_percent = models.PositiveSmallIntegerField(default=12, verbose_name=_("VAT percent"), validators=[
        MinValueValidator(0), MaxValueValidator(100)
    ])

    @property
    def is_allow_cash(self):
        return bool(self.payment_methods & self.PAYMENT_METHOD_CASH)

    @property
    def is_allow_click(self):
        return bool(self.payment_methods & self.PAYMENT_METHOD_CLICK) and bool(self.click_merchant_id) and bool(
            self.click_merchant_user_id) and bool(self.click_service_id) and bool(self.click_secret_key)

    @property
    def is_allow_payme(self):
        return bool(self.payment_methods & self.PAYMENT_METHOD_PAYME) and bool(self.payme_merchant) and bool(
            self.payme_username) and bool(self.payme_password)

    def check_working_day(self, day):
        if day > timezone.localtime().date():
            return False

        n = 1 << (day.isoweekday() - 1)
        return bool(self.working_days & n)

    @property
    def is_working_day(self):
        return self.check_working_day(timezone.localtime().today().date())

    @property
    def working_days_display(self):
        val = self.working_days or 0
        return [str(title) for v, title in Bazaar.DAY_CHOICES if val & v]

    @property
    def payment_methods_display(self):
        val = self.payment_methods or 0
        return [str(title) for v, title in Bazaar.PAYMENT_METHOD_CHOICES if val & v]

    @classmethod
    def ping(cls, bazaar_id, ip, check_files_count=False):

        is_online, files_count, cameras_count, states_count = False, 0, 0, -1
        if ip:
            try:
                ret = subprocess.run(
                    ["ping", "-c", "1", "-W", "1", ip],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                is_online = ret.returncode == 0
            except:
                pass

            if check_files_count:
                try:
                    url = f"http://{ip}:1984/api/info"
                    info_data = requests.get(url, headers={
                        "Authorization": f"Bearer {ACCESS_TOKEN}"
                    }, timeout=5).json()

                    files_count = info_data["files_count"]
                    cameras_count = info_data["cameras_count"]
                    states_count = info_data.get("states_count", -1)
                except:
                    pass

        return bazaar_id, is_online, files_count, cameras_count, states_count

    @classmethod
    def check_online(cls, update=False, *, check_files_count=False):
        bazaars = list(Bazaar.objects.order_by("id").all())

        max_workers = min(50, len(bazaars) or 1)
        result_by_id = dict()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(cls.ping, bazaar.id, bazaar.server_ip, check_files_count) for bazaar in bazaars]
            for f in as_completed(futures):
                bazaar_id, is_online, files_count, cameras_count, states_count = f.result()
                result_by_id[bazaar_id] = (is_online, files_count, cameras_count, states_count)

        result = []

        for bazaar in bazaars:
            bazaar.is_online, bazaar.files_count, bazaar.cameras_count, bazaar.states_count = result_by_id[bazaar.id]

            if update:
                bazaar.save(update_fields=["is_online"])

            result.append(bazaar)

        return result

    def __str__(self):
        if hasattr(self, "display_name"):
            return self.display_name

        return self.name

    class Meta:
        verbose_name = _("Bozor")
        verbose_name_plural = _("Bozorlar")
        permissions = (
            ("bazaar_online", "Bazaar online"),
        )


@i18n
class Area(models.Model):
    bazaar = models.ForeignKey(Bazaar, on_delete=models.RESTRICT, verbose_name=_("Bozor"))
    name_uz = models.CharField(max_length=100, verbose_name=_("Maydon nomi"))

    def __str__(self):
        if hasattr(self, "display_name"):
            return self.display_name

        return self.name

    class Meta:
        verbose_name = _("Blok")
        verbose_name_plural = _("Bloklar")


@i18n
class Section(models.Model):
    area = models.ForeignKey(Area, on_delete=models.RESTRICT, verbose_name=_("Maydon"))
    name_uz = models.CharField(max_length=100, verbose_name=_("Bo'lim nomi"))

    def __str__(self):
        if hasattr(self, "display_name"):
            return self.display_name

        return self.name

    class Meta:
        verbose_name = _("Bo'lim")
        verbose_name_plural = _("Bo'limlar")


class Receipt(models.Model):
    OBJECT_TYPE_STALL = 0
    OBJECT_TYPE_SHOP = 1
    OBJECT_TYPE_RENT = 2
    OBJECT_TYPE_PARKING = 3
    OBJECT_TYPE_LIVESTOCK = 4 # Mol bozor
    OBJECT_TYPE_GROUND_STALL = 5 # Yoymalar

    STATUS_NEW = 0
    STATUS_DONE = 1

    user = models.ForeignKey("account.User", on_delete=models.RESTRICT, verbose_name=_("User"))
    bazaar = models.ForeignKey(Bazaar, on_delete=models.RESTRICT, verbose_name=_("Bazaar"))
    object_type = models.SmallIntegerField(verbose_name=_("Object type"))
    object_id = models.BigIntegerField(verbose_name=_("Object ID"))
    amount = models.BigIntegerField(verbose_name=_("Narxi"))
    status = models.SmallIntegerField(verbose_name=_("Holati"))
    data = models.JSONField(verbose_name=_("Data"))
    ofd_link = models.CharField(max_length=300, null=True, blank=True, default=None, verbose_name=_("OFD link"))
    ofd_time = models.BigIntegerField(default=0)
    added_at = models.DateTimeField(verbose_name=_("Added at"), auto_now_add=True)

    class Meta:
        managed = False
        verbose_name = _("Chek")
        verbose_name_plural = _("Cheklar")
