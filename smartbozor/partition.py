import datetime

from dateutil.relativedelta import relativedelta


def partition_table_info(table_name, add=0, use_days=False):
    months, days = add if not use_days else 0, add if use_days else 0

    current_date = datetime.datetime.now()
    partition_date = (current_date.replace(day=1) if not use_days else current_date) + relativedelta(months=months,
                                                                                                     days=days)

    start = partition_date.strftime('%Y-%m-%d')
    end_date = partition_date + relativedelta(months=1 if not use_days else 0, days=1 if use_days else 0)
    end = end_date.strftime('%Y-%m-%d')

    year, month, day = start.split('-')

    return [
        f"{table_name}_{year}_{month}" + (f"_{day}" if use_days else ""),
        start,
        end
    ]

def drop_partition_table_sql(table_name, add=0, use_days=False):
    partition_table_name, start, end = partition_table_info(table_name, add, use_days)
    return "DROP TABLE IF EXISTS " + partition_table_name


def create_partition_table_sql(table_name, add=0, *, use_days=False, add_time=True):
    partition_table_name, start, end = partition_table_info(table_name, add, use_days)

    date_time = " 00:00:00" if add_time else ""

    sql = (
        f"CREATE TABLE IF NOT EXISTS {partition_table_name} "
        f"PARTITION OF {table_name} "
        f"FOR VALUES FROM ('{start}{date_time}') TO ('{end}{date_time}');"
    )

    return sql
