"""
تسجيل النماذج في لوحة الإدارة - وحدة الفروع الموحدة
"""
from django.contrib import admin
from .models import (
    Branch, BranchStaff, BranchTransfer, BranchTransferItem,
    POSDevice, DeviceAuthToken, BranchAttendance, BranchExpense,
    BranchPurchase, BranchPurchaseItem, BranchStockMovement,
    BranchPayroll, BranchShift, BranchShiftAssignment
)


class BranchStaffInline(admin.TabularInline):
    model = BranchStaff
    extra = 0
    autocomplete_fields = ['user']


class POSDeviceInline(admin.TabularInline):
    model = POSDevice
    extra = 0


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'branch_type', 'city', 'manager', 'status', 'is_main']
    list_filter = ['status', 'branch_type', 'city', 'is_main', 'is_active']
    search_fields = ['code', 'name', 'name_en', 'city', 'phone', 'email']
    list_editable = ['status']
    autocomplete_fields = ['manager', 'parent_branch', 'created_by', 'location']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [BranchStaffInline, POSDeviceInline]
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('code', 'name', 'name_en', 'branch_type', 'status', 'location')
        }),
        ('العنوان', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code')
        }),
        ('معلومات الاتصال', {
            'fields': ('phone', 'mobile', 'email', 'fax', 'contact_person')
        }),
        ('الموقع الجغرافي', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('الإدارة', {
            'fields': ('manager', 'parent_branch', 'is_main', 'is_active')
        }),
        ('إعدادات المخزون', {
            'fields': ('allow_negative_stock', 'auto_approve_transfers')
        }),
        ('إعدادات المصروفات', {
            'fields': ('expense_approval_limit', 'require_expense_approval')
        }),
        ('المعلومات الضريبية', {
            'fields': ('tax_id', 'commercial_register'),
            'classes': ('collapse',)
        }),
        ('التواريخ', {
            'fields': ('opening_date', 'created_at', 'updated_at', 'created_by')
        }),
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )


@admin.register(BranchStaff)
class BranchStaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'branch', 'role', 'position', 'is_active', 'start_date']
    list_filter = ['branch', 'role', 'is_active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'position']
    autocomplete_fields = ['branch', 'user']


class BranchTransferItemInline(admin.TabularInline):
    model = BranchTransferItem
    extra = 1
    autocomplete_fields = ['product']
    readonly_fields = ['total_cost']


@admin.register(BranchTransfer)
class BranchTransferAdmin(admin.ModelAdmin):
    list_display = ['transfer_number', 'from_branch', 'to_branch', 'transfer_date',
                    'status', 'total_items', 'requested_by']
    list_filter = ['status', 'from_branch', 'to_branch', 'transfer_date']
    search_fields = ['transfer_number']
    autocomplete_fields = ['from_branch', 'to_branch', 'requested_by', 'approved_by', 'received_by']
    readonly_fields = ['created_at', 'updated_at', 'approved_at', 'received_at']
    inlines = [BranchTransferItemInline]
    date_hierarchy = 'transfer_date'
    
    fieldsets = (
        ('معلومات التحويل', {
            'fields': ('transfer_number', 'from_branch', 'to_branch', 'status')
        }),
        ('التواريخ', {
            'fields': ('transfer_date', 'expected_arrival', 'actual_arrival')
        }),
        ('الموافقات', {
            'fields': ('requested_by', 'approved_by', 'approved_at', 'received_by', 'received_at')
        }),
        ('ملاحظات', {
            'fields': ('notes', 'rejection_reason'),
            'classes': ('collapse',)
        }),
    )


@admin.register(POSDevice)
class POSDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'identifier', 'branch', 'is_active', 'last_seen']
    list_filter = ['branch', 'is_active']
    search_fields = ['name', 'identifier']
    autocomplete_fields = ['branch']


@admin.register(BranchAttendance)
class BranchAttendanceAdmin(admin.ModelAdmin):
    list_display = ['branch', 'employee', 'date', 'in_time', 'out_time', 'worked_hours']
    list_filter = ['branch', 'date']
    search_fields = ['employee__user__username']
    date_hierarchy = 'date'


@admin.register(BranchExpense)
class BranchExpenseAdmin(admin.ModelAdmin):
    list_display = ['branch', 'category', 'amount', 'date', 'status', 'created_by']
    list_filter = ['branch', 'category', 'status', 'date']
    search_fields = ['description']
    date_hierarchy = 'date'


class BranchPurchaseItemInline(admin.TabularInline):
    model = BranchPurchaseItem
    extra = 1
    autocomplete_fields = ['product']


@admin.register(BranchPurchase)
class BranchPurchaseAdmin(admin.ModelAdmin):
    list_display = ['number', 'branch', 'supplier', 'date', 'status', 'total']
    list_filter = ['branch', 'status', 'date']
    search_fields = ['number']
    inlines = [BranchPurchaseItemInline]
    date_hierarchy = 'date'


@admin.register(BranchStockMovement)
class BranchStockMovementAdmin(admin.ModelAdmin):
    list_display = ['branch', 'product', 'quantity', 'movement_type', 'reference', 'created_at']
    list_filter = ['branch', 'movement_type', 'created_at']
    search_fields = ['reference', 'product__name']
    date_hierarchy = 'created_at'


@admin.register(BranchPayroll)
class BranchPayrollAdmin(admin.ModelAdmin):
    list_display = ['branch', 'employee', 'period', 'entry_type', 'amount', 'status']
    list_filter = ['branch', 'entry_type', 'status', 'period']
    search_fields = ['employee__user__username']


@admin.register(BranchShift)
class BranchShiftAdmin(admin.ModelAdmin):
    list_display = ['branch', 'name', 'start_time', 'end_time', 'break_minutes', 'is_active']
    list_filter = ['branch', 'is_active']


@admin.register(BranchShiftAssignment)
class BranchShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ['shift', 'employee', 'day_of_week', 'active']
    list_filter = ['shift__branch', 'day_of_week', 'active']


# استيراد تسجيلات Admin للموديلات الجديدة
try:
    from . import admin_distribution  # noqa: F401
except ImportError:
    pass

# Import advanced admin registrations
try:
    from . import admin_advanced  # noqa: F401
except ImportError:
    pass
