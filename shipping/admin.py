"""
تسجيل نماذج الشحن في لوحة الإدارة - Tony ERP
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    ShippingCompany, ShippingZone, ShippingRate, Shipment,
    ShipmentTracking, ShippingPickup, ShippingInvoice, ShippingInvoiceItem
)


@admin.register(ShippingCompany)
class ShippingCompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'contact_person', 'phone', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'contact_person']
    ordering = ['name']


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'country', 'is_active']
    list_filter = ['country', 'is_active']
    search_fields = ['name', 'code', 'country']
    ordering = ['country', 'name']


@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ['company', 'zone', 'weight_from', 'weight_to', 'base_rate', 'delivery_days', 'is_active']
    list_filter = ['company', 'zone', 'is_active']
    ordering = ['company', 'zone', 'weight_from']


class ShipmentTrackingInline(admin.TabularInline):
    model = ShipmentTracking
    extra = 0
    readonly_fields = ['timestamp', 'updated_by']


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ['tracking_number', 'company', 'receiver_name', 'receiver_city', 'status', 'shipping_cost', 'created_at']
    list_filter = ['status', 'company', 'payment_type', 'created_at']
    search_fields = ['tracking_number', 'receiver_name', 'receiver_phone', 'sender_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['tracking_number', 'created_at', 'updated_at', 'created_by']
    inlines = [ShipmentTrackingInline]
    
    fieldsets = (
        (_('معلومات الشحنة'), {
            'fields': ('tracking_number', 'company', 'status')
        }),
        (_('المرسل'), {
            'fields': ('sender_name', 'sender_phone', 'sender_address', 'sender_city')
        }),
        (_('المستلم'), {
            'fields': ('receiver_name', 'receiver_phone', 'receiver_address', 'receiver_city', 'zone')
        }),
        (_('تفاصيل الشحنة'), {
            'fields': ('description', 'weight', 'pieces', 'dimensions')
        }),
        (_('المالية'), {
            'fields': ('payment_type', 'shipping_cost', 'cod_amount', 'insurance_amount')
        }),
        (_('التتبع'), {
            'fields': ('pickup_date', 'expected_delivery', 'actual_delivery')
        }),
        (_('مرجعية'), {
            'fields': ('reference_number', 'order_id', 'notes', 'created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(ShipmentTracking)
class ShipmentTrackingAdmin(admin.ModelAdmin):
    list_display = ['shipment', 'status', 'location', 'timestamp', 'updated_by']
    list_filter = ['status', 'timestamp']
    search_fields = ['shipment__tracking_number', 'description']
    date_hierarchy = 'timestamp'


@admin.register(ShippingPickup)
class ShippingPickupAdmin(admin.ModelAdmin):
    list_display = ['pickup_number', 'company', 'pickup_city', 'scheduled_date', 'status']
    list_filter = ['status', 'company', 'scheduled_date']
    search_fields = ['pickup_number', 'contact_name', 'contact_phone']
    date_hierarchy = 'scheduled_date'


class ShippingInvoiceItemInline(admin.TabularInline):
    model = ShippingInvoiceItem
    extra = 0


@admin.register(ShippingInvoice)
class ShippingInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'company', 'invoice_date', 'total', 'status']
    list_filter = ['status', 'company', 'invoice_date']
    search_fields = ['invoice_number']
    date_hierarchy = 'invoice_date'
    inlines = [ShippingInvoiceItemInline]
