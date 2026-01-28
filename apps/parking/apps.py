from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ParkingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.parking'
    verbose_name = _("Avtoturargoh")
    verbose_name_plural = _("Avtoturargohlar")

    def ready(self):
        from apps.parking import signals

