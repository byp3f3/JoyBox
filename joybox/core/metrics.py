import os
import influxdb_client
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Конфигурация InfluxDB
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "ksI76yJaJH6KUBEznO3BmSsOvshwjWBLD6fUJiSotP-jZl9RqQ8sC-vmYwcv7oTFbAbVxukC6HRT5_MKcI8RjA==")
INFLUXDB_ORG = "MPT"
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_BUCKET = "metrics"

def get_influxdb_client():
    """Создание клиента InfluxDB"""
    return influxdb_client.InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG
    )

def collect_users_by_roles():
    """Сбор метрик о пользователях по ролям"""
    from django.db.models import Count
    from .models import User, Role
    
    client = get_influxdb_client()
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    # Собираем данные о пользователях по ролям
    users_data = (User.objects
                  .select_related('roleId')
                  .values('roleId__roleName')
                  .annotate(count_user=Count('userId')))
    
    points = []
    for row in users_data:
        role_name = row['roleId__roleName']
        count = row['count_user']
        
        point = Point("shop_users_by_roles_name")\
            .tag("roleName", role_name)\
            .field("count", float(count))
        points.append(point)
    
    # Добавляем нулевые значения для ролей без пользователей
    existing_role_names = {row['roleId__roleName'] for row in users_data}
    all_roles = Role.objects.all()
    
    for role in all_roles:
        if role.roleName not in existing_role_names:
            point = Point("shop_users_by_roles_name")\
                .tag("roleName", role.roleName)\
                .field("count", 0.0)
            points.append(point)
    
    # Записываем точки в InfluxDB
    if points:
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=points)
    
    client.close()

def collect_orders_by_payment_type():
    """Сбор метрик о заказах по типу оплаты"""
    from django.db.models import Count
    from .models import Order
    
    client = get_influxdb_client()
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    # Собираем данные о заказах по типу оплаты
    orders_data = Order.objects.values('paymentType').annotate(count_order=Count('orderId'))
    
    points = []
    for row in orders_data:
        payment_type = row['paymentType']
        count = row['count_order']
        
        point = Point("shop_orders_by_payment_type")\
            .tag("paymentType", payment_type)\
            .field("count", float(count))
        points.append(point)
    
    # Добавляем нулевые значения для типов оплаты без заказов
    existing_payment_types = {row['paymentType'] for row in orders_data}
    
    for code, _ in Order.PAYMENT_TYPE_CHOICES:
        if code not in existing_payment_types:
            point = Point("shop_orders_by_payment_type")\
                .tag("paymentType", code)\
                .field("count", 0.0)
            points.append(point)
    
    # Записываем точки в InfluxDB
    if points:
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=points)
    
    client.close()

def collect_orders_detailed():
    """Сбор детальной информации о заказах"""
    from django.db.models.functions import ExtractYear, ExtractMonth, ExtractDay
    from django.db.models import Count
    from .models import Order
    
    client = get_influxdb_client()
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    # Собираем данные о заказах с датами
    orders_with_dates = (Order.objects
                        .annotate(
                            year=ExtractYear('createdAt'),
                            month=ExtractMonth('createdAt'),
                            day=ExtractDay('createdAt')
                        )
                        .values('year', 'month', 'day')
                        .annotate(count=Count('orderId')))
    
    points = []
    for row in orders_with_dates:
        year = str(row['year'])
        month = str(row['month']).zfill(2)
        day = str(row['day']).zfill(2)
        date_str = f"{year}-{month}-{day}"
        count = row['count']
        
        point = Point("shop_orders_detailed")\
            .tag("year", year)\
            .tag("month", month)\
            .tag("day", day)\
            .tag("date", date_str)\
            .field("count", float(count))
        points.append(point)
    
    # Записываем точки в InfluxDB
    if points:
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=points)
    
    client.close()