import datetime
from types import SimpleNamespace

from django.utils import timezone

from apps.main.models import Bazaar
from apps.parking.models import ParkingStatus
from apps.payment.models import Click
from apps.payment.providers.base import ProviderParking, ProviderException


class ClickParking(ProviderParking):
    @classmethod
    def prepare(cls, request, params, order_nonce=0):
        parking, parking_status, order_id = cls.validate_params(params["merchant_trans_id"], params["amount"])

        cls.check_bazaar(request, parking)

        for ps in parking_status:
            if ps.payment_progress > 0 and ps.payment_progress != ParkingStatus.PAYMENT_PROGRESS_CLICK:
                raise ProviderException(-2, "Payment is in progress")

            if ps.payment_progress == 0:
                ps.payment_method = Bazaar.PAYMENT_METHOD_CLICK
                ps.payment_progress = ParkingStatus.PAYMENT_PROGRESS_CLICK
                ps.save()
            else:
                raise ProviderException(-50, "Already prepared")

        data = [row.id for row in parking_status]
        return SimpleNamespace(id=order_id), params["amount"], data

    @classmethod
    def complete(cls, request, click_order: Click):
        try:
            parking_status = click_order.order
        except:
            raise ProviderException(-31003, "Payment status not found")

        # cls.check_bazaar(request, shop_payment.shop)

        for ps in parking_status:
            ps.is_paid = True
            ps.paid_at = timezone.now()
            ps.payment_progress = 0
            ps.save()
