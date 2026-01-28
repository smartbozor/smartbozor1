from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.core.management import BaseCommand
from django.db import connection
from django.utils import timezone

from apps.shop.models import ShopStatus, Shop


class Command(BaseCommand):
    def handle(self, *args, **options):
        today = timezone.localtime().date()
        month_start = today.replace(day=1)
        month_end = month_start + relativedelta(months=1)

        to_table = ShopStatus._meta.db_table
        from_table = Shop._meta.db_table

        now = timezone.now()

        with connection.cursor() as cursor:
            cursor.execute(f"""
                INSERT INTO {to_table} ("shop_id", "date", "is_occupied", "rent_price", "occupied_at")
                SELECT "id", %s, TRUE, "rent_price", %s
                FROM {from_table} as ft
                WHERE ft.is_active AND NOT EXISTS (
                    SELECT 1 FROM {to_table} AS ss WHERE ss."shop_id" = ft."id" AND ss."date" >= %s AND ss."date" < %s
                )
                """, params=[today, now, month_start, month_end])

            cursor.execute(f"""
                DELETE FROM {to_table} AS ss WHERE %s <= "date" AND "date" < %s AND EXISTS ( 
                    SELECT 1 FROM {from_table} AS ft WHERE ft."id" = ss."shop_id" AND NOT ft."is_active"
                )
                """, params=[month_start, month_end])
