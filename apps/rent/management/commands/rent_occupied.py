from django.core.management import BaseCommand
from django.db import connection
from django.utils import timezone

from apps.main.models import Bazaar
from apps.rent.models import ThingStatus, ThingData


class Command(BaseCommand):
    def handle(self, *args, **options):
        thing_status_table = ThingStatus._meta.db_table
        thing_data_table = ThingData._meta.db_table

        bazaars_id = []
        for bazaar in Bazaar.objects.order_by('id').all():
            if bazaar.is_working_day:
                bazaars_id.append(bazaar.id)

        if not bazaars_id:
            print("Bugun bozorlar ishlamaydi")
            return

        date = timezone.localtime().date()
        now = timezone.localtime()
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {thing_status_table} (bazaar_id, thing_id, date, number, is_occupied, price, occupied_at)
                SELECT 
                    td.bazaar_id, td.thing_id, %s::date, gs.n, TRUE, td.price, %s::timestamptz
                FROM {thing_data_table} td
                    CROSS JOIN LATERAL generate_series(1, td.count) AS gs(n)
                    LEFT JOIN {thing_status_table} ts
                ON ts.bazaar_id = td.bazaar_id
                    AND ts.thing_id = td.thing_id
                    AND ts.date = %s::date
                    AND ts.number = gs.n
                WHERE ts.bazaar_id IS NULL AND td.bazaar_id IN %s;
                """, params=[date, now, date, tuple(bazaars_id)])

            cursor.execute(
                f"""
                DELETE FROM {thing_status_table} ts
                USING {thing_data_table} td
                WHERE ts.bazaar_id = td.bazaar_id
                  AND ts.thing_id  = td.thing_id
                  AND ts.date      = %s::date
                  AND ts.number    > td.count
                  AND td.bazaar_id IN %s;
                """, params=[date, tuple(bazaars_id)])
