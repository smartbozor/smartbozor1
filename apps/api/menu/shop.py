import datetime

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from humanize import intcomma

from apps.main.models import Bazaar
from apps.shop.models import Shop, ShopPayment, ShopStatus


def init_shop_menu(bazaar, today):
    shop_list = [
        {"id": row.id, "label": f"{row.number} - {row.owner}"} for row in Shop.objects.filter(
            section__area__bazaar_id=bazaar.id
        ).order_by('number').all()
    ]

    return [{
        "id": 2,
        "title": _("Do'kon"),
        "confirm": True,
        "form": [{
            "type": "header",
            "label": _("Do'kon uchun to'lov")
        }, {
            "type": "dropdown",
            "name": "shop_id",
            "label": _("Do'kon raqami"),
            "items": shop_list,
        }, {
            "type": "currency",
            "name": "amount",
            "min": 1_000,
            "max": 10_000_000,
            "label": _("To'lov summasi")
        }, {
            "type": "button",
            "label": _("To'lash"),
        }]
    }]


def get_shop_data_by_type(bazaar, pk, data, now):
    nonce = int(timezone.now().timestamp() * 1000)
    with transaction.atomic():
        shop = Shop.objects.select_for_update().get(id=data["shop_id"])

        today = timezone.localtime().date()
        start = today - datetime.timedelta(days=2)
        shop_payment, __ = ShopPayment.objects.select_for_update().get_or_create(
            shop_id=shop.id,
            date__range=(start, today),
            payment_method=Bazaar.PAYMENT_METHOD_CASH,
            nonce=nonce,
            defaults={
                "date": today,
                "amount": data["amount"],
            }
        )

    print_info = [
        f"ID: {shop_payment.id}",
        f"Tadbirkor: {shop.owner or '-'}",
        f"Do'kon: №{shop.number}",
        f"Narx: {str(intcomma(shop_payment.amount)).replace(',', ' ')} so'm",
        f"Sana: {now:%d.%m.%Y %H:%M:%S}",
    ]

    return shop_payment.pk, shop_payment.amount, dict(shop_id=shop.id), print_info


def save_shop(shop_status_id, extra_data):
    shop = Shop.objects.select_for_update().get(id=extra_data["shop_id"])
    shop_payment = ShopPayment.objects.get(id=shop_status_id)

    if shop_payment.payment_method != Bazaar.PAYMENT_METHOD_CASH:
        # Xato chaqirilgan
        return

    if not shop_payment.paid_at:
        shop_payment.paid_at = timezone.localtime()
        shop_payment.save()


def cancel_shop(shop_status_id, extra_data):
    # Bu hech nima qilmaymiz, chunki Receipt da hal qilinadi
    pass

