"""
تسجيل نماذج المخزون المتقدمة في لوحة التحكم
"""

from django.contrib import admin
from django.utils.html import format_html

from inventory.models_advanced import (
    StockAlert,
    LotTracking,
    CycleCount,
    CycleCountItem,
)


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'location', 'alert_type', 'severity',
        'threshold', 'current_quantity', 'is_active',
        'is_acknowledged', 'last_triggered'
    ]
    list_filter = ['alert_type', 'severity', 'is_active', 'is_acknowledged']
    search_fields = ['product__name']
    list_editable = ['is_active', 'threshold']
    filter_horizontal = ['notify_users']


@admin.register(LotTracking)
class LotTrackingAdmin(admin.ModelAdmin):
    list_display = [
        'lot_number', 'product', 'manufacturing_date',
        'expiry_date', 'current_quantity', 'cost_per_unit',
        'is_expired_display', 'is_active'
    ]
    list_filter = ['is_active', 'location']
    search_fields = ['lot_number', 'batch_number', 'product__name']
    readonly_fields = ['received_date']

    @admin.display(description='منتهي الصلاحية', boolean=True)
    def is_expired_display(self, obj):
        return obj.is_expired


class CycleCountItemInline(admin.TabularInline):
    model = CycleCountItem
    extra = 0
    readonly_fields = ['variance_display']

    @admin.display(description='الفرق')
    def variance_display(self, obj):
        v = obj.variance
        if v is not None:
            color = 'green' if v == 0 else 'red'
            return format_html(
                '<span style="color:{}">{}</span>', color, v
            )
        return '-'


@admin.register(CycleCount)
class CycleCountAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'location', 'count_type', 'scheduled_date',
        'status', 'completion_percentage', 'accuracy_rate', 'assigned_to'
    ]
    list_filter = ['status', 'count_type', 'location']
    search_fields = ['name']
    inlines = [CycleCountItemInline]
    readonly_fields = [
        'started_at', 'completed_at', 'counted_items', 'discrepancies_count'
    ]
