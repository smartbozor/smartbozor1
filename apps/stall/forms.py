from django import forms

from apps.stall.models import Stall


class StallCashForm(forms.Form):
    stall = forms.ModelChoiceField(queryset=Stall.objects.all())
