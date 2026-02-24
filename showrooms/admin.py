from django.contrib import admin
from .models import (
    Showroom,
    ShowroomEmployee,
    POSDevice,
    DeviceAuthToken,
    AttendanceRecord,
    ShowroomExpense,
    ShowroomPurchase,
    ShowroomPurchaseItem,
    ShowroomStockMovement,
    ShowroomPayrollEntry,
    ShowroomShift,
    ShowroomShiftAssignment,
    ShowroomPricingRule,
    ShowroomMoneyTransfer,
    ShowroomStockRequest,
    TemporaryWorker,
    ShowroomRentPayment,
)

@admin.register(Showroom)
class ShowroomAdmin(admin.ModelAdmin):
    list_display = ('code','name','name_ar','property_type','monthly_rent','manager','contact_phone','is_active')
    search_fields = ('code','name','name_ar')
    list_filter = ('is_active','property_type','showroom_type')
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('code', 'name', 'name_ar', 'showroom_type', 'location', 'manager', 'opening_date')
        }),
        ('بيانات الملكية والعقد', {
            'fields': (
                'property_type', 
                'property_value', 
                'monthly_rent', 
                'contract_start_date', 
                'contract_end_date',
                'contract_document',
                'contract_notes'
            )
        }),
        ('الحسابات المرتبطة', {
            'fields': ('asset_account', 'rent_expense_account')
        }),
        ('العنوان', {
            'fields': ('country', 'governorate', 'city', 'address')
        }),
        ('بيانات الاتصال', {
            'fields': ('contact_phone', 'contact_person')
        }),
        ('إعدادات المصروفات', {
            'fields': ('expense_approval_limit', 'require_expense_approval')
        }),
        ('الحالة', {
            'fields': ('is_active',)
        }),
    )

@admin.register(ShowroomEmployee)
class ShowroomEmployeeAdmin(admin.ModelAdmin):
    list_display = ('showroom','user','role','can_cross_access','active')
    list_filter = ('role','active','can_cross_access')
    search_fields = ('showroom__code','user__username')

@admin.register(POSDevice)
class POSDeviceAdmin(admin.ModelAdmin):
    list_display = ('name','showroom','identifier','is_active','last_seen')
    search_fields = ('name','identifier')
    list_filter = ('showroom','is_active')

@admin.register(DeviceAuthToken)
class DeviceAuthTokenAdmin(admin.ModelAdmin):
    list_display = ('device','token','revoked','expires_at')
    list_filter = ('revoked',)
    search_fields = ('token',)

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('date','showroom','employee','in_time','out_time','worked_seconds')
    list_filter = ('showroom','date')
    search_fields = ('employee__user__username',)


class ShowroomPurchaseItemInline(admin.TabularInline):
    model = ShowroomPurchaseItem
    extra = 0


@admin.register(ShowroomPurchase)
class ShowroomPurchaseAdmin(admin.ModelAdmin):
    list_display = ('number','showroom','supplier','status','total','invoice_file','created_at')
    list_filter = ('status','showroom')
    search_fields = ('number','supplier__name')
    inlines = [ShowroomPurchaseItemInline]


@admin.register(ShowroomExpense)
class ShowroomExpenseAdmin(admin.ModelAdmin):
    list_display = ('showroom','category','amount','status','requires_approval','attachment','created_at')
    list_filter = ('status','category','showroom')
    search_fields = ('description',)


@admin.register(ShowroomStockMovement)
class ShowroomStockMovementAdmin(admin.ModelAdmin):
    list_display = ('showroom','movement_type','product','quantity','reference','created_at')
    list_filter = ('movement_type','showroom')
    search_fields = ('reference','note')


@admin.register(ShowroomPayrollEntry)
class ShowroomPayrollEntryAdmin(admin.ModelAdmin):
    list_display = ('showroom','employee','period','amount','entry_type','status')
    list_filter = ('status','entry_type','showroom')
    search_fields = ('employee__user__username',)


@admin.register(ShowroomShift)
class ShowroomShiftAdmin(admin.ModelAdmin):
    list_display = ('showroom','name','start_time','end_time','break_minutes','is_active')
    list_filter = ('showroom','is_active')
    search_fields = ('name','showroom__code')


@admin.register(ShowroomShiftAssignment)
class ShowroomShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ('shift','employee','day_of_week','active','created_at')
    list_filter = ('day_of_week','active','shift__showroom')
    search_fields = ('employee__user__username','shift__name')


@admin.register(ShowroomPricingRule)
class ShowroomPricingRuleAdmin(admin.ModelAdmin):
    list_display = ('showroom', 'product', 'adjustment_type', 'value', 'effective_from', 'effective_to', 'is_active', 'priority')
    list_filter = ('showroom', 'adjustment_type', 'is_active', 'effective_from')
    search_fields = ('showroom__name', 'product__name', 'product__sku')
    date_hierarchy = 'effective_from'
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('showroom', 'product', 'is_active', 'priority')
        }),
        ('إعدادات التسعير', {
            'fields': ('adjustment_type', 'value')
        }),
        ('الفترة الزمنية', {
            'fields': ('effective_from', 'effective_to')
        }),
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ShowroomMoneyTransfer)
class ShowroomMoneyTransferAdmin(admin.ModelAdmin):
    list_display = ('transfer_number', 'from_showroom', 'to_showroom', 'amount', 'status', 'transfer_date', 'transfer_method')
    list_filter = ('status', 'transfer_method', 'from_showroom', 'to_showroom')
    search_fields = ('transfer_number', 'from_showroom__name', 'to_showroom__name', 'notes')
    readonly_fields = ('transfer_number', 'created_at', 'approved_at', 'completed_at', 'approved_by', 'received_by')
    date_hierarchy = 'transfer_date'
    
    fieldsets = (
        ('معلومات التحويل', {
            'fields': ('transfer_number', 'from_showroom', 'to_showroom', 'amount', 'transfer_method')
        }),
        ('الحالة', {
            'fields': ('status', 'transfer_date')
        }),
        ('تفاصيل الدفع', {
            'fields': ('bank_name', 'cheque_number', 'reference_number'),
            'classes': ('collapse',)
        }),
        ('ملاحظات', {
            'fields': ('notes', 'rejection_reason')
        }),
        ('معلومات النظام', {
            'fields': ('initiated_by', 'approved_by', 'received_by', 'created_at', 'approved_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ShowroomStockRequest)
class ShowroomStockRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'requesting_showroom', 'source_showroom', 'product', 'quantity_requested', 'status', 'priority', 'request_date')
    list_filter = ('status', 'priority', 'requesting_showroom', 'source_showroom')
    search_fields = ('request_number', 'product__name', 'customer_name', 'reason')
    readonly_fields = ('request_number', 'created_at', 'updated_at', 'approved_at', 'shipped_at', 'delivered_at')
    date_hierarchy = 'request_date'
    
    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('request_number', 'requesting_showroom', 'source_showroom', 'product')
        }),
        ('الكميات', {
            'fields': ('quantity_requested', 'quantity_approved', 'quantity_delivered')
        }),
        ('الحالة والأولوية', {
            'fields': ('status', 'priority', 'needed_by')
        }),
        ('سبب الطلب', {
            'fields': ('reason', 'customer_name', 'customer_phone')
        }),
        ('ملاحظات', {
            'fields': ('notes', 'rejection_reason')
        }),
        ('معلومات النظام', {
            'fields': ('requested_by', 'approved_by', 'shipped_by', 'received_by', 'request_date', 'approved_at', 'shipped_at', 'delivered_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TemporaryWorker)
class TemporaryWorkerAdmin(admin.ModelAdmin):
    list_display = ('worker_name', 'showroom', 'job_title', 'worker_type', 'start_date', 'end_date', 'total_amount', 'is_paid', 'is_active')
    list_filter = ('worker_type', 'is_paid', 'is_active', 'showroom')
    search_fields = ('worker_name', 'job_title', 'national_id', 'worker_phone')
    readonly_fields = ('total_amount', 'created_at', 'updated_at')
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('معلومات العامل', {
            'fields': ('showroom', 'worker_name', 'worker_phone', 'national_id', 'job_title')
        }),
        ('نوع العمل والأجر', {
            'fields': ('worker_type', 'daily_wage', 'hourly_wage')
        }),
        ('الفترة', {
            'fields': ('start_date', 'end_date', 'days_worked', 'hours_worked')
        }),
        ('المبلغ المستحق', {
            'fields': ('total_amount',)
        }),
        ('السداد', {
            'fields': ('is_paid', 'payment_date', 'payment_reference')
        }),
        ('الحسابات', {
            'fields': ('expense_account', 'journal_entry'),
            'classes': ('collapse',)
        }),
        ('ملاحظات وحالة', {
            'fields': ('notes', 'is_active', 'created_by')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # عند الإضافة
            obj.created_by = request.user
        obj.calculate_total()
        super().save_model(request, obj, form, change)


@admin.register(ShowroomRentPayment)
class ShowroomRentPaymentAdmin(admin.ModelAdmin):
    list_display = ('showroom', 'payment_date', 'amount', 'status', 'actual_payment_date', 'payment_reference')
    list_filter = ('status', 'showroom', 'payment_date')
    search_fields = ('showroom__name', 'payment_reference', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'days_overdue')
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('معلومات الدفعة', {
            'fields': ('showroom', 'payment_date', 'amount')
        }),
        ('الحالة', {
            'fields': ('status', 'actual_payment_date', 'payment_reference')
        }),
        ('الحسابات', {
            'fields': ('journal_entry',)
        }),
        ('ملاحظات', {
            'fields': ('notes',)
        }),
        ('معلومات النظام', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['mark_as_paid', 'check_overdue_payments']
    
    def mark_as_paid(self, request, queryset):
        for payment in queryset:
            payment.mark_as_paid(user=request.user)
        self.message_user(request, f'تم تحديد {queryset.count()} دفعة كمدفوعة')
    mark_as_paid.short_description = 'تحديد كمدفوع'
    
    def check_overdue_payments(self, request, queryset):
        for payment in queryset:
            payment.check_overdue()
        self.message_user(request, f'تم فحص {queryset.count()} دفعة')
    check_overdue_payments.short_description = 'فحص الدفعات المتأخرة'
