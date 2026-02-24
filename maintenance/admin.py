from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    MachineCategory, Machine, MaintenanceType, SparePart, MaintenanceRequest,
    MaintenanceSchedule, MaintenanceRecord, SparePartUsage, MaintenanceChecklist,
    ChecklistExecution
)


@admin.register(MachineCategory)
class MachineCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'default_maintenance_interval_days', 'default_warranty_months', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('code', 'name')
    ordering = ('code',)
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('code', 'name', 'description')
        }),
        ('الإعدادات الافتراضية', {
            'fields': ('default_maintenance_interval_days', 'default_warranty_months')
        }),
        ('الحالة', {
            'fields': ('is_active',)
        }),
    )


class SparePartUsageInline(admin.TabularInline):
    model = SparePartUsage
    extra = 0
    readonly_fields = ('total_cost',)


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'manufacturer', 'status', 'condition', 'location', 'is_under_warranty', 'maintenance_overdue', 'is_active')
    list_filter = ('status', 'condition', 'category', 'is_active', 'purchase_date', 'warranty_end_date')
    search_fields = ('code', 'name', 'manufacturer', 'model', 'serial_number')
    ordering = ('code',)
    readonly_fields = ('is_under_warranty', 'days_since_last_maintenance', 'maintenance_overdue', 'current_book_value', 'created_at', 'updated_at')
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('code', 'name', 'category')
        }),
        ('معلومات الشركة المصنعة', {
            'fields': ('manufacturer', 'model', 'serial_number', 'year_manufactured')
        }),
        ('الموقع والتشغيل', {
            'fields': ('location', 'work_center', 'department', 'responsible_employee')
        }),
        ('الحالة والتشغيل', {
            'fields': ('status', 'condition', 'operational_hours')
        }),
        ('معلومات الشراء والضمان', {
            'fields': ('purchase_date', 'purchase_price', 'warranty_start_date', 'warranty_end_date', 'supplier')
        }),
        ('الصيانة', {
            'fields': ('last_maintenance_date', 'next_maintenance_date', 'maintenance_interval_days')
        }),
        ('الحسابات المحاسبية', {
            'fields': ('asset_account', 'depreciation_account', 'maintenance_expense_account'),
            'classes': ('collapse',)
        }),
        ('إعدادات الإهلاك', {
            'fields': ('depreciation_method', 'useful_life_years', 'salvage_value'),
            'classes': ('collapse',)
        }),
        ('التوثيق', {
            'fields': ('specifications', 'installation_notes', 'user_manual_path'),
            'classes': ('collapse',)
        }),
        ('معلومات محسوبة', {
            'fields': ('is_under_warranty', 'days_since_last_maintenance', 'maintenance_overdue', 'current_book_value'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('is_active', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'location', 'work_center', 'department', 'responsible_employee')


@admin.register(MaintenanceType)
class MaintenanceTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'default_interval_days', 'estimated_cost', 'estimated_duration_hours', 'requires_external_service', 'is_active')
    list_filter = ('category', 'requires_external_service', 'is_active')
    search_fields = ('code', 'name')
    ordering = ('category', 'code')
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('code', 'name', 'description', 'category')
        }),
        ('التكرار والتكلفة', {
            'fields': ('default_interval_days', 'estimated_cost', 'estimated_duration_hours')
        }),
        ('المتطلبات', {
            'fields': ('required_skills', 'requires_external_service')
        }),
        ('الحالة', {
            'fields': ('is_active',)
        }),
    )


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'current_stock', 'minimum_stock', 'needs_reorder', 'stock_status', 'unit_cost', 'is_active')
    list_filter = ('category', 'is_active', 'storage_location')
    search_fields = ('code', 'name', 'manufacturer', 'part_number')
    ordering = ('code',)
    readonly_fields = ('needs_reorder', 'stock_status', 'created_at', 'updated_at')
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('code', 'name', 'description', 'category')
        }),
        ('الماكينات المتوافقة', {
            'fields': ('compatible_machines', 'machine_categories')
        }),
        ('معلومات الشركة المصنعة', {
            'fields': ('manufacturer', 'part_number', 'alternative_part_numbers')
        }),
        ('المخزون', {
            'fields': ('current_stock', 'minimum_stock', 'maximum_stock', 'reorder_point')
        }),
        ('التكلفة والسعر', {
            'fields': ('unit_cost', 'last_purchase_price', 'average_cost')
        }),
        ('الموردين', {
            'fields': ('primary_supplier', 'alternative_suppliers')
        }),
        ('العمر الافتراضي', {
            'fields': ('expected_life_hours', 'shelf_life_months')
        }),
        ('الموقع', {
            'fields': ('storage_location', 'bin_location')
        }),
        ('الحسابات المحاسبية', {
            'fields': ('inventory_account', 'expense_account'),
            'classes': ('collapse',)
        }),
        ('حالة المخزون', {
            'fields': ('needs_reorder', 'stock_status'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('is_active', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def stock_status_colored(self, obj):
        status_colors = {
            'out_of_stock': 'red',
            'low_stock': 'orange',
            'reorder_needed': 'yellow',
            'normal': 'green',
            'overstock': 'blue'
        }
        color = status_colors.get(obj.stock_status, 'black')
        return format_html('<span style="color: {}">{}</span>', color, obj.get_stock_status_display())
    stock_status_colored.short_description = 'حالة المخزون'


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'title', 'machine', 'maintenance_type', 'priority', 'status', 'requested_by', 'assigned_to', 'request_date')
    list_filter = ('status', 'priority', 'maintenance_type', 'request_date')
    search_fields = ('request_number', 'title', 'machine__name', 'machine__code')
    ordering = ('-request_date',)
    readonly_fields = ('request_number', 'actual_cost', 'actual_duration_hours', 'created_at', 'updated_at')
    date_hierarchy = 'request_date'
    
    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('request_number', 'machine', 'maintenance_type', 'title', 'description')
        }),
        ('التفاصيل', {
            'fields': ('problem_symptoms', 'priority', 'status')
        }),
        ('التواريخ', {
            'fields': ('request_date', 'requested_completion_date', 'approved_date', 'started_date', 'completed_date')
        }),
        ('الأشخاص المعنيين', {
            'fields': ('requested_by', 'assigned_to', 'approved_by')
        }),
        ('التكلفة والمدة', {
            'fields': ('estimated_cost', 'estimated_duration_hours', 'actual_cost', 'actual_duration_hours')
        }),
        ('ملاحظات', {
            'fields': ('notes', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'machine', 'maintenance_type', 'frequency', 'next_due_date', 'is_due', 'days_until_due', 'is_active')
    list_filter = ('frequency', 'is_active', 'maintenance_type')
    search_fields = ('name', 'machine__name', 'machine__code')
    ordering = ('next_due_date',)
    readonly_fields = ('is_due', 'days_until_due', 'created_at', 'updated_at')
    
    fieldsets = (
        ('معلومات الجدولة', {
            'fields': ('name', 'machine', 'maintenance_type')
        }),
        ('التكرار', {
            'fields': ('frequency', 'interval_days')
        }),
        ('التواريخ', {
            'fields': ('start_date', 'end_date', 'last_generated_date', 'next_due_date')
        }),
        ('الإعدادات', {
            'fields': ('auto_generate_requests', 'advance_notice_days')
        }),
        ('التكلفة والمدة', {
            'fields': ('estimated_cost', 'estimated_duration_hours', 'assigned_to')
        }),
        ('التفاصيل', {
            'fields': ('description', 'checklist_template'),
            'classes': ('collapse',)
        }),
        ('حالة الاستحقاق', {
            'fields': ('is_due', 'days_until_due'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('is_active', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_due_colored(self, obj):
        if obj.is_due:
            return format_html('<span style="color: red; font-weight: bold;">نعم</span>')
        return format_html('<span style="color: green;">لا</span>')
    is_due_colored.short_description = 'مستحق'


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ('record_number', 'machine', 'maintenance_type', 'technician', 'start_datetime', 'status', 'result', 'total_cost')
    list_filter = ('status', 'result', 'maintenance_type', 'start_datetime')
    search_fields = ('record_number', 'machine__name', 'machine__code', 'technician__name')
    ordering = ('-start_datetime',)
    readonly_fields = ('record_number', 'duration_hours', 'total_cost', 'created_at', 'updated_at')
    date_hierarchy = 'start_datetime'
    inlines = [SparePartUsageInline]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('record_number', 'maintenance_request', 'machine', 'maintenance_type')
        }),
        ('التواريخ والأوقات', {
            'fields': ('start_datetime', 'end_datetime', 'duration_hours')
        }),
        ('الحالة والنتيجة', {
            'fields': ('status', 'result')
        }),
        ('العمل المنفذ', {
            'fields': ('work_performed', 'problems_found', 'solutions_applied')
        }),
        ('فريق العمل', {
            'fields': ('technician', 'assistant_technicians')
        }),
        ('التكاليف', {
            'fields': ('labor_cost', 'parts_cost', 'external_service_cost', 'other_costs', 'total_cost')
        }),
        ('حالة الماكينة', {
            'fields': ('machine_condition_before', 'machine_condition_after')
        }),
        ('ملاحظات', {
            'fields': ('notes', 'recommendations', 'next_maintenance_notes'),
            'classes': ('collapse',)
        }),
        ('المرفقات', {
            'fields': ('photos_before', 'photos_after', 'documents'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SparePartUsage)
class SparePartUsageAdmin(admin.ModelAdmin):
    list_display = ('maintenance_record', 'spare_part', 'quantity_used', 'unit_cost', 'total_cost', 'reason', 'created_at')
    list_filter = ('reason', 'replaced_part_condition', 'created_at')
    search_fields = ('maintenance_record__record_number', 'spare_part__name', 'spare_part__code')
    ordering = ('-created_at',)
    readonly_fields = ('total_cost',)
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('maintenance_record', 'spare_part', 'reason')
        }),
        ('الكمية والتكلفة', {
            'fields': ('quantity_used', 'unit_cost', 'total_cost')
        }),
        ('القطعة المستبدلة', {
            'fields': ('replaced_part_condition', 'notes')
        }),
    )


@admin.register(MaintenanceChecklist)
class MaintenanceChecklistAdmin(admin.ModelAdmin):
    list_display = ('name', 'maintenance_type', 'machine_category', 'is_active', 'created_at')
    list_filter = ('maintenance_type', 'machine_category', 'is_active')
    search_fields = ('name', 'maintenance_type__name')
    ordering = ('name',)
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'maintenance_type', 'machine_category')
        }),
        ('قائمة الفحص', {
            'fields': ('checklist_items', 'instructions', 'safety_notes')
        }),
        ('معلومات النظام', {
            'fields': ('is_active', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ChecklistExecution)
class ChecklistExecutionAdmin(admin.ModelAdmin):
    list_display = ('maintenance_record', 'checklist', 'executed_by', 'execution_datetime')
    list_filter = ('checklist', 'execution_datetime')
    search_fields = ('maintenance_record__record_number', 'checklist__name')
    ordering = ('-execution_datetime',)
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('maintenance_record', 'checklist', 'executed_by', 'execution_datetime')
        }),
        ('النتائج', {
            'fields': ('results', 'notes', 'issues_found')
        }),
    )


# تخصيص واجهة الإدارة
admin.site.site_header = 'نظام إدارة الصيانة والمعدات'
admin.site.site_title = 'إدارة الصيانة'
admin.site.index_title = 'لوحة تحكم الصيانة'