import base64
from types import SimpleNamespace

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class SingleUserBasicAuthentication(BaseAuthentication):
    username = "username"
    password = "password"

    def authenticate(self, request):
        auth = request.headers.get("Authorization")

        if not auth or not auth.startswith("Basic "):
            raise AuthenticationFailed("Invalid credentials")

        try:
            encoded = auth.split(" ")[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":")

            # Bitta foydalanuvchi credential tekshirish
            if username == self.username and password == self.password:
                return SimpleNamespace(
                    username=username,
                    is_authenticated=True,
                ), None
        except:
            pass

        raise AuthenticationFailed("Invalid credentials")


def make_basic_authentication(username, password):
    class _BasicAuth(SingleUserBasicAuthentication):
        pass

    _BasicAuth.username = username
    _BasicAuth.password = password
    return _BasicAuth

