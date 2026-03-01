"""
تسجيل نماذج التطبيق الأساسي في لوحة الإدارة
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Company, Branch, Warehouse


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'get_full_name', 'email', 'branch', 'phone', 'is_active_employee', 'is_staff']
    list_filter = ['is_active_employee', 'is_staff', 'is_superuser', 'branch']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'phone']
    ordering = ['username']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('معلومات إضافية', {'fields': ('branch', 'phone', 'is_active_employee')}),
    )


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'tax_number', 'phone', 'default_currency', 'vat_rate']
    search_fields = ['name', 'tax_number']


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'branch_type', 'governorate', 'manager', 'has_warehouse', 'is_active']
    list_filter = ['branch_type', 'governorate', 'has_warehouse', 'is_active']
    search_fields = ['name', 'governorate', 'area']
    ordering = ['name']


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'warehouse_type', 'branch', 'keeper', 'is_active']
    list_filter = ['warehouse_type', 'is_active', 'branch']
    search_fields = ['name']
    ordering = ['name']

