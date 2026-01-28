from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RestroomConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.restroom'
    verbose_name = _("Hojatxona")
    verbose_name_plural = _("Hojatxonalar")
