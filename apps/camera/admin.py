import os

import requests
from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render, resolve_url
from django.urls import path
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.camera.forms import CameraUpdateAuthForm
from apps.camera.models import Camera


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_select_related = ('bazaar', )
    list_display = ('id', 'bazaar', 'name', 'camera_ip', 'camera_port', 'username', 'is_active', 'use_ai', 'is_online', "get_snapshot_url")
    autocomplete_fields = ('bazaar', )
    list_filter = ('bazaar', )
    actions = ["update_auth", "update_active", "update_inactive"]

    @admin.display(description="Snapshot")
    def get_snapshot_url(self, obj):
        return format_html(
            '<a href="{0}" target="_blank">Snapshot</a>',
            resolve_url("admin:camera-snapshot", obj.pk)
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("change-auth/", self.admin_site.admin_view(self.update_camera_auth_view), name="update-camera-auth"),
            path("snapshot/<int:pk>/", self.admin_site.admin_view(self.camera_snapshot_view), name="camera-snapshot"),
        ]
        return custom_urls + urls

    @admin.action(description=_("Tanlangan kamera login/parollarini almashtirish"))
    def update_auth(self, request, queryset):
        selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
        return redirect(f"change-auth/?ids={','.join(selected)}")

    @admin.action(description=_("Faollashtirish"))
    def update_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description=_("Nofaollashtirish"))
    def update_inactive(self, request, queryset):
        queryset.update(is_active=False)

    def update_camera_auth_view(self, request):
        try:
            ids = map(int, request.GET.get("ids", "").split(","))
        except ValueError:
            return redirect("/")

        cameras = Camera.objects.order_by('camera_ip').filter(id__in=ids).all()
        if len(cameras) == 0:
            return redirect("/")

        if request.method == "POST":
            form = CameraUpdateAuthForm(data=request.POST)
            if form.is_valid():
                with transaction.atomic():
                    for camera in cameras:
                        camera.username = form.cleaned_data["username"]
                        camera.password = form.cleaned_data["password"]
                        # trigger ishlashi uchun
                        camera.save()

                messages.success(request, _("Muvaffaqiyatli saqlandi."))
        else:
            form = CameraUpdateAuthForm()

        context = {
            "form": form,
            "cameras": cameras,
        }
        return render(request, "admin/update_camera_auth.html", context)

    def camera_snapshot_view(self, request, pk):
        if not request.user.has_perm("camera.view_camera"):
            raise PermissionDenied

        access_token = os.environ.get("CONTROL_ACCESS_TOKEN")

        try:
            camera = Camera.objects.get(id=pk)
        except Camera.DoesNotExist:
            messages.error(request, _("Kamera mavjud emas"))
            return redirect("admin:camera_camera_changelist")

        try:
            snapshot_url = f"http://{camera.bazaar.server_ip}:1984/api/snapshot/{camera.device_sn}"
            response = requests.get(snapshot_url, headers={
                "Authorization": f"Bearer {access_token}"
            }, timeout=10)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "image/jpeg")
            return HttpResponse(response.content, content_type=content_type)
        except Exception as e:
            messages.error(request, str(e))
            return redirect("admin:camera_camera_changelist")

    def has_add_permission(self, request):
        return False

