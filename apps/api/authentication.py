import datetime

from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import DeviceToken


class DeviceTokenAuthentication(TokenAuthentication):
    model = DeviceToken
    check_pin = True

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.select_related("user").get(key=key)
        except self.model.DoesNotExist:
            raise AuthenticationFailed("invalid_token")

        token.last_used = timezone.localtime()
        token.save(update_fields=["last_used"])

        if not token.user.is_active:
            raise AuthenticationFailed("user_inactive")

        if not token.is_active:
            raise AuthenticationFailed("token_inactive")

        if self.check_pin and not token.pin:
            raise AuthenticationFailed("pin_empty")

        lock_until = token.pin_attempt.get("lock_until", 0) or 0
        utc_timestamp = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())

        if lock_until > utc_timestamp:
            raise AuthenticationFailed(f"lock_until_{lock_until}")

        return token.user, token


class DeviceTokenAuthenticationNoPin(DeviceTokenAuthentication):
    check_pin = False
