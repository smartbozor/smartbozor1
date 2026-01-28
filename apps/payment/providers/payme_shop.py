import datetime

from django.utils import timezone

from apps.main.models import Bazaar
from apps.payment.models import Payme
from apps.payment.providers.base import ProviderShop, ProviderException
from apps.shop.models import ShopPayment


class PaymeShop(ProviderShop):
    @classmethod
    def check_perform_transaction(cls, request, params):
        shop, __ = cls.validate_params(params["account"]["order_id"], params["amount"])

        cls.check_bazaar(request, shop)

        return {
            "result": {"allow": True}
        }

    @classmethod
    def create_transaction(cls, request, params, order_nonce):
        shop, __ = cls.validate_params(params["account"]["order_id"], params["amount"] // 100)

        cls.check_bazaar(request, shop)

        today = timezone.localtime().date()
        start = today - datetime.timedelta(days = 2)

        shop_payment, __ = ShopPayment.objects.select_for_update().get_or_create(
            shop_id=shop.id,
            date__range=(start, today),
            payment_method=Bazaar.PAYMENT_METHOD_PAYME,
            nonce=order_nonce,
            defaults={
                "date": timezone.localtime().date(),
                "amount": params["amount"]
            }
        )

        return shop_payment, params["amount"]

    @classmethod
    def perform_transaction(cls, request, payme_order: Payme):
        try:
            shop_payment = payme_order.order
        except:
            raise ProviderException(-31003, "Shop payment not found")

        cls.check_bazaar(request, shop_payment.shop)

        shop_payment.paid_at = timezone.now()
        shop_payment.save()
