from django import forms
from django.utils.translation import gettext_lazy as _

from apps.main.models import Bazaar


class BazaarForm(forms.ModelForm):
    working_days = forms.MultipleChoiceField(
        choices=[(str(v), lbl) for v, lbl in Bazaar.DAY_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=Bazaar._meta.get_field("working_days").verbose_name,
    )

    payment_methods = forms.MultipleChoiceField(
        choices=[(str(v), lbl) for v, lbl in Bazaar.PAYMENT_METHOD_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=Bazaar._meta.get_field("payment_methods").verbose_name,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            val = self.instance.working_days or 0
            self.initial['working_days'] = [
                str(v) for v, _ in Bazaar.DAY_CHOICES if val & v
            ]

        if self.instance and self.instance.pk:
            val = self.instance.payment_methods or 0
            self.initial["payment_methods"] = [
                str(v) for v, _ in Bazaar.PAYMENT_METHOD_CHOICES if val & v
            ]

    def clean_working_days(self):
        selected = self.cleaned_data.get("working_days", [])
        result = 0
        for v in selected:
            result |= int(v)
        return result

    def clean_payment_methods(self):
        selected = self.cleaned_data.get("payment_methods", [])
        result = 0
        for v in selected:
            result |= int(v)
        return result

    class Meta:
        model = Bazaar
        fields = '__all__'
