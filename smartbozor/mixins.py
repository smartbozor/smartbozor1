import calendar
import datetime

from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.utils.formats import date_format

from smartbozor.helpers import normalize_d


class NormalizeDataMixin:
    @classmethod
    def date_range(cls, data, use_utc=False):
        date = timezone.now().date() if use_utc else timezone.localtime().date()
        today = date.replace(day=1) + relativedelta(months=data["n"])

        ds, de = map(int, data["d"].split("-"))
        if ds > 0 and de > 0:
            start = today.replace(day=ds)
            end = today.replace(day=de) + datetime.timedelta(days=1)
        elif ds > 0:
            start = today.replace(day=ds)
            end = start + datetime.timedelta(days=1)
        else:
            start = today
            end = start + relativedelta(months=1)

        return start, end

    @classmethod
    def month_days(cls, month):
        return calendar.monthrange(month.year, month.month)[1]

    @classmethod
    def normalize_data(cls, data):
        n, ds, de = 0, 0, 0
        try:
            n = int(data.get("n", 0))
        except:
            pass

        today = timezone.localtime().today().date().replace(day=1)
        month = today + relativedelta(months=n)

        ds, de = normalize_d(data, month.year, month.month)

        months = []
        for i in range(-4, 5):
            m = today + relativedelta(months=n + i)
            months.append({
                "n": n + i,
                "name": date_format(m, "F Y")
            })

        data["n"] = n
        data["d"] = f"{ds}-{de}"

        data["range_title"] = ""
        if ds == 0 and de == 0:
            data["range_title"] = date_format(month, "F Y")
        elif ds > 0 and de == 0:
            data["range_title"] = date_format(month.replace(day=ds), "j-F Y")
        else:
            data["range_title"] = f"{ds} - {de}, {date_format(month, 'F Y')}"


        return data, months, month
