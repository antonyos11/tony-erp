"""
تسجيل نماذج الموردين في لوحة الإدارة
"""
from django.contrib import admin
from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'supplier_type', 'phone', 'country', 'is_taxable', 'payment_terms', 'is_active']
    list_filter = ['supplier_type', 'country', 'is_taxable', 'is_active']
    search_fields = ['code', 'name', 'phone', 'tax_number']
    ordering = ['code']

