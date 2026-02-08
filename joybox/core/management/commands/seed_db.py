# python manage.py seed_db - Заполнить всё
# python manage.py seed_db --force - Перезаписать (удалить и вставить заново)

from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from core.models import (
    Brand, Category, Product, Review, Role, User,
)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Удалить существующие данные и вставить заново',
        )

    def handle(self, *args, **options):
        force = options['force']

        # Проверяем, есть ли уже данные
        if not force and Product.objects.exists():
            self.stdout.write(self.style.WARNING(
                'База уже содержит товары. Для перезаписи используйте --force'
            ))
            return

        if force:
            self._clean()

        # Создаём пользователей 
        created_users = self._create_users()

        # Устанавливаем admin как audit-пользователя для каталога
        admin = created_users.get('admin@joybox.ru')
        if admin:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.current_user_id', %s, false)",
                    [str(admin.userId)]
                )

        # Загружаем каталог 
        self._run_catalog_sql()

        # Создаём отзывы
        self._create_reviews(created_users)

        self.stdout.write(self.style.SUCCESS('Начальные данные успешно загружены!'))

    def _clean(self):
        self.stdout.write('Очистка существующих данных...')
        with connection.cursor() as cur:
            # Сбрасываем audit-переменную
            cur.execute("SELECT set_config('app.current_user_id', '', false)")

            # Удаляем токены (не managed-таблица Django)
            cur.execute('DELETE FROM authtoken_token')

            # TRUNCATE CASCADE обходит триггеры и удаляет всё быстро
            cur.execute('''
                TRUNCATE "auditLog", "review", "cart", "wishlist",
                         "orderItem", "order", "productImage",
                         "productAttribute", "product", "address",
                         "parentChild", "user", "brand", "category"
                CASCADE
            ''')
        self.stdout.write(self.style.SUCCESS('  Очистка завершена'))

    def _create_users(self):
        self.stdout.write('Создание пользователей...')

        users_data = [
            ('admin@joybox.ru',    'Admin123!',   'Админ',    'Системный', None,            4, '79990000001', date(1990, 1, 15), True,  True,  'admin'),
            ('manager@joybox.ru',  'Manager123!', 'Ирина',    'Козлова',   'Сергеевна',     3, '79991112233', date(1992, 5, 20), True,  False, 'manager'),
            ('anna@example.com',   'Anna1234!',   'Анна',     'Смирнова',  'Витальевна',    1, '79161234567', date(1995, 3, 12), False, False, 'anna_s'),
            ('dmitriy@example.com','Dmitry123!',   'Дмитрий',  'Иванов',    'Александрович', 1, '79269876543', date(1988, 8, 25), False, False, 'dmitriy_i'),
            ('elena@example.com',  'Elena1234!',  'Елена',    'Петрова',   'Николаевна',    1, '79035551122', date(1993, 11, 3), False, False, 'elena_p'),
            ('maria@example.com',  'Maria1234!',  'Мария',    'Волкова',   'Дмитриевна',    1, '79117778899', date(1990, 7, 18), False, False, 'maria_v'),
            ('sergey@example.com', 'Sergey123!',  'Сергей',   'Кузнецов',  'Игоревич',      1, '79054443322', date(1985, 12, 1), False, False, 'sergey_k'),
            ('child1@example.com', 'Child1234!',  'Алиса',    'Смирнова',  None,            2, '79161234500', date(2015, 6, 22), False, False, 'alisa_s'),
        ]

        created_users = {}

        for (email, password, first, last, middle, role_id, phone, birth,
             is_staff, is_super, username) in users_data:

            if User.objects.filter(email=email).exists():
                created_users[email] = User.objects.get(email=email)
                continue

            role = Role.objects.get(roleId=role_id)

            with connection.cursor() as cur:
                cur.execute("SELECT set_config('app.current_user_id', '', false)")

            user = User(
                email=email,
                username=username,
                first_name=first,
                last_name=last,
                firstName=first,
                lastName=last,
                middleName=middle,
                roleId=role,
                phone=phone,
                birthDate=birth,
                is_staff=is_staff,
                is_superuser=is_super,
                is_active=True,
                date_joined=timezone.now(),
                createdAt=timezone.now(),
            )
            user.set_password(password)
            user.save()

            created_users[email] = user

        # Связь родитель-ребёнок
        anna = created_users.get('anna@example.com')
        alisa = created_users.get('child1@example.com')
        if anna and alisa:
            with connection.cursor() as cur:
                admin = created_users.get('admin@joybox.ru')
                if admin:
                    cur.execute(
                        "SELECT set_config('app.current_user_id', %s, false)",
                        [str(admin.userId)]
                    )
                cur.execute('''
                    INSERT INTO "parentChild" ("userId", "childId")
                    SELECT %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM "parentChild"
                        WHERE "userId" = %s AND "childId" = %s
                    )
                ''', [anna.userId, alisa.userId, anna.userId, alisa.userId])

        self.stdout.write(self.style.SUCCESS(
            f'  Создано пользователей: {len(created_users)}'
        ))
        return created_users

    def _run_catalog_sql(self):
        self.stdout.write('Загрузка каталога (seed_data.sql)...')
        sql_path = Path(__file__).resolve().parents[4] / 'seed_data.sql'
        if not sql_path.exists():
            sql_path = Path('/app/seed_data.sql')
        if not sql_path.exists():
            self.stderr.write(self.style.ERROR(
                f'Файл seed_data.sql не найден'
            ))
            return

        sql = sql_path.read_text(encoding='utf-8')

        with connection.cursor() as cur:
            cur.execute(sql)

        self.stdout.write(self.style.SUCCESS(
            f'  Каталог загружен: '
            f'{Category.objects.count()} категорий, '
            f'{Brand.objects.count()} брендов, '
            f'{Product.objects.count()} товаров'
        ))

    def _create_reviews(self, created_users=None):
        self.stdout.write('Создание отзывов...')

        if Review.objects.exists():
            self.stdout.write('  Отзывы уже существуют, пропускаем')
            return

        try:
            anna    = User.objects.get(email='anna@example.com')
            dmitriy = User.objects.get(email='dmitriy@example.com')
            elena   = User.objects.get(email='elena@example.com')
            maria   = User.objects.get(email='maria@example.com')
            sergey  = User.objects.get(email='sergey@example.com')
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                '  Пользователи не найдены, отзывы не созданы'
            ))
            return

        now = timezone.now()

        reviews_data = [
            (1, anna.userId, 5,
             'Замечательный конструктор! Дочка в восторге, собирали всей семьёй. '
             'Качество деталей отличное, инструкция понятная. Три модели в одном — отличная идея!'),
            (1, dmitriy.userId, 4,
             'Хороший набор, но 261 деталь — маловато для такой цены. '
             'Зато качество LEGO как всегда на высоте, наклейки классные.'),
            (2, elena.userId, 5,
             'Потрясающая кукла! 22 сустава — это реально впечатляет, можно посадить в любую позу. '
             'Дочь занимается гимнастикой и в восторге, что Барби тоже «занимается».'),
            (2, maria.userId, 4,
             'Красивая кукла, хорошо сделана. Единственный минус — не стоит самостоятельно, '
             'нужна подставка. Но суставы действительно двигаются отлично.'),
            (3, anna.userId, 5,
             'Шикарная кукла для коллекции! Платье просто волшебное, аксессуары детализированы. '
             'Дочка не выпускает из рук. Волосы можно расчёсывать и делать причёски.'),
            (3, sergey.userId, 4,
             'Покупал в подарок племяннице — очень довольна! '
             'Упаковка красивая, подарочный вид. Качество пластика хорошее.'),
            (4, elena.userId, 5,
             'Обожаем серию Tweens! Оливия — самая стильная. Аксессуары-сюрпризы добавляют интриги, '
             'дочь распаковывала с горящими глазами. Подставка — приятный бонус.'),
            (4, maria.userId, 5,
             'Отличная кукла, дочка коллекционирует всю серию. Качество на высоте, '
             'суставы двигаются, одежда снимается. Очень рекомендую!'),
            (4, dmitriy.userId, 3,
             'Неплохая кукла, но за такую цену ожидал большего. '
             'Аксессуары мелкие, могут потеряться. Зато дочь довольна.'),
            (5, anna.userId, 5,
             'Волшебная русалочка! Хвост реально меняет цвет в воде — дочка проверяла в ванной '
             'раз двадцать. Тиара с жемчугом очень красивая.'),
            (5, elena.userId, 4,
             'Красивая кукла-русалка. Эффект смены цвета хвоста работает, '
             'но нужна именно холодная вода. В целом — отличный подарок для девочки.'),
            (6, maria.userId, 5,
             'Самый красивый набор LEGO, который мы собирали! Замок огромный, '
             'столько деталей и секретов внутри. Пять принцесс — мечта любой девочки. '
             'Мушу — невероятно милый!'),
            (6, sergey.userId, 5,
             'Шикарный набор. 787 деталей — собирали два вечера с дочкой, '
             'это отличное время вместе. Водопад и пещера — гениально продумано.'),
            (6, anna.userId, 4,
             'Прекрасный конструктор, но цена кусается. '
             'Зато качество безупречное и детали проработаны до мелочей.'),
            (7, dmitriy.userId, 5,
             'Сын обожает Щенячий патруль, а этот Чейз — просто супер! '
             'Мягкий, качественно сшитый, можно стирать. 33 см — идеальный размер для обнимашек.'),
            (7, elena.userId, 5,
             'Очень качественная мягкая игрушка. Приятная на ощупь, '
             'полностью повторяет персонажа. Ребёнок спит с ней каждую ночь.'),
            (8, anna.userId, 5,
             'Скай — любимый персонаж дочки! Игрушка мягчайшая, '
             'цвета яркие, не линяет при стирке. Рекомендую!'),
            (8, maria.userId, 4,
             'Хорошая мягкая игрушка, очень приятная на ощупь. '
             'Немного меньше, чем ожидала по фото, но качество отличное.'),
            (9, dmitriy.userId, 5,
             'Потрясающая детализация! Кран выдвигается, опоры работают, '
             'двери открываются — сыну 5 лет и он играет каждый день. '
             'Свет и звук — отдельный восторг. Немецкое качество!'),
            (9, sergey.userId, 4,
             'Отличная модель, очень реалистичная. Тяжёлая (4 кг!) — чувствуется качество. '
             'Минус — цена, но для Bruder это нормально.'),
            (10, dmitriy.userId, 5,
             'Вторая модель Bruder в коллекции сына — качество такое же высокое. '
             'Барабан крутится, кабина откидывается. Играет с ней часами.'),
            (10, sergey.userId, 4,
             'Реалистичная бетономешалка, сыну очень понравилась. '
             'Механизм вращения барабана продуман отлично. Рекомендую для мальчиков от 4 лет.'),
            (11, dmitriy.userId, 5,
             'Классический Hot Wheels — сын в восторге! Монстр-трак с динозавром '
             'и бонусная машинка в комплекте. За такую цену — отличный подарок.'),
            (11, anna.userId, 4,
             'Покупала племяннику на день рождения. Машинка качественная, '
             'выглядит эффектно. Монстр-трак с большими колёсами — мечта мальчишек.'),
            (11, sergey.userId, 5,
             'Отличная машинка! Сын добавил в свою коллекцию Hot Wheels. '
             'Динозавр-дизайн просто крутой, хорошая детализация для масштаба 1:64.'),
        ]

        with connection.cursor() as cur:
            # Устанавливаем admin для аудита
            admin = User.objects.filter(roleId__roleId=4).first()
            if admin:
                cur.execute(
                    "SELECT set_config('app.current_user_id', %s, false)",
                    [str(admin.userId)]
                )

            for product_id, user_id, rating, text in reviews_data:
                cur.execute('''
                    INSERT INTO "review" ("productId", "userId", "rating", "reviewText",
                                          "createdAt", "updatedAt")
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', [product_id, user_id, rating, text, now, now])

        self.stdout.write(self.style.SUCCESS(
            f'  Создано отзывов: {len(reviews_data)}'
        ))
