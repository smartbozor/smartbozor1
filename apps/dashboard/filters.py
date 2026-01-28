import django_filters
from dateutil.relativedelta import relativedelta
from django.utils import timezone


class MonthFilter(django_filters.FilterSet):
    n = django_filters.CharFilter(
        method='filter_month'
    )

    d = django_filters.CharFilter(
        method='filter_day'
    )

    def __init__(self, *args, apply_d=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_d = apply_d

    def filter_month(self, queryset, name, value):
        n = 0
        try:
            n = int(value)
        except:
            pass

        start = timezone.localtime().date().replace(day=1) + relativedelta(months=n)

        return queryset.filter(
            date__gte=start,
            date__lt=start + relativedelta(months=1)
        )

    def filter_day(self, queryset, name, value):
        if not self.apply_d:
            return queryset

        ds, de = 0, 0
        try:
            ds, de = map(int, value.split("-"))
        except:
            pass

        if ds > 0 and de > 0:
            return queryset.filter(
                date__day__range=(ds, de)
            )
        elif ds > 0:
            return queryset.filter(
                date__day=ds
            )

        return queryset



