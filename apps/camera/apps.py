from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CameraConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.camera'
    verbose_name = _("Kamera")
    verbose_name_plural = _("Kameralar")

    def ready(self):
        import apps.camera.signals
