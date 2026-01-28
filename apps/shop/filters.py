import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.shop.models import Shop


class ShopFilter(django_filters.FilterSet):
    number = django_filters.CharFilter(
        field_name='number',
        label="",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Do'kon raqami")}),
    )

    class Meta:
        model = Shop
        fields = ['number']