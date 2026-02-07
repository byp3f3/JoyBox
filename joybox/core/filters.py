import django_filters
from .models import Product, Category, Brand

class ProductFilter(django_filters.FilterSet):
    category = django_filters.ModelChoiceFilter(
        field_name='categoryId', 
        queryset=Category.objects.all(),
        label='Категория'
    )
    brand = django_filters.ModelChoiceFilter(
        field_name='brandId', 
        queryset=Brand.objects.all(),
        label='Бренд'
    )
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_age_rating = django_filters.NumberFilter(field_name='ageRating', lookup_expr='gte')
    max_age_rating = django_filters.NumberFilter(field_name='ageRating', lookup_expr='lte')
    
    class Meta:
        model = Product
        fields = ['category', 'brand', 'min_price', 'max_price', 'min_age_rating', 'max_age_rating']