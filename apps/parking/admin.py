import datetime

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.parking.forms import ParkingWhitelistForm, ParkingPriceForm, ParkingPriceFormSet
from apps.parking.models import Parking, ParkingPrice, ParkingCamera, ParkingWhitelist


class ParkingPriceInline(admin.TabularInline):
    form = ParkingPriceForm
    formset = ParkingPriceFormSet
    model = ParkingPrice
    extra = 0
    min_num = 1
    ordering = ("duration",)


@admin.register(Parking)
class ParkingAdmin(admin.ModelAdmin):
    inlines = [ParkingPriceInline]
    list_select_related = ('bazaar__district__region', )
    list_display = ('id', 'get_address', 'name', 'billing_mode', 'save_image')
    autocomplete_fields = ('bazaar',)
    search_fields = ('name_uz',)

    def get_search_results(self, request, queryset, search_term):
        if request.headers.get("x-requested-with") != "XMLHttpRequest":
            return super().get_search_results(request, queryset, search_term)

        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        object_list = list(queryset.all())
        for row in object_list:
            row.display_name = self.get_address(row, str(row))

        return object_list, use_distinct

    def get_address(self, obj, *args):
        return " » ".join([
            str(obj.bazaar.district.region),
            str(obj.bazaar.district),
            str(obj.bazaar),
            *args
        ])

    get_address.short_description = _("Joylashgan joyi")


@admin.register(ParkingCamera)
class ParkingCameraAdmin(admin.ModelAdmin):
    list_select_related = ('parking__bazaar__district__region', )
    list_display = ('get_address', 'get_role_display', 'mac', 'get_callback_link')
    autocomplete_fields = ('parking',)

    @admin.display(description="Address")
    def get_address(self, obj):
        return " » ".join([
            str(obj.parking.bazaar.district.region),
            str(obj.parking.bazaar.district),
            str(obj.parking.bazaar),
            str(obj.parking),
        ])

    @admin.display(description="Callback link")
    def get_callback_link(self, obj):
        action = "enter" if obj.role == ParkingCamera.ROLE_ENTER else "exit"
        link = f"https://smart-bozor.uz/parking/{action}/{obj.token}/"
        return format_html(
            "<a href='{0}' data-clipboard='{1}' target='_blank'>{2}</a>",
            link,
            link,
            "Copy"
        )

    class Media:
        js = ('js/data-clipboard.min.js',)


@admin.register(ParkingWhitelist)
class ParkingWhitelistAdmin(admin.ModelAdmin):
    form = ParkingWhitelistForm
    list_select_related = ('bazaar__district__region', )
    list_display = ('id', 'region', 'district', 'bazaar', 'pattern')
    autocomplete_fields = ('region', 'district', 'bazaar')
