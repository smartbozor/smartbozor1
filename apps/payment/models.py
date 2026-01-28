from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.main.models import District
from apps.parking.models import ParkingStatus
from apps.payment.providers.base import ProviderParking
from apps.rent.models import ThingStatus
from apps.shop.models import ShopPayment
from apps.stall.models import StallStatus


class Payme(models.Model):
    order_type = models.CharField(max_length=1)
    order_id = models.BigIntegerField()
    payme_id = models.CharField(max_length=50)
    create_order_id = models.BigIntegerField(default=0)
    create_order_nonce = models.BigIntegerField(default=0)
    amount = models.BigIntegerField(default=0)
    state = models.SmallIntegerField(default=0)
    reason = models.SmallIntegerField(default=None, null=True, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
    perform_time = models.DateTimeField(default=None, null=True, blank=True)
    cancel_time = models.DateTimeField(default=None, null=True, blank=True)
    data = models.JSONField(null=True, blank=True, default=None)

    @property
    def transaction_id(self):
        return f"{self.order_type}-{self.order_id}"

    @property
    def create_time_ts(self):
        return self.ts(self.create_time)

    @property
    def perform_time_ts(self):
        return self.ts(self.perform_time)

    @property
    def cancel_time_ts(self):
        return self.ts(self.cancel_time)

    @property
    def order(self):
        if self.order_type == 's':
            return StallStatus.objects.get(id=self.order_id)
        elif self.order_type == 'm':
            return ShopPayment.objects.get(id=self.order_id)
        elif self.order_type == 'r':
            return ThingStatus.objects.get(id=self.order_id)
        elif self.order_type == 'p':
            return ParkingStatus.objects.filter(id__in=self.data).all()

    @classmethod
    def ts(cls, t):
        if t is None:
            return 0

        return int(t.timestamp() * 1000)

    class Meta:
        managed = False


class Click(models.Model):
    order_type = models.CharField(max_length=1)
    order_id = models.BigIntegerField()
    create_order_id = models.BigIntegerField(default=0)
    click_trans_id = models.BigIntegerField()
    click_paydoc_id = models.BigIntegerField()
    amount = models.BigIntegerField()
    status = models.SmallIntegerField(default=0)
    prepare_time = models.DateTimeField()
    complete_time = models.DateTimeField(null=True, blank=True, default=None)
    data = models.JSONField(null=True, blank=True, default=None)

    @property
    def transaction_id(self):
        return f"{self.order_type}-{self.order_id}"

    @property
    def order(self):
        if self.order_type == 's':
            return StallStatus.objects.get(id=self.order_id)
        elif self.order_type == 'm':
            return ShopPayment.objects.get(id=self.order_id)
        elif self.order_type == 'r':
            return ThingStatus.objects.get(id=self.order_id)
        elif self.order_type == 'p':
            return ParkingStatus.objects.filter(id__in=self.data).all()

    class Meta:
        managed = False


class Point(models.Model):
    district = models.ForeignKey(District, on_delete=models.RESTRICT)
    name = models.CharField(max_length=50, default=None, null=True, blank=True)
    click_merchant_id = models.BigIntegerField(null=True, blank=True, default=None)
    click_merchant_user_id = models.BigIntegerField(null=True, blank=True, default=None)
    click_service_id = models.BigIntegerField(null=True, blank=True, default=None)
    click_secret_key = models.CharField(max_length=50, null=True, blank=True, default=None)
    slug = models.CharField(max_length=30, unique=True, verbose_name=_("Slug"))
    status = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.id}: {self.name}"


class PointProduct(models.Model):
    point = models.ForeignKey(Point, on_delete=models.RESTRICT)
    name = models.CharField(max_length=50, default=None, null=True, blank=True)
    fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fee_price = models.IntegerField(default=0)
    fee_included = models.BooleanField(default=False)
    price = models.IntegerField(default=0)
    status = models.BooleanField(default=True)

    def calc_total_price(self, price):
        if self.price > 0:
            price = self.price

        fee_percent_price = round(price * self.fee_percent / 100, 2)

        total_price = price
        if not self.fee_included:
            total_price += self.fee_price + fee_percent_price

        return fee_percent_price, total_price

    @property
    def is_available(self):
        return all([
            self.status,
            self.point.status,
            bool(self.point.click_service_id),
            bool(self.point.click_merchant_id),
            bool(self.point.click_merchant_user_id),
            bool(self.point.click_secret_key)
        ])
