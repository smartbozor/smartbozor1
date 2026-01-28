from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.restroom.models import Restroom


@admin.register(Restroom)
class RestroomAdmin(admin.ModelAdmin):
    list_select_related = ('bazaar__district__region', )
    list_display = ('id', 'get_address', 'number')
    autocomplete_fields = ('bazaar',)
    search_fields = ('number',)

    def get_address(self, obj, *args):
        return " » ".join([
            str(obj.bazaar.district.region),
            str(obj.bazaar.district),
            str(obj.bazaar),
            *args
        ])

    get_address.short_description = _("Joylashgan joyi")
