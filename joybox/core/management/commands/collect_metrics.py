from django.core.management.base import BaseCommand
from core.metrics import (
    collect_users_by_roles,
    collect_orders_by_payment_type,
    collect_orders_detailed
)

class Command(BaseCommand):
    help = 'Сбор метрик и отправка их в InfluxDB'

    def handle(self, *args, **options):
        self.stdout.write('Начинаем сбор метрик...')
        
        try:
            collect_users_by_roles()
            self.stdout.write(self.style.SUCCESS('Метрики пользователей по ролям собраны'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при сборе метрик пользователей: {e}'))

        try:
            collect_orders_by_payment_type()
            self.stdout.write(self.style.SUCCESS('Метрики заказов по типу оплаты собраны'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при сборе метрик заказов: {e}'))

        try:
            collect_orders_detailed()
            self.stdout.write(self.style.SUCCESS('Детальные метрики заказов собраны'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при сборе детальных метрик заказов: {e}'))

        self.stdout.write(self.style.SUCCESS('Все метрики успешно собраны и отправлены в InfluxDB'))