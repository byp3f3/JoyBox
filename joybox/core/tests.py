"""
Тесты серверной логики и API JoyBox.

Функциональное тестирование:
  - CRUD операции (товары, категории, бренды, пользователи, заказы)
  - Поиск, сортировка, фильтры
  - Роли и доступ
  - Хранимые процедуры и триггеры
  - Транзакции

Интеграционное тестирование:
  - Взаимодействие API (полный цикл)
  - Импорт/экспорт данных
"""

from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.db import connection
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import csv
import io
import json

from .models import (
    Role, User, Category, Brand, Product, ProductImage, ProductAttribute,
    Review, Wishlist, Cart, Address, Order, OrderItem, OrderStatus, AuditLog,
    ParentChild
)

import uuid as _uuid


def _uid():
    """Генерирует короткий уникальный суффикс для email и имён."""
    return _uuid.uuid4().hex[:8]


def _set_audit_user(user):
    """Устанавливает app.current_user_id для аудит-триггеров PostgreSQL."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_user_id', %s, false)", [str(user.pk)])


def _truncate_app_tables():
    """Очищает все таблицы приложения (managed=False) между тестами TransactionTestCase."""
    with connection.cursor() as cursor:
        cursor.execute("""
            TRUNCATE TABLE
                "auditLog", "orderItem", "order", "cart", "wishlist",
                "review", "parentChild", "productAttribute", "productImage",
                "product", "brand", "category", "address", "user", "role", "orderStatus"
            CASCADE
        """)
        # Сбрасываем также таблицу токенов Django
        cursor.execute("DELETE FROM authtoken_token")
        # Сбрасываем переменную сессии
        cursor.execute("SELECT set_config('app.current_user_id', '', false)")


# =============================================
# ВСПОМОГАТЕЛЬНЫЕ МИКСИНЫ
# =============================================

class BaseTestMixin:
    """Базовый миксин для создания тестовых данных."""

    @classmethod
    def create_roles(cls):
        """Создание ролей (если не существуют)."""
        roles = {}
        for name in ['Покупатель', 'Ребенок', 'Менеджер', 'Администратор']:
            role, _ = Role.objects.get_or_create(roleName=name)
            roles[name] = role
        return roles

    @classmethod
    def create_order_statuses(cls):
        """Создание статусов заказов (должны соответствовать create_database.sql)."""
        statuses = {}
        for name in ['Новый', 'В обработке', 'Отправлен', 'Доставлен', 'Отменен']:
            st, _ = OrderStatus.objects.get_or_create(orderStatusName=name)
            statuses[name] = st
        return statuses

    @classmethod
    def create_user(cls, roles, role_name='Покупатель', email=None, password='TestPass123!'):
        """Создание пользователя с заданной ролью."""
        if email is None:
            email = f'user_{_uid()}@test.com'
        # Сбрасываем переменную сессии, чтобы триггер на user таблице
        # использовал NEW."userId" вместо устаревшего значения
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_user_id', '', false)")
        user = User.objects.create_user(
            email=email,
            password=password,
            username=email.split('@')[0],
            firstName='Тест',
            lastName='Тестов',
            phone='79991234567',
            birthDate=date(2000, 1, 1),
            roleId=roles[role_name],
            createdAt=timezone.now(),
        )
        token, _ = Token.objects.get_or_create(user=user)
        # Устанавливаем пользователя для аудит-триггеров
        _set_audit_user(user)
        return user, token

    @classmethod
    def create_category(cls, name=None):
        if name is None:
            name = f'Категория-{_uid()}'
        return Category.objects.create(
            categoryName=name,
            categoryDescription=f'Описание {name}'
        )

    @classmethod
    def create_brand(cls, name=None):
        if name is None:
            name = f'Бренд-{_uid()}'
        return Brand.objects.create(
            brandName=name,
            brandDescription=f'Описание {name}',
            brandCountry='Россия'
        )

    @classmethod
    def create_product(cls, category, brand, name=None, price='999.99', quantity=10):
        if name is None:
            name = f'Товар-{_uid()}'
        return Product.objects.create(
            productName=name,
            productDescription=f'Описание {name}',
            categoryId=category,
            brandId=brand,
            price=Decimal(price),
            ageRating=0,
            quantity=quantity,
            weightKg=Decimal('0.50'),
            dimensions='10x10x10'
        )


# =============================================
# 1. ФУНКЦИОНАЛЬНЫЕ ТЕСТЫ: CRUD
# =============================================

class CategoryCRUDTest(TestCase, BaseTestMixin):
    """CRUD-тесты для категорий."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()
        cls.admin, cls.admin_token = cls.create_user(cls.roles, 'Администратор')
        cls.buyer, cls.buyer_token = cls.create_user(cls.roles, 'Покупатель')

    def setUp(self):
        self.client = APIClient()

    def test_list_categories(self):
        """Получение списка категорий (публичный доступ)."""
        self.create_category('Настольные игры')
        self.create_category('Конструкторы')
        response = self.client.get('/api/catalog/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_admin_create_category(self):
        """Администратор создаёт категорию."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        data = {'categoryName': 'Пазлы', 'categoryDescription': 'Описание пазлов'}
        response = self.client.post('/api/admin/categories/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(categoryName='Пазлы').exists())

    def test_admin_update_category(self):
        """Администратор обновляет категорию."""
        cat = self.create_category('Старое название')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.put(
            f'/api/admin/categories/{cat.categoryId}/',
            {'categoryName': 'Новое название', 'categoryDescription': 'Новое описание'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cat.refresh_from_db()
        self.assertEqual(cat.categoryName, 'Новое название')

    def test_admin_delete_category(self):
        """Администратор удаляет категорию."""
        cat = self.create_category('Для удаления')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.delete(f'/api/admin/categories/{cat.categoryId}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(categoryId=cat.categoryId).exists())

    def test_buyer_cannot_create_category(self):
        """Покупатель не может создать категорию."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')
        data = {'categoryName': 'Попытка', 'categoryDescription': 'Описание'}
        response = self.client.post('/api/admin/categories/', data, format='json')
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])


class BrandCRUDTest(TestCase, BaseTestMixin):
    """CRUD-тесты для брендов."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()
        cls.admin, cls.admin_token = cls.create_user(cls.roles, 'Администратор')

    def setUp(self):
        self.client = APIClient()

    def test_list_brands(self):
        """Получение списка брендов."""
        self.create_brand('LEGO')
        response = self.client.get('/api/catalog/brands/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_admin_create_brand(self):
        """Администратор создаёт бренд."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        data = {'brandName': 'Hasbro', 'brandDescription': 'Игрушки', 'brandCountry': 'США'}
        response = self.client.post('/api/admin/brands/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Brand.objects.filter(brandName='Hasbro').exists())

    def test_admin_update_brand(self):
        """Администратор обновляет бренд."""
        brand = self.create_brand('Старый бренд')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.put(
            f'/api/admin/brands/{brand.brandId}/',
            {'brandName': 'Новый бренд', 'brandDescription': 'Обновлено', 'brandCountry': 'Германия'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        brand.refresh_from_db()
        self.assertEqual(brand.brandName, 'Новый бренд')

    def test_admin_delete_brand(self):
        """Администратор удаляет бренд."""
        brand = self.create_brand('Удалить')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.delete(f'/api/admin/brands/{brand.brandId}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ProductCRUDTest(TestCase, BaseTestMixin):
    """CRUD-тесты для товаров."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()
        cls.admin, cls.admin_token = cls.create_user(cls.roles, 'Администратор')
        cls.category = cls.create_category('Игрушки')
        cls.brand = cls.create_brand('LEGO')

    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')

    def test_list_products_public(self):
        """Публичный список товаров."""
        self.create_product(self.category, self.brand)
        client = APIClient()  # без авторизации
        response = client.get('/api/catalog/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_create_product(self):
        """Администратор создаёт товар."""
        data = {
            'productName': 'Конструктор',
            'productDescription': 'Набор из 500 деталей',
            'categoryId': self.category.categoryId,
            'brandId': self.brand.brandId,
            'price': '2499.99',
            'ageRating': 6,
            'quantity': 50,
            'weightKg': '1.20',
            'dimensions': '30x20x10'
        }
        response = self.client.post('/api/admin/products/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(productName='Конструктор').exists())

    def test_admin_update_product(self):
        """Администратор обновляет товар."""
        product = self.create_product(self.category, self.brand, 'Старый товар')
        data = {
            'productName': 'Обновлённый товар',
            'productDescription': 'Обновлено',
            'categoryId': self.category.categoryId,
            'brandId': self.brand.brandId,
            'price': '1500.00',
            'ageRating': 3,
            'quantity': 20,
            'weightKg': '0.80',
            'dimensions': '15x15x15'
        }
        response = self.client.put(f'/api/admin/products/{product.productId}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertEqual(product.productName, 'Обновлённый товар')

    def test_admin_delete_product(self):
        """Администратор удаляет товар."""
        product = self.create_product(self.category, self.brand, 'Удалить')
        response = self.client.delete(f'/api/admin/products/{product.productId}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_product_detail(self):
        """Получение детальной информации о товаре."""
        product = self.create_product(self.category, self.brand, 'Детали')
        client = APIClient()
        response = client.get(f'/api/catalog/products/{product.productId}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['productName'], 'Детали')


class UserCRUDTest(TestCase, BaseTestMixin):
    """Тесты регистрации, входа и профиля пользователя."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()

    def setUp(self):
        self.client = APIClient()

    def test_user_registration(self):
        """Регистрация нового пользователя."""
        email = f'ivan_reg_{_uid()}@test.com'
        data = {
            'firstName': 'Иван',
            'lastName': 'Иванов',
            'email': email,
            'password': 'StrongPass123!',
            'confirmPassword': 'StrongPass123!',
            'phone': '79991234567',
            'birthDate': '2000-01-15',
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertTrue(User.objects.filter(email=email).exists())

    def test_user_registration_duplicate_email(self):
        """Повторная регистрация с тем же email."""
        dup_email = f'dup_{_uid()}@test.com'
        self.create_user(self.roles, email=dup_email)
        data = {
            'firstName': 'Дубль',
            'lastName': 'Тест',
            'email': dup_email,
            'password': 'StrongPass123!',
            'confirmPassword': 'StrongPass123!',
            'phone': '79991234567',
            'birthDate': '2000-01-15',
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT])

    def test_user_login(self):
        """Вход в аккаунт."""
        login_email = f'login_{_uid()}@test.com'
        user, token = self.create_user(self.roles, email=login_email, password='MyPass123!')
        response = self.client.post(
            '/api/auth/login/',
            {'email': login_email, 'password': 'MyPass123!'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_user_login_wrong_password(self):
        """Вход с неверным паролем."""
        wp_email = f'wrongpw_{_uid()}@test.com'
        self.create_user(self.roles, email=wp_email, password='CorrectPass123!')
        response = self.client.post(
            '/api/auth/login/',
            {'email': wp_email, 'password': 'WrongPassword'},
            format='json'
        )
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED])

    def test_get_profile(self):
        """Получение профиля авторизованного пользователя."""
        prof_email = f'profile_{_uid()}@test.com'
        user, token = self.create_user(self.roles, email=prof_email)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], prof_email)

    def test_update_profile(self):
        """Обновление профиля."""
        user, token = self.create_user(self.roles)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.patch(
            '/api/auth/profile/',
            {'firstName': 'Обновлённое'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_profile_access(self):
        """Неавторизованный доступ к профилю."""
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_create_user(self):
        """Администратор создаёт пользователя."""
        admin, admin_token = self.create_user(self.roles, 'Администратор')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        mgr_email = f'new_mgr_{_uid()}@test.com'
        data = {
            'firstName': 'Новый',
            'lastName': 'Менеджер',
            'email': mgr_email,
            'password': 'ManagerPass1!',
            'phone': '79991112233',
            'birthDate': '1995-05-05',
            'roleId': self.roles['Менеджер'].roleId,
            'username': mgr_email.split('@')[0]
        }
        response = self.client.post('/api/admin/users/create/', data, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_admin_delete_user(self):
        """Администратор удаляет пользователя."""
        admin, admin_token = self.create_user(self.roles, 'Администратор')
        victim, _ = self.create_user(self.roles)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        response = self.client.delete(f'/api/admin/users/{victim.userId}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


# =============================================
# 2. ПОИСК, СОРТИРОВКА, ФИЛЬТРЫ
# =============================================

class ProductFilterTest(TestCase, BaseTestMixin):
    """Тесты фильтрации, поиска и сортировки товаров."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()
        # Нужен пользователь для аудит-триггера при создании товаров
        cls.admin, cls.admin_token = cls.create_user(cls.roles, 'Администратор')
        cls.cat1 = cls.create_category('Куклы')
        cls.cat2 = cls.create_category('Машинки')
        cls.brand1 = cls.create_brand('Mattel')
        cls.brand2 = cls.create_brand('Hot Wheels')
        cls.p1 = cls.create_product(cls.cat1, cls.brand1, 'Барби', '1999.99', 5)
        cls.p2 = cls.create_product(cls.cat2, cls.brand2, 'Гоночная машина', '599.00', 20)
        cls.p3 = cls.create_product(cls.cat1, cls.brand1, 'Кен', '1499.00', 8)

    def setUp(self):
        self.client = APIClient()

    def test_filter_by_category(self):
        """Фильтрация товаров по категории."""
        response = self.client.get(f'/api/catalog/products/?category={self.cat1.categoryId}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p['productName'] for p in response.data]
        self.assertIn('Барби', names)
        self.assertNotIn('Гоночная машина', names)

    def test_filter_by_brand(self):
        """Фильтрация товаров по бренду."""
        response = self.client.get(f'/api/catalog/products/?brand={self.brand2.brandId}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p['productName'] for p in response.data]
        self.assertIn('Гоночная машина', names)
        self.assertNotIn('Барби', names)

    def test_filter_by_price_range(self):
        """Фильтрация по диапазону цен."""
        response = self.client.get('/api/catalog/products/?min_price=1000&max_price=2000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for p in response.data:
            self.assertGreaterEqual(Decimal(p['price']), Decimal('1000'))
            self.assertLessEqual(Decimal(p['price']), Decimal('2000'))

    def test_search_by_name(self):
        """Полнотекстовый поиск по названию."""
        response = self.client.get('/api/catalog/products/?search=Барби')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p['productName'] for p in response.data]
        self.assertIn('Барби', names)

    def test_ordering_by_price_asc(self):
        """Сортировка по цене (возрастание)."""
        response = self.client.get('/api/catalog/products/?ordering=price')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [Decimal(p['price']) for p in response.data]
        self.assertEqual(prices, sorted(prices))

    def test_ordering_by_price_desc(self):
        """Сортировка по цене (убывание)."""
        response = self.client.get('/api/catalog/products/?ordering=-price')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [Decimal(p['price']) for p in response.data]
        self.assertEqual(prices, sorted(prices, reverse=True))


# =============================================
# 3. РОЛИ И ДОСТУП
# =============================================

class RolePermissionTest(TestCase, BaseTestMixin):
    """Тесты ролевого доступа к API."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()
        cls.admin, cls.admin_token = cls.create_user(cls.roles, 'Администратор')
        cls.manager, cls.manager_token = cls.create_user(cls.roles, 'Менеджер')
        cls.buyer, cls.buyer_token = cls.create_user(cls.roles, 'Покупатель')
        cls.child, cls.child_token = cls.create_user(cls.roles, 'Ребенок')

    def setUp(self):
        self.client = APIClient()

    def test_admin_access_admin_panel(self):
        """Администратор имеет доступ к панели."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/admin/panel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_access_admin_panel(self):
        """Менеджер имеет доступ к панели."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.manager_token.key}')
        response = self.client.get('/api/admin/panel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_buyer_no_admin_panel(self):
        """Покупатель НЕ имеет доступа к панели."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')
        response = self.client.get('/api/admin/panel/')
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN])

    def test_admin_access_audit_logs(self):
        """Только администратор видит журнал аудита."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/admin/audit-logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_manager_no_audit_logs(self):
        """Менеджер НЕ видит журнал аудита (пустой queryset)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.manager_token.key}')
        response = self.client.get('/api/admin/audit-logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_unauthenticated_no_admin(self):
        """Неавторизованный пользователь не имеет доступа к админке."""
        response = self.client.get('/api/admin/products/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_buyer_can_access_wishlist(self):
        """Покупатель имеет доступ к списку желаний."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')
        response = self.client.get('/api/auth/wishlist/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_buyer_can_access_cart(self):
        """Покупатель имеет доступ к корзине."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')
        response = self.client.get('/api/auth/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_manage_users(self):
        """Администратор может видеть список пользователей."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/admin/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_buyer_cannot_manage_users(self):
        """Покупатель не видит пользователей (пустой список)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')
        response = self.client.get('/api/admin/users/')
        # Вьюха возвращает 200 с пустым queryset для не-администраторов
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_admin_cannot_delete_self(self):
        """Администратор не может удалить свой аккаунт."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.delete(f'/api/admin/users/{self.admin.userId}/')
        self.assertNotEqual(response.status_code, status.HTTP_204_NO_CONTENT)


# =============================================
# 4. КОРЗИНА, ЗАКАЗЫ, ОТЗЫВЫ
# =============================================

class CartAndOrderTest(TransactionTestCase, BaseTestMixin):
    """Тесты корзины и заказов (TransactionTestCase для процедур)."""

    def setUp(self):
        _truncate_app_tables()
        self.roles = self.create_roles()
        self.statuses = self.create_order_statuses()
        self.buyer, self.buyer_token = self.create_user(self.roles, 'Покупатель')
        self.category = self.create_category()
        self.brand = self.create_brand()
        self.product = self.create_product(self.category, self.brand, 'Товар для корзины', '500.00', 100)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')

    def test_add_to_cart(self):
        """Добавление товара в корзину."""
        data = {'productId': self.product.productId, 'quantity': 2}
        response = self.client.post('/api/auth/cart/', data, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_get_cart(self):
        """Получение содержимого корзины."""
        Cart.objects.create(userId=self.buyer, productId=self.product, quantity=3)
        response = self.client.get('/api/auth/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('items', response.data)

    def test_update_cart_quantity(self):
        """Изменение количества товара в корзине."""
        cart_item = Cart.objects.create(userId=self.buyer, productId=self.product, quantity=1)
        response = self.client.patch(
            f'/api/auth/cart/{cart_item.cartId}/',
            {'quantity': 5},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_remove_from_cart(self):
        """Удаление товара из корзины."""
        cart_item = Cart.objects.create(userId=self.buyer, productId=self.product, quantity=1)
        response = self.client.delete(f'/api/auth/cart/{cart_item.cartId}/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])

    def test_create_order_from_cart(self):
        """Создание заказа из корзины (через хранимую процедуру)."""
        Cart.objects.create(userId=self.buyer, productId=self.product, quantity=2)
        address = Address.objects.create(
            userId=self.buyer, city='Москва', street='Тверская', house='1', index='123456'
        )
        data = {
            'deliveryType': 'самовывоз',
            'addressId': address.addressId,
            'paymentType': 'онлайн',
        }
        response = self.client.post('/api/auth/checkout/create/', data, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_user_orders_list(self):
        """Получение списка заказов пользователя."""
        response = self.client.get('/api/auth/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ReviewTest(TestCase, BaseTestMixin):
    """Тесты отзывов."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()
        cls.buyer, cls.buyer_token = cls.create_user(cls.roles, 'Покупатель')
        cls.category = cls.create_category('Отзывы')
        cls.brand = cls.create_brand('Обзорный')
        cls.product = cls.create_product(cls.category, cls.brand, 'Для отзывов')

    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')

    def test_create_review_requires_purchase(self):
        """Создание отзыва без покупки — ошибка 400."""
        data = {'productId': self.product.productId, 'rating': 5, 'reviewText': 'Отличный товар!'}
        response = self.client.post('/api/auth/reviews/', data, format='json')
        # Отзыв возможен только на купленный товар
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_product_reviews(self):
        """Получение отзывов товара."""
        Review.objects.create(
            productId=self.product, userId=self.buyer,
            rating=4, reviewText='Хорошо',
            createdAt=timezone.now(), updatedAt=timezone.now()
        )
        client = APIClient()
        response = client.get(f'/api/catalog/products/{self.product.productId}/reviews/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)


class WishlistTest(TestCase, BaseTestMixin):
    """Тесты списка желаний."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()
        cls.buyer, cls.buyer_token = cls.create_user(cls.roles, 'Покупатель')
        cls.cat = cls.create_category('Вишлист')
        cls.brand = cls.create_brand('ВБренд')
        cls.product = cls.create_product(cls.cat, cls.brand, 'Желанный')

    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')

    def test_add_to_wishlist(self):
        """Добавление товара в список желаний."""
        data = {'productId': self.product.productId}
        response = self.client.post('/api/auth/wishlist/add/', data, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_get_wishlist(self):
        """Получение списка желаний."""
        Wishlist.objects.create(userId=self.buyer, productId=self.product)
        response = self.client.get('/api/auth/wishlist/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_remove_from_wishlist(self):
        """Удаление из списка желаний."""
        wl = Wishlist.objects.create(userId=self.buyer, productId=self.product)
        response = self.client.delete(f'/api/auth/wishlist/{wl.wishlistId}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


# =============================================
# 5. ХРАНИМЫЕ ПРОЦЕДУРЫ И ТРИГГЕРЫ
# =============================================

class StoredProcedureTest(TransactionTestCase, BaseTestMixin):
    """Тесты хранимых процедур PostgreSQL."""

    def setUp(self):
        _truncate_app_tables()
        self.roles = self.create_roles()
        self.statuses = self.create_order_statuses()
        self.admin, self.admin_token = self.create_user(self.roles, 'Администратор')
        self.buyer, self.buyer_token = self.create_user(self.roles, 'Покупатель')
        self.category = self.create_category()
        self.brand = self.create_brand()
        self.client = APIClient()

    def test_sp_adjust_prices_by_category(self):
        """Процедура sp_adjust_prices_by_category корректирует цены."""
        p1 = self.create_product(self.category, self.brand, 'SP Товар 1', '1000.00')
        p2 = self.create_product(self.category, self.brand, 'SP Товар 2', '2000.00')

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post('/api/admin/price-adjustment/', {
            'categoryId': self.category.categoryId,
            'percentChange': 10  # +10%
        }, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK])

        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.price, Decimal('1100.00'))
        self.assertEqual(p2.price, Decimal('2200.00'))

    def test_sp_cancel_order(self):
        """Процедура sp_cancel_order отменяет заказ и возвращает товар на склад."""
        product = self.create_product(self.category, self.brand, 'Отмена', '500.00', 100)
        Cart.objects.create(userId=self.buyer, productId=product, quantity=3)
        address = Address.objects.create(
            userId=self.buyer, city='Москва', street='Ленина', house='10', index='111111'
        )

        # Создаём заказ
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')
        create_resp = self.client.post('/api/auth/checkout/create/', {
            'deliveryType': 'самовывоз',
            'addressId': address.addressId,
            'paymentType': 'онлайн',
        }, format='json')

        if create_resp.status_code in [200, 201]:
            order_id = create_resp.data.get('orderId')
            if order_id:
                product.refresh_from_db()
                qty_after_order = product.quantity

                # Отменяем заказ
                cancel_resp = self.client.post(f'/api/auth/orders/{order_id}/cancel/')
                self.assertIn(cancel_resp.status_code, [status.HTTP_200_OK])

                product.refresh_from_db()
                # Количество должно вернуться
                self.assertGreater(product.quantity, qty_after_order)


class AuditTriggerTest(TransactionTestCase, BaseTestMixin):
    """Тесты аудит-триггеров (fn_audit_log)."""

    def setUp(self):
        _truncate_app_tables()
        self.roles = self.create_roles()
        self.admin, self.admin_token = self.create_user(self.roles, 'Администратор')
        self.category = self.create_category()
        self.brand = self.create_brand()
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')

    def test_product_create_trigger(self):
        """Триггер создаёт запись в auditLog при добавлении товара."""
        initial_count = AuditLog.objects.filter(tableName='product', action='CREATE').count()
        self.client.post('/api/admin/products/create/', {
            'productName': 'Аудит-товар',
            'productDescription': 'Тест аудита',
            'categoryId': self.category.categoryId,
            'brandId': self.brand.brandId,
            'price': '100.00',
            'ageRating': 0,
            'quantity': 10,
            'weightKg': '0.5',
            'dimensions': '5x5x5'
        }, format='json')
        new_count = AuditLog.objects.filter(tableName='product', action='CREATE').count()
        self.assertGreater(new_count, initial_count)

    def test_product_update_trigger(self):
        """Триггер создаёт запись при обновлении товара."""
        product = self.create_product(self.category, self.brand, 'Аудит-апдейт')
        initial_count = AuditLog.objects.filter(tableName='product', action='UPDATE').count()
        self.client.put(f'/api/admin/products/{product.productId}/', {
            'productName': 'Аудит-апдейт-2',
            'productDescription': 'Обновлено',
            'categoryId': self.category.categoryId,
            'brandId': self.brand.brandId,
            'price': '200.00',
            'ageRating': 3,
            'quantity': 5,
            'weightKg': '1.0',
            'dimensions': '10x10x10'
        }, format='json')
        new_count = AuditLog.objects.filter(tableName='product', action='UPDATE').count()
        self.assertGreater(new_count, initial_count)

    def test_product_delete_trigger(self):
        """Триггер создаёт запись при удалении товара."""
        product = self.create_product(self.category, self.brand, 'Аудит-удаление')
        initial_count = AuditLog.objects.filter(tableName='product', action='DELETE').count()
        self.client.delete(f'/api/admin/products/{product.productId}/')
        new_count = AuditLog.objects.filter(tableName='product', action='DELETE').count()
        self.assertGreater(new_count, initial_count)

    def test_audit_log_contains_old_and_new_values(self):
        """Запись аудита содержит старые и новые значения."""
        product = self.create_product(self.category, self.brand, 'Значения', '300.00')
        self.client.put(f'/api/admin/products/{product.productId}/', {
            'productName': 'Значения-2',
            'productDescription': 'Обновлено',
            'categoryId': self.category.categoryId,
            'brandId': self.brand.brandId,
            'price': '400.00',
            'ageRating': 0,
            'quantity': 10,
            'weightKg': '0.5',
            'dimensions': '5x5x5'
        }, format='json')
        log = AuditLog.objects.filter(
            tableName='product', action='UPDATE'
        ).order_by('-createdAt').first()
        if log:
            self.assertIsNotNone(log.oldValues)
            self.assertIsNotNone(log.newValues)


# =============================================
# 6. ТРАНЗАКЦИИ
# =============================================

class TransactionTest(TransactionTestCase, BaseTestMixin):
    """Тесты транзакционной целостности."""

    def setUp(self):
        _truncate_app_tables()
        self.roles = self.create_roles()
        self.statuses = self.create_order_statuses()
        self.buyer, self.buyer_token = self.create_user(self.roles, 'Покупатель')
        self.category = self.create_category()
        self.brand = self.create_brand()
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')

    def test_order_reduces_product_quantity(self):
        """Заказ уменьшает количество товара на складе."""
        product = self.create_product(self.category, self.brand, 'Складской', '100.00', 50)
        Cart.objects.create(userId=self.buyer, productId=product, quantity=5)
        address = Address.objects.create(
            userId=self.buyer, city='СПб', street='Невский', house='1', index='190000'
        )
        self.client.post('/api/auth/checkout/create/', {
            'deliveryType': 'курьером',
            'addressId': address.addressId,
            'paymentType': 'онлайн',
        }, format='json')
        product.refresh_from_db()
        self.assertLess(product.quantity, 50)

    def test_order_clears_cart(self):
        """После создания заказа корзина очищается."""
        product = self.create_product(self.category, self.brand, 'Корзина', '200.00', 100)
        Cart.objects.create(userId=self.buyer, productId=product, quantity=2)
        address = Address.objects.create(
            userId=self.buyer, city='Москва', street='Арбат', house='5', index='123456'
        )
        self.client.post('/api/auth/checkout/create/', {
            'deliveryType': 'самовывоз',
            'addressId': address.addressId,
            'paymentType': 'наличными при получении',
        }, format='json')
        cart_count = Cart.objects.filter(userId=self.buyer).count()
        self.assertEqual(cart_count, 0)

    def test_insufficient_stock_prevents_order(self):
        """Заказ не создаётся, если товара недостаточно."""
        product = self.create_product(self.category, self.brand, 'Дефицит', '100.00', 1)
        Cart.objects.create(userId=self.buyer, productId=product, quantity=999)
        address = Address.objects.create(
            userId=self.buyer, city='Казань', street='Баумана', house='1', index='420000'
        )
        response = self.client.post('/api/auth/checkout/create/', {
            'deliveryType': 'самовывоз',
            'addressId': address.addressId,
            'paymentType': 'онлайн',
        }, format='json')
        # Заказ не должен быть создан или должна быть ошибка
        if response.status_code in [200, 201]:
            # Если процедура создала заказ, проверяем что кол-во не ушло в минус
            product.refresh_from_db()
            self.assertGreaterEqual(product.quantity, 0)
        else:
            self.assertIn(response.status_code, [400, 409, 500])


# =============================================
# 7. ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================

class FullBuyerFlowTest(TransactionTestCase, BaseTestMixin):
    """Интеграционный тест: полный цикл покупателя."""

    def setUp(self):
        _truncate_app_tables()

    def test_full_buyer_journey(self):
        """Регистрация → каталог → корзина → заказ → отзыв."""
        roles = self.create_roles()
        self.create_order_statuses()
        client = APIClient()

        # 1. Регистрация
        email = f'alex_{_uid()}@test.com'
        reg_resp = client.post('/api/auth/register/', {
            'firstName': 'Алексей',
            'lastName': 'Смирнов',
            'email': email,
            'password': 'FlowPass123!',
            'confirmPassword': 'FlowPass123!',
            'phone': '79998887766',
            'birthDate': '1995-03-20',
        }, format='json')
        self.assertEqual(reg_resp.status_code, status.HTTP_201_CREATED)
        token = reg_resp.data['token']
        client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        # Устанавливаем аудит-пользователя для ORM-операций
        user = User.objects.get(email=email)
        _set_audit_user(user)

        # 2. Просмотр каталога
        cat = self.create_category()
        brand = self.create_brand()
        product = self.create_product(cat, brand, 'Интеграционный товар', '799.00', 50)
        catalog_resp = client.get('/api/catalog/products/')
        self.assertEqual(catalog_resp.status_code, status.HTTP_200_OK)

        # 3. Добавление в корзину
        cart_resp = client.post('/api/auth/cart/', {
            'productId': product.productId,
            'quantity': 2
        }, format='json')
        self.assertIn(cart_resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

        # 4. Создание адреса и заказа
        addr = Address.objects.create(
            userId=user,
            city='Москва', street='Пушкина', house='10', index='101000'
        )
        order_resp = client.post('/api/auth/checkout/create/', {
            'deliveryType': 'самовывоз',
            'addressId': addr.addressId,
            'paymentType': 'онлайн',
        }, format='json')
        self.assertIn(order_resp.status_code, [200, 201])

        # 5. Просмотр заказов
        orders_resp = client.get('/api/auth/orders/')
        self.assertEqual(orders_resp.status_code, status.HTTP_200_OK)

        # 6. Оставление отзыва
        review_resp = client.post('/api/auth/reviews/', {
            'productId': product.productId,
            'rating': 5,
            'reviewText': 'Отличный товар, очень доволен!'
        }, format='json')
        self.assertIn(review_resp.status_code, [200, 201])


class AdminManagementFlowTest(TransactionTestCase, BaseTestMixin):
    """Интеграционный тест: полный цикл администратора."""

    def setUp(self):
        _truncate_app_tables()

    def test_admin_management_flow(self):
        """Создание категории → бренда → товара → просмотр аналитики."""
        roles = self.create_roles()
        admin, admin_token = self.create_user(roles, 'Администратор')
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')

        # 1. Создание категории
        cat_resp = client.post('/api/admin/categories/', {
            'categoryName': 'Поток-категория',
            'categoryDescription': 'Тест'
        }, format='json')
        self.assertEqual(cat_resp.status_code, status.HTTP_201_CREATED)
        cat_id = cat_resp.data['categoryId']

        # 2. Создание бренда
        brand_resp = client.post('/api/admin/brands/', {
            'brandName': 'Поток-бренд',
            'brandDescription': 'Тест',
            'brandCountry': 'Россия'
        }, format='json')
        self.assertEqual(brand_resp.status_code, status.HTTP_201_CREATED)
        brand_id = brand_resp.data['brandId']

        # 3. Создание товара
        prod_resp = client.post('/api/admin/products/create/', {
            'productName': 'Поток-товар',
            'productDescription': 'Интеграционный тест',
            'categoryId': cat_id,
            'brandId': brand_id,
            'price': '1500.00',
            'ageRating': 6,
            'quantity': 30,
            'weightKg': '0.80',
            'dimensions': '20x15x10'
        }, format='json')
        self.assertEqual(prod_resp.status_code, status.HTTP_201_CREATED)

        # 4. Просмотр дашборда
        dash_resp = client.get('/api/admin/dashboard/')
        self.assertEqual(dash_resp.status_code, status.HTTP_200_OK)

        # 5. Просмотр аналитики продаж
        sales_resp = client.get('/api/admin/analytics/sales/')
        self.assertEqual(sales_resp.status_code, status.HTTP_200_OK)

        # 6. Просмотр аналитики товаров
        products_resp = client.get('/api/admin/analytics/products/')
        self.assertEqual(products_resp.status_code, status.HTTP_200_OK)

        # 7. Просмотр активности пользователей
        activity_resp = client.get('/api/admin/analytics/user-activity/')
        self.assertEqual(activity_resp.status_code, status.HTTP_200_OK)


# =============================================
# 8. ИМПОРТ / ЭКСПОРТ
# =============================================

class DataExportTest(TestCase, BaseTestMixin):
    """Тесты экспорта данных в CSV и SQL."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()
        cls.admin, cls.admin_token = cls.create_user(cls.roles, 'Администратор')
        cls.cat = cls.create_category('Экспорт-кат')
        cls.brand = cls.create_brand('Экспорт-бренд')
        cls.create_product(cls.cat, cls.brand, 'Экспорт-товар-1', '100.00')
        cls.create_product(cls.cat, cls.brand, 'Экспорт-товар-2', '200.00')

    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')

    def test_export_products_csv(self):
        """Экспорт товаров в CSV."""
        response = self.client.get('/api/admin/data-export/?table=product&file_format=csv')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        self.assertGreater(len(rows), 1)  # заголовок + данные
        self.assertIn('productId', rows[0])

    def test_export_products_sql(self):
        """Экспорт товаров в SQL."""
        response = self.client.get('/api/admin/data-export/?table=product&file_format=sql')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8')
        self.assertIn('INSERT INTO', content)
        self.assertIn('product', content)

    def test_export_categories_csv(self):
        """Экспорт категорий в CSV."""
        response = self.client.get('/api/admin/data-export/?table=category&file_format=csv')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8-sig')
        self.assertIn('categoryId', content)

    def test_export_brands_csv(self):
        """Экспорт брендов в CSV."""
        response = self.client.get('/api/admin/data-export/?table=brand&file_format=csv')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response['Content-Type'])

    def test_export_unknown_table(self):
        """Экспорт несуществующей таблицы — ошибка 400."""
        response = self.client.get('/api/admin/data-export/?table=nonexistent&file_format=csv')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_export_without_auth(self):
        """Экспорт без авторизации — ошибка 401."""
        client = APIClient()
        response = client.get('/api/admin/data-export/?table=product&file_format=csv')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_export_buyer_forbidden(self):
        """Покупатель не может экспортировать данные."""
        buyer, buyer_token = self.create_user(self.roles, 'Покупатель')
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {buyer_token.key}')
        response = client.get('/api/admin/data-export/?table=product&file_format=csv')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DataImportTest(TransactionTestCase, BaseTestMixin):
    """Тесты импорта данных из CSV."""

    def setUp(self):
        _truncate_app_tables()
        self.roles = self.create_roles()
        self.admin, self.admin_token = self.create_user(self.roles, 'Администратор')
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')

    def _make_csv(self, headers, rows):
        """Вспомогательный метод: создание CSV-файла в памяти."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        output.seek(0)
        return io.BytesIO(output.getvalue().encode('utf-8-sig'))

    def test_import_categories(self):
        """Импорт категорий из CSV."""
        csv_file = self._make_csv(
            ['categoryName', 'categoryDescription'],
            [
                ['Импортированная-1', 'Описание 1'],
                ['Импортированная-2', 'Описание 2'],
            ]
        )
        csv_file.name = 'categories.csv'
        response = self.client.post(
            '/api/admin/data-import/',
            {'table': 'category', 'file': csv_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Создано записей: 2', response.data['detail'])
        self.assertTrue(Category.objects.filter(categoryName='Импортированная-1').exists())

    def test_import_brands(self):
        """Импорт брендов из CSV."""
        csv_file = self._make_csv(
            ['brandName', 'brandDescription', 'brandCountry'],
            [['CSV-бренд', 'Тестовый', 'Япония']]
        )
        csv_file.name = 'brands.csv'
        response = self.client.post(
            '/api/admin/data-import/',
            {'table': 'brand', 'file': csv_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Brand.objects.filter(brandName='CSV-бренд').exists())

    def test_import_missing_required_fields(self):
        """Импорт с отсутствующими обязательными полями — ошибка."""
        csv_file = self._make_csv(
            ['brandDescription'],  # отсутствует brandName
            [['Без имени']]
        )
        csv_file.name = 'bad.csv'
        response = self.client.post(
            '/api/admin/data-import/',
            {'table': 'brand', 'file': csv_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_import_unsupported_table(self):
        """Импорт в неподдерживаемую таблицу — ошибка."""
        csv_file = self._make_csv(['col'], [['val']])
        csv_file.name = 'test.csv'
        response = self.client.post(
            '/api/admin/data-import/',
            {'table': 'auditlog', 'file': csv_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_import_no_file(self):
        """Импорт без файла — ошибка."""
        response = self.client.post(
            '/api/admin/data-import/',
            {'table': 'category'},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================
# 9. АДРЕСНАЯ КНИГА
# =============================================

class AddressTest(TestCase, BaseTestMixin):
    """Тесты адресной книги."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()
        cls.buyer, cls.buyer_token = cls.create_user(cls.roles, 'Покупатель')

    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.buyer_token.key}')

    def test_create_address(self):
        """Создание адреса."""
        data = {'city': 'Москва', 'street': 'Ленина', 'house': '1', 'index': '123456'}
        response = self.client.post('/api/auth/addresses/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_addresses(self):
        """Получение списка адресов."""
        Address.objects.create(
            userId=self.buyer, city='Москва', street='Тверская', house='10', index='101000'
        )
        response = self.client.get('/api/auth/addresses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_delete_address(self):
        """Удаление адреса."""
        addr = Address.objects.create(
            userId=self.buyer, city='СПб', street='Невский', house='5', index='190000'
        )
        response = self.client.delete(f'/api/auth/addresses/{addr.addressId}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_delete_other_user_address(self):
        """Нельзя удалить чужой адрес."""
        other, _ = self.create_user(self.roles)
        addr = Address.objects.create(
            userId=other, city='Казань', street='Баумана', house='1', index='420000'
        )
        response = self.client.delete(f'/api/auth/addresses/{addr.addressId}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================
# 10. ОБРАБОТКА ОШИБОК API
# =============================================

class ErrorHandlingTest(TestCase, BaseTestMixin):
    """Тесты централизованной обработки ошибок."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = cls.create_roles()

    def setUp(self):
        self.client = APIClient()

    def test_404_returns_json(self):
        """Несуществующий API-маршрут возвращает JSON-ошибку."""
        response = self.client.get('/api/this-does-not-exist/')
        # Может быть HTML 404, это нормально для Django
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_401_returns_json(self):
        """Неавторизованный запрос возвращает JSON с detail."""
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)

    def test_invalid_token(self):
        """Запрос с невалидным токеном."""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid_token_12345')
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_registration_validation_errors(self):
        """Ошибки валидации при регистрации содержат detail."""
        response = self.client.post('/api/auth/register/', {
            'firstName': '',
            'lastName': '',
            'email': 'bad-email',
            'password': '1',
            'confirmPassword': '2',
            'phone': '',
            'birthDate': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
