from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    WooCommerceConfig,
    ProductMapping,
    OrderMapping,
    CustomerMapping,
    SyncLog
)


@admin.register(WooCommerceConfig)
class WooCommerceConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'store_url', 'is_active', 'is_default', 'last_order_sync', 'last_inventory_sync']
    list_filter = ['is_active', 'is_default', 'auto_sync_orders', 'auto_sync_inventory']
    search_fields = ['name', 'store_url']
    readonly_fields = ['last_product_sync', 'last_order_sync', 'last_inventory_sync', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'store_url', 'consumer_key', 'consumer_secret')
        }),
        (_('حالة النشاط'), {
            'fields': ('is_active', 'is_default')
        }),
        (_('إعدادات المزامنة'), {
            'fields': ('auto_sync_products', 'auto_sync_orders', 'auto_sync_inventory', 'sync_interval_minutes')
        }),
        (_('الإعدادات الافتراضية'), {
            'fields': ('default_location', 'default_customer_type')
        }),
        (_('آخر مزامنة'), {
            'fields': ('last_product_sync', 'last_order_sync', 'last_inventory_sync'),
            'classes': ('collapse',)
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductMapping)
class ProductMappingAdmin(admin.ModelAdmin):
    list_display = ['erp_product', 'woo_product_id', 'woo_sku', 'config', 'sync_enabled', 'last_synced']
    list_filter = ['config', 'sync_enabled', 'sync_stock', 'sync_price']
    search_fields = ['erp_product__name', 'erp_product__sku', 'woo_sku', 'woo_product_id']
    raw_id_fields = ['erp_product']
    readonly_fields = ['last_synced', 'created_at', 'updated_at']


@admin.register(OrderMapping)
class OrderMappingAdmin(admin.ModelAdmin):
    list_display = ['woo_order_number', 'erp_invoice', 'erp_customer', 'status', 'woo_created_at', 'synced_at']
    list_filter = ['status', 'config', 'woo_created_at']
    search_fields = ['woo_order_number', 'woo_order_id', 'erp_invoice__number', 'erp_customer__name']
    raw_id_fields = ['erp_invoice', 'erp_customer']
    readonly_fields = ['synced_at', 'updated_at', 'woo_data']
    date_hierarchy = 'woo_created_at'


@admin.register(CustomerMapping)
class CustomerMappingAdmin(admin.ModelAdmin):
    list_display = ['erp_customer', 'woo_customer_id', 'woo_email', 'config', 'last_synced']
    list_filter = ['config']
    search_fields = ['woo_email', 'erp_customer__name', 'woo_customer_id']
    raw_id_fields = ['erp_customer']
    readonly_fields = ['last_synced', 'created_at', 'updated_at']


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['sync_type', 'status', 'records_processed', 'records_success', 'records_failed', 'started_at', 'duration_seconds']
    list_filter = ['sync_type', 'status', 'config', 'started_at']
    search_fields = ['message', 'error_details']
    readonly_fields = ['started_at', 'completed_at', 'duration_seconds']
    date_hierarchy = 'started_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
