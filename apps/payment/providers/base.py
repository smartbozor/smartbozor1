from types import SimpleNamespace

from django.db.models import Count, Sum, Min
from django.db.models.functions import Coalesce
from django.utils import timezone
from prompt_toolkit.validation import Validator

from apps.parking.models import Parking, ParkingStatus
from apps.rent.models import ThingData, ThingStatus
from apps.shop.models import Shop, ShopPayment
from apps.stall.models import Stall, StallStatus


class ProviderException(Exception):
    def __init__(self, code, message, *args, **kwargs):
        self.code = code
        self.message = message
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.code}: {self.message}"


class ProviderBadRequestException(ProviderException):
    def __init__(self, *args, **kwargs):
        super().__init__(-32700, "Bad request", *args, **kwargs)


class ProviderStall:
    @classmethod
    def validate_params(cls, order_id, amount):
        try:
            order_id = order_id.split("-")[1]
            stall = Stall.objects.select_for_update().get(id=order_id)
        except:
            raise ProviderException(-31050, "Stall not found")

        if not stall.section.area.bazaar.is_working_day:
            raise ProviderException(-31052, "Bugun bozor ishlamaydi")

        stall_status = StallStatus.objects.filter(
            stall_id=stall.id,
            date=timezone.localtime().date(),
        ).select_for_update().first()

        if stall_status:
            if stall_status.price != amount:
                raise ProviderException(-31001, "Invalid amount")

            if stall_status.is_paid:
                raise ProviderException(-31060, "Stall already paid")

        elif stall.price != amount:
            raise ProviderException(-31001, "Invalid amount")

        return stall, stall_status

    @classmethod
    def cancel_order(cls, stall_status):
        stall_status.is_paid = False
        stall_status.paid_at = None
        stall_status.payment_method = 0
        stall_status.payment_progress = 0
        stall_status.save()

    @classmethod
    def check_bazaar(cls, request, stall):
        if stall.section.area.bazaar_id != request.bazaar.id:
            raise ProviderException(-32700, "Bad request")


class ProviderShop:
    @classmethod
    def validate_params(cls, order_id, amount):
        try:
            order_id = order_id.split("-")[1]
            shop = Shop.objects.select_for_update().get(id=order_id)
        except:
            raise ProviderException(-31050, "Shop not found")

        if amount < 1000:
            raise ProviderException(-31001, "Invalid amount")

        return shop, None

    @classmethod
    def cancel_order(cls, shop_payment: ShopPayment):
        shop_payment.amount = 0
        shop_payment.paid_at = None
        shop_payment.save()

    @classmethod
    def check_bazaar(cls, request, shop):
        if shop.section.area.bazaar_id != request.bazaar.id:
            raise ProviderException(-32700, "Bad request")


class ProviderRent:
    @classmethod
    def validate_params(cls, order_id, amount):
        try:
            rent_id = int(order_id.split("-")[1])
            bazaar_id, thing_id, number = rent_id // (10 ** 8), (rent_id % (10 ** 8) // (10 ** 4)), rent_id % (10 ** 4)

            thing_data = ThingData.objects.select_for_update().get(
                bazaar_id=bazaar_id,
                thing_id=thing_id,
            )

            if number > thing_data.count or number < 0:
                raise Validator
        except:
            raise ProviderException(-31050, "Stall not found")

        if not thing_data.bazaar.is_working_day:
            raise ProviderException(-31052, "Bugun bozor ishlamaydi")

        thing_status = ThingStatus.objects.filter(
            bazaar_id=thing_data.bazaar_id,
            thing_id=thing_data.thing_id,
            number=number,
            date=timezone.localtime().date(),
        ).select_for_update().first()

        if thing_status:
            if thing_status.price != amount:
                raise ProviderException(-31001, "Invalid amount")

            if thing_status.is_paid:
                raise ProviderException(-31060, "Stall already paid")

        elif thing_data.price != amount:
            raise ProviderException(-31001, "Invalid amount")

        return thing_data, thing_status, number

    @classmethod
    def cancel_order(cls, thing_status):
        thing_status.is_paid = False
        thing_status.paid_at = None
        thing_status.payment_method = 0
        thing_status.payment_progress = 0
        thing_status.save()

    @classmethod
    def check_bazaar(cls, request, thing_data):
        if thing_data.bazaar_id != request.bazaar.id:
            raise ProviderException(-32700, "Bad request")


class ProviderParking:
    @classmethod
    def split_order_id(cls, order_id):
        return (order_id >> 32) & 0x7FFFFFFF, (order_id & 0x7FFFFFFF)

    @classmethod
    def validate_params(cls, order_id, payment_amount):
        try:
            parts = order_id.split("-")
            order_id, order_nonce = int(parts[1]), int(parts[2])

            parking_id, __ = cls.split_order_id(order_id)
            parking = Parking.objects.select_for_update().get(id=parking_id)

            query = Parking.extract_query(order_nonce)
            parking_status, excepted_payment_amount, excepted_order_hash_id = parking.get_payment_amount(query, True)

            if len(parking_status) == 0:
                raise Exception()

            if order_id != excepted_order_hash_id:
                raise Exception()
        except:
            raise ProviderException(-31050, "Parking status not found")

        if payment_amount != excepted_payment_amount:
            raise ProviderException(-31001, "Invalid amount")

        for ps in parking_status:
            if ps.is_paid:
                raise ProviderException(-31060, "Parking already paid")

        return parking, parking_status, order_id

    @classmethod
    def cancel_order(cls, parking_status: list[ParkingStatus]|Parking):
        if hasattr(parking_status, "parking_status"):
            # Payme da do_create_transaction da kelishi mumkin
            parking_status = parking_status.parking_status

        for ps in parking_status:
            ps.is_paid = False
            ps.payment_method = 0
            ps.payment_progress = 0
            ps.paid_at = None
            ps.data = None
            ps.save()

    @classmethod
    def check_bazaar(cls, request, parking):
        if parking.bazaar_id != request.bazaar.id:
            raise ProviderException(-32700, "Bad request")
