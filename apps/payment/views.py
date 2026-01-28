import datetime
import math
import re
import secrets

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Count
from django.db.models.functions import Coalesce
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView, DetailView
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.main.models import Bazaar
from apps.parking.models import Parking, ParkingStatus, ParkingPrice
from apps.payment.authentication import make_basic_authentication
from apps.payment.models import Payme, Click, Point, PointProduct
from apps.payment.providers.base import ProviderException, ProviderBadRequestException
from apps.payment.providers.click_parking import ClickParking
from apps.payment.providers.click_rent import ClickRent
from apps.payment.providers.click_shop import ClickShop
from apps.payment.providers.click_stall import ClickStall
from apps.payment.providers.payme_parking import PaymeParking
from apps.payment.providers.payme_rent import PaymeRent
from apps.payment.providers.payme_shop import PaymeShop
from apps.payment.providers.payme_stall import PaymeStall
from apps.payment.serializers import PaymentSerializer, ClickSerializer
from apps.rent.models import ThingData, ThingStatus
from apps.shop.models import Shop, ShopStatus, ShopPayment
from apps.stall.models import Stall, StallStatus
from smartbozor.helpers import to_snake_case, run_clickhouse_sql, to_int


class PaymentQrScanMixin:
    def get_object_info(self):
        return None, None

    def render_to_response(self, context, **response_kwargs):
        ret = super().render_to_response(context, **response_kwargs)

        obj, object_type = self.get_object_info()
        if obj is not None:
            run_clickhouse_sql(
                """INSERT INTO smartbozor.scan (`object_type`, `object_id`, `scan_at`) VALUES ({object_type:char}, {object_id:Int64}, {now:DateTime})""",
                object_type=object_type,
                object_id=obj.pk,
                now=timezone.now()
            )

        return ret


class PaymentQrStallView(PaymentQrScanMixin, TemplateView):
    template_name = 'payment/stall.j2'

    def get(self, request, bazaar_id, area_id, section_id, number, *args, **kwargs):
        try:
            self.stall = Stall.objects.get(
                section_id=section_id,
                number=number,
            )
        except Stall.DoesNotExist:
            raise Http404
        except Stall.MultipleObjectsReturned:
            raise Http404

        if self.stall.section.area_id != area_id:
            raise Http404

        if self.stall.section.area.bazaar_id != bazaar_id:
            raise Http404

        return super().get(request, bazaar_id, area_id, section_id, number, *args, **kwargs)

    def get_object_info(self):
        return self.stall, 's'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stall"] = self.stall
        context["bazaar"] = self.stall.section.area.bazaar

        stall_status = StallStatus.objects.filter(
            stall_id=self.stall.id,
            date=timezone.localtime().date(),
        ).first()

        context["payment_progress"] = 0
        context["payment_progress_title"] = ''
        context["price"] = self.stall.price

        if stall_status:
            context["is_paid"] = stall_status.is_paid
            context["payment_progress"] = stall_status.payment_progress
            context["payment_progress_title"] = stall_status.payment_progress_title
            context["payment_method"] = Bazaar.PAYMENT_METHOD_DICT.get(stall_status.payment_method, "-")
            context["price"] = stall_status.price

        return context


class PaymentQrShopView(PaymentQrScanMixin, TemplateView):
    template_name = 'payment/shop.j2'

    def get(self, request, bazaar_id, area_id, section_id, number, *args, **kwargs):
        try:
            self.shop = Shop.objects.get(
                section_id=section_id,
                number=number,
            )
        except Shop.DoesNotExist:
            raise Http404
        except Shop.MultipleObjectsReturned:
            raise Http404

        if self.shop.section.area_id != area_id:
            raise Http404

        if self.shop.section.area.bazaar_id != bazaar_id:
            raise Http404

        return super().get(request, bazaar_id, area_id, section_id, number, *args, **kwargs)

    def get_object_info(self):
        return self.shop, 'm'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shop"] = self.shop
        context["bazaar"] = self.shop.section.area.bazaar

        context['total_rent'] = ShopStatus.objects.filter(
            shop_id=self.shop.id
        ).filter(is_occupied=True).aggregate(
            total_amount=Coalesce(Sum("rent_price"), 0)
        )["total_amount"]

        context['total_payment'] = ShopPayment.objects.filter(
            shop_id=self.shop.id
        ).aggregate(
            total_amount=Coalesce(Sum("amount"), 0)
        )["total_amount"]

        start = timezone.localtime().today().date().replace(day=1)
        end = start + relativedelta(months=1, days=-1)

        context['current_month_total_payment'] = ShopPayment.objects.filter(
            shop_id=self.shop.id,
            date__range=(start, end),
        ).aggregate(
            total_amount=Coalesce(Sum("amount"), 0)
        )["total_amount"]

        payment_amount = 0
        try:
            payment_amount = int(self.request.GET.get("amount", 0))
            if payment_amount < 1000:
                payment_amount = 0
        except ValueError:
            pass

        context["payment_amount"] = max(payment_amount, 0)
        context["timestamp_ms"] = int(timezone.now().timestamp() * 1000)

        return context


class PaymentQrRentView(PaymentQrScanMixin, TemplateView):
    template_name = 'payment/rent.j2'

    def get(self, request, bazaar_id, thing_id, number, *args, **kwargs):
        try:
            self.thing_data = ThingData.objects.prefetch_related('thing').get(
                bazaar_id=bazaar_id,
                thing_id=thing_id,
            )
        except Stall.DoesNotExist:
            raise Http404
        except Stall.MultipleObjectsReturned:
            raise Http404

        if number > self.thing_data.count:
            raise Http404

        return super().get(request, bazaar_id, thing_id, number, *args, **kwargs)

    def get_object_info(self):
        return self.thing_data, 'r'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["thing_data"] = self.thing_data
        context["bazaar"] = self.thing_data.bazaar
        context["number"] = self.kwargs["number"]

        thing_status = ThingStatus.objects.filter(
            bazaar_id=self.thing_data.bazaar_id,
            thing_id=self.thing_data.thing_id,
            number=self.kwargs['number'],
            date=timezone.localtime().date(),
        ).first()

        context["payment_progress"] = 0
        context["payment_progress_title"] = ''
        context["price"] = self.thing_data.price

        if thing_status:
            context["is_paid"] = thing_status.is_paid
            context["payment_progress"] = thing_status.payment_progress
            context["payment_progress_title"] = thing_status.payment_progress_title
            context["payment_method"] = Bazaar.PAYMENT_METHOD_DICT.get(thing_status.payment_method, "-")
            context["price"] = thing_status.price

        return context


class PaymentQrParkingView(PaymentQrScanMixin, TemplateView):
    template_name = 'payment/parking.j2'

    def get(self, request, pk, *args, **kwargs):
        try:
            self.parking = Parking.objects.get(
                id=pk,
            )
        except Stall.DoesNotExist:
            raise Http404
        except Stall.MultipleObjectsReturned:
            raise Http404

        return super().get(request, pk, *args, **kwargs)

    def get_object_info(self):
        return self.parking, 'p'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parking"] = self.parking
        context["bazaar"] = self.parking.bazaar

        after = timezone.now().date().replace(day=1) - relativedelta(months=6)
        not_paid = ParkingStatus.objects.filter(
            parking_id=self.parking.id,
            is_paid=False,
            price__gt=0,
            payment_progress=0,
            date__gte=after,
        ).aggregate(
            count=Count("id"),
            total_amount=Coalesce(Sum("price"), 0)
        )

        context["not_paid"] = not_paid

        context["parking_prices"] = ParkingPrice.objects.filter(
            parking_id=self.parking.id,
        ).order_by('duration').all()

        query, order_nonce, found_rows, payment_amount = 0, 0, 0, 0
        try:
            query = self.request.GET.get("query", "")
            if query.isdigit():
                query = max(min(int(query), not_paid["count"]), 0)
                order_nonce = int("1" + str(query))
            else:
                query = re.sub(r"[^A-Z0-9]+", "", query.upper())
                order_nonce = int("9" + str(int(query, 36)))

            if (isinstance(query, int) and query > 0) or (isinstance(query, str) and len(query) > 0):
                payment_rows, payment_amount, order_id = self.parking.get_payment_amount(query)
                if payment_amount > 0:
                    context["order_id"] = order_id
                    context["found_rows"] = len(payment_rows)
        except ValueError:
            pass

        context["payment_amount"] = payment_amount
        context["query"] = query
        context["order_nonce"] = order_nonce

        return context


class PaymentQrPoint(PaymentQrScanMixin, DetailView):
    model = PointProduct
    template_name = 'payment/point.j2'

    def get_object_info(self):
        return self.object, 'x'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["is_available"] = self.object.is_available

        price = max(to_int(self.request.GET.get("price", 0)), 0)

        fee_percent_price, total_price = self.object.calc_total_price(price)

        context["price"] = price
        context["fee_percent_price"] = fee_percent_price
        context["total_price"] = total_price
        context["nonce"] = secrets.randbits(32)

        return context


class PaymentSystemErrorHandlerMixin:
    def http_method_not_allowed(self, request, *args, **kwargs):
        raise ProviderException(-32300, "Method Not Allowed" + (" DEBUG" if settings.DEBUG else ""))

    def handle_exception(self, exc):
        if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
            return self.response_error(-32504, "Not authenticated")
        elif isinstance(exc, ProviderBadRequestException):
            return self.response_error(exc.code, exc.message)
        elif isinstance(exc, ProviderException):
            return self.response_error(exc.code, exc.message)

        return super().handle_exception(exc)

    def response_error(self, code, message):
        return Response({
            "code": code,
            "message": message,
        })


class PaymentSystemMixin(PaymentSystemErrorHandlerMixin):
    permission_classes = []
    authentication_classes = []

    def post_internal(self, request, name, provider_serializer):
        try:
            request.bazaar = Bazaar.objects.get(slug=name)
        except Bazaar.DoesNotExist:
            raise ProviderException(-9999, "Bazaar not found")

        self.check_auth(request)

        data = provider_serializer(request.bazaar, data=request.data)
        if not data.is_valid():
            if settings.DEBUG:
                return JsonResponse(data.errors, status=400)

            raise ProviderBadRequestException()

        method = "do_" + to_snake_case(data.validated_data["method"])
        if not hasattr(self, method):
            self.http_method_not_allowed(request)

        return Response(
            getattr(self, method)(request, data.validated_data["validated_params"])
        )

    def check_auth(self, request):
        pass

    def check_order_id(self, order_id):
        try:
            parts = str(order_id).split("-", 2)
            if parts[0] not in {"s", "m", "r", "p"}:
                raise Exception()

            if len(parts) == 2:
                parts.append(0)

            if len(parts) != 3:
                raise Exception()

            return parts[0], int(parts[1]), parts[2]
        except:
            raise ProviderException(-31098, "Invalid order id")


class PaymentClick(PaymentSystemMixin, APIView):
    def post(self, request, name, *args, **kwargs):
        return self.post_internal(request, name, ClickSerializer)

    def check_auth(self, request):
        if not request.bazaar.is_allow_click:
            raise ProviderException(-31051, "Invalid request")

    def do_prepare(self, request, params):
        order_type, create_order_id, order_nonce = self.check_order_id(params)

        if params["error"] != 0:
            return {
                "click_trans_id": params["click_trans_id"],
                "merchant_trans_id": 0,
                "merchant_prepare_id": 0,
                "error": params["error"],
                "error_note": params["error_note"],
            }

        start_day = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = start_day + datetime.timedelta(days=1)

        with transaction.atomic():
            data = None
            if order_type == "s":
                order, order_price = ClickStall.prepare(request, params)
            elif order_type == "m":
                order, order_price = ClickShop.prepare(request, params, order_nonce)
            elif order_type == "r":
                order, order_price = ClickRent.prepare(request, params, order_nonce)
            elif order_type == "p":
                order, order_price, data = ClickParking.prepare(request, params, order_nonce)

            click_order, created = Click.objects.get_or_create(
                order_type=order_type,
                order_id=order.id,
                prepare_time__range=(start_day, end_day),
                status=0,
                defaults={
                    "create_order_id": create_order_id,
                    "click_trans_id": params["click_trans_id"],
                    "click_paydoc_id": params["click_paydoc_id"],
                    "amount": order_price,
                    "prepare_time": timezone.now(),
                    "data": data
                }
            )

            if not created:
                raise ProviderException(-100, "Already prepared")

        return {
            "click_trans_id": params["click_trans_id"],
            "merchant_trans_id": click_order.transaction_id,
            "merchant_prepare_id": click_order.id,
            "error": 0,
            "error_note": ""
        }

    def do_complete(self, request, params):
        with transaction.atomic():
            try:
                click_order = Click.objects.select_for_update().get(id=params["merchant_prepare_id"])
            except:
                raise ProviderException(-20, "Order not found")

            if click_order.status != 0:
                raise ProviderException(-10, "Order already completed")

            if params["error"] != 0:
                if click_order.order_type == "s":
                    ClickStall.cancel_order(click_order.order)
                elif click_order.order_type == "m":
                    ClickShop.cancel_order(click_order.order)
                elif click_order.order_type == "r":
                    ClickRent.cancel_order(click_order.order)
                elif click_order.order_type == "p":
                    ClickParking.cancel_order(click_order.order)

                click_order.status = params["error"]
                click_order.save()
                return {
                    "click_trans_id": click_order.click_trans_id,
                    "merchant_trans_id": click_order.transaction_id,
                    "merchant_confirm_id": click_order.create_order_id,
                    "error": params["error"],
                    "error_note": ""
                }

            if click_order.order_type == "s":
                ClickStall.complete(request, click_order)
            elif click_order.order_type == "m":
                ClickShop.complete(request, click_order)
            elif click_order.order_type == "r":
                ClickRent.complete(request, click_order)
            elif click_order.order_type == "p":
                ClickParking.complete(request, click_order)

            click_order.status = 1
            click_order.complete_time = timezone.now()
            click_order.save()

        return {
            "click_trans_id": click_order.click_trans_id,
            "merchant_trans_id": click_order.transaction_id,
            "merchant_confirm_id": click_order.create_order_id,
            "error": 0,
            "error_note": ""
        }

    def response_error(self, code, message):
        return Response({
            "error": code,
            "error_note": message,
        })

    def check_order_id(self, params):
        return super().check_order_id(params["merchant_trans_id"])


class PaymentPayme(PaymentSystemMixin, APIView):
    TIMEOUT = 12 * 3600

    def post(self, request, name, *args, **kwargs):
        return self.post_internal(request, name, PaymentSerializer)

    def check_auth(self, request):
        auth = make_basic_authentication(request.bazaar.payme_username, request.bazaar.payme_password)()
        auth.authenticate(request)

        if not request.bazaar.is_allow_payme:
            raise ProviderException(-31051, "Invalid request")

    def do_check_perform_transaction(self, request, params):
        order_type, __, __ = self.check_order_id(params)

        with transaction.atomic():
            if order_type == "s":
                return PaymeStall.check_perform_transaction(request, params)
            if order_type == "m":
                return PaymeShop.check_perform_transaction(request, params)
            if order_type == "r":
                return PaymeRent.check_perform_transaction(request, params)
            if order_type == "p":
                return PaymeParking.check_perform_transaction(request, params)

        raise ProviderException(-31099, "Not implemented")

    def do_create_transaction(self, request, params):
        order_type, create_order_id, order_nonce = self.check_order_id(params)

        start_day = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = start_day + datetime.timedelta(days=1)

        with transaction.atomic():
            data = None
            if order_type == "s":
                order, order_amount = PaymeStall.create_transaction(request, params)
            elif order_type == "m":
                order, order_amount = PaymeShop.create_transaction(request, params, order_nonce)
            elif order_type == "r":
                order, order_amount = PaymeRent.create_transaction(request, params, order_nonce)
            elif order_type == "p":
                order, order_amount, data = PaymeParking.create_transaction(request, params)

            payme_order, __ = Payme.objects.get_or_create(
                order_type=order_type,
                order_id=order.id,
                state__gt=0,
                create_time__range=(start_day, end_day),
                defaults={
                    "state": 1,
                    "create_order_id": create_order_id,
                    "create_order_nonce": order_nonce,
                    "payme_id": params["id"],
                    "amount": order_amount,
                    "create_time": timezone.now(),
                    "data": data
                }
            )

            if payme_order.state != 1:
                raise ProviderException(-31008, "Invalid request")

            if payme_order.payme_id != params["id"]:
                raise ProviderException(-31070, "Invalid payme id")

            if (timezone.now() - payme_order.create_time).total_seconds() >= self.TIMEOUT:
                return self.cancel_order(payme_order, order)

            return {
                "result": {
                    "create_time": payme_order.create_time_ts,
                    "transaction": payme_order.transaction_id,
                    "state": payme_order.state,
                    "receivers": None
                }
            }

    def do_perform_transaction(self, request, params):
        with transaction.atomic():
            payme_order = self.get_payme_order(params)
            if payme_order.state == 1:
                if (timezone.now() - payme_order.create_time).total_seconds() >= self.TIMEOUT:
                    return self.cancel_order(payme_order, payme_order.order)

                if payme_order.order_type == "s":
                    PaymeStall.perform_transaction(request, payme_order)
                elif payme_order.order_type == "m":
                    PaymeShop.perform_transaction(request, payme_order)
                elif payme_order.order_type == "r":
                    PaymeRent.perform_transaction(request, payme_order)
                elif payme_order.order_type == "p":
                    PaymeParking.perform_transaction(request, payme_order)

                payme_order.state = 2
                payme_order.perform_time = timezone.now()
                payme_order.save()
            elif payme_order.state != 2:
                raise ProviderException(-31008, "Order is cancelled")

            return {
                "result": {
                    "transaction": payme_order.transaction_id,
                    "perform_time": payme_order.perform_time_ts,
                    "state": payme_order.state,
                }
            }

    def do_cancel_transaction(self, request, params):
        with transaction.atomic():
            payme_order = self.get_payme_order(params)
            return self.cancel_order(payme_order, payme_order.order, params["reason"])

    def do_check_transaction(self, request, params):
        payme_order = self.get_payme_order(params)

        return {
            "result": {
                "create_time": payme_order.create_time_ts,
                "perform_time": payme_order.perform_time_ts,
                "cancel_time": payme_order.cancel_time_ts,
                "transaction": payme_order.transaction_id,
                "state": payme_order.state,
                "reason": payme_order.reason,
            }
        }

    def do_get_statement(self, request, params):
        start = datetime.datetime.fromtimestamp(params["from_"] / 1000, datetime.timezone.utc)
        end = datetime.datetime.fromtimestamp(params["to_"] / 1000, datetime.timezone.utc)

        result = []
        for row in Payme.objects.filter(
                create_time__range=(start, end),
        ).order_by('id').all():
            result.append({
                "id": row.payme_id,
                "time": row.create_time_ts,
                "amount": row.amount * 100, # tiyinga o'tkazamiz
                "account": {
                    "order_id": f"{row.order_type}-{row.create_order_id}" + (
                        f"-{row.create_order_nonce}" if row.create_order_nonce > 0 else ""),
                },
                "create_time": row.create_time_ts,
                "perform_time": row.perform_time_ts,
                "cancel_time": row.cancel_time_ts,
                "transaction": row.transaction_id,
                "state": row.state,
                "reason": row.reason,
                "receivers": None
            })

        return {
            "result": {
                "transactions": result,
            }
        }

    def cancel_order(self, payme_order, order, reason=4):
        if payme_order.state > 0:
            if payme_order.order_type == 's':
                PaymeStall.cancel_order(order)
            elif payme_order.order_type == 'm':
                PaymeShop.cancel_order(order)
            elif payme_order.order_type == 'r':
                PaymeRent.cancel_order(order)
            elif payme_order.order_type == 'p':
                PaymeParking.cancel_order(order)

            payme_order.state = -payme_order.state
            payme_order.reason = reason
            payme_order.cancel_time = timezone.now()
            payme_order.save()

        return {
            "result": {
                "state": payme_order.state,
                "cancel_time": payme_order.cancel_time_ts,
                "transaction": payme_order.transaction_id,
            }
        }

    def get_payme_order(self, params):
        end_day = timezone.localtime() + datetime.timedelta(days=1)
        start_day = end_day - datetime.timedelta(days=60)

        try:
            payme_id = params["id"]
            return Payme.objects.select_related().get(
                payme_id=payme_id,
                create_time__range=(start_day, end_day),
            )
        except:
            raise ProviderBadRequestException()

    def check_order_id(self, params):
        return super().check_order_id(params["account"]["order_id"])

    def response_error(self, code, message):
        return Response({
            "error": {
                "code": code,
                "message": message,
            }
        })


class PaymentClickPointProduct(PaymentSystemErrorHandlerMixin, APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        try:
            request.point = Point.objects.get(slug=self.kwargs["slug"])
        except PointProduct.DoesNotExist:
            raise ProviderException(-100, "Point product not found")

        data = ClickSerializer(request.point, data=request.data)
        if not data.is_valid():
            if settings.DEBUG:
                return JsonResponse(data.errors, status=400)

            raise ProviderBadRequestException()

        method = "do_" + to_snake_case(data.validated_data["method"])
        if not hasattr(self, method):
            self.http_method_not_allowed(request)

        return Response(
            getattr(self, method)(request, data.validated_data["validated_params"])
        )

    def do_prepare(self, request, params):
        order_type, point_product_id, order_price, order_nonce = self.check_order_id(params["merchant_trans_id"])

        if params["error"] != 0:
            return {
                "click_trans_id": params["click_trans_id"],
                "merchant_trans_id": 0,
                "merchant_prepare_id": 0,
                "error": params["error"],
                "error_note": params["error_note"],
            }

        click_order_id = (order_nonce << 24) | point_product_id
        start_day = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=1)
        end_day = start_day + datetime.timedelta(days=2)

        with transaction.atomic():
            point_product = PointProduct.objects.select_for_update().get(pk=point_product_id)

            if not point_product.is_available:
                raise ProviderException(-101, "Point product isn't available")

            __, total_price = point_product.calc_total_price(order_price)
            if total_price != params["amount"]:
                raise ProviderException(-102, "Point product price was changed")

            click_order, created = Click.objects.get_or_create(
                order_type=order_type,
                order_id=click_order_id,
                prepare_time__range=(start_day, end_day),
                status=0,
                defaults={
                    "create_order_id": point_product.id,
                    "click_trans_id": params["click_trans_id"],
                    "click_paydoc_id": params["click_paydoc_id"],
                    "amount": total_price,
                    "prepare_time": timezone.now(),
                    "data": None
                }
            )

            if not created:
                raise ProviderException(-103, "Already prepared")

        return {
            "click_trans_id": params["click_trans_id"],
            "merchant_trans_id": click_order.transaction_id,
            "merchant_prepare_id": click_order.id,
            "error": 0,
            "error_note": ""
        }

    def do_complete(self, request, params):
        with transaction.atomic():
            try:
                click_order = Click.objects.select_for_update().get(id=params["merchant_prepare_id"])
            except:
                raise ProviderException(-20, "Order not found")

            if click_order.status != 0:
                raise ProviderException(-10, "Order already completed")

            if params["error"] != 0:
                click_order.status = params["error"]
                click_order.save()

                return {
                    "click_trans_id": click_order.click_trans_id,
                    "merchant_trans_id": click_order.transaction_id,
                    "merchant_confirm_id": click_order.create_order_id,
                    "error": params["error"],
                    "error_note": ""
                }

            click_order.status = 1
            click_order.complete_time = timezone.now()
            click_order.save()

        return {
            "click_trans_id": click_order.click_trans_id,
            "merchant_trans_id": click_order.transaction_id,
            "merchant_confirm_id": click_order.create_order_id,
            "error": 0,
            "error_note": ""
        }

    def check_order_id(self, order_id):
        try:
            parts = str(order_id).split("-")
            if len(parts) != 4:
                raise Exception()

            if parts[0] not in {"x"}:
                raise Exception()

            return parts[0], int(parts[1]), int(parts[2]), int(parts[3])
        except:
            raise ProviderException(-31098, "Invalid order id")
