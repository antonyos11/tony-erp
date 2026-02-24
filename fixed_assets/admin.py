from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    AssetCategory,
    Asset,
    DepreciationSchedule,
    AssetMaintenance,
    AssetTransfer
)


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'default_useful_life_years', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


class DepreciationScheduleInline(admin.TabularInline):
    model = DepreciationSchedule
    extra = 0
    readonly_fields = ['accumulated_depreciation', 'book_value', 'status', 'posted_at']
    can_delete = False


class AssetMaintenanceInline(admin.TabularInline):
    model = AssetMaintenance
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'category', 'acquisition_date', 'acquisition_cost', 'current_book_value', 'status']
    list_filter = ['status', 'category', 'acquisition_date']
    search_fields = ['number', 'name', 'serial_number']
    readonly_fields = ['number', 'current_book_value', 'accumulated_depreciation', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('number', 'name', 'category', 'description', 'serial_number', 'manufacturer', 'model')
        }),
        (_('الموقع والتخصيص'), {
            'fields': ('location', 'department', 'assigned_to')
        }),
        (_('المعلومات المالية'), {
            'fields': ('acquisition_date', 'acquisition_cost', 'purchase_invoice', 'current_book_value', 'accumulated_depreciation')
        }),
        (_('إعدادات الاستهلاك'), {
            'fields': ('depreciation_method', 'useful_life_years', 'useful_life_units', 'salvage_value', 'depreciation_start_date')
        }),
        (_('الحالة'), {
            'fields': ('status',)
        }),
        (_('الاستبعاد'), {
            'fields': ('disposal_date', 'disposal_value', 'disposal_notes'),
            'classes': ('collapse',)
        }),
        (_('الصيانة'), {
            'fields': ('warranty_expiry_date', 'last_maintenance_date', 'next_maintenance_date'),
            'classes': ('collapse',)
        }),
        (_('مرفقات'), {
            'fields': ('image', 'documents'),
            'classes': ('collapse',)
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
    )
    
    inlines = [DepreciationScheduleInline, AssetMaintenanceInline]


@admin.register(DepreciationSchedule)
class DepreciationScheduleAdmin(admin.ModelAdmin):
    list_display = ['asset', 'period_start', 'period_end', 'depreciation_amount', 'accumulated_depreciation', 'book_value', 'status']
    list_filter = ['status', 'period_start']
    search_fields = ['asset__number', 'asset__name']
    readonly_fields = ['created_at', 'posted_at']
    date_hierarchy = 'period_start'


@admin.register(AssetMaintenance)
class AssetMaintenanceAdmin(admin.ModelAdmin):
    list_display = ['asset', 'maintenance_type', 'date', 'cost', 'vendor']
    list_filter = ['maintenance_type', 'date']
    search_fields = ['asset__number', 'asset__name', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'


@admin.register(AssetTransfer)
class AssetTransferAdmin(admin.ModelAdmin):
    list_display = ['asset', 'transfer_date', 'from_location', 'to_location', 'approved_by']
    list_filter = ['transfer_date']
    search_fields = ['asset__number', 'asset__name', 'from_location', 'to_location']
    readonly_fields = ['created_at']
    date_hierarchy = 'transfer_date'
