import datetime

from django.utils import timezone

from apps.main.models import Bazaar
from apps.payment.models import Click
from apps.payment.providers.base import ProviderShop, ProviderException
from apps.shop.models import ShopPayment


class ClickShop(ProviderShop):
    @classmethod
    def prepare(cls, request, params, order_nonce=0):
        shop, __ = cls.validate_params(params["merchant_trans_id"], params["amount"])

        cls.check_bazaar(request, shop)

        today = timezone.localtime().date()
        start = today.replace(day=1)

        shop_payment, __ = ShopPayment.objects.select_for_update().get_or_create(
            shop_id=shop.id,
            date__range=(start, today),
            payment_method=Bazaar.PAYMENT_METHOD_CLICK,
            nonce=order_nonce,
            defaults={
                "date": timezone.localtime().date(),
                "amount": params["amount"]
            }
        )

        return shop_payment, params["amount"]

    @classmethod
    def complete(cls, request, click_order: Click):
        try:
            shop_payment = click_order.order
        except:
            raise ProviderException(-31003, "Shop payment not found")

        cls.check_bazaar(request, shop_payment.shop)

        shop_payment.paid_at = timezone.now()
        shop_payment.save()
