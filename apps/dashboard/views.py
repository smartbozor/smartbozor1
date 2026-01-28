import calendar

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import Sum, F, Count
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from apps.dashboard.filters import MonthFilter
from apps.main.models import Bazaar
from apps.stall.models import Stall, StallStatus
from smartbozor.mixins import NormalizeDataMixin


class DashboardIndexView(NormalizeDataMixin, LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.j2'

    def get(self, request, pk=0, *args, **kwargs):
        self.object = None
        if pk > 0:
            self.object = Bazaar.objects.filter(
                id__in=self.request.user.allowed_bazaar.values_list('id', flat=True)
            ).get(pk=pk)

        return super().get(request, pk, *args, **kwargs)

    def get_context_data1(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["object"] = self.object
        if self.object:
            bazaars = [self.object]
        else:
            bazaars = list(self.request.user.allowed_bazaar.order_by('id').all())

        self.update_context(self.request, bazaars, context)

        return context

    @classmethod
    def update_context(cls, request, bazaars, context):
        if not bazaars:
            return

        data, months, selected_month = cls.normalize_data(request.GET.dict())

        bazaars_id = [row.id for row in bazaars]

        stall_count_by_bazaar = {row["bazaar_id"]: row["total"] for row in Stall.objects.filter(
            section__area__bazaar_id__in=bazaars_id
        ).values(bazaar_id=F("section__area__bazaar_id")).annotate(
            total=Count("id")
        ).values("bazaar_id", "total")}

        md = calendar.monthrange(selected_month.year, selected_month.month)[1]

        stall_total_by_data, stall_total_by_payment_method = {}, {}
        for row in MonthFilter(data, queryset=StallStatus.objects.filter(
                stall__section__area__bazaar_id__in=bazaars_id
        )).qs.filter(is_paid=True).values("date", "payment_method").annotate(
            total=Coalesce(Sum("price"), 0)
        ).values("date", "payment_method", "total"):

            pm = row["payment_method"]
            stall_total_by_payment_method[pm] = stall_total_by_payment_method.get(pm, 0) + row["total"]
            if pm not in stall_total_by_data:
                stall_total_by_data[pm] = [0] * md

            stall_total_by_data[pm][row["date"].day - 1] = row["total"]

        context["months"] = months
        context["n"] = data["n"]
        context["filter"] = MonthFilter(data, queryset=Stall.objects.none())

        sections = [
            (
                _("Jami"),
                "bi-collection",
                [
                    (_("Bozorlar"), _("{0} ta").format(len(bazaars))),
                    (_("Rastlar"), _("{0} ta").format(sum(stall_count_by_bazaar.values()))),
                    (_("Do'konlar"), _("{0} ta").format(0)),
                    (_("Avtoturargohlar"), _("{0} ta").format(0)),
                    (_("Xojatxonalar"), _("{0} ta").format(0)),
                    (_("Daromad"), _("{0} so'm").format(
                        intcomma(sum(stall_total_by_payment_method.values()))
                    ))
                ] + [
                    (Bazaar.PAYMENT_METHOD_DICT.get(pm), _("{0} so'm").format(
                        intcomma(val)
                    )) for pm, val in
                    sorted(stall_total_by_payment_method.items())
                ]
            )
        ]

        # Rastalar
        stall_amount_datasets = []
        for pm, pm_data in sorted(stall_total_by_data.items()):
            stall_amount_datasets.append({
                "label": str(Bazaar.PAYMENT_METHOD_DICT.get(pm, "-")),
                "data": pm_data,
            })

        if not stall_amount_datasets:
            stall_amount_datasets.append({
                "label": "-",
                "data": [0] * md,
            })

        total_month_stalls, stall_total_by_day = 0, [0] * md
        for day_n in range(1, md + 1):
            day = selected_month.replace(day=day_n)
            for bazaar in bazaars:  # type: Bazaar
                if bazaar.check_working_day(day):
                    sc = stall_count_by_bazaar.get(bazaar.id, 0)
                    stall_total_by_day[day_n - 1] += sc
                    total_month_stalls += sc

        stall_occupied_qs = MonthFilter(data, queryset=StallStatus.objects.filter(
            is_occupied=True,
            stall__section__area__bazaar_id__in=bazaars_id
        )).qs.values("date").annotate(
            n=Count("id")
        ).values_list("date", "n")

        stall_occupied, stall_occupied_by_day = 0, [0] * md
        for (so_date, so_n) in sorted(stall_occupied_qs):
            if stall_total_by_day[so_date.day - 1] > 0:
                stall_occupied_by_day[so_date.day - 1] += so_n
                stall_occupied += so_n

        stall_occupied_percent = 0 if total_month_stalls == 0 else round(stall_occupied * 100 / total_month_stalls, 2)

        sections.append((
            _("Rastalar bo'yicha"),
            "bi bi-dice-4", [
                (_("Band"),
                 _("{0} ta / {1} ({2}%)").format(stall_occupied, total_month_stalls, stall_occupied_percent)),
                (_("Daromad"), _("{0} so'm").format(
                    intcomma(sum(stall_total_by_payment_method.values()))
                ))
            ] + [
                (Bazaar.PAYMENT_METHOD_DICT.get(pm), _("{0} so'm").format(
                    intcomma(val)
                )) for pm, val in sorted(stall_total_by_payment_method.items())
            ] + [
                (_("Daromad kunlar bo'yicha"), {
                    "type": "bar",
                    "data": {
                        "labels": list(range(1, md + 1)),
                        "datasets": stall_amount_datasets
                    },
                    "options": {
                        "x": {"stacked": True},
                        "y": {"stacked": True}
                    }
                }),
                (_("Bandlik kunlar bo'yicha"), {
                    "type": "bar",
                    "data": {
                        "labels": list(range(1, md + 1)),
                        "datasets": [{
                            "label": str(_("Band bo'lgan")),
                            "data": stall_occupied_by_day,
                            "backgroundColor": "#81C784"
                        }, {
                            "label": str(_("Band emas")),
                            "data": [a - b for a, b in zip(stall_total_by_day, stall_occupied_by_day)],
                            "backgroundColor": "#E57373"
                        }]
                    },
                    "options": {
                        "x": {"stacked": True},
                        "y": {"stacked": True}
                    }
                })
            ]
        ))

        context["sections"] = sections
