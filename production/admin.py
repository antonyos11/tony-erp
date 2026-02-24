from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import (
    ProductionSettings, ProductionWorkCenter, BillOfMaterials, BOMItem,
    ProductionStage, BOMStage, ProductionOrder, ProductionOrderStage,
    MaterialConsumption, ProductionTimeLog, ProductionQualityCheck,
    ProductionCostAnalysis, ProductionReport, ProductionAlert
)


@admin.register(ProductionSettings)
class ProductionSettingsAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'overhead_allocation_method', 'overhead_rate', 'updated_at']
    fieldsets = [
        ('معلومات أساسية', {
            'fields': ['company_name', 'default_work_center']
        }),
        ('الحسابات المحاسبية', {
            'fields': [
                'wip_account', 'finished_goods_account', 'raw_materials_account',
                'labor_cost_account', 'overhead_account'
            ]
        }),
        ('إعدادات التكلفة', {
            'fields': ['overhead_allocation_method', 'overhead_rate']
        }),
    ]


@admin.register(ProductionWorkCenter)
class ProductionWorkCenterAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'work_center_type', 'supervisor', 'hourly_rate',
        'efficiency_rate', 'is_active'
    ]
    list_filter = ['work_center_type', 'is_active', 'department']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('معلومات أساسية', {
            'fields': ['code', 'name', 'work_center_type', 'department', 'location', 'supervisor']
        }),
        ('معدلات التكلفة', {
            'fields': ['hourly_rate', 'setup_time', 'efficiency_rate']
        }),
        ('السعة والقدرة', {
            'fields': ['capacity_per_hour', 'working_hours_per_day']
        }),
        ('إعدادات أخرى', {
            'fields': ['is_active', 'cost_center']
        }),
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'department', 'location', 'supervisor', 'cost_center'
        )


class BOMItemInline(admin.TabularInline):
    model = BOMItem
    extra = 1
    fields = ['sequence', 'material', 'item_type', 'quantity', 'unit_cost', 'wastage_percentage', 'notes']
    ordering = ['sequence']


class BOMStageInline(admin.TabularInline):
    model = BOMStage
    extra = 0
    fields = ['sequence', 'stage', 'is_required']
    ordering = ['sequence']


@admin.register(BillOfMaterials)
class BillOfMaterialsAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'version', 'base_quantity', 'total_material_cost',
        'total_cost_per_unit', 'is_active', 'is_default'
    ]
    list_filter = ['is_active', 'is_default', 'product__name']
    search_fields = ['product__name', 'name', 'version']
    readonly_fields = ['total_material_cost', 'total_labor_cost', 'total_overhead_cost', 'created_at', 'updated_at']
    inlines = [BOMItemInline, BOMStageInline]
    
    fieldsets = [
        ('معلومات أساسية', {
            'fields': ['product', 'version', 'name', 'description']
        }),
        ('كمية الإنتاج', {
            'fields': ['base_quantity']
        }),
        ('التواريخ', {
            'fields': ['effective_date', 'expiry_date']
        }),
        ('الحالة', {
            'fields': ['is_active', 'is_default']
        }),
        ('التكاليف المحسوبة (للعرض فقط)', {
            'fields': ['total_material_cost', 'total_labor_cost', 'total_overhead_cost'],
            'classes': ['collapse']
        }),
    ]
    
    def total_cost_per_unit(self, obj):
        return f"{obj.total_cost_per_unit:.2f} ج.م"
    total_cost_per_unit.short_description = 'تكلفة الوحدة'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'created_by')


@admin.register(ProductionStage)
class ProductionStageAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'work_center', 'sequence', 'operation_time',
        'required_workers', 'skill_level', 'requires_quality_check', 'is_active'
    ]
    list_filter = ['work_center', 'skill_level', 'requires_quality_check', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['sequence']
    
    fieldsets = [
        ('معلومات أساسية', {
            'fields': ['code', 'name', 'description', 'sequence', 'work_center']
        }),
        ('أوقات العملية', {
            'fields': ['setup_time', 'operation_time', 'teardown_time']
        }),
        ('العمالة المطلوبة', {
            'fields': ['required_workers', 'skill_level']
        }),
        ('فحص الجودة', {
            'fields': ['requires_quality_check', 'quality_check_percentage']
        }),
        ('الحالة', {
            'fields': ['is_active']
        }),
    ]


class ProductionOrderStageInline(admin.TabularInline):
    model = ProductionOrderStage
    extra = 0
    fields = ['stage', 'status', 'planned_quantity', 'completed_quantity', 'quality_approved']
    readonly_fields = ['estimated_cost', 'actual_cost']


class MaterialConsumptionInline(admin.TabularInline):
    model = MaterialConsumption
    extra = 0
    fields = ['material', 'planned_quantity', 'consumed_quantity', 'wastage_quantity', 'total_cost']
    readonly_fields = ['total_cost']


@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = [
        'number', 'product', 'status', 'priority', 'planned_quantity',
        'produced_quantity', 'completion_percentage_display', 'planned_end_date',
        'cost_status'
    ]
    list_filter = [
        'status', 'priority', 'order_date', 'planned_start_date',
        'product__name', 'supervisor'
    ]
    search_fields = ['number', 'product__name', 'notes']
    readonly_fields = [
        'number', 'completion_percentage', 'remaining_quantity',
        'estimated_total_cost', 'actual_total_cost', 'cost_variance',
        'unit_cost', 'created_at', 'updated_at'
    ]
    inlines = [ProductionOrderStageInline, MaterialConsumptionInline]
    date_hierarchy = 'order_date'
    
    fieldsets = [
        ('معلومات الأمر', {
            'fields': ['number', 'product', 'bom']
        }),
        ('الكميات', {
            'fields': ['planned_quantity', 'produced_quantity', 'scrap_quantity']
        }),
        ('التواريخ', {
            'fields': [
                'order_date', 'planned_start_date', 'planned_end_date',
                'actual_start_date', 'actual_end_date'
            ]
        }),
        ('الحالة والأولوية', {
            'fields': ['status', 'priority']
        }),
        ('المسؤوليات', {
            'fields': ['supervisor', 'created_by']
        }),
        ('التكاليف المقدرة', {
            'fields': ['estimated_material_cost', 'estimated_labor_cost', 'estimated_overhead_cost'],
            'classes': ['collapse']
        }),
        ('التكاليف الفعلية', {
            'fields': ['actual_material_cost', 'actual_labor_cost', 'actual_overhead_cost'],
            'classes': ['collapse']
        }),
        ('معلومات إضافية', {
            'fields': [
                'completion_percentage', 'remaining_quantity', 'estimated_total_cost',
                'actual_total_cost', 'cost_variance', 'unit_cost'
            ],
            'classes': ['collapse']
        }),
        ('ملاحظات', {
            'fields': ['notes']
        }),
    ]
    
    def completion_percentage_display(self, obj):
        percentage = obj.completion_percentage
        if percentage >= 100:
            color = 'green'
        elif percentage >= 75:
            color = 'orange'
        elif percentage >= 50:
            color = 'blue'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, percentage
        )
    completion_percentage_display.short_description = 'نسبة الإنجاز'
    
    def cost_status(self, obj):
        variance = obj.cost_variance
        if variance > 0:
            return format_html('<span style="color: red;">تجاوز: {:.2f}</span>', variance)
        elif variance < 0:
            return format_html('<span style="color: green;">وفرة: {:.2f}</span>', abs(variance))
        else:
            return format_html('<span style="color: blue;">متطابق</span>')
    cost_status.short_description = 'حالة التكلفة'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'product', 'bom', 'supervisor', 'created_by'
        ).prefetch_related('order_stages')


@admin.register(MaterialConsumption)
class MaterialConsumptionAdmin(admin.ModelAdmin):
    list_display = [
        'production_order', 'material', 'planned_quantity', 'consumed_quantity',
        'variance_quantity', 'variance_percentage_display', 'total_cost',
        'consumption_date'
    ]
    list_filter = [
        'consumption_date', 'production_order__status',
        'material__name', 'location'
    ]
    search_fields = ['production_order__number', 'material__name']
    readonly_fields = ['total_cost', 'variance_quantity', 'variance_percentage']
    date_hierarchy = 'consumption_date'
    
    fieldsets = [
        ('معلومات أساسية', {
            'fields': ['production_order', 'stage', 'material']
        }),
        ('الكميات', {
            'fields': ['planned_quantity', 'consumed_quantity', 'wastage_quantity']
        }),
        ('التكلفة', {
            'fields': ['unit_cost', 'total_cost']
        }),
        ('التواريخ والمسؤوليات', {
            'fields': ['consumption_date', 'issued_by', 'location']
        }),
        ('التحليل (للعرض فقط)', {
            'fields': ['variance_quantity', 'variance_percentage'],
            'classes': ['collapse']
        }),
        ('ملاحظات', {
            'fields': ['notes']
        }),
    ]
    
    def variance_percentage_display(self, obj):
        percentage = obj.variance_percentage
        if percentage > 10:
            color = 'red'
        elif percentage > 5:
            color = 'orange'
        elif percentage < -5:
            color = 'green'
        else:
            color = 'black'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, percentage
        )
    variance_percentage_display.short_description = 'نسبة الانحراف'


@admin.register(ProductionTimeLog)
class ProductionTimeLogAdmin(admin.ModelAdmin):
    list_display = [
        'production_order', 'employee', 'activity_type', 'start_time',
        'duration_hours_display', 'quantity_produced', 'productivity_rate_display',
        'total_cost'
    ]
    list_filter = [
        'activity_type', 'start_time', 'work_center',
        'production_order__status', 'employee__department'
    ]
    search_fields = ['production_order__number', 'employee__arabic_name']
    readonly_fields = ['duration_hours', 'productivity_rate', 'total_cost']
    date_hierarchy = 'start_time'
    
    fieldsets = [
        ('معلومات أساسية', {
            'fields': ['production_order', 'stage', 'employee', 'work_center']
        }),
        ('النشاط والوقت', {
            'fields': [
                'activity_type', 'start_time', 'end_time',
                'break_time_minutes', 'duration_hours'
            ]
        }),
        ('الإنتاج', {
            'fields': ['quantity_produced', 'quantity_scrapped', 'productivity_rate']
        }),
        ('التكلفة', {
            'fields': ['hourly_rate', 'total_cost']
        }),
        ('التقييم', {
            'fields': ['efficiency_percentage', 'quality_rating']
        }),
        ('إضافي', {
            'fields': ['notes', 'recorded_by']
        }),
    ]
    
    def duration_hours_display(self, obj):
        hours = obj.duration_hours
        return f"{hours:.2f} ساعة"
    duration_hours_display.short_description = 'مدة العمل'
    
    def productivity_rate_display(self, obj):
        rate = obj.productivity_rate
        return f"{rate:.2f} قطعة/ساعة"
    productivity_rate_display.short_description = 'معدل الإنتاجية'


@admin.register(ProductionQualityCheck)
class ProductionQualityCheckAdmin(admin.ModelAdmin):
    list_display = [
        'production_order', 'stage', 'inspector', 'check_date',
        'overall_result', 'quality_score', 'pass_rate_percentage_display'
    ]
    list_filter = [
        'overall_result', 'check_date', 'inspector',
        'production_order__status'
    ]
    search_fields = ['production_order__number', 'inspector__arabic_name']
    readonly_fields = ['pass_rate_percentage', 'reject_rate_percentage']
    date_hierarchy = 'check_date'
    
    fieldsets = [
        ('معلومات أساسية', {
            'fields': ['production_order', 'stage', 'check_date', 'inspector']
        }),
        ('الكميات', {
            'fields': [
                'quantity_checked', 'quantity_passed',
                'quantity_failed', 'quantity_rework'
            ]
        }),
        ('النتيجة', {
            'fields': ['overall_result', 'quality_score']
        }),
        ('التفاصيل', {
            'fields': ['defect_types', 'corrective_actions']
        }),
        ('المتطلبات', {
            'fields': ['standards_reference', 'test_conditions']
        }),
        ('التحليل (للعرض فقط)', {
            'fields': ['pass_rate_percentage', 'reject_rate_percentage'],
            'classes': ['collapse']
        }),
        ('ملاحظات', {
            'fields': ['notes']
        }),
    ]
    
    def pass_rate_percentage_display(self, obj):
        percentage = obj.pass_rate_percentage
        if percentage >= 95:
            color = 'green'
        elif percentage >= 85:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, percentage
        )
    pass_rate_percentage_display.short_description = 'نسبة النجاح'


@admin.register(ProductionCostAnalysis)
class ProductionCostAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'production_order', 'cost_category', 'description',
        'budgeted_amount', 'actual_amount', 'variance_display',
        'cost_date'
    ]
    list_filter = [
        'cost_category', 'cost_date', 'production_order__status',
        'cost_center'
    ]
    search_fields = ['production_order__number', 'description']
    readonly_fields = ['variance', 'variance_percentage']
    date_hierarchy = 'cost_date'
    
    fieldsets = [
        ('معلومات أساسية', {
            'fields': [
                'production_order', 'cost_category', 'cost_center',
                'description', 'reference_document'
            ]
        }),
        ('المبالغ', {
            'fields': ['budgeted_amount', 'actual_amount']
        }),
        ('التحليل (للعرض فقط)', {
            'fields': ['variance', 'variance_percentage'],
            'classes': ['collapse']
        }),
        ('التواريخ والمسؤوليات', {
            'fields': ['cost_date', 'recorded_by']
        }),
        ('الربط المحاسبي', {
            'fields': ['journal_entry']
        }),
        ('ملاحظات', {
            'fields': ['notes']
        }),
    ]
    
    def variance_display(self, obj):
        variance = obj.variance
        if variance > 0:
            return format_html('<span style="color: red;">+{:.2f}</span>', variance)
        elif variance < 0:
            return format_html('<span style="color: green;">{:.2f}</span>', variance)
        else:
            return format_html('<span style="color: blue;">0.00</span>')
    variance_display.short_description = 'الانحراف'


@admin.register(ProductionAlert)
class ProductionAlertAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'alert_type', 'priority', 'status',
        'production_order', 'assigned_to', 'alert_date',
        'is_overdue_display'
    ]
    list_filter = [
        'alert_type', 'priority', 'status', 'alert_date',
        'work_center', 'assigned_to'
    ]
    search_fields = ['title', 'description', 'production_order__number']
    readonly_fields = ['is_overdue']
    date_hierarchy = 'alert_date'
    
    fieldsets = [
        ('معلومات التنبيه', {
            'fields': ['title', 'alert_type', 'priority', 'status']
        }),
        ('المصدر', {
            'fields': ['production_order', 'work_center']
        }),
        ('التفاصيل', {
            'fields': ['description', 'suggested_action']
        }),
        ('المسؤوليات', {
            'fields': ['assigned_to', 'created_by']
        }),
        ('التواريخ', {
            'fields': [
                'alert_date', 'due_date', 'resolved_date',
                'acknowledged_date', 'is_overdue'
            ]
        }),
        ('الإقرار والحل', {
            'fields': [
                'acknowledged_by', 'resolution_notes', 'resolved_by'
            ],
            'classes': ['collapse']
        }),
    ]
    
    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red; font-weight: bold;">متأخر</span>')
        else:
            return format_html('<span style="color: green;">في الوقت</span>')
    is_overdue_display.short_description = 'حالة التوقيت'


@admin.register(ProductionReport)
class ProductionReportAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'report_type', 'period_start', 'period_end',
        'status', 'generated_by', 'created_at'
    ]
    list_filter = [
        'report_type', 'status', 'period_start',
        'work_center', 'product', 'department'
    ]
    search_fields = ['title', 'summary']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('معلومات التقرير', {
            'fields': ['title', 'report_type', 'status']
        }),
        ('الفترة', {
            'fields': ['period_start', 'period_end']
        }),
        ('الفلاتر', {
            'fields': ['work_center', 'product', 'department']
        }),
        ('المحتوى', {
            'fields': ['summary', 'details']
        }),
        ('المسؤوليات', {
            'fields': ['generated_by', 'approved_by']
        }),
        ('الملف', {
            'fields': ['report_file']
        }),
    ]


# تخصيص موقع الإدارة
admin.site.site_header = "إدارة نظام الإنتاج - المحاسب الشامل"
admin.site.site_title = "نظام الإنتاج"

# استيراد تسجيلات Admin للموديلات الجديدة
try:
    from . import admin_enterprise  # noqa: F401
except ImportError:
    pass
admin.site.index_title = "لوحة تحكم الإنتاج"

# Import advanced admin registrations
try:
    from . import admin_advanced  # noqa: F401
except ImportError:
    pass