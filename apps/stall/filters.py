import datetime

import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.stall.models import Stall, StallStatus


class StallFilter(django_filters.FilterSet):
    number = django_filters.CharFilter(
        field_name='number',
        label="",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Rasta raqami')}),
    )
    is_paid = django_filters.BooleanFilter(
        field_name='is_paid_today',
        widget=forms.Select(
            choices=[
                ('', _('Barchasi')),
                ('true', _("To'langanlar")),
                ('false', _("To'lanmaganlar"))
            ],
            attrs={'class': 'form-control'}
        ),
    )

    class Meta:
        model = Stall
        fields = ['number']


class StallStatusFilter(django_filters.FilterSet):
    number = django_filters.CharFilter(
        field_name='stall__number',
        lookup_expr='icontains',
        label="",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Rasta raqami')}),
    )

    date = django_filters.DateFilter(
        field_name='date',
        label="",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Sana'), 'type': 'date'}),
    )

    def __init__(self, *args, **kwargs):
        data = kwargs.get('data', None)
        if data is None:
            data = {}
        else:
            data = {k: v for k, v in data.items()}

        if 'date' not in data:
            data['date'] = datetime.date.today()

        kwargs['data'] = data
        super().__init__(*args, **kwargs)

    class Meta:
        model = StallStatus
        fields = ['date', 'number']
