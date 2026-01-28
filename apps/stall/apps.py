from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StallConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.stall'
    verbose_name = _("Rasta")
    verbose_name_plural = _("Rastalar")