from django.utils import timezone

from apps.main.models import Bazaar
from apps.payment.models import Click
from apps.payment.providers.base import ProviderStall, ProviderException
from apps.stall.models import StallStatus


class ClickStall(ProviderStall):
    @classmethod
    def prepare(cls, request, params, order_nonce=0):
        stall, stall_status = cls.validate_params(params["merchant_trans_id"], params["amount"])

        cls.check_bazaar(request, stall)

        if not stall_status:
            stall_status = StallStatus.objects.create(
                stall_id=stall.id,
                date=timezone.localtime().date(),
                payment_method=Bazaar.PAYMENT_METHOD_CLICK,
                payment_progress=StallStatus.PAYMENT_PROGRESS_CLICK,
                price=stall.price
            )
        else:
            if stall_status.payment_progress > 0 and stall_status.payment_progress != StallStatus.PAYMENT_PROGRESS_CLICK:
                raise ProviderException(-2, "Payment is in progress")

            if stall_status.payment_progress == 0:
                stall_status.payment_method = Bazaar.PAYMENT_METHOD_CLICK
                stall_status.payment_progress = StallStatus.PAYMENT_PROGRESS_CLICK
                stall_status.save()
            else:
                raise ProviderException(-50, "Already prepared")

        return stall_status, stall_status.price

    @classmethod
    def complete(cls, request, click_order: Click):
        try:
            stall_status = click_order.order
        except:
            raise ProviderException(-3, "Order doesn't exist")

        cls.check_bazaar(request, stall_status.stall)

        if stall_status.is_paid:
            raise ProviderException(-5, "Already paid")

        if not stall_status.is_occupied:
            stall_status.is_occupied = True
            stall_status.occupied_at = timezone.now()

        stall_status.is_paid = True
        stall_status.paid_at = timezone.now()
        stall_status.payment_progress = 0
        stall_status.save()
