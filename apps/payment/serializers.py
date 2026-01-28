import hashlib
from decimal import Decimal

from django.conf import settings
from rest_framework import serializers


class PaymeCheckPerformTransactionParamsSerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    account = serializers.JSONField()


class PaymeCreateTransactionParamsSerializer(serializers.Serializer):
    id = serializers.CharField()
    time = serializers.IntegerField()
    amount = serializers.IntegerField()
    account = serializers.JSONField()


class PaymePerformTransactionParamsSerializer(serializers.Serializer):
    id = serializers.CharField()


class PaymeCancelTransactionParamsSerializer(serializers.Serializer):
    id = serializers.CharField()
    reason = serializers.IntegerField()


class PaymeCheckTransactionParamsSerializer(serializers.Serializer):
    id = serializers.CharField()


class PaymeGetStatementParamsSerializer(serializers.Serializer):
    from_ = serializers.IntegerField()
    to_ = serializers.IntegerField()


class PaymeFiscalDataSerializer(serializers.Serializer):
    receipt_id = serializers.IntegerField()
    status_code = serializers.IntegerField()
    message = serializers.CharField()
    terminal_id = serializers.CharField()
    fiscal_sign = serializers.CharField()
    qr_code_url = serializers.CharField()
    date = serializers.CharField()


class PaymeSetFiscalDataParamsSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    fiscal_data = PaymeFiscalDataSerializer


class PaymentSerializer(serializers.Serializer):
    METHOD_PARAMS = {
        "CheckPerformTransaction": PaymeCheckPerformTransactionParamsSerializer,
        "CreateTransaction": PaymeCreateTransactionParamsSerializer,
        "PerformTransaction": PaymePerformTransactionParamsSerializer,
        "CancelTransaction": PaymeCancelTransactionParamsSerializer,
        "CheckTransaction": PaymeCheckTransactionParamsSerializer,
        "GetStatement": PaymeGetStatementParamsSerializer,
        "SetFiscalData": PaymeSetFiscalDataParamsSerializer,
    }

    jsonrpc = serializers.CharField()
    id = serializers.IntegerField()
    method = serializers.ChoiceField(choices=[
        (a, a) for a, b in METHOD_PARAMS.items()
    ])
    params = serializers.DictField(required=False, default=dict)

    def __init__(self, bazaar, *args, **kwargs):
        self.bazaar = bazaar
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        method = attrs.get("method")
        params = attrs.get("params") or {}

        ParamsSer = self.METHOD_PARAMS.get(method)
        if not ParamsSer:
            raise serializers.ValidationError(
                {"method": f"Unsupported method: {method}"}
            )

        if method == "GetStatement":
            params = {
                "from_": params.get("from", None),
                "to_": params.get("to", None),
            }

        ps = ParamsSer(data=params, context=self.context)
        ps.is_valid(raise_exception=True)
        params = ps.validated_data
        if "amount" in params:
            params["amount"] //= 100

        attrs["validated_params"] = params
        return attrs


class ClickSerializer(serializers.Serializer):
    ACTION_PREPARE = 0
    ACTION_COMPLETE = 1

    click_trans_id = serializers.IntegerField()
    service_id = serializers.IntegerField()
    click_paydoc_id = serializers.IntegerField()
    merchant_trans_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    action = serializers.IntegerField()
    error = serializers.IntegerField()
    error_note = serializers.CharField(allow_blank=True)
    sign_time = serializers.CharField()
    sign_string = serializers.CharField()

    merchant_prepare_id = serializers.IntegerField(required=False)

    def __init__(self, bazaar, **kwargs):
        self.bazaar = bazaar
        super().__init__(**kwargs)

    def validate_action(self, value):
        if value not in (0, 1):
            raise serializers.ValidationError("Action must be 0 or 1")
        return value

    def validate_service_id(self, value):
        if value != self.bazaar.click_service_id:
            raise serializers.ValidationError("Service wrong")
        return value

    def validate(self, attrs):
        action = attrs.get("action")

        amount = attrs.get("amount") # type: Decimal
        if amount == amount.to_integral_value():
            attrs["amount"] = int(amount)

        if action == self.ACTION_PREPARE:
            attrs["method"] = "prepare"
        else:
            attrs["method"] = "complete"

            if "merchant_prepare_id" not in attrs:
                raise serializers.ValidationError({
                    "merchant_prepare_id": "This field is required when action=1 (Complete)."
                })

        if attrs["sign_string"].lower() != self.sign(action, attrs).lower():
            if settings.DEBUG:
                print(self.sign(action, attrs))
            raise serializers.ValidationError("Incorrect signature")

        attrs["amount"] = int(attrs["amount"])
        attrs["validated_params"] = attrs
        return attrs

    def sign(self, action, attrs):
        if action == 0:
            return hashlib.md5(f"{attrs['click_trans_id']}{attrs['service_id']}{self.bazaar.click_secret_key}{attrs['merchant_trans_id']}{attrs['amount']}{attrs['action']}{attrs['sign_time']}".encode("utf-8")).hexdigest()
        else:
            return hashlib.md5(f"{attrs['click_trans_id']}{attrs['service_id']}{self.bazaar.click_secret_key}{attrs['merchant_trans_id']}{attrs['merchant_prepare_id']}{attrs['amount']}{attrs['action']}{attrs['sign_time']}".encode("utf-8")).hexdigest()

