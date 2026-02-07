from django.http import JsonResponse
from influxdb_client.client.influxdb_client import InfluxDBClient
from .metrics import (
    INFLUXDB_TOKEN,
    INFLUXDB_ORG,
    INFLUXDB_URL,
    INFLUXDB_BUCKET,
    collect_users_by_roles,
    collect_orders_by_payment_type,
    collect_orders_detailed
)

def influxdb_metrics_view(_request):
    """Отправка метрик в InfluxDB"""
    try:
        # Собираем все метрики
        collect_users_by_roles()
        collect_orders_by_payment_type()
        collect_orders_detailed()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Метрики успешно отправлены в InfluxDB'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка при отправке метрик: {str(e)}'
        }, status=500)

def influxdb_query_view(_request):
    """Запрос метрик из InfluxDB"""
    try:
        # Создаем клиент InfluxDB
        client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        
        query_api = client.query_api()
        
        # Пример запроса к метрикам (последние 10 минут)
        queries = [
            '''from(bucket: "metrics")
               |> range(start: -10m)
               |> filter(fn: (r) => r._measurement == "shop_users_by_roles_name")''',
            
            '''from(bucket: "metrics")
               |> range(start: -10m)
               |> filter(fn: (r) => r._measurement == "shop_orders_by_payment_type")''',
            
            '''from(bucket: "metrics")
               |> range(start: -10m)
               |> filter(fn: (r) => r._measurement == "shop_orders_detailed")'''
        ]
        
        results = []
        for query in queries:
            tables = query_api.query(query, org=INFLUXDB_ORG)
            for table in tables:
                for record in table.records:
                    results.append({
                        'measurement': record.get_measurement(),
                        'time': record.get_time(),
                        'value': record.get_value(),
                        'fields': record.values
                    })
        
        client.close()
        
        return JsonResponse({
            'status': 'success',
            'data': results
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка при запросе метрик: {str(e)}'
        }, status=500)