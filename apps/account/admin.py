from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.account.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    filter_horizontal = BaseUserAdmin.filter_horizontal + ('allowed_bazaar', )

    fieldsets = BaseUserAdmin.fieldsets + (
        (_("Qo'shimcha"), {'fields': ('allowed_bazaar',)}),
    )

    # Agar yangi foydalanuvchi qo‘shayotgan bo‘lsangiz, u yerga ham qo‘shish kerak
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_("Huquqi"), {
            "classes": "wide",
            "fields": ("groups", )
        }),
        (_("Qo'shimcha"), {
            'classes': ('wide',),
            'fields': ('allowed_bazaar',),
        }),
    )

    list_display = BaseUserAdmin.list_display + ('is_superuser', )

