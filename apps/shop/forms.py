from django import forms

from apps.shop.models import Shop


class ShopCashForm(forms.Form):
    shop = forms.ModelChoiceField(queryset=Shop.objects.all())
    amount = forms.IntegerField(min_value=1)
