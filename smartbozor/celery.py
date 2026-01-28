import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbozor.settings')

app = Celery('smartbozor')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.timezone = settings.TIME_ZONE
app.conf.enable_utc = False
app.conf.broker_connection_retry_on_startup = True

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
