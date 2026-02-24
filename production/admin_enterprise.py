"""
Admin للنماذج الجديدة في وحدة الإنتاج
- MRP Planning
- Standard Cost
- Cost Variances
- Overhead Allocations
"""

from django.contrib import admin
from .mrp import MRPPlanningModel, MaterialReorderPoint
from .costing import StandardCost, CostVarianceRecord, OverheadAllocation
from .factory_showroom_integration import ProductionShowroomLink, DemandForecast, IntegrationLog


@admin.register(MRPPlanningModel)
class MRPPlanningModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'status', 'start_date', 'end_date', 'total_orders', 'estimated_cost', 'created_at']
    list_filter = ['plan_type', 'status', 'created_at']
    search_fields = ['name']
    readonly_fields = ['total_orders', 'total_products', 'estimated_cost', 'requirements_data', 'schedule_data', 'created_at', 'updated_at']
    
    fieldsets = (
        ('معلومات الخطة', {
            'fields': ('name', 'plan_type', 'status', 'start_date', 'end_date')
        }),
        ('ملخص', {
            'fields': ('total_orders', 'total_products', 'estimated_cost')
        }),
        ('البيانات', {
            'fields': ('requirements_data', 'schedule_data'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MaterialReorderPoint)
class MaterialReorderPointAdmin(admin.ModelAdmin):
    list_display = ['product', 'minimum_quantity', 'reorder_point', 'maximum_quantity', 'economic_order_quantity', 'lead_time_days']
    list_filter = ['auto_calculate', 'lead_time_days']
    search_fields = ['product__name', 'product__sku']
    raw_id_fields = ['product']
    
    actions = ['calculate_from_consumption']
    
    def calculate_from_consumption(self, request, queryset):
        for obj in queryset:
            obj.calculate_from_consumption()
        self.message_user(request, f"تم حساب نقاط إعادة الطلب لـ {queryset.count()} منتج")
    calculate_from_consumption.short_description = "حساب من الاستهلاك"


@admin.register(StandardCost)
class StandardCostAdmin(admin.ModelAdmin):
    list_display = ['product', 'effective_date', 'material_cost', 'labor_cost', 'overhead_cost', 'total_cost', 'is_active']
    list_filter = ['is_active', 'effective_date']
    search_fields = ['product__name', 'product__sku']
    raw_id_fields = ['product']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('المنتج', {
            'fields': ('product', 'effective_date', 'expiry_date', 'is_active')
        }),
        ('التكاليف', {
            'fields': ('material_cost', 'labor_cost', 'overhead_cost', 'other_cost')
        }),
        ('تفاصيل إضافية', {
            'fields': ('labor_hours', 'machine_hours', 'notes'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CostVarianceRecord)
class CostVarianceRecordAdmin(admin.ModelAdmin):
    list_display = ['production_order', 'variance_type', 'variance_date', 'standard_value', 'actual_value', 'variance_amount', 'is_favorable']
    list_filter = ['variance_type', 'is_favorable', 'variance_date']
    search_fields = ['production_order__order_number']
    raw_id_fields = ['production_order']
    readonly_fields = ['variance_amount', 'is_favorable', 'created_at']


@admin.register(OverheadAllocation)
class OverheadAllocationAdmin(admin.ModelAdmin):
    list_display = ['production_order', 'work_center', 'period_start', 'period_end', 'allocation_method', 'allocated_amount', 'is_posted']
    list_filter = ['allocation_method', 'is_posted', 'period_start']
    search_fields = ['production_order__order_number']
    raw_id_fields = ['production_order', 'work_center', 'journal_entry']


@admin.register(ProductionShowroomLink)
class ProductionShowroomLinkAdmin(admin.ModelAdmin):
    list_display = ['production_order', 'target_branch', 'quantity', 'status', 'transfer', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['production_order__order_number', 'target_branch__name']
    raw_id_fields = ['production_order', 'replenishment_request', 'target_branch', 'transfer']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DemandForecast)
class DemandForecastAdmin(admin.ModelAdmin):
    list_display = ['product', 'branch', 'forecast_date', 'forecast_quantity', 'confidence_level', 'is_active']
    list_filter = ['is_active', 'forecast_date', 'branch']
    search_fields = ['product__name']
    raw_id_fields = ['product', 'branch']


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'action_date', 'production_order', 'transfer', 'branch', 'user']
    list_filter = ['action_type', 'action_date']
    search_fields = ['message']
    raw_id_fields = ['production_order', 'transfer', 'branch', 'user']
    readonly_fields = ['action_date']
