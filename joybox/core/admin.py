from django.contrib import admin
from .models import (
    Role, User, Category, Brand, Product, ProductImage, ProductAttribute,
    Address, OrderStatus, Order, OrderItem, Review, Wishlist, Cart,
    ParentChild, AuditLog
)


# --- Inline для редактирования фото и характеристик на странице продукта ---

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('url', 'altText', 'isMain')
    verbose_name = 'Изображение'
    verbose_name_plural = 'Фотографии продукта'


class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 1
    fields = ('productAttributeName', 'productAttributeValue', 'productAttributeUnit')
    verbose_name = 'Характеристика'
    verbose_name_plural = 'Характеристики продукта'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('productName', 'categoryId', 'brandId', 'price', 'quantity')
    list_filter = ('categoryId', 'brandId')
    search_fields = ('productName', 'productDescription')
    inlines = [ProductImageInline, ProductAttributeInline]
    fieldsets = (
        (None, {
            'fields': ('productName', 'productDescription', 'categoryId', 'brandId')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'quantity', 'ageRating', 'weightKg', 'dimensions')
        }),
    )


# --- Управление категориями ---

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('categoryId', 'categoryName')
    search_fields = ('categoryName', 'categoryDescription')
    list_display_links = ('categoryName',)


# --- Управление брендами ---

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('brandId', 'brandName', 'brandCountry')
    search_fields = ('brandName', 'brandDescription', 'brandCountry')
    list_display_links = ('brandName',)
    list_filter = ('brandCountry',)


# --- Остальные модели (без изменений) ---

admin.site.register(Role)
admin.site.register(User)
admin.site.register(Address)
admin.site.register(OrderStatus)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Review)
admin.site.register(Wishlist)
admin.site.register(Cart)
admin.site.register(ParentChild)
admin.site.register(AuditLog)

# Изображения и атрибуты можно редактировать и отдельно (например, для массовых правок)
admin.site.register(ProductImage)
admin.site.register(ProductAttribute)
