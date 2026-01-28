import re

from django.contrib.admin.utils import lookup_field
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.stall.models import Stall


class CameraRoiPointSerializer(serializers.Serializer):
    x = serializers.IntegerField()
    y = serializers.IntegerField()


class CameraRoiSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.IntegerField(required=True)
    value = serializers.CharField(min_length=1, required=True)
    points = CameraRoiPointSerializer(many=True)

    PATTERNS = {
        0: Stall.NUMBER_PATTERN
    }

    def validate(self, attrs):
        typ = attrs.get('type')
        if typ in self.PATTERNS and not re.match(self.PATTERNS[typ], attrs.get("value", "")):
            raise ValidationError({
                "value": _("Qiymat noto'g'ri kritilgan")
            })

        return attrs

class DeviceInfo(serializers.Serializer):
    device_sn = serializers.CharField(required=True)
    mac = serializers.CharField(required=True)
    ip = serializers.CharField(required=True, source='ip_v4_address')
    is_online = serializers.BooleanField(required=False, default=False)
