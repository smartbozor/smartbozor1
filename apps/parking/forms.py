import re

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _

from apps.parking.models import ParkingWhitelist, ParkingStatus, Parking, ParkingPrice


class ParkingPriceForm(forms.ModelForm):
    def clean_duration(self):
        duration = self.cleaned_data['duration']

        if duration % 60 != 0:
            raise ValidationError(_("Vaqt 60 ga karrali bo'lishi lozim"))

        return duration

    def clean_price(self):
        price = self.cleaned_data['price']
        if price % 1000 != 0:
            raise ValidationError(_("Narx 1000 ga karrali bo'lishi lozim"))

        return price

    class Meta:
        model = ParkingPrice
        fields = '__all__'


class ParkingPriceFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        total_forms = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                total_forms += 1

        if total_forms < 1:
            raise ValidationError(_("Kamida bitta narx kiritilishi lozim"))

        pairs = [
            (form.cleaned_data.get("duration", 0), form.cleaned_data.get("price", 0), form) for form in self.forms
        ]

        # pairs.sort(key=lambda pair: pair[0])

        for (d, p, __), (nd, np, form) in zip(pairs[:-1], pairs[1:]):
            if d == nd:
                form.add_error("duration", _("Qiymat takrorlangan"))
            elif d > nd:
                form.add_error("duration", _("Qiymat oldingisidan katta bo'lishi lozim"))

            if p == np:
                form.add_error("price", _("Qiymat takrorlangan"))
            elif p > np:
                form.add_error("price", _("Qiymat oldingisidan katta bo'lishi lozim"))




class ParkingWhitelistForm(forms.ModelForm):
    def clean(self):
        data = super().clean()
        region, district, bazaar = data.get('region', None), data.get('district', None), data.get('bazaar', None)

        if sum([bool(region), bool(district), bool(bazaar)]) != 1:
            raise ValidationError({
                "bazaar": _("Viloyat, tuman, bozor uchalasidan bittasi kiritilishi lozim")
            })

        if not self.has_error("pattern"):
            pattern = data['pattern']
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValidationError({
                    "pattern": str(e)
                })

        return data

    class Meta:
        model = ParkingWhitelist
        fields = '__all__'


class ParkingCashForm(forms.Form):
    status = forms.ModelChoiceField(queryset=ParkingStatus.objects.all(), required=False)
    parking = forms.ModelChoiceField(queryset=Parking.objects.all(), required=False)
    amount = forms.IntegerField(required=False, min_value=0)
    order_id = forms.IntegerField(required=False)

