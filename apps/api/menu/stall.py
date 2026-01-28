from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from humanize import intcomma

from apps.api.exceptions import AlreadyPaidException, ProcessAlreadyInProgressException
from apps.api.menu.helpers import currency
from apps.main.models import Bazaar
from apps.stall.models import Stall, StallStatus


def init_stall_menu(bazaar, today):
    stall_count = Stall.objects.filter(
        section__area__bazaar_id=bazaar.id
    ).count()

    stall_paid_id = set(StallStatus.objects.filter(
        stall__section__area__bazaar_id=bazaar.id,
        date=today
    ).filter(
        Q(is_paid=True) | Q(payment_progress__gt=0)
    ).values_list('stall_id', flat=True))

    stall_list = [
        {"id": row.id, "label": f"{row.number} - {currency(row.price)}"} for row in Stall.objects.filter(
            section__area__bazaar_id=bazaar.id
        ).exclude(id__in=stall_paid_id).order_by('number').all()
    ]

    return [{
        "id": 1,
        "title": _("Rasta\n{} / {}").format(stall_count - len(stall_list), stall_count),
        "form": [{
            "type": "header",
            "label": _("Rasta uchun to'lov")
        }, {
            "type": "dropdown",
            "name": "stall_id",
            "label": _("Rasta raqami"),
            "items": stall_list,
        }, {
            "type": "button",
            "label": _("To'lash"),
        }]
    }]


def get_stall_data_by_type(bazaar, pk, data, now):
    stall = Stall.objects.select_for_update().get(id=data["stall_id"])

    ss, created = StallStatus.objects.select_for_update().get_or_create(
        stall=stall,
        date=timezone.localtime().date(),
        defaults={
            'is_occupied': False,
            'is_paid': False,
            'payment_method': Bazaar.PAYMENT_METHOD_CASH,
            'payment_progress': 0,
            'price': stall.price
        }
    )

    if ss.is_paid:
        raise AlreadyPaidException()

    if ss.payment_progress > 0:
        raise ProcessAlreadyInProgressException()

    ss.payment_method = Bazaar.PAYMENT_METHOD_CASH
    ss.payment_progress = StallStatus.PAYMENT_PROGRESS_CASH
    ss.save()

    print_info = [
        f"ID: {ss.id}",
        f"Rasta: №{stall.number}",
        f"Narx: {currency(ss.price)}",
        f"Sana: {now:%d.%m.%Y %H:%M:%S}",
    ]

    return ss.pk, ss.price, dict(stall_id=stall.id), print_info


def save_stall(stall_status_id, extra_data):
    Stall.objects.select_for_update().get(id=extra_data["stall_id"])

    try:
        ss = StallStatus.objects.select_for_update().get(id=stall_status_id)
    except StallStatus.DoesNotExist:
        # Agar stall_status mavjud bo'lmasa demak API noto'g'ri chaqirilgan
        return

    if ss.is_paid:
        # 2 marta chaqirilyapti
        return

    if ss.payment_progress != StallStatus.PAYMENT_PROGRESS_CASH:
        # Xato chaqirilgan
        return

    if not ss.is_occupied:
        ss.is_occupied = True
        ss.occupied_at = timezone.localtime()

    ss.is_paid = True
    ss.paid_at = timezone.localtime()
    ss.payment_progress = 0
    ss.save()


def cancel_stall(stall_status_id, extra_data):
    Stall.objects.select_for_update().get(id=extra_data["stall_id"])

    try:
        ss = StallStatus.objects.select_for_update().get(id=stall_status_id)
    except StallStatus.DoesNotExist:
        # Agar stall_status mavjud bo'lmasa demak API noto'g'ri chaqirilgan
        return

    if ss.is_paid or ss.payment_progress != StallStatus.PAYMENT_PROGRESS_CASH:
        # Agar to'langan bo'lsa cancel qilolmaymiz
        return

    ss.is_paid = False
    ss.paid_at = None
    ss.payment_progress = 0
    ss.save()
