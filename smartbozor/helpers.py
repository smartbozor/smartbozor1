import calendar
import datetime
import os
import re
import time
import uuid
from urllib.parse import urlencode
from string import digits, ascii_lowercase

import clickhouse_connect
from django.conf import settings
from django.utils.dates import WEEKDAYS_ABBR
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class UploadTo:
    def __init__(self, format):
        self.format = format

    def __call__(self, instance, filename):
        fn, fext = os.path.splitext(filename)
        filename = "{:%Y-%m-%d-%H-%M-%S}-{}{}".format(
            datetime.datetime.now(),
            # random.randint(100000, 999999),
            str(uuid.uuid4()).lower(),
            fext.lower()
        )

        return os.path.join(time.strftime(self.format), filename)



def to_snake_case(name):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def normalize_d(data, year, month):
    ds, de = 0, 0
    md = calendar.monthrange(year, month)[1]

    def check(val):
        if val < 1 or val > md:
            return 0
        return val

    if 'd' in data:
        if '-' in data['d']:
            a, b = data['d'].split('-')
            if a.isdigit() and b.isdigit():
                ds, de = check(int(a)), check(int(b))
                if ds == 0 or de == 0:
                    ds, de = 0, 0
                else:
                    ds, de = min(ds, de), max(ds, de)
        elif data['d'].isdigit():
            ds = check(int(data['d']))

    return ds, de

def range_d(month, d):
    ds, de = map(int, d.split('-'))
    if ds == 0 and de == 0:
        ds, de = 1, calendar.monthrange(month.year, month.month)[1]
    elif de == 0:
        de = ds

    for d in range(ds, de + 1):
        yield month.replace(day=d)

class DayWeekCalendar(calendar.HTMLCalendar):
    def __init__(self, query_args, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_args = query_args

    def formatday(self, day, weekday, theyear, themonth):
        if day == 0:
            return '<td class="noday">&nbsp;</td>'

        params = {**self.query_args}
        current_start_d, current_end_d = normalize_d(params, theyear, themonth)

        is_active = False
        if (current_start_d > 0 and current_end_d > 0) or (current_start_d == 0 and current_end_d == 0):
            is_active = current_start_d <= day <= current_end_d
            params['d'] = day
        elif current_start_d > 0:
            is_active = current_start_d == day
            if current_start_d != day:
                a, b = min(current_start_d, day), max(current_start_d, day)
                params['d'] = f"{a}-{b}"
            else:
                del params['d']

        query_params = urlencode(params)
        # Use double quotes for the HTML attribute values so we can safely use single quotes
        # inside the Python expression without breaking the f-string syntax.
        day_label = (
            f"<a href=\"?{query_params}\" "
            f"class=\"day-link text-decoration-none d-block px-1 "
            f"{'text-white' if is_active else ''}\">{day}</a>"
        )

        cls = self.cssclasses[weekday]
        if weekday in {5, 6}:
            cls += " weekend"

        if is_active:
            cls += " bg-primary"

        return f'<td class="{cls} text-center"><div class="day">{day_label}</div></td>'

    def formatweekday(self, day):
        """
        Return a weekday name as a table header.
        """
        return '<th class="%s">%s</th>' % (
            self.cssclasses_weekday_head[day], WEEKDAYS_ABBR[day])

    def formatweek(self, theweek, theyear, themonth):
        tds = ''.join(self.formatday(d, wd, theyear, themonth) for (d, wd) in theweek)
        return f"<tr>{tds}</tr>\n"

    def formatmonth(self, theyear, themonth, withyear=True):
        """Bir oylik kalendar jadvali."""
        v = []
        v.append('<table class="month table table-sm">')
        # v.append(self.formatmonthname(theyear, themonth, withyear=withyear))
        v.append(self.formatweekheader())
        for week in self.monthdays2calendar(theyear, themonth):
            v.append(self.formatweek(week, theyear, themonth))
        v.append("</table>")
        return ''.join(v)


def run_clickhouse_sql(sql, **parameters):
    client = clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        username=settings.CLICKHOUSE_USERNAME,
        password=settings.CLICKHOUSE_PASSWORD
    )

    return client.query(query=sql, parameters=parameters)


def to_int(s, default=None):
    try:
        return int(s)
    except (ValueError, TypeError):
        return default

ALPHABET = digits + ascii_lowercase

def int_to_base36(n):
    if n == 0:
        return "0"

    s = ""
    while n > 0:
        n, r = divmod(n, 36)
        s = ALPHABET[r] + s

    return s

MONTH_FULL = [
    _("Yanvar"), _("Fevral"), _("Mart"), _("Aprel"), _("May"), _("Iyun"),
    _("Iyul"), _("Avgust"), _("Sentyabr"), _("Oktyabr"), _("Noyabr"), _("Dekabr")
]

def uz_month(date):
    idx = date.month - 1
    return MONTH_FULL[idx]


