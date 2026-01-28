import xml.etree.ElementTree as ET
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.db.models import Count
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.main.models import Bazaar
from apps.parking.caching import get_compiled_whitelist
from apps.parking.forms import ParkingCashForm
from apps.parking.models import ParkingCamera, ParkingStatus, Parking, ParkingPrice


class ParkingBazaarChoiceView(LoginRequiredMixin, TemplateView):
    template_name = 'main/bazaar-choice.j2'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["route"] = "parking:list"
        context["extra"] = {
            bid: _("{0} ta avtoturargoh").format(n) for bid, n in Parking.objects.values(
                "bazaar_id",
            ).annotate(
                n=Count("id")
            ).values_list("bazaar_id", "n")
        }

        return context


class ParkingStatusListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ParkingStatus
    paginate_by = 50
    ordering = ("-id", )
    permission_required = "parking.view_parking"
    template_name = "parking/list.j2"

    def get(self, request, *args, **kwargs):
        self.set_bazaar(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.set_bazaar(request, *args, **kwargs)

        if not self.bazaar.is_allow_cash or not request.user.has_perm("parking.add_parkingstatus"):
            return JsonResponse({
                "success": False,
                "message": "Permission denied",
            })

        data = ParkingCashForm(data=self.request.POST)
        if not data.is_valid():
            return JsonResponse({
                "success": False,
                "error": data.errors,
            })

        status, parking = data.cleaned_data.get("status"), data.cleaned_data.get("parking")
        if not status and not parking:
            return JsonResponse({
                "success": False,
                "error": "Data error",
            })

        try:
            with transaction.atomic():
                if status:
                    ps = ParkingStatus.objects.select_for_update().filter(
                        parking__bazaar_id=self.bazaar.id
                    ).get(pk=data.cleaned_data["status"].id)
                    parking_status = [ps]
                else:
                    # lock qilish uchun
                    parking = Parking.objects.select_for_update().get(id=parking.id)
                    parking_status, __, order_id = parking.get_payment_amount(Parking.extract_query(data.cleaned_data.get("amount")), True)
                    if order_id != data.cleaned_data["order_id"]:
                        raise Exception(_("Iltimos, sahifani qayta yuklang"))

                if not self.bazaar.is_working_day:
                    raise Exception(_('Bugun bozor ish kuni emas'))

                for ps in parking_status:
                    if ps.price <= 0:
                        raise Exception(_("Avtomobil avtoturargohdan tekinga foydalangan"))

                    if ps.is_paid:
                        raise Exception(_("Avtomobil uchun allqachon to'lov qabul qilingan"))

                    if ps.payment_progress > 0:
                        raise Exception(_("{} orqali to'lov qabul qilinmoqda ...").format(ps.payment_progress_title))

                    ps.is_paid = True
                    ps.payment_method = Bazaar.PAYMENT_METHOD_CASH
                    ps.payment_progress = 0
                    ps.paid_at = timezone.localtime()
                    ps.save()

        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e),
            })

        return JsonResponse({
            "success": True,
            "message": _("Avtoturargoh uchun naqd to'lov muvaffaqiyatli qabul qilindi")
        })

    def set_bazaar(self, request, *args, **kwargs):
        try:
            self.bazaar = Bazaar.objects.filter(
                id__in=request.user.allowed_bazaar.values_list('id', flat=True)
            ).get(pk=kwargs['pk'])  # type: Bazaar
        except Bazaar.DoesNotExist:
            raise Http404

    def get_queryset(self):
        return super().get_queryset().prefetch_related("parking").filter(
            parking__bazaar_id=self.bazaar.id
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bazaar"] = self.bazaar
        context["PAGE_TITLE"] = str(self.bazaar) + " » " + _("Avtoturargohdagi avtomobillar")

        return context


class ParkingActionView(APIView):
    permission_classes = []
    authentication_classes = []

    XML_FILE_NAME = "anpr.xml"
    LICENSE_PLATE_FILE_NAME = "licensePlatePicture.jpg"
    DETECTION_PICTURE_FILE_NAME = "detectionPicture.jpg"
    LICENSE_PLATE_UNKNOWN = ParkingStatus.LICENSE_PLATE_UNKNOWN

    def post(self, request, action, token, *args, **kwargs):
        if action not in {"enter", "exit", "action"}:
            return Response({
                "success": False,
                "error": "Invalid action",
            })

        if self.XML_FILE_NAME not in request.FILES:
            return Response({
                "success": False,
                "message": "XML file not found",
            })

        try:
            xml_string = request.FILES[self.XML_FILE_NAME].read().decode("utf-8")

            root = ET.fromstring(xml_string)

            if root.tag.startswith("{"):
                ns_uri = root.tag.split("}")[0].strip("{")
                ns = {'hik': ns_uri}
            else:
                ns = {}

            license_plate = root.find('.//hik:licensePlate', ns).text.upper()
            direction = root.find('.//hik:direction', ns).text.lower()
            mac_address = root.find('.//hik:macAddress', ns).text.replace(":", "").upper()
            date_time = timezone.localtime(datetime.fromisoformat(root.find('.//hik:dateTime', ns).text))
        except ET.ParseError:
            return Response({
                "success": False,
                "message": "XML parsing error",
            })
        except Exception as e:
            return Response({
                "success": False,
                "message": str(e),
            })

        if direction != "forward":
            return Response({
                "success": False,
                "message": "Invalid direction",
            })

        today = timezone.localtime().date()
        if date_time.date() != today:
            return Response({
                "success": False,
                "message": "Invalid action date",
            })

        try:
            camera = ParkingCamera.objects.get(token=token[:32])
            camera_role = "enter" if camera.role == ParkingCamera.ROLE_ENTER else "exit"
            if action == "action":
                action = camera_role

            if action != camera_role:
                return Response({
                    "success": False,
                    "message": "Invalid action",
                })

            if camera.mac and camera.mac.upper() != mac_address:
                return Response({
                    "success": False,
                    "message": "Invalid mac address",
                })
        except ParkingCamera.DoesNotExist:
            return Response({
                "success": False,
                "message": "Invalid token",
            })

        with transaction.atomic():
            parking = Parking.objects.select_for_update().get(id=camera.parking_id)
            if not parking.bazaar.is_working_day:
                return Response({
                    "success": False,
                    "message": "Parking is not working day",
                })

            # Agar raqamsiz moshina kelsa va billing ENTER da hisoblanmasa
            # Bularni SKIP qilamiz
            if parking.billing_mode != Parking.BILLING_MODE_ENTER and license_plate == self.LICENSE_PLATE_UNKNOWN:
                return Response({
                    "success": False,
                    "message": "Invalid billing mode",
                })

            ps = None
            if license_plate != self.LICENSE_PLATE_UNKNOWN:
                # Eng oxirgi ROW ni olamiz
                ps = ParkingStatus.objects.select_for_update().filter(
                    parking_id=parking.id,
                    date=today,
                    number=license_plate,
                ).order_by('-enter_at').first()

            if action == "enter":
                if ps and ps.enter_at >= date_time:
                    # Agar mavjud bo'lsa va sana eski kelsa, demak yozmaymiz
                    return Response({
                        "success": False,
                        "message": "Invalid data",
                    })

                if not ps or ps.leave_at:
                    # Agar oxirgi ROW mavjud bo'lmasa va
                    # chiqib ketgan bo'lsa yangi yaratamiz
                    ps = ParkingStatus(
                        parking_id=parking.id,
                        date=today,
                        number=license_plate,
                        enter_count=1,
                        enter_at=date_time,
                    )

                    if parking.billing_mode == Parking.BILLING_MODE_ENTER and not self.is_free(parking, license_plate):
                        price = ParkingPrice.objects.select_for_update().filter(
                            parking_id=parking.id,
                        ).order_by('-duration').first()
                        if price:
                            self.check_paid(price, ps)
                else:
                    # Agar row mavjud bo'lsa, enter_count ni bittaga oshiramiz
                    # va vaqtni to'g'irlaymiz, chunki vaqt har doim eng oxirgisini
                    # olish kerak. Sababi, KIRISH kamerasi oldiga kelib qaytib ketgan
                    # yoki boshqa sababga ko'ra, chiqish kamerasiga tushmay qolgan
                    # bo'lishi mumkin
                    ps.enter_count += 1
                    ps.enter_at = date_time

                if parking.save_image:
                    ps.enter_image = request.FILES.get(self.DETECTION_PICTURE_FILE_NAME)

                ps.save()
            else:
                if not ps or ps.enter_at > date_time or ps.leave_at:
                    if ps:
                        ps.leave_count += 1
                        ps.save()

                    # Agar oxirgi yoziv mavjud bo'lmasa yoki
                    # Chiqish vaqti kirgan vaqtidan oldin bo'lsa
                    return Response({
                        "success": False,
                        "message": "Invalid data",
                    })

                ps.leave_at = date_time
                ps.duration = int((ps.leave_at - ps.enter_at).total_seconds())
                ps.leave_count = 1

                if parking.billing_mode == Parking.BILLING_MODE_EXIT:
                    ps.price = 0
                    if not self.is_free(parking, license_plate):
                        price = ParkingPrice.objects.select_for_update().filter(
                            parking_id=parking.id,
                            duration__lte=ps.duration,
                        ).order_by('-duration').first()
                        if price:
                            self.check_paid(price, ps)

                if parking.save_image:
                    ps.leave_image = request.FILES.get(self.DETECTION_PICTURE_FILE_NAME)

                ps.save()

        return Response({
            "status": "success",
        })

    def check_paid(self, pp, ps):
        ps.price = pp.price

        if ps.payment_progress == 0 and pp.cash_receipts > 0:
            ps.is_paid = True
            ps.paid_at = timezone.localtime()
            ps.payment_method = Bazaar.PAYMENT_METHOD_CASH

            pp.cash_receipts -= 1
            pp.save()

    def is_free(self, parking, license_plate):
        if license_plate == self.LICENSE_PLATE_UNKNOWN:
            return False

        is_free = False
        for (region_id, district_id, bazaar_id, pattern) in get_compiled_whitelist():
            if not pattern.match(license_plate):
                continue

            if bazaar_id and bazaar_id != parking.bazaar_id:
                continue

            if district_id and district_id != parking.bazaar.district_id:
                continue

            if region_id and region_id != parking.bazaar.district.region_id:
                continue

            is_free = True
            break

        return is_free
