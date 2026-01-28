from datetime import date

from dateutil.relativedelta import relativedelta
from django.core.management import BaseCommand
from django.db.models import F, OuterRef, Subquery
from django.utils import timezone

from apps.shop.models import ShopStatus, Shop


class Command(BaseCommand):
    def handle(self, *args, **options):
        today = timezone.now().date()
        first_day = date(today.year, today.month, 1)
        last_day = first_day + relativedelta(months=1, days=-1)

        shop_rent_sq = Shop.objects.filter(pk=OuterRef('shop_id')).values('rent_price')[:1]

        ShopStatus.objects.filter(
            date__range=(first_day, last_day)
        ).update(rent_price=Subquery(shop_rent_sq))
