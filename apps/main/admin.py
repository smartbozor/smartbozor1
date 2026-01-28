from django.conf import settings
from django.contrib import admin
from django.template.context_processors import request
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.main.forms import BazaarForm
from apps.main.models import Region, District, Bazaar, Area, Section


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    search_fields = ('name_uz',)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_select_related = ('region',)
    list_display = ('id', 'region', 'name')
    autocomplete_fields = ('region',)
    list_filter = ('region',)
    search_fields = ('name_uz',)


@admin.register(Bazaar)
class BazaarAdmin(admin.ModelAdmin):
    form = BazaarForm
    list_select_related = ('district__region',)
    list_display = ('id', 'get_address', 'name', 'get_working_days', 'get_payment_methods', 'get_qr_codes_link',
                    'click_enabled', 'payme_enabled', 'get_slug', 'server_ip', 'server_port', 'is_online')
    autocomplete_fields = ('district',)
    search_fields = ('name_uz',)

    @admin.display(description="Callback link")
    def get_slug(self, obj):
        return format_html(
            "<a href='#' data-clipboard='{0}'>{1}</a>",
            f"https://smart-bozor.uz/payment/click/{obj.slug}/",
            obj.slug,
        )

    @admin.display(boolean=True, description="Click")
    def click_enabled(self, obj):
        return obj.is_allow_click

    @admin.display(boolean=True, description="Payme")
    def payme_enabled(self, obj):
        return obj.is_allow_payme

    def get_qr_codes_link(self, obj):
        links = []
        titles = [
            (obj.stall_pdf, _("Rastalar")),
            (obj.shop_pdf, _("Do'konlar")),
            (obj.rent_pdf, _("Ijara buyumlari")),
            (obj.parking_pdf, _("Avtoturargoh")),
        ]
        for pdf, title in titles:
            if pdf:
                links.append(format_html('<a href="{}" target="_blank">{}</a>', pdf.url, title))

        return format_html(" | ".join(links))

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
            str(obj.district.region),
            str(obj.district),
            *args
        ])

    def get_working_days(self, obj):
        return ", ".join(obj.working_days_display)

    def get_payment_methods(self, obj):
        return ", ".join(obj.payment_methods_display)

    get_address.short_description = _("Manzil")
    get_working_days.short_description = Bazaar._meta.get_field("working_days").verbose_name
    get_payment_methods.short_description = Bazaar._meta.get_field("payment_methods").verbose_name

    class Media:
        js = ('js/data-clipboard.min.js',)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_select_related = ('bazaar__district__region',)
    list_display = ('id', 'get_address', 'name')
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


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_select_related = ('area__bazaar__district__region',)
    list_display = ('id', 'get_address', 'name')
    autocomplete_fields = ('area',)
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
            str(obj.area.bazaar.district.region),
            str(obj.area.bazaar.district),
            str(obj.area.bazaar),
            str(obj.area),
            *args
        ])

    get_address.short_description = _("Joylashgan joyi")
