from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.stall.models import Stall


@admin.register(Stall)
class StallAdmin(admin.ModelAdmin):
    list_select_related = ('section__area__bazaar__district__region', )
    list_display = ('id', 'get_address', 'number', 'price')
    autocomplete_fields = ('section', )
    list_filter = ('section__area__bazaar', )

    def get_address(self, obj):
        return " » ".join([
            str(obj.section.area.bazaar.district.region),
            str(obj.section.area.bazaar.district),
            str(obj.section.area.bazaar),
            str(obj.section.area),
            str(obj.section),
        ])

    get_address.short_description = _("Joylashgan joyi")
