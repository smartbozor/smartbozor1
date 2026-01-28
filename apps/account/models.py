from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.main.models import Bazaar


class User(AbstractUser):
    allowed_bazaar = models.ManyToManyField(Bazaar, verbose_name=_("Ruxsat berilgan bozorlar"), blank=True)

