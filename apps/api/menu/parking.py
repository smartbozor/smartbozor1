import datetime
from collections import defaultdict

from django.db import transaction
from django.db.models import F, Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.api.menu.helpers import currency
from apps.main.models import Bazaar
from apps.parking.models import Parking, ParkingPrice, ParkingStatus


def init_parking_menu(bazaar, today):
    menu = []

    qs = Parking.objects.prefetch_related('parkingprice_set').filter(
        bazaar=bazaar,
    ).order_by('id')

    after = today - datetime.timedelta(days=30)
    parking_status_count = ParkingStatus.objects.filter(
        parking__bazaar_id=bazaar.id,
        date__gte=after,
        is_paid=False,
        price__gt=0,
    ).values('parking_id').annotate(
        count=Count("id"),
    ).values_list('parking_id', 'count')

    count_by_parking_id = dict()
    for a, b in parking_status_count:
        count_by_parking_id[a] = b

    for parking in qs.all():
        prices = []
        total_receipts = 0
        for pp in parking.parkingprice_set.all():
            total_receipts += pp.cash_receipts
            prices.append({
                "id": pp.id,
                "price": pp.price,
            })

        prices.sort(key=lambda x: x["price"])
        prices = [{"id": row["id"], "label": currency(row["price"])} for row in prices]

        not_paid_count = count_by_parking_id.get(parking.id, 0)
        menu.append({
            "id": 4_000_000 + parking.id,
            "title": _("AT {}\n{} / {}").format(parking.name, total_receipts, not_paid_count),
            "form": [{
                "type": "header",
                "label": _("Avtoturargoh uchun to'lov")
            }, {
                "type": "radio",
                "name": "price_id",
                "label": _("Autorargoh narxi"),
                "items": prices,
            }, {
                "type": "button",
                "label": _("To'lash"),
            }]
        })

    return menu


def get_parking_data_by_type(bazaar, pk, data, now):
    parking_id = pk - 4_000_000
    with transaction.atomic():
        parking = Parking.objects.select_for_update().get(id=parking_id)
        pp = ParkingPrice.objects.get(id=data["price_id"])

    print_info = [
        f"ID: {pp.id}",
        f"Avtoturargoh: {parking.name}",
        f"Narx: {currency(pp.price)}",
        f"Sana: {now:%d.%m.%Y %H:%M:%S}",
    ]

    return pp.id, pp.price, dict(parking_id=parking.id), print_info


def save_parking(parking_price_id, extra_data):
    Parking.objects.select_for_update().get(id=extra_data["parking_id"])

    pp = ParkingPrice.objects.select_for_update().get(id=parking_price_id)
    total_receipts = pp.cash_receipts + 1

    after = timezone.localtime().date() - datetime.timedelta(days=30)

    cars = ParkingStatus.objects.select_for_update().filter(
        parking_id=extra_data["parking_id"],
        date__gte=after,
        price__gt=0,
        price=pp.price,
        is_paid=False,
        payment_progress=0
    ).order_by('-enter_at')

    for car in cars.all()[:total_receipts]:
        car.is_paid = True
        car.paid_at = timezone.localtime()
        car.payment_method = Bazaar.PAYMENT_METHOD_CASH
        car.payment_progress = 0
        car.save()

        total_receipts -= 1

    pp.cash_receipts = total_receipts
    pp.save()


def cancel_parking(parking_price_id, extra_data):
    # Bu yam hech nima qilmaydi, Receipt da aniqlanadi
    pass