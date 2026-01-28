from django.core.validators import RegexValidator
from rest_framework import serializers

from apps.account.models import User
from apps.main.models import Bazaar


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    device_id = serializers.UUIDField()


class PinSerializer(serializers.Serializer):
    pin = serializers.CharField(required=True, validators=[
        RegexValidator(regex=r'^[0-9]{4}$',)
    ])


class BazaarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bazaar
        fields = ('id', 'name')


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name')


class ReceiptStallSerializer(serializers.Serializer):
    stall_id = serializers.IntegerField()


class ReceiptShopSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1_000, max_value=10_000_000)


class ReceiptRentSerializer(serializers.Serializer):
    number = serializers.IntegerField()


class ReceiptParkingSerializer(serializers.Serializer):
    price_id = serializers.IntegerField()


class ReceiptSaveSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ofd_status = serializers.IntegerField(min_value=1)
    ofd_link = serializers.URLField(allow_null=True, required=False)
    ofd_time = serializers.IntegerField()
