from django.db import transaction
from django.http import Http404
from django.utils import timezone

from apps.api.exceptions import AlreadyPaidException, ProcessAlreadyInProgressException
from apps.api.menu.helpers import currency
from apps.main.models import Bazaar
from apps.rent.models import ThingData, ThingStatus
from django.utils.translation import gettext_lazy as _


def init_rent_menu(bazaar, today):
    menu = []

    qs = ThingStatus.objects.filter(
        bazaar_id=bazaar.id,
        date=today,
        is_paid=True,
    )

    paid_things, paid_count_by_thing_id = set(), dict()
    for a, b in qs.values_list('thing_id', 'number'):
        paid_things.add((a, b))
        paid_count_by_thing_id[a] = paid_count_by_thing_id.get(a, 0) + 1

    things = ThingData.objects.prefetch_related("thing").filter(
        bazaar=bazaar
    ).order_by('id').all()

    for row in things:  # type: ThingData
        if row.count > 0:
            count_info = "{} / {}".format(paid_count_by_thing_id.get(row.thing_id, 0), row.count)

            thing_items = []
            for n in range(1, row.count + 1):
                if (row.thing_id, n) in paid_things:
                    continue

                thing_items.append({
                    "id": n,
                    "label": "{}-{}".format(n, row.thing.name_uz.lower()),
                })

            form_control = [{
                "type": "dropdown",
                "name": "number",
                "label": _("Ijara raqami"),
                "items": thing_items
            }]
        else:
            count_info = str(paid_count_by_thing_id.get(row.thing_id, 0))

            form_control = [{
                "type": "text",
                "name": "number",
                "label": _("Raqam"),
                "value": 0,
                "keyboard": "number"
            }, {
                "type": "currency",
                "name": "price",
                "label": _("Ijara narxi"),
                "value": row.price,
                "readonly": True,
            }]

        menu.append({
            "id": 3_000_000 + row.id,
            "title": row.thing.name_uz + "\n" + count_info + "\n" + currency(row.price),
            "confirm": True,
            "form": [{
                "type": "header",
                "label": _("{} uchun to'lov").format(row.thing.name_uz),
            }, *form_control, {
                "type": "button",
                "label": _("To'lash"),
            }]
        })

    return menu


def get_rent_data_by_type(bazaar, pk, data, now):
    thing_data_id = pk - 3_000_000
    with transaction.atomic():
        thing_data = ThingData.objects.select_for_update().get(pk=thing_data_id)
        if thing_data.bazaar_id != bazaar.id:
            raise Http404

        if thing_data.count > 0:
            number = data.get("number", 0)
            if number <= 0 or number > thing_data.count:
                raise Http404

            ts, __ = ThingStatus.objects.get_or_create(
                bazaar_id=bazaar.id,
                thing_id=thing_data.thing_id,
                number=data["number"],
                date=timezone.localtime().date(),
                defaults={
                    'is_occupied': False,
                    'is_paid': False,
                    'payment_method': 0,
                    'payment_progress': 0,
                    'price': thing_data.price,
                    'occupied_at': None,
                    'paid_at': None,
                }
            )

            if ts.is_paid:
                raise AlreadyPaidException()

            if ts.payment_progress > 0:
                raise ProcessAlreadyInProgressException()
        else:
            ts = ThingStatus.objects.create(
                bazaar_id=bazaar.id,
                thing_id=thing_data.thing_id,
                date=timezone.localtime().date(),
                number=data.get("number", 0),
                is_occupied=False,
                is_paid=False,
                payment_method=0,
                payment_progress=0,
                price=thing_data.price
            )

        ts.payment_method = Bazaar.PAYMENT_METHOD_CASH
        ts.payment_progress = ThingStatus.PAYMENT_PROGRESS_CASH
        ts.save()

        print_info = [
            f"ID: {ts.id}",
            f"Buyum: {ts.number}-{thing_data.thing.name_uz.lower()}",
            f"Narx: {currency(ts.price)}",
            f"Sana: {now:%d.%m.%Y %H:%M:%S}",
        ]

        return ts.pk, ts.price, dict(thing_data_id=thing_data.id), print_info


def save_rent(thing_status_id, extra_data):
    ThingData.objects.select_for_update().get(pk=extra_data['thing_data_id'])

    try:
        ts = ThingStatus.objects.select_for_update().get(pk=thing_status_id)
    except ThingStatus.DoesNotExist:
        return

    if ts.is_paid:
        return

    if ts.payment_progress != ThingStatus.PAYMENT_PROGRESS_CASH:
        # Xato chaqirilgan
        return

    if not ts.is_occupied:
        ts.is_occupied = True
        ts.occupied_at = timezone.localtime()

    ts.is_paid = True
    ts.paid_at = timezone.localtime()
    ts.payment_progress = 0
    ts.save()


def cancel_rent(thing_status_id, extra_data):
    ThingData.objects.select_for_update().get(pk=extra_data['thing_data_id'])

    try:
        ts = ThingStatus.objects.select_for_update().get(pk=thing_status_id)
    except ThingStatus.DoesNotExist:
        return

    if ts.is_paid or ts.payment_progress != ThingStatus.PAYMENT_PROGRESS_CASH:
        # To'langan bo'lsa CANCEL qilib bo'lmaydi
        return

    ts.is_paid = False
    ts.paid_at = None
    ts.payment_progress = 0
    ts.save()
