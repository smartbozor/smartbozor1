from django.contrib import admin

from apps.payment.models import Point, PointProduct


@admin.register(Point)
class PointAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'click_service_id', 'slug', 'status')
    search_fields = ('name', )
    autocomplete_fields = ('district', )


@admin.register(PointProduct)
class PointProductAdmin(admin.ModelAdmin):
    list_select_related = ('point',)
    list_display = ('id', 'point', 'fee_price', 'fee_percent', 'fee_included', 'price', 'status')
    list_filter = ('point', 'status')
    autocomplete_fields = ('point',)
