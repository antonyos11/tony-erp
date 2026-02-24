"""
تسجيل نماذج الإنتاج المتقدمة في لوحة التحكم
"""

from django.contrib import admin
from django.utils.html import format_html

from production.models_advanced import (
    ProductionLine,
    ProductionSchedule,
    CostVariance,
)


@admin.register(ProductionLine)
class ProductionLineAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'branch', 'capacity_per_hour', 'is_active']
    list_filter = ['is_active', 'branch']
    search_fields = ['name', 'code']


@admin.register(ProductionSchedule)
class ProductionScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'production_order', 'production_line', 'planned_start',
        'status', 'priority', 'efficiency_percentage', 'oee', 'delay_hours'
    ]
    list_filter = ['status', 'priority', 'production_line']
    filter_horizontal = ['assigned_workers']
    readonly_fields = ['actual_start', 'actual_end']
    fieldsets = (
        ('معلومات أساسية', {
            'fields': (
                'production_order', 'production_line', 'priority', 'status'
            )
        }),
        ('الجدولة', {
            'fields': (
                'planned_start', 'planned_end', 'actual_start', 'actual_end'
            )
        }),
        ('الكميات', {
            'fields': (
                'planned_quantity', 'actual_quantity', 'defective_quantity'
            )
        }),
        ('العمالة', {
            'fields': ('assigned_workers',)
        }),
        ('ملاحظات', {
            'fields': ('notes',)
        }),
    )


@admin.register(CostVariance)
class CostVarianceAdmin(admin.ModelAdmin):
    list_display = [
        'production_order', 'total_standard_cost', 'total_actual_cost',
        'total_variance_display', 'total_variance_percentage', 'is_favorable_display'
    ]
    readonly_fields = ['analysis_date']
    fieldsets = (
        ('أمر الإنتاج', {
            'fields': ('production_order', 'analyzed_by', 'notes')
        }),
        ('تكاليف المواد', {
            'fields': ('standard_material_cost', 'actual_material_cost')
        }),
        ('تكاليف العمالة', {
            'fields': ('standard_labor_cost', 'actual_labor_cost')
        }),
        ('تكاليف غير مباشرة', {
            'fields': ('standard_overhead', 'actual_overhead')
        }),
    )

    @admin.display(description='التباين')
    def total_variance_display(self, obj):
        v = obj.total_variance
        color = 'green' if v <= 0 else 'red'
        return format_html(
            '<span style="color:{}">{:,.2f}</span>', color, v
        )

    @admin.display(description='مواتي', boolean=True)
    def is_favorable_display(self, obj):
        return obj.is_favorable
