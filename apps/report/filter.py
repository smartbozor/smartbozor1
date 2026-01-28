import datetime

from django import forms
from django.utils import timezone
import django_filters
from apps.payment.models import Click


class ClickFilter(django_filters.FilterSet):
    s = django_filters.DateFilter(
        field_name="complete_time",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    e = django_filters.DateFilter(
        field_name="complete_time",
        lookup_expr="lt",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )

    @staticmethod
    def default_month_range():
        today = timezone.now().date()
        start = today.replace(day=1)

        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end = today.replace(month=today.month + 1, day=1)

        return start, end

    def filter_queryset(self, queryset):
        start_date = self.form.cleaned_data.get("s")
        end_date = self.form.cleaned_data.get("e")

        if not start_date and not end_date:
            start, end = self.default_month_range()
            queryset = queryset.filter(
                complete_time__gte=start,
                complete_time__lt=end
            )
        else:
            queryset = super().filter_queryset(queryset)

        return queryset.filter(status=1)

    class Meta:
        model = Click
        fields = ["s", "e"]
