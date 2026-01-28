from django.urls import re_path

from apps.camera.views_ws import CameraTunnel

urlpatterns = [
    re_path(r"^ws/camera/tunnel/(?P<camera_id>\d+)/$", CameraTunnel.as_asgi(), name="camera-tunnel")
]