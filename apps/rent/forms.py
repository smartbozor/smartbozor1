from django import forms


class ThingCashForm(forms.Form):
    number = forms.IntegerField()
