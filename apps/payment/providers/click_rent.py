from django.utils import timezone

from apps.main.models import Bazaar
from apps.payment.models import Click
from apps.payment.providers.base import ProviderRent, ProviderException
from apps.rent.models import ThingStatus, ThingData


class ClickRent(ProviderRent):
    @classmethod
    def prepare(cls, request, params, order_nonce=0):
        thing_data, thing_status, number = cls.validate_params(params["merchant_trans_id"], params["amount"])

        cls.check_bazaar(request, thing_data)

        if not thing_status:
            thing_status = ThingStatus.objects.create(
                bazaar_id=thing_data.bazaar_id,
                thing_id=thing_data.thing_id,
                number=number,
                date=timezone.localtime().date(),
                payment_method=Bazaar.PAYMENT_METHOD_CLICK,
                payment_progress=ThingStatus.PAYMENT_PROGRESS_CLICK,
                price=thing_data.price
            )
        else:
            if thing_status.payment_progress > 0 and thing_status.payment_progress != ThingStatus.PAYMENT_PROGRESS_CLICK:
                raise ProviderException(-2, "Payment is in progress")

            if thing_status.payment_progress == 0:
                thing_status.payment_method = Bazaar.PAYMENT_METHOD_CLICK
                thing_status.payment_progress = ThingStatus.PAYMENT_PROGRESS_CLICK
                thing_status.save()
            else:
                raise ProviderException(-50, "Already prepared")

        return thing_status, thing_status.price

    @classmethod
    def complete(cls, request, click_order: Click):
        try:
            thing_status = click_order.order
            thing_data = ThingData.objects.get(
                bazaar_id=thing_status.bazaar_id,
                thing_id=thing_status.thing_id,
            )
        except:
            raise ProviderException(-3, "Order doesn't exist")

        cls.check_bazaar(request, thing_data)

        if thing_status.is_paid:
            raise ProviderException(-5, "Already paid")

        if not thing_status.is_occupied:
            thing_status.is_occupied = True
            thing_status.occupied_at = timezone.now()

        thing_status.is_paid = True
        thing_status.paid_at = timezone.now()
        thing_status.payment_progress = 0
        thing_status.save()
