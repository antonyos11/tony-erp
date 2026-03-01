"""
لوحة إدارة تطبيق الضمان — RITA ERP
"""
from django.contrib import admin
from .models import WarrantyCard, WarrantyClaim


@admin.register(WarrantyCard)
class WarrantyCardAdmin(admin.ModelAdmin):
    list_display   = ['serial_number', 'product', 'customer_name', 'purchase_date', 'expiry_date', 'status']
    list_filter    = ['status']
    search_fields  = ['serial_number', 'customer_name', 'customer_phone']
    ordering       = ['-purchase_date']
    readonly_fields = ['serial_number', 'activation_date', 'activated_by']


@admin.register(WarrantyClaim)
class WarrantyClaimAdmin(admin.ModelAdmin):
    list_display  = ['warranty', 'claim_date', 'status', 'created_at']
    list_filter   = ['status']
    search_fields = ['warranty__serial_number', 'issue_description']
    ordering      = ['-claim_date']
