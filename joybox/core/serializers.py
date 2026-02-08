from datetime import date
from django.utils import timezone
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from .models import Product, Category, Brand, ProductImage, ProductAttribute, Review, User, Role, Wishlist, ParentChild, Cart, Order, OrderItem, Address, OrderStatus, AuditLog
from .profanity import contains_profanity

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['categoryId', 'categoryName', 'categoryDescription']

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['brandId', 'brandName', 'brandDescription', 'brandCountry']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['productImageId', 'productId', 'url', 'altText', 'isMain']
        read_only_fields = ['productImageId', 'productId']


class ProductAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = ['productAttributeId', 'productId', 'productAttributeName', 'productAttributeValue', 'productAttributeUnit']
        read_only_fields = ['productAttributeId', 'productId']


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(source='categoryId', read_only=True)
    brand = BrandSerializer(source='brandId', read_only=True)
    main_image = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'productId', 'productName', 'productDescription', 
            'category', 'brand', 'price', 'ageRating', 
            'quantity', 'weightKg', 'dimensions', 'main_image',
            'average_rating', 'review_count'
        ]
    
    def get_main_image(self, obj):
        main_image = obj.productimage_set.filter(isMain=True).first()
        if main_image:
            return ProductImageSerializer(main_image).data
        return None
    
    def get_average_rating(self, obj):
        return obj.get_average_rating()
    
    def get_review_count(self, obj):
        return obj.get_review_count()

class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True, source='productimage_set')
    attributes = ProductAttributeSerializer(many=True, read_only=True, source='productattribute_set')
    
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ['images', 'attributes']

class UserSerializer(serializers.ModelSerializer):
    roleName = serializers.CharField(source='roleId.roleName', read_only=True)
    roleId = serializers.IntegerField(source='roleId.roleId', read_only=True)
    
    class Meta:
        model = User
        fields = ['userId', 'firstName', 'lastName', 'email', 'phone', 'birthDate', 'roleName', 'roleId', 'createdAt', 'is_active']

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['roleId', 'roleName']


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    roleId = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'firstName', 'lastName', 'middleName', 'email', 'password',
            'phone', 'birthDate', 'roleId', 'username', 'is_active'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'birthDate': {'required': True},
            'middleName': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        
        if 'username' not in validated_data or not validated_data['username']:
            validated_data['username'] = validated_data['email']
        
        from django.utils import timezone
        validated_data['createdAt'] = timezone.now()
        
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        username = validated_data.pop('username', None)
        role_id = validated_data.pop('roleId', None)
        if username is not None:
            validated_data['username'] = username.strip() or instance.email
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if role_id is not None:
            instance.roleId = role_id
        if password:
            instance.set_password(password)
        instance.save()
        return instance
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['roleId'] = instance.roleId.roleId if instance.roleId else None
        data['roleName'] = instance.roleId.roleName if instance.roleId else None
        return data

class UserProfileSerializer(serializers.ModelSerializer):
    roleName = serializers.CharField(source='roleId.roleName', read_only=True)
    
    class Meta:
        model = User
        fields = ['userId', 'firstName', 'lastName', 'middleName', 'email', 'phone', 'birthDate', 'roleName']
        read_only_fields = ['userId', 'email']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirmPassword = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['firstName', 'lastName', 'middleName', 'email', 'password', 'confirmPassword', 'phone', 'birthDate']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirmPassword']:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirmPassword')
        try:
            role, created = Role.objects.get_or_create(roleName='Покупатель')
            validated_data['roleId'] = role
        except Exception as e:
            raise serializers.ValidationError("Ошибка при назначении роли пользователю.")
        
        if 'username' not in validated_data:
            validated_data['username'] = validated_data['email']
            
        from django.utils import timezone
        validated_data['createdAt'] = timezone.now()
        
        user = User(
            firstName=validated_data['firstName'],
            lastName=validated_data['lastName'],
            middleName=validated_data.get('middleName'),
            email=validated_data['email'],
            username=validated_data['username'],
            phone=validated_data['phone'],
            birthDate=validated_data['birthDate'],
            roleId=validated_data['roleId'],
            createdAt=validated_data['createdAt']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError('Необходимо указать email и пароль')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Неверный email или пароль')

        if not user.check_password(password):
            raise serializers.ValidationError('Неверный email или пароль')

        if not user.is_active:
            raise serializers.ValidationError(
                'Ваш аккаунт заблокирован в связи с нарушением правил. Обратитесь к администратору.'
            )

        attrs['user'] = user
        return attrs

class TokenSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Token
        fields = ['key', 'user']

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(source='userId', read_only=True)
    
    class Meta:
        model = Review
        fields = ['reviewId', 'productId', 'user', 'rating', 'reviewText', 'createdAt', 'updatedAt']


class ReviewCreateSerializer(serializers.Serializer):
    productId = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=True)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    reviewText = serializers.CharField(required=False, allow_blank=True)

    def validate_reviewText(self, value):
        if value and contains_profanity(value):
            raise serializers.ValidationError('Текст отзыва содержит недопустимые выражения. Измените формулировку.')
        return value


class ReviewUpdateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    reviewText = serializers.CharField(required=False, allow_blank=True)

    def validate_reviewText(self, value):
        if value and contains_profanity(value):
            raise serializers.ValidationError('Текст отзыва содержит недопустимые выражения. Измените формулировку.')
        return value


class AdminReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(source='userId', read_only=True)
    productName = serializers.CharField(source='productId.productName', read_only=True)
    
    class Meta:
        model = Review
        fields = ['reviewId', 'productId', 'productName', 'userId', 'user', 'rating', 'reviewText', 'createdAt', 'updatedAt']

class WishlistSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(source='productId', read_only=True)
    user = UserSerializer(source='userId', read_only=True)
    
    class Meta:
        model = Wishlist
        fields = ['wishlistId', 'product', 'user']


class WishlistCreateSerializer(serializers.ModelSerializer):
    productId = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=True,
        error_messages={'does_not_exist': 'Товар не найден.', 'incorrect_type': 'Укажите номер товара (productId).'}
    )
    
    class Meta:
        model = Wishlist
        fields = ['productId']
    
    def validate_productId(self, value):
        user = self.context['request'].user
        if Wishlist.objects.filter(userId=user, productId=value).exists():
            raise serializers.ValidationError('Товар уже в списке желаний.')
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        product = validated_data['productId']
        return Wishlist.objects.create(userId=user, productId=product)


def _child_age_ok(birth_date):
    if not birth_date:
        return False
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age <= 18


class ChildAccountSerializer(serializers.Serializer):
    parentChildId = serializers.IntegerField(read_only=True)
    userId = serializers.IntegerField(read_only=True)
    firstName = serializers.CharField(read_only=True)
    lastName = serializers.CharField(read_only=True)
    middleName = serializers.CharField(allow_null=True, read_only=True)
    email = serializers.EmailField(read_only=True)
    phone = serializers.CharField(read_only=True)
    birthDate = serializers.DateField(read_only=True)

    def to_representation(self, instance):
        # instance is ParentChild
        child = instance.childId
        return {
            'parentChildId': instance.parentChildId,
            'userId': child.userId,
            'firstName': child.firstName,
            'lastName': child.lastName,
            'middleName': child.middleName,
            'email': child.email,
            'phone': child.phone,
            'birthDate': child.birthDate,
        }


class ChildAccountCreateSerializer(serializers.Serializer):
    firstName = serializers.CharField(required=True, max_length=100)
    lastName = serializers.CharField(required=True, max_length=100)
    middleName = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=100)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True, max_length=11)
    birthDate = serializers.DateField(required=True)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirmPassword = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('confirmPassword'):
            raise serializers.ValidationError({'confirmPassword': 'Пароли не совпадают.'})
        if not _child_age_ok(attrs.get('birthDate')):
            raise serializers.ValidationError({'birthDate': 'Ребёнок не может быть старше 18 лет.'})
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({'email': 'Пользователь с таким email уже зарегистрирован.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirmPassword')
        password = validated_data.pop('password')
        role_child, _ = Role.objects.get_or_create(roleName='Ребенок')
        child = User(
            firstName=validated_data['firstName'],
            lastName=validated_data['lastName'],
            middleName=validated_data.get('middleName'),
            email=validated_data['email'],
            username=validated_data['email'],
            phone=validated_data['phone'],
            birthDate=validated_data['birthDate'],
            roleId=role_child,
            createdAt=timezone.now(),
        )
        child.set_password(password)
        child.save()
        parent = self.context['request'].user
        link = ParentChild.objects.create(userId=parent, childId=child)
        return link


class ChildAccountUpdateSerializer(serializers.Serializer):
    firstName = serializers.CharField(required=False, max_length=100)
    lastName = serializers.CharField(required=False, max_length=100)
    middleName = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=100)
    phone = serializers.CharField(required=False, max_length=11)
    birthDate = serializers.DateField(required=False)

    def validate_birthDate(self, value):
        if not _child_age_ok(value):
            raise serializers.ValidationError('Ребёнок не может быть старше 18 лет.')
        return value

    def update(self, instance, validated_data):
        # instance is User (child)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class CartItemSerializer(serializers.Serializer):
    cartId = serializers.IntegerField(read_only=True)
    productId = serializers.IntegerField(read_only=True)
    productName = serializers.CharField(read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    lineTotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    mainImage = serializers.SerializerMethodField(read_only=True)

    def get_mainImage(self, obj):
        from .models import ProductImage
        img = ProductImage.objects.filter(productId=obj.productId, isMain=True).first()
        return ProductImageSerializer(img).data if img else None

    def to_representation(self, instance):
        product = instance.productId
        price = product.price
        qty = instance.quantity
        line_total = price * qty
        from .models import ProductImage
        img = ProductImage.objects.filter(productId=product, isMain=True).first()
        return {
            'cartId': instance.cartId,
            'productId': product.productId,
            'productName': product.productName,
            'price': price,
            'quantity': qty,
            'lineTotal': line_total,
            'mainImage': ProductImageSerializer(img).data if img else None,
        }


class CartListSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class CartAddSerializer(serializers.Serializer):
    productId = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=999, default=1)

    def validate(self, attrs):
        product = attrs['productId']
        qty = attrs['quantity']
        if qty > product.quantity:
            raise serializers.ValidationError({'quantity': f'На складе доступно {product.quantity} шт.'})
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        product = validated_data['productId']
        quantity = validated_data['quantity']
        cart_item, created = Cart.objects.get_or_create(
            userId=user,
            productId=product,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            if cart_item.quantity > product.quantity:
                raise serializers.ValidationError({'quantity': f'На складе доступно {product.quantity} шт. Всего в корзине не должно превышать это число.'})
            cart_item.save()
        return cart_item


class CartUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=999)

    def update(self, instance, validated_data):
        qty = validated_data['quantity']
        if qty > instance.productId.quantity:
            raise serializers.ValidationError({'quantity': f'На складе доступно {instance.productId.quantity} шт.'})
        instance.quantity = qty
        instance.save()
        return instance


class AddressBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['addressId', 'city', 'street', 'house', 'flat', 'index']


class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(source='userId', read_only=True)
    status = serializers.CharField(source='orderStatusId.orderStatusName', read_only=True)
    
    class Meta:
        model = Order
        fields = ['orderId', 'user', 'total', 'status', 'createdAt']


class UserOrderSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='orderStatusId.orderStatusName', read_only=True)
    deliveryTypeLabel = serializers.SerializerMethodField()
    paymentTypeLabel = serializers.SerializerMethodField()
    paymentStatusLabel = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['orderId', 'total', 'status', 'deliveryType', 'deliveryTypeLabel', 'paymentType', 'paymentTypeLabel', 'paymentStatus', 'paymentStatusLabel', 'createdAt']
    
    def get_deliveryTypeLabel(self, obj):
        return dict(Order.DELIVERY_TYPE_CHOICES).get(obj.deliveryType, obj.deliveryType)
    
    def get_paymentTypeLabel(self, obj):
        return dict(Order.PAYMENT_TYPE_CHOICES).get(obj.paymentType, obj.paymentType)
    
    def get_paymentStatusLabel(self, obj):
        return dict(Order.PAYMENT_STATUS_CHOICES).get(obj.paymentStatus, obj.paymentStatus)


class OrderItemSerializer(serializers.ModelSerializer):
    productName = serializers.CharField(source='productId.productName', read_only=True)
    productId = serializers.PrimaryKeyRelatedField(read_only=True)
    userHasReview = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['orderItemId', 'productId', 'productName', 'quantity', 'unitPrice', 'userHasReview']
    
    def get_userHasReview(self, obj):
        return Review.objects.filter(productId=obj.productId, userId=obj.orderId.userId).exists()


class UserOrderDetailSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='orderStatusId.orderStatusName', read_only=True)
    address = AddressBriefSerializer(source='addressId', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True, source='orderitem_set')
    deliveryTypeLabel = serializers.SerializerMethodField()
    paymentTypeLabel = serializers.SerializerMethodField()
    paymentStatusLabel = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'orderId', 'total', 'status', 'deliveryType', 'deliveryTypeLabel',
            'paymentType', 'paymentTypeLabel', 'paymentStatus', 'paymentStatusLabel',
            'address', 'note', 'createdAt', 'items'
        ]
    
    def get_deliveryTypeLabel(self, obj):
        return dict(Order.DELIVERY_TYPE_CHOICES).get(obj.deliveryType, obj.deliveryType)
    
    def get_paymentTypeLabel(self, obj):
        return dict(Order.PAYMENT_TYPE_CHOICES).get(obj.paymentType, obj.paymentType)
    
    def get_paymentStatusLabel(self, obj):
        return dict(Order.PAYMENT_STATUS_CHOICES).get(obj.paymentStatus, obj.paymentStatus)


class PaymentProcessSerializer(serializers.Serializer):
    orderId = serializers.IntegerField()
    cardNumber = serializers.CharField(max_length=19, min_length=16)
    cardHolder = serializers.CharField(max_length=100)
    expiryMonth = serializers.IntegerField(min_value=1, max_value=12)
    expiryYear = serializers.IntegerField(min_value=2024, max_value=2099)
    cvv = serializers.CharField(min_length=3, max_length=4)


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = ['orderStatusId', 'orderStatusName']


class AuditLogSerializer(serializers.ModelSerializer):
    userDisplay = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['auditLogId', 'userId', 'userDisplay', 'action', 'tableName', 'recordId', 'oldValues', 'newValues', 'createdAt']

    def get_userDisplay(self, obj):
        if obj.userId:
            u = obj.userId
            return f"{u.firstName or ''} {u.lastName or ''} ({u.email or ''})".strip() or str(obj.userId_id)
        return str(obj.userId_id)


class AddressCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['city', 'street', 'house', 'flat', 'index']
        extra_kwargs = {'flat': {'required': False, 'allow_blank': True}}

    def create(self, validated_data):
        validated_data['userId'] = self.context['request'].user
        return super().create(validated_data)


class CheckoutCreateSerializer(serializers.Serializer):
    deliveryType = serializers.ChoiceField(choices=Order.DELIVERY_TYPE_CHOICES)
    addressId = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.none(),
        required=False,
        allow_null=True
    )
    newAddress = serializers.DictField(required=False, allow_null=True)
    paymentType = serializers.ChoiceField(choices=Order.PAYMENT_TYPE_CHOICES)
    note = serializers.CharField(required=False, allow_blank=True, max_length=100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'request' in self.context:
            self.fields['addressId'].queryset = Address.objects.filter(userId=self.context['request'].user)

    def validate(self, attrs):
        delivery = attrs.get('deliveryType')
        address_id = attrs.get('addressId')
        new_address = attrs.get('newAddress')

        if delivery == Order.DELIVERY_PICKUP:
            return attrs

        if address_id and new_address:
            raise serializers.ValidationError('Укажите либо существующий адрес (addressId), либо новый (newAddress), но не оба.')
        if not address_id and not new_address:
            raise serializers.ValidationError('Укажите адрес: addressId или newAddress.')
        if new_address:
            required = ['city', 'street', 'house', 'index']
            for key in required:
                if not new_address.get(key):
                    raise serializers.ValidationError({'newAddress': f'Поле {key} обязательно для нового адреса.'})
        if delivery == Order.DELIVERY_POINT and attrs.get('paymentType') != Order.PAYMENT_ONLINE:
            raise serializers.ValidationError(
                {'paymentType': 'При доставке в пункт выдачи доступна только оплата онлайн.'}
            )
        return attrs


class OrderDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(source='userId', read_only=True)
    status = serializers.CharField(source='orderStatusId.orderStatusName', read_only=True)
    orderStatusId = serializers.PrimaryKeyRelatedField(queryset=OrderStatus.objects.all())
    address = AddressBriefSerializer(source='addressId', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True, source='orderitem_set')
    
    class Meta:
        model = Order
        fields = [
            'orderId', 'userId', 'user', 'orderStatusId', 'status', 'total',
            'addressId', 'address', 'deliveryType', 'paymentType', 'paymentStatus',
            'note', 'createdAt', 'items'
        ]
        read_only_fields = ['orderId', 'userId', 'total', 'addressId', 'deliveryType', 'paymentType', 'paymentStatus', 'note', 'createdAt', 'items', 'address', 'user', 'status']

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    categoryId = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    brandId = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all())
    
    class Meta:
        model = Product
        fields = [
            'productId', 'productName', 'productDescription', 'categoryId', 
            'brandId', 'price', 'ageRating', 'quantity', 
            'weightKg', 'dimensions'
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['categoryId'] = instance.categoryId.categoryId if instance.categoryId else None
        data['brandId'] = instance.brandId.brandId if instance.brandId else None
        return data


class ProductWithRelationsSerializer(serializers.ModelSerializer):
    """Serializer for product with all related data"""
    category = CategorySerializer(source='categoryId', read_only=True)
    brand = BrandSerializer(source='brandId', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True, source='productimage_set')
    attributes = ProductAttributeSerializer(many=True, read_only=True, source='productattribute_set')
    
    class Meta:
        model = Product
        fields = [
            'productId', 'productName', 'productDescription', 'categoryId', 'brandId',
            'price', 'ageRating', 'quantity', 'weightKg', 'dimensions',
            'category', 'brand', 'images', 'attributes'
        ]
