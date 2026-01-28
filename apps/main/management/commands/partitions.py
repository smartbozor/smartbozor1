from django.core.management import BaseCommand
from django.db import connection

from smartbozor.partition import create_partition_table_sql


class Command(BaseCommand):
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            for i in range(1, 6):
                cursor.execute(create_partition_table_sql("stall_stallstatus", i))
                cursor.execute(create_partition_table_sql("shop_shoppayment", i))
                cursor.execute(create_partition_table_sql("shop_shopstatus", i))
                cursor.execute(create_partition_table_sql("rent_thingstatus", i))
                cursor.execute(create_partition_table_sql("ai_stalldataset", i))
                cursor.execute(create_partition_table_sql("ai_stalloccupation", i))


