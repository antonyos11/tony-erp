"""
Inventory REST API Serializers
سيرياليزرز واجهة المخزون
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Product, Category, Stock, Location


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, default=None)
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'parent', 'parent_name',
            'is_active', 'sort_order', 'products_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    @extend_schema_field(serializers.IntegerField())
    def get_products_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer مُبسّط للقوائم"""
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    code = serializers.CharField(source='sku', read_only=True)
    price = serializers.FloatField()
    cost = serializers.FloatField()

    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'code', 'name', 'barcode',
            'category', 'category_name',
            'price', 'cost', 'min_stock',
            'product_type', 'is_active',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer مُفصّل"""
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    stock_summary = serializers.SerializerMethodField()
    code = serializers.CharField(source='sku', required=False)
    price = serializers.FloatField()
    cost = serializers.FloatField()

    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'code', 'name', 'description', 'image',
            'barcode', 'internal_code',
            'category', 'category_name',
            'price', 'cost', 'min_stock',
            'purchase_uom', 'usage_uom', 'conversion_factor',
            'product_type', 'raw_material_type',
            'preferred_supplier',
            'purchase_price', 'usage_unit_cost', 'waste_percentage',
            'is_active', 'is_third_party',
            'show_in_store', 'is_new', 'store_featured',
            'width', 'length', 'height',
            'promo_percent', 'promo_price', 'promo_start', 'promo_end', 'is_promo_active',
            'stock_summary',
        ]
        read_only_fields = ['sku', 'barcode']

    @extend_schema_field(serializers.DictField())
    def get_stock_summary(self, obj):
        stocks = Stock.objects.filter(product=obj).select_related('location')
        total = sum(s.quantity for s in stocks)
        return {
            'total_quantity': total,
            'by_location': [
                {'location_id': s.location_id, 'location': s.location.name, 'quantity': s.quantity}
                for s in stocks
            ],
        }


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            'id', 'name', 'code', 'address', 'type',
            'is_active', 'is_default',
        ]
        ref_name = 'InventoryLocation'


class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = Stock
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'location', 'location_name', 'quantity',
        ]
        read_only_fields = ['quantity']
        ref_name = 'InventoryStock'
