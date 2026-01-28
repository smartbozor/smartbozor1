from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, TemplateView
from humanize import intcomma

from apps.main.models import Bazaar
from apps.rent.forms import ThingCashForm
from apps.rent.models import ThingData, ThingStatus, Thing
from smartbozor.qrcode import render_qr_png_file


class RentBazaarChoice(LoginRequiredMixin, TemplateView):
    template_name = "main/bazaar-choice.j2"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        qs = ThingData.objects.prefetch_related('thing').filter(
            thing_id=self.kwargs["pk"]
        )

        extra, zero_id = {}, set()
        for row in qs.all():
            if row.count == 0:
                zero_id.add((row.bazaar_id, row.thing_id))

            extra[row.bazaar_id] = _("{0} ta {1}").format(row.count, row.thing.name.lower())

        if zero_id:
            paid_count = ThingStatus.objects.filter(
                bazaar_id__in=(a[0] for a in zero_id),
                thing_id__in=(a[1] for a in zero_id),
            ).values("bazaar_id", "thing_id").annotate(
                count=Count("id", distinct=True)
            ).values_list("bazaar_id", "thing_id", "count")
            for a, b, c in paid_count:
                key = (a, b)
                if key not in zero_id:
                    continue

                extra[a] = str(c) + extra[a][1:]

        context["route"] = "rent:list"
        context["extra"] = extra

        return context


class RentListView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    template_name = 'rent/list.j2'
    permission_required = "rent.view_thingdata"

    def get(self, request, *args, **kwargs):
        self.set_bazaar(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.set_bazaar(request, *args, **kwargs)

        if not self.bazaar.is_allow_cash or not request.user.has_perm("rent.add_thingstatus"):
            return JsonResponse({
                "success": False,
                "message": "Permission denied",
            })

        data = ThingCashForm(data=self.request.POST)
        if not data.is_valid():
            return JsonResponse({
                "success": False,
                "error": data.errors,
            })

        try:
            with transaction.atomic():
                thing_data = ThingData.objects.select_for_update().select_related("thing").get(
                    bazaar_id=self.bazaar.id,
                    thing_id=self.kwargs.get("pk"),
                )

                if not self.bazaar.is_working_day:
                    raise Exception(_('Bugun bozor ish kuni emas'))

                ts, created = ThingStatus.objects.get_or_create(
                    bazaar_id=thing_data.bazaar_id,
                    thing_id=thing_data.thing_id,
                    number=data.cleaned_data["number"],
                    date=timezone.localtime().date(),
                    defaults={
                        'is_occupied': True,
                        'is_paid': True,
                        'payment_method': Bazaar.PAYMENT_METHOD_CASH,
                        'price': thing_data.price,
                        'occupied_at': timezone.now(),
                        'paid_at': timezone.now(),
                    }
                )

                if not created:
                    if ts.is_paid:
                        raise Exception(_("{0} № {1} uchun allqachon to'lov qabul qilingan").format(
                            thing_data.thing.name,
                            data.cleaned_data["number"]
                        ))

                    if ts.payment_progress > 0:
                        raise Exception(_("{} orqali to'lov qabul qilinmoqda ...").format(ts.payment_progress_title))

                    if not ts.is_occupied:
                        ts.is_occupied = True
                        ts.occupied_at = timezone.now()

                    ts.is_paid = True
                    ts.payment_method = Bazaar.PAYMENT_METHOD_CASH
                    ts.price = thing_data.price
                    ts.paid_at = timezone.now()
                    ts.save()

        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e),
            })

        return JsonResponse({
            "success": True,
            "message": _("{0} № {1} uchun naqd to'lov muvaffaqiyatli qabul qilindi").format(
                thing_data.thing.name,
                data.cleaned_data["number"],
            )
        })

    def patch(self, request, *args, **kwargs):
        if not request.user.has_perm("rent.view_thingstatus"):
            raise PermissionDenied

        self.set_bazaar(request, *args, **kwargs)

        try:
            number = int(request.GET.get("number"))

            thing_data = ThingData.objects.get(
                bazaar_id=self.bazaar.id,
                thing_id=self.kwargs.get("pk"),
            )

            if number < 1 or thing_data.count < number:
                raise ValueError
        except Thing.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Thing data not found"
            })
        except ValueError:
            return JsonResponse({
                "success": False,
                "error": "Invalid number"
            })

        data = []

        for row in ThingStatus.objects.filter(
                bazaar_id=thing_data.bazaar_id,
                thing_id=thing_data.thing_id,
                is_paid=True
        ).order_by("-date", "-paid_at").all():
            data.append([
                f"{timezone.localtime(row.paid_at):%d.%m.%Y %H:%M}",
                Bazaar.PAYMENT_METHOD_DICT.get(row.payment_method, "-"),
                intcomma(row.price).replace(",", " ") + " " + _("so'm")
            ])

        return JsonResponse({
            "title": _("Rasta uchun to'lovlar"),
            "headers": [
                _("Sana"),
                _("To'lov turi"),
                _("Summa")
            ],
            "data": data
        })

    def get_object(self, *args, **kwargs):
        return ThingData.objects.filter(
            bazaar_id=self.kwargs.get('bazaar_id'),
            thing_id=self.kwargs.get('pk'),
        ).first()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context["pk"] = self.kwargs.get("pk")
        context["numbers"] = range(1, self.object.count + 1) if self.object else None
        context["bazaar"] = self.bazaar
        context["thing"] = Thing.objects.get(pk=self.kwargs.get("pk"))
        context["thing_status"] = {row.number: row for row in ThingStatus.objects.filter(
            bazaar_id=self.bazaar.id,
            thing_id=self.kwargs.get("pk"),
            date=timezone.localtime().date(),
        ).all()}

        return context

    def set_bazaar(self, request, *args, **kwargs):
        try:
            self.bazaar = Bazaar.objects.filter(
                id__in=request.user.allowed_bazaar.values_list('id', flat=True)
            ).get(pk=kwargs['bazaar_id'])  # type: Bazaar
        except Bazaar.DoesNotExist:
            raise Http404


class RentQrCode(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = 'rent.view_thingdata'

    def get_object(self, queryset=...):
        bazaars_id = self.request.user.allowed_bazaar.values_list('id', flat=True)
        if self.kwargs.get('bazaar_id') not in bazaars_id:
            raise Http404

        return ThingData.objects.get(
            bazaar_id=self.kwargs.get('bazaar_id'),
            thing_id=self.kwargs.get('thing_id')
        )

    def render_to_response(self, context, **response_kwargs):
        obj = self.object  # type: ThingData
        if self.kwargs['number'] > obj.count:
            raise Http404

        return render_qr_png_file(obj.get_qr_image_file(self.kwargs.get('number')))
