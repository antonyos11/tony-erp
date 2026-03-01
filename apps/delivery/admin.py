"""
لوحة إدارة تطبيق التوصيل — RITA ERP
"""
from django.contrib import admin
from .models import DeliveryZone, DeliveryOrder


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display  = ['name', 'governorate', 'delivery_fee', 'free_delivery_above', 'estimated_days', 'is_active']
    list_filter   = ['governorate', 'is_active']
    search_fields = ['name', 'governorate']
    ordering      = ['governorate', 'name']


@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display  = ['order_number', 'invoice', 'zone', 'driver', 'status', 'delivery_date', 'delivery_fee']
    list_filter   = ['status', 'zone']
    search_fields = ['order_number', 'delivery_address']
    ordering      = ['-created_at']
    readonly_fields = ['order_number']
