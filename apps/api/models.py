import os
import uuid

import binascii
from django.conf import settings
from django.db import models
from rest_framework.authtoken.models import Token

from apps.account.models import User
from apps.main.models import Bazaar


class DeviceToken(models.Model):
    key = models.CharField(max_length=40, primary_key=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="device_tokens",
        on_delete=models.CASCADE
    )
    bazaar = models.ForeignKey(Bazaar, on_delete=models.RESTRICT, default=1)
    device_id = models.UUIDField(default=uuid.uuid4, editable=False)
    pin = models.CharField(max_length=128, editable=False, null=True, default=None)
    pin_attempt = models.JSONField(default=dict, editable=False)
    name = models.CharField(max_length=64, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True, editable=False)
    is_active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["device_id", "user"], name="uniq_user_device"),
        ]
        indexes = [
            models.Index(fields=["device_id", "user"]),
        ]

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    @staticmethod
    def generate_key():
        return binascii.hexlify(os.urandom(20)).decode()

