from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rent'
    verbose_name = _("Ijaraga buyum")
    verbose_name_plural = _("Ijaraga buyumlar")
