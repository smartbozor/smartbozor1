from django.contrib import admin

from apps.rent.models import Thing, ThingData


@admin.register(Thing)
class ThingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name_uz', )


@admin.register(ThingData)
class ThingDataAdmin(admin.ModelAdmin):
    list_select_related = ('thing', 'bazaar', )
    list_display = ('id', 'thing', 'bazaar', 'count', 'price')
    list_filter = ('bazaar', 'thing')
    autocomplete_fields = ('thing', 'bazaar')
