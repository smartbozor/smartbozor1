import hashlib
import json
import os

import requests
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from apps.camera.models import Camera
from apps.camera.tasks import update_camera_info, run_update_camera_info


@receiver(pre_save, sender=Camera)
def before_camera_saved(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_values = None
    else:
        try:
            old = Camera.objects.get(pk=instance.pk)
            instance._old_values = {f.name: getattr(old, f.name) for f in instance._meta.fields}
            instance._old_values["roi"] = hashlib.sha256((json.dumps(old.roi) if old.roi else '').encode()).hexdigest()
        except Camera.DoesNotExist:
            instance._old_values = None


@receiver(post_save, sender=Camera)
def after_camera_saved(instance, **kwargs):
    if not instance._old_values:
        return

    changed = {}
    for f in instance._meta.fields:
        field_name = f.name
        old = instance._old_values.get(field_name)
        new = getattr(instance, field_name)
        if field_name == "roi":
            new = hashlib.sha256((json.dumps(new) if new else '').encode()).hexdigest()

        if old != new:
            changed[field_name] = {"old": old, "new": new}

    fields = {'username', 'password', 'roi', 'camera_port', 'use_ai'}
    if fields & set(changed.keys()):
        run_update_camera_info(instance.pk)

