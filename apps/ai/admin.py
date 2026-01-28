from django.contrib import admin

from apps.ai.models import StallOccupation


@admin.register(StallOccupation)
class StallOccupationAdmin(admin.ModelAdmin):
    list_select_related = ('camera', )
    list_display = ("id", "camera", "roi_id", "state", "check_at")
    list_filter = ("state",)
