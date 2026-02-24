"""
Purchases REST API Serializers
سيرياليزرز واجهة المشتريات
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import PurchaseOrder, PurchaseOrderItem, PurchaseBill, PurchaseItem
from partners.models import Partner


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = [
            'id', 'name', 'email', 'phone', 'address',
            'partner_type', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']
        ref_name = 'PurchasesSupplier'

    def create(self, validated_data):
        validated_data.setdefault('partner_type', 'supplier')
        return super().create(validated_data)


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'product', 'product_name',
            'location', 'quantity', 'cost', 'received_quantity',
        ]
        ref_name = 'PurchasesPurchaseOrderItem'


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'number', 'supplier', 'supplier_name',
            'date', 'expected_date', 'status', 'discount',
            'total', 'created_at',
        ]

    @extend_schema_field(serializers.FloatField())
    def get_total(self, obj):
        return float(obj.total)


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'number', 'supplier', 'supplier_name',
            'date', 'expected_date', 'status', 'discount', 'notes',
            'bill', 'created_by', 'requested_by',
            'items', 'total', 'created_at', 'updated_at',
        ]
        read_only_fields = ['number', 'created_by', 'created_at', 'updated_at']

    @extend_schema_field(serializers.FloatField())
    def get_total(self, obj):
        return float(obj.total)


class PurchaseBillListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = PurchaseBill
        fields = [
            'id', 'number', 'supplier', 'supplier_name',
            'date', 'discount', 'paid', 'status',
            'is_deleted',
        ]


class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PurchaseItem
        fields = [
            'id', 'product', 'product_name',
            'quantity', 'cost', 'location',
        ]


class PurchaseBillDetailSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items = PurchaseItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseBill
        fields = [
            'id', 'number', 'supplier', 'supplier_name',
            'date', 'showroom', 'discount', 'paid', 'status',
            'posted_at', 'payment_method', 'payment_reference',
            'supplier_invoice_number',
            'is_deleted', 'deleted_at', 'delete_reason',
            'items',
        ]
        read_only_fields = ['number', 'posted_at', 'is_deleted', 'deleted_at']
