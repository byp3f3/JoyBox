from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class Role(models.Model):
    roleId = models.AutoField(primary_key=True)
    roleName = models.CharField(max_length=100, verbose_name='Название роли')
    
    class Meta:
        managed = False
        db_table = 'role'
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'
    
    def __str__(self):
        return str(self.roleName)

class User(AbstractUser):
    
    userId = models.BigAutoField(primary_key=True)
    lastName = models.CharField(max_length=100, verbose_name='Фамилия')
    firstName = models.CharField(max_length=100, verbose_name='Имя')
    middleName = models.CharField(max_length=100, null=True, blank=True, verbose_name='Отчество')
    email = models.EmailField(max_length=255, unique=True, verbose_name='Email')
    password = models.CharField(max_length=100, verbose_name='Пароль')
    roleId = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='roleId', verbose_name='Роль')
    phone = models.CharField(max_length=11, verbose_name='Телефон')
    birthDate = models.DateField(verbose_name='Дата рождения')
    createdAt = models.DateTimeField(verbose_name='Дата создания')
    
    # Override username field to make it non-unique (email will be used for login)
    username = models.CharField(max_length=150, unique=False, verbose_name='Имя пользователя')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    # Add related_name to avoid clashes with auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='core_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        related_query_name='core_user'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='core_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        related_query_name='core_user'
    )
    
    class Meta(AbstractUser.Meta):
        managed = False
        db_table = 'user'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return f"{self.firstName} {self.lastName}"

class Category(models.Model):
    categoryId = models.AutoField(primary_key=True)
    categoryName = models.CharField(max_length=100, verbose_name='Название категории')
    categoryDescription = models.TextField(verbose_name='Описание категории')
    
    class Meta:
        managed = False
        db_table = 'category'
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
    
    def __str__(self):
        return str(self.categoryName)

class Brand(models.Model):
    brandId = models.AutoField(primary_key=True)
    brandName = models.CharField(max_length=100, verbose_name='Название бренда')
    brandDescription = models.TextField(verbose_name='Описание бренда')
    brandCountry = models.CharField(max_length=100, verbose_name='Страна бренда')
    
    class Meta:
        managed = False
        db_table = 'brand'
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
    
    def __str__(self):
        return str(self.brandName)

class Product(models.Model):
    productId = models.BigAutoField(primary_key=True)
    productName = models.CharField(max_length=100, verbose_name='Название продукта')
    productDescription = models.TextField(verbose_name='Описание продукта')
    categoryId = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='categoryId', verbose_name='Категория')
    brandId = models.ForeignKey(Brand, on_delete=models.CASCADE, db_column='brandId', verbose_name='Бренд')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    ageRating = models.IntegerField(verbose_name='Возрастной рейтинг')
    quantity = models.IntegerField(verbose_name='Количество')
    weightKg = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Вес (кг)')
    dimensions = models.CharField(max_length=50, verbose_name='Размеры')
    
    class Meta:
        managed = False
        db_table = 'product'
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
    
    def __str__(self):
        return str(self.productName)

    def get_average_rating(self):
        from django.db.models import Avg
        reviews = self.review_set.all()
        if reviews.exists():
            return reviews.aggregate(Avg('rating'))['rating__avg']
        return 0.0

    def get_review_count(self):
        return self.review_set.count()

class ProductImage(models.Model):
    productImageId = models.BigAutoField(primary_key=True)
    productId = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='productId', verbose_name='Продукт')
    url = models.CharField(max_length=500, verbose_name='URL изображения')
    altText = models.CharField(max_length=100, verbose_name='Альтернативный текст')
    isMain = models.BooleanField(default=False, verbose_name='Основное изображение')
    
    class Meta:
        managed = False
        db_table = 'productImage'
        verbose_name = 'Изображение продукта'
        verbose_name_plural = 'Изображения продуктов'
    
    def __str__(self):
        return f"Image for {self.productId}"

class ProductAttribute(models.Model):
    productAttributeId = models.BigAutoField(primary_key=True)
    productId = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='productId', verbose_name='Продукт')
    productAttributeName = models.CharField(max_length=100, verbose_name='Название атрибута')
    productAttributeValue = models.CharField(max_length=100, verbose_name='Значение атрибута')
    productAttributeUnit = models.CharField(max_length=50, null=True, blank=True, verbose_name='Единица измерения')
    
    class Meta:
        managed = False
        db_table = 'productAttribute'
        verbose_name = 'Атрибут продукта'
        verbose_name_plural = 'Атрибуты продуктов'
    
    def __str__(self):
        return f"{self.productAttributeName}: {self.productAttributeValue}"

class Address(models.Model):
    addressId = models.BigAutoField(primary_key=True)
    userId = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId', verbose_name='Пользователь')
    city = models.CharField(max_length=100, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    house = models.CharField(max_length=50, verbose_name='Дом')
    flat = models.CharField(max_length=10, null=True, blank=True, verbose_name='Квартира')
    index = models.CharField(max_length=6, verbose_name='Индекс')
    
    class Meta:
        managed = False
        db_table = 'address'
        verbose_name = 'Адрес'
        verbose_name_plural = 'Адреса'
    
    def __str__(self):
        return f"{self.city}, {self.street}, {self.house}"

class OrderStatus(models.Model):
    orderStatusId = models.AutoField(primary_key=True)
    orderStatusName = models.CharField(max_length=100, verbose_name='Название статуса заказа')
    
    class Meta:
        managed = False
        db_table = 'orderStatus'
        verbose_name = 'Статус заказа'
        verbose_name_plural = 'Статусы заказов'
    
    def __str__(self):
        return str(self.orderStatusName)

class Order(models.Model):
    # Define choices for delivery type
    DELIVERY_PICKUP = 'самовывоз'
    DELIVERY_POINT = 'пункт выдачи'
    DELIVERY_COURIER = 'курьером'
    
    DELIVERY_TYPE_CHOICES = [
        (DELIVERY_PICKUP, 'Самовывоз'),
        (DELIVERY_POINT, 'Пункт выдачи'),
        (DELIVERY_COURIER, 'Курьером'),
    ]
    
    # Define choices for payment type
    PAYMENT_ONLINE = 'онлайн'
    PAYMENT_CARD = 'картой при получении'
    PAYMENT_CASH = 'наличными при получении'
    
    PAYMENT_TYPE_CHOICES = [
        (PAYMENT_ONLINE, 'Онлайн'),
        (PAYMENT_CARD, 'Картой при получении'),
        (PAYMENT_CASH, 'Наличными при получении'),
    ]
    
    # Define choices for payment status
    PAYMENT_STATUS_PENDING = 'ждет оплаты'
    PAYMENT_STATUS_PAID = 'оплачено'
    PAYMENT_STATUS_REFUND = 'возврат средств'
    PAYMENT_STATUS_REFUNDED = 'средства возвращены'
    
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, 'Ждет оплаты'),
        (PAYMENT_STATUS_PAID, 'Оплачено'),
        (PAYMENT_STATUS_REFUND, 'Возврат средств'),
        (PAYMENT_STATUS_REFUNDED, 'Средства возвращены'),
    ]
    
    orderId = models.BigAutoField(primary_key=True)
    userId = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId', verbose_name='Пользователь')
    orderStatusId = models.ForeignKey(OrderStatus, on_delete=models.CASCADE, db_column='orderStatusId', verbose_name='Статус заказа')
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Итого')
    addressId = models.ForeignKey(Address, on_delete=models.CASCADE, db_column='addressId', verbose_name='Адрес')
    deliveryType = models.CharField(max_length=20, choices=DELIVERY_TYPE_CHOICES, verbose_name='Тип доставки')
    paymentType = models.CharField(max_length=30, choices=PAYMENT_TYPE_CHOICES, verbose_name='Тип оплаты')
    paymentStatus = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, verbose_name='Статус оплаты')
    note = models.CharField(max_length=100, null=True, blank=True, verbose_name='Примечание')
    createdAt = models.DateTimeField(verbose_name='Дата создания')
    
    class Meta:
        managed = False
        db_table = 'order'
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
    
    def __str__(self):
        return f"Order {self.orderId}"

class OrderItem(models.Model):
    orderItemId = models.BigAutoField(primary_key=True)
    orderId = models.ForeignKey(Order, on_delete=models.CASCADE, db_column='orderId', verbose_name='Заказ')
    productId = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='productId', verbose_name='Продукт')
    quantity = models.IntegerField(verbose_name='Количество')
    unitPrice = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена за единицу')
    
    class Meta:
        managed = False
        db_table = 'orderItem'
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'
    
    def __str__(self):
        return f"Order Item {self.orderItemId} for Order {self.orderId}"

class Review(models.Model):
    reviewId = models.BigAutoField(primary_key=True)
    productId = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='productId', verbose_name='Продукт')
    userId = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId', verbose_name='Пользователь')
    rating = models.IntegerField(verbose_name='Рейтинг')
    reviewText = models.TextField(null=True, blank=True, verbose_name='Текст отзыва')
    createdAt = models.DateTimeField(verbose_name='Дата создания')
    updatedAt = models.DateTimeField(verbose_name='Дата обновления')
    
    class Meta:
        managed = False
        db_table = 'review'
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
    
    def __str__(self):
        return f"Review {self.reviewId} for {self.productId}"

class Wishlist(models.Model):
    wishlistId = models.BigAutoField(primary_key=True)
    userId = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId', verbose_name='Пользователь')
    productId = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='productId', verbose_name='Продукт')
    
    class Meta:
        managed = False
        db_table = 'wishlist'
        verbose_name = 'Список желаний'
        verbose_name_plural = 'Списки желаний'
    
    def __str__(self):
        return f"Wishlist item {self.wishlistId}"

class Cart(models.Model):
    cartId = models.BigAutoField(primary_key=True)
    userId = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId', verbose_name='Пользователь')
    productId = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='productId', verbose_name='Продукт')
    quantity = models.IntegerField(verbose_name='Количество')
    
    class Meta:
        managed = False
        db_table = 'cart'
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
    
    def __str__(self):
        return f"Cart item {self.cartId}"

class ParentChild(models.Model):
    parentChildId = models.BigAutoField(primary_key=True)
    userId = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId', related_name='parent_relations', verbose_name='Родитель')
    childId = models.ForeignKey(User, on_delete=models.CASCADE, db_column='childId', related_name='child_relations', verbose_name='Ребенок')
    
    class Meta:
        managed = False
        db_table = 'parentChild'
        verbose_name = 'Родитель-ребенок'
        verbose_name_plural = 'Родитель-ребенок связи'
    
    def __str__(self):
        return f"Parent-Child relation {self.parentChildId}"

class AuditLog(models.Model):
    auditLogId = models.BigAutoField(primary_key=True)
    userId = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId', verbose_name='Пользователь')
    action = models.CharField(max_length=100, verbose_name='Действие')
    tableName = models.CharField(max_length=100, verbose_name='Имя таблицы')
    recordId = models.BigIntegerField(verbose_name='ID записи')
    oldValues = models.JSONField(null=True, blank=True, verbose_name='Старые значения')
    newValues = models.JSONField(null=True, blank=True, verbose_name='Новые значения')
    createdAt = models.DateTimeField(verbose_name='Дата создания')
    
    class Meta:
        managed = False
        db_table = 'auditLog'
        verbose_name = 'Журнал аудита'
        verbose_name_plural = 'Журналы аудита'
    
    def __str__(self):
        return f"Audit log {self.auditLogId}"