from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.main.models import Bazaar
from apps.shop.models import Shop, ShopStatus, ShopPayment


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_select_related = ('section__area__bazaar__district__region', )
    list_display = ('id', 'get_address', 'number', 'rent_price', 'is_active')
    autocomplete_fields = ('section', )
    list_filter = ('section__area__bazaar',)
    search_fields = ('id', )

    def get_address(self, obj):
        return " » ".join([
            str(obj.section.area.bazaar.district.region),
            str(obj.section.area.bazaar.district),
            str(obj.section.area.bazaar),
            str(obj.section.area),
            str(obj.section),
        ])

    get_address.short_description = _("Joylashgan joyi")


# @admin.register(ShopStatus)
# class ShopStatusAdmin(admin.ModelAdmin):
#     list_select_related = ('shop',)
#     list_display = ('id', 'shop', 'date', 'rent_price', 'is_occupied', 'occupied_at')
#     search_fields = ('shop__number', )
#     autocomplete_fields = ('shop',)
#
#
# @admin.register(ShopPayment)
# class ShopPaymentAdmin(admin.ModelAdmin):
#     list_select_related = ('shop',)
#     list_display = ('id', 'shop', 'date', 'payment_method', 'amount', 'paid_at')
#     search_fields = ('shop__number', )
#     autocomplete_fields = ('shop', )
#
#     def has_add_permission(self, request, obj: ShopPayment = None):
#         return False
#
#     def has_change_permission(self, request, obj: ShopPayment = None):
#         if not obj:
#             return super().has_change_permission(request, obj)
#
#         return obj.payment_method == Bazaar.PAYMENT_METHOD_CASH
#
#     def has_delete_permission(self, request, obj: ShopPayment = None):
#         if not obj:
#             return super().has_delete_permission(request, obj)
#
#         return obj.payment_method == Bazaar.PAYMENT_METHOD_CASH
#

