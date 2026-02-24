"""
Admin للنماذج الجديدة في وحدة الفروع/التوزيع
- Replenishment Requests
- Branch Stock Settings
- Auto Replenishment Rules
"""

from django.contrib import admin
from .distribution import (
    ShowroomReplenishmentRequest,
    ReplenishmentRequestItem,
    BranchStockSettings,
    AutoReplenishmentRule
)


class ReplenishmentRequestItemInline(admin.TabularInline):
    model = ReplenishmentRequestItem
    extra = 0
    raw_id_fields = ['product']
    fields = ['product', 'requested_quantity', 'approved_quantity', 'shipped_quantity', 'received_quantity', 'current_stock', 'notes']
    readonly_fields = ['shipped_quantity', 'received_quantity']


@admin.register(ShowroomReplenishmentRequest)
class ShowroomReplenishmentRequestAdmin(admin.ModelAdmin):
    list_display = ['request_number', 'branch', 'status', 'priority', 'request_date', 'required_date', 'transfer', 'created_at']
    list_filter = ['status', 'priority', 'request_date', 'branch']
    search_fields = ['request_number', 'branch__name', 'branch__code']
    raw_id_fields = ['branch', 'requested_by', 'approved_by', 'transfer']
    readonly_fields = ['request_number', 'created_at', 'updated_at']
    inlines = [ReplenishmentRequestItemInline]
    
    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('request_number', 'branch', 'status', 'priority')
        }),
        ('التواريخ', {
            'fields': ('request_date', 'required_date')
        }),
        ('المسؤولين', {
            'fields': ('requested_by', 'approved_by'),
            'classes': ('collapse',)
        }),
        ('الربط', {
            'fields': ('transfer', 'notes'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        queryset.filter(status='pending').update(status='approved')
        self.message_user(request, f"تم اعتماد {queryset.count()} طلب")
    approve_requests.short_description = "اعتماد الطلبات المحددة"
    
    def reject_requests(self, request, queryset):
        queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f"تم رفض {queryset.count()} طلب")
    reject_requests.short_description = "رفض الطلبات المحددة"


@admin.register(BranchStockSettings)
class BranchStockSettingsAdmin(admin.ModelAdmin):
    list_display = ['branch', 'product', 'minimum_quantity', 'reorder_point', 'maximum_quantity', 'auto_replenish']
    list_filter = ['auto_replenish', 'branch']
    search_fields = ['branch__name', 'branch__code', 'product__name', 'product__sku']
    raw_id_fields = ['branch', 'product', 'preferred_source']
    
    fieldsets = (
        ('الفرع والمنتج', {
            'fields': ('branch', 'product')
        }),
        ('مستويات المخزون', {
            'fields': ('minimum_quantity', 'reorder_point', 'maximum_quantity')
        }),
        ('التموين التلقائي', {
            'fields': ('auto_replenish', 'preferred_source')
        }),
    )


@admin.register(AutoReplenishmentRule)
class AutoReplenishmentRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'apply_to_all_showrooms', 'apply_to_all_products', 'check_frequency_hours', 'last_run']
    list_filter = ['is_active', 'apply_to_all_showrooms', 'apply_to_all_products']
    search_fields = ['name']
    filter_horizontal = ['target_branches', 'target_products', 'target_categories']
    readonly_fields = ['last_run', 'created_at', 'updated_at']
    
    fieldsets = (
        ('معلومات القاعدة', {
            'fields': ('name', 'is_active')
        }),
        ('الفروع المستهدفة', {
            'fields': ('apply_to_all_showrooms', 'target_branches')
        }),
        ('المنتجات المستهدفة', {
            'fields': ('apply_to_all_products', 'target_products', 'target_categories')
        }),
        ('شروط التشغيل', {
            'fields': ('trigger_at_reorder_point', 'trigger_at_minimum')
        }),
        ('كمية التموين', {
            'fields': ('replenish_to_maximum', 'fixed_replenish_quantity')
        }),
        ('الجدولة', {
            'fields': ('check_frequency_hours', 'last_run')
        }),
        ('الإشعارات', {
            'fields': ('notify_on_trigger', 'notification_emails'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
