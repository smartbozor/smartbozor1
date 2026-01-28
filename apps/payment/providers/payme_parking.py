from types import SimpleNamespace

from django.utils import timezone

from apps.main.models import Bazaar
from apps.parking.models import ParkingStatus
from apps.payment.models import Payme
from apps.payment.providers.base import ProviderParking, ProviderException


class PaymeParking(ProviderParking):
    @classmethod
    def check_perform_transaction(cls, request, params):
        parking, parking_status, __ = cls.validate_params(params["account"]["order_id"], params["amount"])

        cls.check_bazaar(request, parking)

        for ps in parking_status:
            if ps.payment_progress > 0:
                raise ProviderException(-31061, "Payment is in progress")

        return {
            "result": {"allow": True}
        }

    @classmethod
    def create_transaction(cls, request, params):
        parking, parking_status, order_id = cls.validate_params(params["account"]["order_id"], params["amount"])

        cls.check_bazaar(request, parking)

        for ps in parking_status:
            if ps.payment_progress > 0 and ps.payment_progress != ParkingStatus.PAYMENT_PROGRESS_PAYME:
                raise ProviderException(-31061, "Payment is in progress")

            if ps.payment_progress == 0:
                ps.payment_method = Bazaar.PAYMENT_METHOD_PAYME
                ps.payment_progress = ParkingStatus.PAYMENT_PROGRESS_PAYME
                ps.save()

        data = [row.id for row in parking_status]
        return SimpleNamespace(
            id=order_id,
            parking_status=parking_status,
        ), params["amount"], data

    @classmethod
    def perform_transaction(cls, request, payme_order: Payme):
        try:
            parking_status = payme_order.order
        except:
            raise ProviderException(-31003, "Stall status not found")

        # cls.check_bazaar(request, stall_status.stall)

        for ps in parking_status:
            if ps.is_paid:
                raise ProviderException(-31050, "Already paid")

            ps.is_paid = True
            ps.paid_at = timezone.now()
            ps.payment_progress = 0
            ps.save()
