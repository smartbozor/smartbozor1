import datetime

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.account.models import User
from apps.api.authentication import DeviceTokenAuthenticationNoPin
from apps.api.menu import *
from apps.api.models import DeviceToken
from apps.api.serializers import BazaarSerializer, LoginSerializer, UserSerializer, PinSerializer, \
    ReceiptStallSerializer, ReceiptSaveSerializer, ReceiptShopSerializer, ReceiptRentSerializer, \
    ReceiptParkingSerializer
from apps.main.models import Bazaar, Receipt


class LoginView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = LoginSerializer(data=request.data)
        if not data.is_valid():
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        auth_user = authenticate(username=data.data['username'], password=data.data['password'])
        if auth_user is None:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=auth_user.pk)
            bazaar = auth_user.allowed_bazaar.order_by('id').first()

            DeviceToken.objects.filter(
                device_id=data.validated_data['device_id']
            ).delete()
            token, __ = DeviceToken.objects.get_or_create(
                device_id=data.validated_data['device_id'],
                user=user,
                bazaar=bazaar
            )

        return Response({
            "access_token": token.key,
        })


class SetPinView(APIView):
    authentication_classes = [
        DeviceTokenAuthenticationNoPin
    ]

    def get(self, request, *args, **kwargs):
        return Response({
            "set": not bool(request.auth.pin)
        })

    def post(self, request, *args, **kwargs):
        data = PinSerializer(data=request.data)
        data.is_valid(raise_exception=True)

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=self.request.user.pk)
            try:
                device_token = DeviceToken.objects.select_for_update().get(
                    pk=self.request.auth.pk,
                    user=user
                )

                if device_token.pin:
                    return Response({}, status=status.HTTP_400_BAD_REQUEST)

                device_token.pin = make_password(data.validated_data['pin'])
                device_token.save()

                return Response({})
            except DeviceToken.DoesNotExist:
                return Response({}, status=status.HTTP_404_NOT_FOUND)


class PinValidateView(APIView):
    def post(self, request, *args, **kwargs):
        data = PinSerializer(data=request.data)
        data.is_valid(raise_exception=True)

        with transaction.atomic():
            dt = DeviceToken.objects.select_related().get(pk=request.auth.pk)
            if not dt.pin:
                return Response({}, status=status.HTTP_400_BAD_REQUEST)

            attempt_count = (dt.pin_attempt.get("count", 0) or 0) + 1
            lock_until = dt.pin_attempt.get("lock_until", 0) or 0
            utc_timestamp = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())

            if not check_password(data.validated_data['pin'], request.auth.pin):
                if attempt_count >= 10:
                    # 10 yilga LOCK qilamiz
                    lock_until = utc_timestamp + int(datetime.timedelta(days=3650).total_seconds())
                elif attempt_count >= 3:
                    k = attempt_count - 3
                    lock_until = utc_timestamp + int(datetime.timedelta(minutes=2 ** k).total_seconds())

                dt.pin_attempt = {
                    "count": attempt_count,
                    "lock_until": lock_until,
                }
                dt.save()
                return Response({}, status=status.HTTP_403_FORBIDDEN)

            dt.pin_attempt = dict()
            dt.save()

        return Response({})


class SyncDeviceView(APIView):
    def get(self, request):
        bazaar = request.auth.bazaar
        today = timezone.localtime().date()

        return Response({
            "user": UserSerializer(self.request.user).data,
            "bazaar": BazaarSerializer(bazaar).data,
            "menu": init_menu(bazaar, today),
        })


class ReceiptView(APIView):
    MENU_SERIALIZERS = {
        1: (Receipt.OBJECT_TYPE_STALL, ReceiptStallSerializer),
        2: (Receipt.OBJECT_TYPE_SHOP, ReceiptShopSerializer),
        3: (Receipt.OBJECT_TYPE_RENT, ReceiptRentSerializer),
        4: (Receipt.OBJECT_TYPE_PARKING, ReceiptParkingSerializer)
    }

    OBJECT_NAME = {
        Receipt.OBJECT_TYPE_STALL: _("Rasta"),
        Receipt.OBJECT_TYPE_SHOP: _("Do'kon"),
        Receipt.OBJECT_TYPE_RENT: _("Ijara buyumi"),
        Receipt.OBJECT_TYPE_PARKING: _("Avtoturargoh"),
    }

    OFD_DATA = {
        Receipt.OBJECT_TYPE_STALL: {
            "spic": "10701001003000000",
            "units": 1494956
        },
        Receipt.OBJECT_TYPE_SHOP: {
            "spic": "10701001003000000",
            "units": 1494956
        },
        Receipt.OBJECT_TYPE_RENT: {
            "spic": "10701001003000000",
            "units": 1494956
        },
        Receipt.OBJECT_TYPE_PARKING: {
            "spic": "10199001007000000",
            "units": 91058
        }
    }

    def post(self, request, pk, *args, **kwargs):
        original_pk = pk
        if 3_000_000 <= pk < 4_000_000:
            pk = 3
        elif 4_000_000 <= pk < 5_000_000:
            pk = 4

        if pk not in self.MENU_SERIALIZERS:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        object_type, menu_serializer = self.MENU_SERIALIZERS[pk]
        data = menu_serializer(data=request.data)
        if not data.is_valid():
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            bazaar = Bazaar.objects.select_related().filter(id=request.auth.bazaar_id).get()
            if not bazaar.is_working_day:
                return Response({
                    "detail": _("Bugun bozor ish kuni emas")
                }, status=status.HTTP_403_FORBIDDEN)

            if not bazaar.is_allow_cash:
                return Response({
                    "detail": _("Naqd orqali to'lov qabul qilishga ruxsat berilmagan")
                }, status=status.HTTP_403_FORBIDDEN)

            now = timezone.localtime()
            object_pk, amount, extra_data, print_info = self.get_object_data_by_type(
                object_type,
                bazaar, original_pk, data.validated_data, now
            )

            receipt = Receipt.objects.create(
                user=request.user,
                bazaar=bazaar,
                object_type=object_type,
                object_id=object_pk,
                amount=amount,
                data=extra_data,
                status=Receipt.STATUS_NEW,
                added_at=now,
            )

        ofd_data = self.OFD_DATA.get(object_type, {})
        vat_k = 1 + bazaar.vat_percent / 100
        amount_tiyin = receipt.amount * 100

        return Response({
            "id": receipt.id,
            "print_info": print_info,
            "cash_amount": amount_tiyin,
            "card_amount": 0,
            "time": f"{now:%Y-%m-%d %H:%M:%S}",
            "avval": {
                "services": [],
                "method": "sale-services",
                "sale": True,
                "service_id": "Vr80ztkEp1RDJAm1dRxzWsKyQT42d0zr",
                "user_id": 12,
                "check_number": receipt.id,
                "check_id": str(receipt.id),
                "barcode": "",
                "type": "sale"
            },
            "items": [{
                "price": amount_tiyin,
                "discount": 0,
                "barcode": "",
                "vat_percent": bazaar.vat_percent,
                "vat": int(amount_tiyin - amount_tiyin / vat_k),
                "package_code": "",
                "other": 0,
                "commission_info": {
                    "tin": "",
                    "pinfl": ""
                },
                "amount": 1,
                "owner_type": 0,

                "label": "",
                "name": self.OBJECT_NAME.get(object_type, f"Object-{object_type}"),

                # "spic": "",
                # "units": 0,
                **ofd_data
            }]
        })

    @classmethod
    def get_object_data_by_type(cls, object_type, *args, **kwargs):
        if object_type == Receipt.OBJECT_TYPE_STALL:
            return get_stall_data_by_type(*args, **kwargs)
        elif object_type == Receipt.OBJECT_TYPE_SHOP:
            return get_shop_data_by_type(*args, **kwargs)
        elif object_type == Receipt.OBJECT_TYPE_RENT:
            return get_rent_data_by_type(*args, **kwargs)
        elif object_type == Receipt.OBJECT_TYPE_PARKING:
            return get_parking_data_by_type(*args, **kwargs)

        return 0, 0, dict(), []


class ReceiptSaveView(APIView):
    def post(self, request):
        data = ReceiptSaveSerializer(data=request.data, many=True)
        if not data.is_valid():
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            for row in data.data:
                try:
                    receipt = Receipt.objects.select_for_update().filter(
                        bazaar_id=request.auth.bazaar_id,
                        id=row["id"]
                    ).get()
                except Receipt.DoesNotExist:
                    continue

                if receipt.status > 0:
                    continue

                if row["ofd_status"] == 1:
                    receipt.status = 1
                    receipt.ofd_link = row["ofd_link"]
                    receipt.ofd_time = row["ofd_time"]
                else:
                    receipt.status = 2
                receipt.save()

                if receipt.object_type == Receipt.OBJECT_TYPE_STALL:
                    if receipt.status == 1:
                        save_stall(receipt.object_id, receipt.data)
                    else:
                        cancel_stall(receipt.object_id, receipt.data)
                elif receipt.object_type == Receipt.OBJECT_TYPE_SHOP:
                    if receipt.status == 1:
                        save_shop(receipt.object_id, receipt.data)
                    else:
                        cancel_shop(receipt.object_id, receipt.data)
                elif receipt.object_type == Receipt.OBJECT_TYPE_RENT:
                    if receipt.status == 1:
                        save_rent(receipt.object_id, receipt.data)
                    else:
                        cancel_rent(receipt.object_id, receipt.data)
                elif receipt.object_type == Receipt.OBJECT_TYPE_PARKING:
                    if receipt.status == 1:
                        save_parking(receipt.object_id, receipt.data)
                    else:
                        cancel_parking(receipt.object_id, receipt.data)

        return Response({})

