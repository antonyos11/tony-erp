"""
E-commerce API Serializers
Serializers for REST API endpoints - Mobile App Support
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    OnlineProduct, ProductCategory, ProductImage, Brand,
    Cart, CartItem, Order, OrderItem,
    Wishlist, ProductReview, Coupon,
    PaymentGateway, ShippingCompany
)

User = get_user_model()


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images"""
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'alt_text', 'sort_order']
        read_only_fields = ['id']


class BrandSerializer(serializers.ModelSerializer):
    """Serializer for brands"""
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo', 'description', 'is_featured']
        read_only_fields = ['id', 'slug']


class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories with parent-child support"""
    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'slug', 'description', 'image',
            'parent', 'children', 'product_count', 'is_active'
        ]
        read_only_fields = ['id', 'slug']
    
    def get_children(self, obj):
        """Get child categories"""
        if obj.children.exists():
            return ProductCategorySerializer(
                obj.children.filter(is_active=True),
                many=True,
                context=self.context
            ).data
        return []
    
    def get_product_count(self, obj):
        """Get number of active products in category"""
        return obj.online_products.filter(is_active=True).count()


class OnlineProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product listing"""
    name = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    sku = serializers.CharField(source='inventory_item.sku', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    main_image_url = serializers.ImageField(source='main_image', read_only=True)
    final_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = OnlineProduct
        fields = [
            'id', 'name', 'display_name', 'sku',
            'price', 'custom_price', 'discount_price', 'final_price', 'discount_percentage',
            'category_name', 'main_image_url',
            'is_featured', 'is_new', 'is_active', 'is_in_stock',
            'views_count', 'sales_count'
        ]
        read_only_fields = ['id']
    
    def get_name(self, obj):
        """Get product name (display_name or inventory_item name)"""
        if obj.display_name:
            return obj.display_name
        return obj.inventory_item.name if obj.inventory_item else ''
    
    def get_price(self, obj):
        """Get effective price"""
        if obj.custom_price:
            return obj.custom_price
        return obj.inventory_item.price if obj.inventory_item else Decimal('0')
    
    def get_main_image_url(self, obj):
        """Get main product image URL"""
        if obj.main_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.main_image.url)
            return obj.main_image.url
        return None
    
    def get_final_price(self, obj):
        """Get final price after discount"""
        from django.utils import timezone
        now = timezone.now()
        price = obj.custom_price or (obj.inventory_item.price if obj.inventory_item else Decimal('0'))
        if obj.discount_price and obj.discount_start and obj.discount_end:
            if obj.discount_start <= now <= obj.discount_end:
                return obj.discount_price
        return price
    
    def get_discount_percentage(self, obj):
        """Calculate discount percentage"""
        price = obj.custom_price or (obj.inventory_item.price if obj.inventory_item else Decimal('0'))
        if obj.discount_price and price and price > obj.discount_price:
            discount = ((price - obj.discount_price) / price) * 100
            return round(discount, 0)
        return 0
    
    def get_is_in_stock(self, obj):
        """Check if product is in stock"""
        if not obj.inventory_item:
            return False
        return obj.inventory_item.current_stock > 0


class OnlineProductDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single product view"""
    category = ProductCategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    discount_percentage = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()
    
    class Meta:
        model = OnlineProduct
        fields = [
            'id', 'display_name', 'slug',
            'full_description', 'short_description',
            'custom_price', 'discount_price', 'discount_percentage',
            'category', 'brand', 'images',
            'is_featured', 'is_new', 'is_in_stock',
            'reviews', 'related_products',
            'meta_title', 'meta_description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
    
    def get_discount_percentage(self, obj):
        """Calculate discount percentage"""
        price = obj.custom_price or 0
        if obj.discount_price and price > obj.discount_price:
            discount = ((price - obj.discount_price) / price) * 100
            return round(discount, 0)
        return 0

    def get_is_in_stock(self, obj):
        """Check if product is in stock via inventory_item"""
        if hasattr(obj, 'inventory_item') and obj.inventory_item:
            return True
        return False
    
    def get_reviews(self, obj):
        """Get approved product reviews (limited to 10)"""
        reviews = obj.reviews.filter(is_approved=True).order_by('-created_at')[:10]
        return ProductReviewSerializer(reviews, many=True, context=self.context).data
    
    def get_related_products(self, obj):
        """Get related products from same category"""
        related = OnlineProduct.objects.filter(
            category=obj.category,
            is_active=True
        ).exclude(id=obj.id).select_related('category', 'brand')[:6]
        return OnlineProductListSerializer(related, many=True, context=self.context).data


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items"""
    product = OnlineProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, source='product.custom_price')
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'price', 'subtotal']
        read_only_fields = ['id', 'subtotal']
    
    def validate_product_id(self, value):
        """Validate product exists and is active"""
        try:
            product = OnlineProduct.objects.get(id=value, is_active=True)
            if not product.is_in_stock:
                raise serializers.ValidationError("المنتج غير متوفر في المخزن")
            return value
        except OnlineProduct.DoesNotExist:
            raise serializers.ValidationError("المنتج غير موجود")
    
    def validate_quantity(self, value):
        """Validate quantity is positive"""
        if value < 1:
            raise serializers.ValidationError("الكمية يجب أن تكون 1 على الأقل")
        if value > 100:
            raise serializers.ValidationError("الكمية القصوى هي 100")
        return value


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart"""
    items = CartItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'items_count', 'total', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    product_name = serializers.CharField(source='product.display_name', read_only=True)
    product_image = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name', 'product_image',
            'quantity', 'unit_price', 'subtotal'
        ]
        read_only_fields = ['id']
    
    def get_product_image(self, obj):
        """Get product main image"""
        if obj.product:
            primary_image = obj.product.images.filter(is_primary=True).first()
            if primary_image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(primary_image.image.url)
                return primary_image.image.url
        return None


class PaymentGatewaySerializer(serializers.ModelSerializer):
    """Serializer for payment gateways"""
    
    class Meta:
        model = PaymentGateway
        fields = [
            'id', 'name', 'gateway_type', 'description',
            'icon', 'is_active', 'sort_order'
        ]
        read_only_fields = ['id']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders"""
    items = OrderItemSerializer(many=True, read_only=True)
    payment_method_details = PaymentGatewaySerializer(source='payment_method', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display',
            'payment_status', 'payment_status_display',
            'payment_method_details', 'items',
            'subtotal', 'shipping_cost', 'discount', 'tax', 'total',
            'customer_name', 'customer_email', 'customer_phone',
            'shipping_address', 'shipping_city', 'shipping_country',
            'customer_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'subtotal', 'tax', 'total',
            'created_at', 'updated_at'
        ]


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders"""
    customer_name = serializers.CharField(max_length=200)
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(max_length=20)
    shipping_address = serializers.CharField()
    shipping_city = serializers.CharField(max_length=100)
    shipping_country = serializers.CharField(max_length=100, default='مصر')
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    payment_gateway_id = serializers.IntegerField(required=False)
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    
    def validate_payment_gateway_id(self, value):
        """Validate payment gateway exists and is active"""
        if value:
            try:
                gateway = PaymentGateway.objects.get(id=value, is_active=True)
                return value
            except PaymentGateway.DoesNotExist:
                raise serializers.ValidationError("بوابة الدفع غير صحيحة")
        return value


class WishlistSerializer(serializers.ModelSerializer):
    """Serializer for wishlist items"""
    product = OnlineProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_id', 'added_at']
        read_only_fields = ['id', 'added_at']
    
    def validate_product_id(self, value):
        """Validate product exists"""
        try:
            OnlineProduct.objects.get(id=value, is_active=True)
            return value
        except OnlineProduct.DoesNotExist:
            raise serializers.ValidationError("المنتج غير موجود")


class ProductReviewSerializer(serializers.ModelSerializer):
    """Serializer for product reviews"""
    customer_name = serializers.CharField(source='user.get_full_name', read_only=True)
    product_name = serializers.CharField(source='product.display_name', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'product_name', 'customer_name',
            'rating', 'comment', 'is_approved',
            'created_at'
        ]
        read_only_fields = ['id', 'is_approved', 'created_at']
    
    def validate_rating(self, value):
        """Validate rating is between 1-5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("التقييم يجب أن يكون بين 1 و 5")
        return value


class CouponSerializer(serializers.ModelSerializer):
    """Serializer for coupons"""
    discount_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'discount_type', 'discount_value',
            'discount_display', 'min_order_amount',
            'valid_from', 'valid_to', 'is_active'
        ]
        read_only_fields = ['id']
    
    def get_discount_display(self, obj):
        """Get formatted discount display"""
        if obj.discount_type == 'percentage':
            return f"{obj.discount_value}%"
        else:
            return f"{obj.discount_value} ج.م"
