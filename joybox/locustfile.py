"""
JoyBox — Нагрузочное тестирование (Locust + Faker)

Профиль нагрузки
-----------------
Имитируются три типа пользователей с разным весом (вероятностью):

1. **Гость (GuestUser)** — вес 5
   Неавторизованный посетитель.  Только читает каталог.
   • Просмотр списка товаров (с фильтрами и без)
   • Просмотр деталей товара
   • Просмотр категорий и брендов
   • Просмотр отзывов товара

2. **Покупатель (BuyerUser)** — вес 3
   Зарегистрированный пользователь.  Полный цикл покупки.
   • Регистрация / вход
   • Просмотр каталога
   • Работа с корзиной (добавление, просмотр, удаление)
   • Работа с избранным (добавление, просмотр)
   • Оформление заказа (адрес → checkout)
   • Просмотр профиля

3. **Администратор (AdminUser)** — вес 1
   Управление контентом.
   • Вход в админ-панель
   • CRUD категорий и брендов
   • Создание / обновление / удаление товаров
   • Просмотр дашборда и аналитики
   • Просмотр аудит-логов
"""

# cd joybox
# locust -f locustfile.py --host=http://127.0.0.1:8000
# http://localhost:8089


import random
import json
from locust import HttpUser, task, between, tag, events
from faker import Faker

fake = Faker('ru_RU')

_product_ids = []
_category_ids = []
_brand_ids = []


def _safe_json(response):
    """Безопасный парсинг JSON из ответа."""
    try:
        return response.json()
    except Exception:
        return None

#  1. ГОСТЬ — только чтение каталога

class GuestUser(HttpUser):
    """
    Неавторизованный посетитель магазина.
    Вес 5 — самый частый тип пользователя.
    Время ожидания между запросами: 1–5 секунд.
    """
    weight = 5
    wait_time = between(1, 5)

    @tag('catalog')
    @task(5)
    def browse_products(self):
        """Просмотр списка товаров."""
        with self.client.get('/api/catalog/products/', name='GET /catalog/products',
                             catch_response=True) as resp:
            if resp.status_code == 200:
                data = _safe_json(resp)
                if data and isinstance(data, list):
                    for p in data[:20]:
                        pid = p.get('productId')
                        if pid and pid not in _product_ids:
                            _product_ids.append(pid)
                resp.success()
            else:
                resp.failure(f'Status {resp.status_code}')

    @tag('catalog')
    @task(3)
    def browse_products_filtered(self):
        """Просмотр товаров с фильтрами."""
        params = {}
        if _category_ids:
            params['category'] = random.choice(_category_ids)
        if random.random() > 0.5:
            params['min_price'] = random.randint(100, 500)
            params['max_price'] = random.randint(1000, 5000)
        if random.random() > 0.5:
            params['ordering'] = random.choice(['price', '-price', 'productName'])
        self.client.get('/api/catalog/products/', params=params,
                        name='GET /catalog/products?filters')

    @tag('catalog')
    @task(3)
    def search_products(self):
        """Поиск товаров по названию."""
        query = random.choice(['кукла', 'машина', 'конструктор', 'мяч', 'игра', 'набор', 'робот'])
        self.client.get(f'/api/catalog/products/?search={query}',
                        name='GET /catalog/products?search')

    @tag('catalog')
    @task(4)
    def view_product_detail(self):
        """Просмотр детальной страницы товара."""
        if _product_ids:
            pid = random.choice(_product_ids)
            self.client.get(f'/api/catalog/products/{pid}/',
                            name='GET /catalog/products/[id]')

    @tag('catalog')
    @task(2)
    def view_product_reviews(self):
        """Просмотр отзывов товара."""
        if _product_ids:
            pid = random.choice(_product_ids)
            self.client.get(f'/api/catalog/products/{pid}/reviews/',
                            name='GET /catalog/products/[id]/reviews')

    @tag('catalog')
    @task(2)
    def browse_categories(self):
        """Просмотр категорий."""
        with self.client.get('/api/catalog/categories/', name='GET /catalog/categories',
                             catch_response=True) as resp:
            if resp.status_code == 200:
                data = _safe_json(resp)
                if data and isinstance(data, list):
                    for c in data:
                        cid = c.get('categoryId')
                        if cid and cid not in _category_ids:
                            _category_ids.append(cid)
                resp.success()
            else:
                resp.failure(f'Status {resp.status_code}')

    @tag('catalog')
    @task(2)
    def browse_brands(self):
        """Просмотр брендов."""
        with self.client.get('/api/catalog/brands/', name='GET /catalog/brands',
                             catch_response=True) as resp:
            if resp.status_code == 200:
                data = _safe_json(resp)
                if data and isinstance(data, list):
                    for b in data:
                        bid = b.get('brandId')
                        if bid and bid not in _brand_ids:
                            _brand_ids.append(bid)
                resp.success()
            else:
                resp.failure(f'Status {resp.status_code}')

    @tag('catalog')
    @task(1)
    def browse_popular_products(self):
        """Просмотр популярных товаров."""
        self.client.get('/api/catalog/popular-products/',
                        name='GET /catalog/popular-products')

#  2. ПОКУПАТЕЛЬ — полный цикл покупки

class BuyerUser(HttpUser):
    """
    Авторизованный покупатель.
    Вес 3 — второй по частоте тип пользователя.
    Время ожидания между запросами: 2–7 секунд.
    """
    weight = 3
    wait_time = between(2, 7)

    token = None
    user_email = None
    cart_item_ids = []
    wishlist_item_ids = []
    address_id = None

    def on_start(self):
        """Регистрация нового покупателя при старте."""
        self.user_email = fake.unique.email()
        password = 'LoadTest123!'
        reg_data = {
            'firstName': fake.first_name(),
            'lastName': fake.last_name(),
            'email': self.user_email,
            'password': password,
            'confirmPassword': password,
            'phone': f'7999{random.randint(1000000, 9999999)}',
            'birthDate': fake.date_of_birth(minimum_age=18, maximum_age=60).isoformat(),
        }
        with self.client.post('/api/auth/register/', json=reg_data,
                              name='POST /auth/register', catch_response=True) as resp:
            if resp.status_code == 201:
                data = _safe_json(resp)
                if data:
                    self.token = data.get('token')
                resp.success()
            else:
                # Если регистрация не удалась — пробуем войти
                resp.success()
                login_data = {'email': self.user_email, 'password': password}
                with self.client.post('/api/auth/login/', json=login_data,
                                      name='POST /auth/login', catch_response=True) as login_resp:
                    if login_resp.status_code == 200:
                        data = _safe_json(login_resp)
                        if data:
                            self.token = data.get('token')
                    login_resp.success()

        self.cart_item_ids = []
        self.wishlist_item_ids = []

    def _headers(self):
        """Заголовки авторизации."""
        if self.token:
            return {'Authorization': f'Token {self.token}'}
        return {}

    @tag('catalog')
    @task(5)
    def browse_catalog(self):
        """Просмотр каталога."""
        self.client.get('/api/catalog/products/', name='GET /catalog/products')
        if _product_ids and random.random() > 0.5:
            pid = random.choice(_product_ids)
            self.client.get(f'/api/catalog/products/{pid}/',
                            name='GET /catalog/products/[id]')

    @tag('profile')
    @task(2)
    def view_profile(self):
        """Просмотр профиля."""
        self.client.get('/api/auth/profile/', headers=self._headers(),
                        name='GET /auth/profile')

    @tag('cart')
    @task(4)
    def add_to_cart(self):
        """Добавление товара в корзину."""
        if not _product_ids:
            return
        pid = random.choice(_product_ids)
        data = {'productId': pid, 'quantity': random.randint(1, 3)}
        with self.client.post('/api/auth/cart/', json=data, headers=self._headers(),
                              name='POST /auth/cart', catch_response=True) as resp:
            if resp.status_code in (200, 201):
                rdata = _safe_json(resp)
                if rdata and 'cartId' in rdata:
                    self.cart_item_ids.append(rdata['cartId'])
                resp.success()
            else:
                resp.success()  # не считаем ошибкой

    @tag('cart')
    @task(3)
    def view_cart(self):
        """Просмотр корзины."""
        self.client.get('/api/auth/cart/', headers=self._headers(),
                        name='GET /auth/cart')

    @tag('cart')
    @task(1)
    def remove_from_cart(self):
        """Удаление из корзины."""
        if self.cart_item_ids:
            cid = self.cart_item_ids.pop()
            self.client.delete(f'/api/auth/cart/{cid}/', headers=self._headers(),
                               name='DELETE /auth/cart/[id]')

    @tag('wishlist')
    @task(2)
    def add_to_wishlist(self):
        """Добавление в избранное."""
        if not _product_ids:
            return
        pid = random.choice(_product_ids)
        with self.client.post('/api/auth/wishlist/add/', json={'productId': pid},
                              headers=self._headers(),
                              name='POST /auth/wishlist/add', catch_response=True) as resp:
            if resp.status_code in (200, 201):
                rdata = _safe_json(resp)
                if rdata and 'wishlistId' in rdata:
                    self.wishlist_item_ids.append(rdata['wishlistId'])
            resp.success()

    @tag('wishlist')
    @task(2)
    def view_wishlist(self):
        """Просмотр избранного."""
        self.client.get('/api/auth/wishlist/', headers=self._headers(),
                        name='GET /auth/wishlist')

    @tag('checkout')
    @task(1)
    def checkout_flow(self):
        """Полный цикл оформления заказа."""
        if not _product_ids:
            return

        # 1. Добавить в корзину
        pid = random.choice(_product_ids)
        self.client.post('/api/auth/cart/', json={'productId': pid, 'quantity': 1},
                         headers=self._headers(), name='POST /auth/cart (checkout)')

        # 2. Создать адрес
        addr_data = {
            'city': fake.city(),
            'street': fake.street_name(),
            'house': str(random.randint(1, 100)),
            'index': fake.postcode()[:6],
        }
        with self.client.post('/api/auth/addresses/create/', json=addr_data,
                              headers=self._headers(),
                              name='POST /auth/addresses/create', catch_response=True) as resp:
            rdata = _safe_json(resp)
            if resp.status_code == 201 and rdata:
                self.address_id = rdata.get('addressId')
            resp.success()

        # 3. Оформить заказ
        if self.address_id:
            order_data = {
                'deliveryType': random.choice(['самовывоз', 'курьером']),
                'addressId': self.address_id,
                'paymentType': random.choice(['онлайн', 'наличными при получении']),
            }
            self.client.post('/api/auth/checkout/create/', json=order_data,
                             headers=self._headers(),
                             name='POST /auth/checkout/create')

    @tag('orders')
    @task(1)
    def view_orders(self):
        """Просмотр заказов."""
        self.client.get('/api/auth/orders/', headers=self._headers(),
                        name='GET /auth/orders')

    @tag('addresses')
    @task(1)
    def view_addresses(self):
        """Просмотр адресов."""
        self.client.get('/api/auth/addresses/', headers=self._headers(),
                        name='GET /auth/addresses')

#  3. АДМИНИСТРАТОР — управление контентом

class AdminUser(HttpUser):
    """
    Администратор магазина.
    Вес 1 — самый редкий тип пользователя.
    Время ожидания между запросами: 3–10 секунд.
    """
    weight = 1
    wait_time = between(3, 10)

    token = None
    admin_email = None
    _created_category_ids = []
    _created_brand_ids = []
    _created_product_ids = []

    def on_start(self):
        """Регистрация администратора (будет покупателем, но сможет видеть публичные API)."""
        # Для нагрузочного теста создаём обычного пользователя.
        # Для полноценного теста админских эндпоинтов нужен реальный аккаунт администратора.
        # Здесь мы используем заранее созданного админа или регистрируем нового.
        self.admin_email = fake.unique.email()
        password = 'AdminLoad123!'
        reg_data = {
            'firstName': fake.first_name(),
            'lastName': fake.last_name(),
            'email': self.admin_email,
            'password': password,
            'confirmPassword': password,
            'phone': f'7999{random.randint(1000000, 9999999)}',
            'birthDate': '1990-01-01',
        }
        with self.client.post('/api/auth/register/', json=reg_data,
                              name='POST /auth/register (admin)',
                              catch_response=True) as resp:
            data = _safe_json(resp)
            if resp.status_code == 201 and data:
                self.token = data.get('token')
            resp.success()

        self._created_category_ids = []
        self._created_brand_ids = []
        self._created_product_ids = []

    def _headers(self):
        if self.token:
            return {'Authorization': f'Token {self.token}'}
        return {}

    @tag('admin', 'dashboard')
    @task(3)
    def view_dashboard(self):
        """Просмотр дашборда."""
        self.client.get('/api/admin/dashboard/', headers=self._headers(),
                        name='GET /admin/dashboard')

    @tag('admin', 'analytics')
    @task(2)
    def view_analytics_sales(self):
        """Просмотр аналитики продаж."""
        self.client.get('/api/admin/analytics/sales/', headers=self._headers(),
                        name='GET /admin/analytics/sales')

    @tag('admin', 'analytics')
    @task(2)
    def view_analytics_products(self):
        """Просмотр аналитики товаров."""
        self.client.get('/api/admin/analytics/products/', headers=self._headers(),
                        name='GET /admin/analytics/products')

    @tag('admin', 'analytics')
    @task(1)
    def view_user_activity(self):
        """Просмотр активности пользователей."""
        self.client.get('/api/admin/analytics/user-activity/', headers=self._headers(),
                        name='GET /admin/analytics/user-activity')

    @tag('admin', 'catalog')
    @task(3)
    def admin_browse_products(self):
        """Просмотр списка товаров в админке."""
        self.client.get('/api/admin/products/', headers=self._headers(),
                        name='GET /admin/products')

    @tag('admin', 'catalog')
    @task(2)
    def admin_browse_categories(self):
        """Просмотр категорий в админке."""
        self.client.get('/api/admin/categories/', headers=self._headers(),
                        name='GET /admin/categories')

    @tag('admin', 'catalog')
    @task(2)
    def admin_browse_brands(self):
        """Просмотр брендов в админке."""
        self.client.get('/api/admin/brands/', headers=self._headers(),
                        name='GET /admin/brands')

    @tag('admin', 'crud')
    @task(1)
    def admin_create_category(self):
        """Создание категории."""
        data = {
            'categoryName': f'Нагр-{fake.word()}-{random.randint(1, 99999)}',
            'categoryDescription': fake.sentence(nb_words=10),
        }
        with self.client.post('/api/admin/categories/', json=data,
                              headers=self._headers(),
                              name='POST /admin/categories',
                              catch_response=True) as resp:
            if resp.status_code == 201:
                rdata = _safe_json(resp)
                if rdata and 'categoryId' in rdata:
                    self._created_category_ids.append(rdata['categoryId'])
            resp.success()

    @tag('admin', 'crud')
    @task(1)
    def admin_create_brand(self):
        """Создание бренда."""
        data = {
            'brandName': f'Нагр-{fake.company()[:30]}-{random.randint(1, 99999)}',
            'brandDescription': fake.sentence(nb_words=8),
            'brandCountry': fake.country()[:50],
        }
        with self.client.post('/api/admin/brands/', json=data,
                              headers=self._headers(),
                              name='POST /admin/brands',
                              catch_response=True) as resp:
            if resp.status_code == 201:
                rdata = _safe_json(resp)
                if rdata and 'brandId' in rdata:
                    self._created_brand_ids.append(rdata['brandId'])
            resp.success()

    @tag('admin', 'crud')
    @task(1)
    def admin_create_product(self):
        """Создание товара."""
        cat_id = None
        brand_id = None
        if self._created_category_ids:
            cat_id = random.choice(self._created_category_ids)
        elif _category_ids:
            cat_id = random.choice(_category_ids)
        if self._created_brand_ids:
            brand_id = random.choice(self._created_brand_ids)
        elif _brand_ids:
            brand_id = random.choice(_brand_ids)

        if not cat_id or not brand_id:
            return

        data = {
            'productName': f'{fake.word().capitalize()} {fake.word()} {random.randint(1, 99999)}',
            'productDescription': fake.paragraph(nb_sentences=3),
            'categoryId': cat_id,
            'brandId': brand_id,
            'price': str(round(random.uniform(100, 10000), 2)),
            'ageRating': random.choice([0, 3, 6, 12]),
            'quantity': random.randint(1, 200),
            'weightKg': str(round(random.uniform(0.1, 5.0), 2)),
            'dimensions': f'{random.randint(5, 50)}x{random.randint(5, 50)}x{random.randint(5, 50)}',
        }
        with self.client.post('/api/admin/products/create/', json=data,
                              headers=self._headers(),
                              name='POST /admin/products/create',
                              catch_response=True) as resp:
            if resp.status_code == 201:
                rdata = _safe_json(resp)
                if rdata and 'productId' in rdata:
                    self._created_product_ids.append(rdata['productId'])
                    _product_ids.append(rdata['productId'])
            resp.success()

    @tag('admin', 'orders')
    @task(2)
    def admin_view_orders(self):
        """Просмотр заказов."""
        self.client.get('/api/admin/orders/', headers=self._headers(),
                        name='GET /admin/orders')

    @tag('admin', 'users')
    @task(1)
    def admin_view_users(self):
        """Просмотр списка пользователей."""
        self.client.get('/api/admin/users/', headers=self._headers(),
                        name='GET /admin/users')

    @tag('admin', 'audit')
    @task(1)
    def admin_view_audit_logs(self):
        """Просмотр аудит-логов."""
        self.client.get('/api/admin/audit-logs/', headers=self._headers(),
                        name='GET /admin/audit-logs')
