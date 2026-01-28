from django.utils import timezone

from apps.main.models import Bazaar
from apps.payment.models import Payme
from apps.payment.providers.base import ProviderException, ProviderStall
from apps.stall.models import StallStatus


class PaymeStall(ProviderStall):
    @classmethod
    def check_perform_transaction(cls, request, params):
        stall, stall_status = cls.validate_params(params["account"]["order_id"], params["amount"])

        cls.check_bazaar(request, stall)

        if stall_status:
            if stall_status.payment_progress > 0:
                raise ProviderException(-31061, "Payment is in progress")

        return {
            "result": {"allow": True}
        }

    @classmethod
    def create_transaction(cls, request, params):
        stall, stall_status = cls.validate_params(params["account"]["order_id"], params["amount"])

        cls.check_bazaar(request, stall)

        if not stall_status:
            stall_status = StallStatus.objects.create(
                stall_id=stall.id,
                date=timezone.localtime().date(),
                payment_method=Bazaar.PAYMENT_METHOD_PAYME,
                payment_progress=StallStatus.PAYMENT_PROGRESS_PAYME,
                price=stall.price
            )
        else:
            if stall_status.payment_progress > 0:
                raise ProviderException(-31061, "Payment is in progress")

            if stall_status.payment_progress == 0:
                stall_status.payment_method = Bazaar.PAYMENT_METHOD_PAYME
                stall_status.payment_progress = StallStatus.PAYMENT_PROGRESS_PAYME
                stall_status.save()

        return stall_status, stall_status.price

    @classmethod
    def perform_transaction(cls, request, payme_order: Payme):
        try:
            stall_status = payme_order.order
        except:
            raise ProviderException(-31003, "Stall status not found")

        cls.check_bazaar(request, stall_status.stall)

        # Parallel qayerdandir to'langan
        # Aslida bunaqa bo'lishi kerak emas, chunki
        # perform_transaction state = 1 bo'lganida chaqiriladi
        if stall_status.is_paid:
            raise ProviderException(-31050, "Already paid")

        if not stall_status.is_occupied:
            stall_status.is_occupied = True
            stall_status.occupied_at = timezone.now()

        stall_status.is_paid = True
        stall_status.paid_at = timezone.now()
        stall_status.payment_progress = 0
        stall_status.save()

