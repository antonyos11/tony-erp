from rest_framework import serializers
from .models import (
    WooCommerceConfig,
    ProductMapping,
    OrderMapping,
    CustomerMapping,
    SyncLog
)


class WooCommerceConfigSerializer(serializers.ModelSerializer):
    """Serializer for WooCommerce Store Configuration"""
    
    last_product_sync_display = serializers.DateTimeField(
        source='last_product_sync',
        read_only=True,
        format='%Y-%m-%d %H:%M'
    )
    last_order_sync_display = serializers.DateTimeField(
        source='last_order_sync',
        read_only=True,
        format='%Y-%m-%d %H:%M'
    )
    last_inventory_sync_display = serializers.DateTimeField(
        source='last_inventory_sync',
        read_only=True,
        format='%Y-%m-%d %H:%M'
    )
    
    class Meta:
        model = WooCommerceConfig
        fields = [
            'id', 'name', 'store_url', 'consumer_key', 'consumer_secret',
            'is_active', 'is_default', 'auto_sync_products', 'auto_sync_orders',
            'auto_sync_inventory', 'sync_interval_minutes', 'default_location',
            'default_customer_type', 'last_product_sync', 'last_order_sync',
            'last_inventory_sync', 'last_product_sync_display',
            'last_order_sync_display', 'last_inventory_sync_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'consumer_secret': {'write_only': True},
        }


class ProductMappingSerializer(serializers.ModelSerializer):
    """Serializer for Product Mapping"""
    
    config_name = serializers.CharField(source='config.name', read_only=True)
    erp_product_name = serializers.CharField(source='erp_product.name', read_only=True)
    erp_product_code = serializers.CharField(source='erp_product.code', read_only=True)
    
    class Meta:
        model = ProductMapping
        fields = [
            'id', 'config', 'config_name', 'erp_product', 'erp_product_name',
            'erp_product_code', 'woo_product_id', 'woo_sku', 'sync_enabled',
            'sync_stock', 'sync_price', 'last_synced', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class OrderMappingSerializer(serializers.ModelSerializer):
    """Serializer for Order Mapping"""
    
    config_name = serializers.CharField(source='config.name', read_only=True)
    invoice_number = serializers.CharField(source='erp_invoice.number', read_only=True)
    customer_name = serializers.CharField(source='erp_customer.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = OrderMapping
        fields = [
            'id', 'config', 'config_name', 'woo_order_id', 'woo_order_number',
            'erp_invoice', 'invoice_number', 'erp_customer', 'customer_name',
            'status', 'status_display', 'woo_data', 'woo_created_at',
            'synced_at', 'updated_at'
        ]
        read_only_fields = ['synced_at', 'updated_at']


class CustomerMappingSerializer(serializers.ModelSerializer):
    """Serializer for Customer Mapping"""
    
    config_name = serializers.CharField(source='config.name', read_only=True)
    erp_customer_name = serializers.CharField(source='erp_customer.name', read_only=True)
    erp_customer_code = serializers.CharField(source='erp_customer.code', read_only=True)
    
    class Meta:
        model = CustomerMapping
        fields = [
            'id', 'config', 'config_name', 'woo_customer_id', 'woo_email',
            'erp_customer', 'erp_customer_name', 'erp_customer_code',
            'last_synced', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class SyncLogSerializer(serializers.ModelSerializer):
    """Serializer for Sync Log"""
    
    config_name = serializers.CharField(source='config.name', read_only=True)
    sync_type_display = serializers.CharField(source='get_sync_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SyncLog
        fields = [
            'id', 'config', 'config_name', 'sync_type', 'sync_type_display',
            'status', 'status_display', 'records_processed', 'records_success',
            'records_failed', 'message', 'error_details', 'started_at',
            'completed_at', 'duration_seconds'
        ]
        read_only_fields = ['started_at', 'completed_at']


class WooCommerceConfigListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing configs"""
    
    class Meta:
        model = WooCommerceConfig
        fields = ['id', 'name', 'store_url', 'is_active', 'is_default']
