from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import APIException


class AlreadyPaidException(APIException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE

    def __init__(self):
        super().__init__(_("Allaqachon to'langan"))


class ProcessAlreadyInProgressException(APIException):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self):
        super().__init__(_("To‘lov qabul qilinmoqda..."))
