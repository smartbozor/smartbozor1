import datetime
from io import BytesIO

import xlsxwriter
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Sum, F, Case, When, Q, Count
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from xlsxwriter.utility import xl_col_to_name

from apps.dashboard.filters import MonthFilter
from apps.main.models import Bazaar
from apps.parking.models import ParkingStatus
from apps.rent.models import ThingStatus, Thing, ThingData
from apps.report.filter import ClickFilter
from apps.shop.models import ShopPayment, ShopStatus, Shop
from apps.stall.models import StallStatus, Stall
from smartbozor.helpers import DayWeekCalendar, run_clickhouse_sql, range_d
from smartbozor.mixins import NormalizeDataMixin


class ReportTotalRevenueView(NormalizeDataMixin, LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    TITLE = _("Jami daromad")

    template_name = 'report/total-revenue.j2'
    permission_required = 'report.can_view_total_revenue'

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get("export", '0') == '1':
            return self.export(context)

        return super().render_to_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        bazaars = list(self.request.user.allowed_bazaar.order_by('id').all())

        context["bazaars"] = bazaars

        self.update_report(self.request, bazaars, context)

        return context

    def export(self, context):
        xls = BytesIO()

        workbook = xlsxwriter.Workbook(xls, {'in_memory': True})
        worksheet = workbook.add_worksheet(name="Jami daromad")

        header_format = workbook.add_format({
            'bg_color': '#263D54',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': 'white',
            'border': 1
        })

        uzs_format = workbook.add_format({
            'num_format': '#,##0 "so\'m"',
            'align': 'right'
        })

        text_right_format = workbook.add_format({
            "align": "right",
        })

        text_center_format = workbook.add_format({
            "align": "center",
        })


        worksheet.write(0, 0, str(_("HUJJAT YARATILGAN SANA:")), text_right_format)
        worksheet.merge_range(0, 1, 0, 5, f"{timezone.localtime().now():%d.%m.%Y %H:%M}")

        worksheet.write(1, 0, str(_("SANA:")), text_right_format)
        worksheet.merge_range(1, 1, 1, 5, str(context["range_title"]))

        table_row = 3
        worksheet.merge_range(table_row, 0, table_row + 1, 0, str(_("Bozor nomi")), header_format)
        worksheet.merge_range(table_row, 1, table_row + 1, 1, str(_("Ish kuni")), header_format)

        things = context["things"]
        things_header = [
            [row.name, [_("Mavjud"), _("Band"), _("Narxi"), _("To'langan"), _("Jami tushum")]] for row in things
        ]
        thing_header_count = len(things_header[0][1])

        header = [
            [_("Rasta"), [_("Mavjud"), _("Band"), _("To'langan"), _("Jami tushum")]],
            [_("Magazin"), [_("Mavjud"), _("To'langan"), _("Jami tushum")]],
            *things_header,
            [_("Avtoturargoh"), [ _("Avtomobil soni"), _("To'langan"), _("Jami tushum")]],
            [_("JAMI"), [_("TO'LANGAN"), _("TUSHUM")]]
        ]

        header_col = 2
        for title, sub_title in header:
            worksheet.merge_range(table_row, header_col, table_row, header_col + len(sub_title) - 1, str(title), header_format)

            for n, st in enumerate(sub_title):
                col = header_col + n
                worksheet.write(table_row + 1, col,  str(st), header_format)

            header_col += len(sub_title)

        last_col = sum([len(st) for __, st in header]) + 1
        worksheet.set_column(0, 0, width=25)
        worksheet.set_column(1, last_col, width=12)

        working_days = context["working_days"]
        stall_count, stall_occupied_total, stall_paid_total = context["stall_count"], context["stall_occupied_total"], context["stall_paid_total"]
        shop_count, shop_paid_total, shop_occupied_total = context["shop_count"], context["shop_paid_total"], context["shop_occupied_total"]
        rent_count, rent_occupied_total, rent_paid_total = context["rent_count"], context["rent_occupied_total"], context["rent_paid_total"]
        parking = context["parking"]

        bazaar_thing_pt = dict()
        for key, value in rent_paid_total.items():
            bazaar_id, thing_id, pm = map(int, key.split("-"))
            if bazaar_id not in bazaar_thing_pt:
                bazaar_thing_pt[bazaar_id] = dict()

            bazaar_thing_pt[bazaar_id][thing_id] = bazaar_thing_pt[bazaar_id].get(thing_id, 0) + value

        paid_cols, total_cols = [], []
        for row, bazaar in enumerate(context['bazaars'], start=table_row + 2):
            worksheet.write(row, 0, bazaar.name)
            worksheet.write(row, 1, _("{0} kun").format(working_days.get(bazaar.id, 0)), text_center_format)
            # Stall
            stall_c = stall_count.get(bazaar.id, {})
            stall_ot = stall_occupied_total.get(bazaar.id, {})
            stall_pt, shop_pt = 0, 0

            for pm in Bazaar.PAYMENT_METHOD_DICT.keys():
                stall_pt += stall_paid_total.get(f"{bazaar.id}-{pm}", 0)
                shop_pt += shop_paid_total.get(f"{bazaar.id}-{pm}", 0)

            worksheet.write(row, 2, stall_c.get("count", 0), text_center_format)
            worksheet.write(row, 3, f"{stall_ot.get('count', 0)} / {stall_c.get('total', 0)}", text_center_format)
            worksheet.write(row, 4, stall_pt, uzs_format)
            worksheet.write(row, 5, stall_ot.get("total", 0), uzs_format)

            # Shop
            worksheet.write(row, 6, shop_count.get(bazaar.id, 0), text_center_format)
            worksheet.write(row, 7, shop_pt, uzs_format)
            worksheet.write(row, 8, shop_occupied_total.get(bazaar.id, 0), uzs_format)

            paid_cols, total_cols = [4, 7], [5, 8]
            thing_pt = bazaar_thing_pt.get(bazaar.id, {})
            for n, thing in enumerate(things):
                col, key = 9 + thing_header_count * n, f"{bazaar.id}-{thing.id}"
                thing_d = rent_count.get(key, {})
                thing_ot = rent_occupied_total.get(key, {})
                worksheet.write(row, col + 0, thing_d.get("count", 0), text_center_format)
                worksheet.write(row, col + 1, f"{thing_ot.get('count', 0)} / {thing_d.get('total', 0)}", text_center_format)
                worksheet.write(row, col + 2, thing_d.get("price", 0), uzs_format)
                worksheet.write(row, col + 3, thing_pt.get(thing.id, 0), uzs_format)
                worksheet.write(row, col + 4, thing_ot.get("total", 0), uzs_format)

                paid_cols.append(col + 3)
                total_cols.append(col + 4)

            col = 9 + thing_header_count * len(things)
            worksheet.write(row, col + 0, parking.get(bazaar.id, {}).get("paid_count", 0), text_center_format)
            worksheet.write(row, col + 1, parking.get(bazaar.id, {}).get("total_paid", 0), uzs_format)
            worksheet.write(row, col + 2, parking.get(bazaar.id, {}).get("total", 0), uzs_format)

            paid_cols.append(col + 1)
            total_cols.append(col + 2)

            paid_sum_args = ",".join([f"{xl_col_to_name(c)}{row + 1}" for c in paid_cols])
            worksheet.write_formula(row, col + 3, f"=SUM({paid_sum_args})", uzs_format)

            total_sum_args = ",".join([f"{xl_col_to_name(c)}{row + 1}" for c in total_cols])
            worksheet.write_formula(row, col + 4, f"=SUM({total_sum_args})", uzs_format)

        row = table_row + len(context["bazaars"]) + 3
        col = 9 + thing_header_count * len(things) + 3
        worksheet.write(row, 0, str(_("JAMI")))

        for col in paid_cols + total_cols + [col, col + 1]:
            col_name = xl_col_to_name(col)
            worksheet.write_formula(row, col, f"=SUM({col_name}{table_row + 3}:{col_name}{row})", uzs_format)

        workbook.close()

        xls.seek(0)

        name = "jami-daromad"
        response = HttpResponse(xls, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'inline; filename="{}-{:%Y-%m-%d-%H-%M}.xlsx"'.format(
            slugify(name),
            datetime.datetime.now()
        )

        return response

    @classmethod
    def update_report(cls, request, bazaars, context):
        if not bazaars:
            return

        data, months, selected_month = cls.normalize_data(request.GET.dict())
        bazaars_id, working_days = [], dict()
        for bazaar in bazaars:
            bazaars_id.append(bazaar.id)

            for day in range_d(selected_month, data["d"]):
                working_days[bazaar.id] = working_days.get(bazaar.id, 0) + (1 if bazaar.check_working_day(day) else 0)

        context["working_days"] = working_days

        context["stall_count"] = {
            row["bazaar_id"]: {
                "count": row["count"],
                "total": working_days.get(row["bazaar_id"], 0) * row["count"]
            } for row in Stall.objects.annotate(
                bazaar_id=F("section__area__bazaar_id")
            ).filter(bazaar_id__in=bazaars_id).values("bazaar_id").annotate(
                count=Count("id")
            ).values("bazaar_id", "count")
        }

        context["stall_occupied_total"] = {
            row["bazaar_id"]: row for row in
            MonthFilter(data, queryset=StallStatus.objects.filter(
                stall__section__area__bazaar_id__in=bazaars_id
            )).qs.filter(is_occupied=True).values(
                bazaar_id=F("stall__section__area__bazaar_id"),
            ).annotate(
                count=Count("id"),
                total=Coalesce(Sum("price"), 0)
            ).values("bazaar_id", "total", "count")
        }

        context["stall_paid_total"] = {
            f"{row['bazaar_id']}-{row['pm']}": row["total"] for row in
            MonthFilter(data, queryset=StallStatus.objects.filter(
                stall__section__area__bazaar_id__in=bazaars_id
            )).qs.filter(is_paid=True).values(
                bazaar_id=F("stall__section__area__bazaar_id"),
                pm=F("payment_method")
            ).annotate(
                total=Coalesce(Sum("price"), 0)
            ).values("bazaar_id", "pm", "total")
        }

        context["shop_count"] = {
            row["bazaar_id"]: row["count"] for row in Shop.objects.annotate(
                bazaar_id=F("section__area__bazaar_id")
            ).filter(bazaar_id__in=bazaars_id).values("bazaar_id").annotate(
                count=Count("id")
            ).values("bazaar_id", "count")
        }

        context["shop_occupied_total"] = {
            row["bazaar_id"]: row["total"] for row in
            MonthFilter(data, apply_d=False, queryset=ShopStatus.objects.filter(
                shop__section__area__bazaar_id__in=bazaars_id
            )).qs.values(
                bazaar_id=F("shop__section__area__bazaar_id"),
            ).annotate(
                total=Coalesce(Sum("rent_price"), 0)
            ).values("bazaar_id", "total")
        }

        context["shop_paid_total"] = {
            f"{row['bazaar_id']}-{row['pm']}": row["total"] for row in
            MonthFilter(data, queryset=ShopPayment.objects.filter(
                shop__section__area__bazaar_id__in=bazaars_id
            )).qs.values(
                bazaar_id=F("shop__section__area__bazaar_id"),
                pm=F("payment_method")
            ).annotate(
                total=Coalesce(Sum("amount"), 0)
            ).values("bazaar_id", "pm", "total")
        }

        context["things"] = Thing.objects.order_by("id").all()

        context["rent_count"] = {
            f"{row.bazaar_id}-{row.thing_id}": {
                "price": row.price,
                "count": row.count,
                "total": working_days.get(row.bazaar_id, 0) * row.count
            } for row in ThingData.objects.filter(
                bazaar_id__in=bazaars_id
            ).all()
        }

        context["rent_occupied_total"] = {
            f"{row['bazaar_id']}-{row['thing_id']}": row for row in
            MonthFilter(data, queryset=ThingStatus.objects.filter(
                bazaar_id__in=bazaars_id
            )).qs.filter(is_occupied=True).values(
                "bazaar_id", "thing_id"
            ).annotate(
                count=Count("thing_id"),
                total=Coalesce(Sum("price"), 0)
            ).values("bazaar_id", "thing_id", "total", "count")
        }

        context["rent_paid_total"] = {
            f"{row['bazaar_id']}-{row['thing_id']}-{row['pm']}": row["total"] for row in
            MonthFilter(data, queryset=ThingStatus.objects.filter(
                bazaar_id__in=bazaars_id
            )).qs.filter(is_paid=True).values(
                "bazaar_id", "thing_id", pm=F("payment_method")
            ).annotate(
                total=Coalesce(Sum("price"), 0)
            ).values("bazaar_id", "thing_id", "pm", "total")
        }

        context["parking"] = {row["bazaar_id"]: row for row in MonthFilter(data, queryset=ParkingStatus.objects.filter(
            parking__bazaar_id__in=bazaars_id
        )).qs.values(
            bazaar_id=F("parking__bazaar_id"),
        ).annotate(
            free_count=Count("id", filter=Q(price=0), distinct=True),
            paid_count=Count("id", filter=Q(price__gt=0), distinct=True),
            unknown_count=Count("id", filter=Q(number=ParkingStatus.LICENSE_PLATE_UNKNOWN), distinct=True),
            total=Sum("price"),
            total_paid_cash=Sum(Case(When(Q(is_paid=True) & Q(payment_method=Bazaar.PAYMENT_METHOD_CASH), then=F("price")), default=0)),
            total_paid_click=Sum(Case(When(Q(is_paid=True) & Q(payment_method=Bazaar.PAYMENT_METHOD_CLICK), then=F("price")), default=0)),
            total_paid_payme=Sum(Case(When(Q(is_paid=True) & Q(payment_method=Bazaar.PAYMENT_METHOD_PAYME), then=F("price")), default=0)),
            total_paid=Sum(Case(When(is_paid=True, then=F("price")), default=0)),
        ).values("bazaar_id", "free_count", "paid_count", "unknown_count", "total", "total_paid", "total_paid_cash", "total_paid_click", "total_paid_payme")}

        context["months"] = months
        context["n"] = data["n"]
        context["range_title"] = data["range_title"]

        cal = DayWeekCalendar(request.GET.dict())
        context["calendar"] = cal.formatmonth(selected_month.year, selected_month.month)


class ReportTotalScanView(NormalizeDataMixin, LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'report/total-scan.j2'
    permission_required = 'report.can_view_total_scan'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        data, months, selected_month = self.normalize_data(self.request.GET.dict())
        md = self.month_days(selected_month)

        start, end = self.date_range(data, True)
        scan_data = run_clickhouse_sql(
            "SELECT "
            "toStartOfDay(toTimeZone(scan_at, 'Asia/Tashkent')) AS local_day,"
            "object_type, COUNT(object_id) FROM smartbozor.scan "
            "WHERE {start:DateTime} <= scan_at AND scan_at < {end:DateTime} "
            "GROUP BY local_day, object_type",
            start=start,
            end=end
        ).result_rows

        chart_data = {
            's': [0] * md,
            'm': [0] * md,
            'r': [0] * md,
            'p': [0] * md,
        }

        for local_day, object_type, n in scan_data:
            chart_data[object_type][local_day.day - 1] = n

        context["data"] = {
            "type": "line",
            "data": {
                "labels": list(range(1, md + 1)),
                "datasets": [{
                    "label": str(_("Rasta")),
                    "data": chart_data['s']
                }, {
                    "label": str(_("Magazin")),
                    "data": chart_data['m']
                }, {
                    "label": str(_("Ijara buyumlari")),
                    "data": chart_data['r']
                }, {
                    "label": str(_("Avtoturargoh")),
                    "data": chart_data['p']
                }]
            },
        }

        context["months"] = months
        context["n"] = data["n"]
        context["range_title"] = data["range_title"]

        cal = DayWeekCalendar(self.request.GET.dict())
        context["calendar"] = cal.formatmonth(selected_month.year, selected_month.month)

        return context


class ReportTotalClick(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    TITLE = _("Click hisobot")
    template_name = 'report/total-click.j2'
    permission_required = "payment.view_click"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        fl = ClickFilter(self.request.GET.dict())
        context["filter"] = fl

        qs = fl.qs.annotate(
            date=F("complete_time__date")
        ).values("date").annotate(
            total=Sum("amount")
        ).order_by("date")

        context["data"] = qs.all()

        def_s, def_e = ClickFilter.default_month_range()
        context["start"] = fl.form.cleaned_data.get("start", None) or def_s
        context["end"] = fl.form.cleaned_data.get("end", None) or def_e

        return context

