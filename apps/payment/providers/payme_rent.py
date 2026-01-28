from django.utils import timezone

from apps.main.models import Bazaar
from apps.payment.models import Payme
from apps.payment.providers.base import ProviderRent, ProviderException
from apps.rent.models import ThingStatus, ThingData


class PaymeRent(ProviderRent):
    @classmethod
    def check_perform_transaction(cls, request, params):
        thing_data, thing_status, number = cls.validate_params(params["account"]["order_id"], params["amount"])

        cls.check_bazaar(request, thing_data)

        if thing_status:
            if thing_status.payment_progress > 0:
                raise ProviderException(-31061, "Payment is in progress")

        return {
            "result": {"allow": True}
        }

    @classmethod
    def create_transaction(cls, request, params, order_nonce=None):
        thing_data, thing_status, number = cls.validate_params(params["account"]["order_id"], params["amount"])

        cls.check_bazaar(request, thing_data)

        if not thing_status:
            thing_status = ThingStatus.objects.create(
                bazaar_id=thing_data.bazaar_id,
                thing_id=thing_data.thing_id,
                number=number,
                date=timezone.localtime().date(),
                payment_method=Bazaar.PAYMENT_METHOD_PAYME,
                payment_progress=0,
                price=thing_data.price
            )
        else:
            if thing_status.payment_progress > 0 and thing_status.payment_progress != ThingStatus.PAYMENT_PROGRESS_PAYME:
                raise ProviderException(-31061, "Payment is in progress")

            if thing_status.payment_progress == 0:
                thing_status.payment_method = Bazaar.PAYMENT_METHOD_PAYME
                thing_status.payment_progress = ThingStatus.PAYMENT_PROGRESS_PAYME
                thing_status.save()

        return thing_status, thing_status.price

    @classmethod
    def perform_transaction(cls, request, payme_order: Payme):
        try:
            thing_status = payme_order.order
            thing_data = ThingData.objects.get(
                bazaar_id=thing_status.bazaar_id,
                thing_id=thing_status.thing_id,
            )
        except:
            raise ProviderException(-31003, "Stall status not found")

        cls.check_bazaar(request, thing_data)

        # Parallel qayerdandir to'langan
        # Aslida bunaqa bo'lishi kerak emas, chunki
        # perform_transaction state = 1 bo'lganida chaqiriladi
        if thing_status.is_paid:
            raise ProviderException(-31050, "Already paid")

        if not thing_status.is_occupied:
            thing_status.is_occupied = True
            thing_status.occupied_at = timezone.now()

        thing_status.is_paid = True
        thing_status.paid_at = timezone.now()
        thing_status.payment_progress = 0
        thing_status.save()

