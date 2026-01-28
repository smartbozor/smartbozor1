from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.api.models import DeviceToken



@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    actions = ["reset_lock"]
    list_select_related = ("user",)
    list_display = ('user', 'device_id', 'pin_attempt', 'name', 'created', 'last_used', 'is_active')

    @admin.action(description=_("Qurilmani ochish"))
    def reset_lock(self, request, queryset):
        queryset.update(pin_attempt=dict())
