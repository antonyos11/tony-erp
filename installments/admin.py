from django.contrib import admin
from django.db import models
from .models import (
    InstallmentPlan, InstallmentContract, Installment,
    InstallmentPayment, Guarantor, InstallmentReminder, InstallmentSettings
)


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0
    readonly_fields = ['installment_number', 'due_date', 'amount', 'paid_amount', 'late_fee', 'status', 'payment_date']
    can_delete = False


class GuarantorInline(admin.TabularInline):
    model = Guarantor
    extra = 0


class InstallmentPaymentInline(admin.TabularInline):
    model = InstallmentPayment
    extra = 0
    readonly_fields = ['amount', 'payment_date', 'receipt_number']


@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration_months', 'annual_interest_rate', 'min_down_payment_percentage', 'requires_guarantor', 'is_active']
    list_filter = ['is_active', 'requires_guarantor', 'duration_months']
    search_fields = ['name', 'description']
    ordering = ['duration_months']


@admin.register(InstallmentContract)
class InstallmentContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'customer', 'plan', 'principal_amount', 'monthly_payment', 'status', 'start_date']
    list_filter = ['status', 'plan', 'showroom', 'contract_date']
    search_fields = ['contract_number', 'customer__name', 'national_id', 'phone']
    readonly_fields = ['contract_number', 'uuid', 'financed_amount', 'total_amount', 'created_at', 'updated_at']
    date_hierarchy = 'contract_date'
    inlines = [InstallmentInline, GuarantorInline]
    
    fieldsets = (
        ('معلومات العقد', {
            'fields': ('contract_number', 'uuid', 'customer', 'plan', 'invoice', 'showroom', 'status')
        }),
        ('المبالغ', {
            'fields': ('principal_amount', 'down_payment', 'financed_amount', 'admin_fee', 'total_interest', 'monthly_payment', 'total_amount')
        }),
        ('التواريخ', {
            'fields': ('contract_date', 'start_date', 'end_date')
        }),
        ('بيانات العميل', {
            'fields': ('national_id', 'national_id_image', 'address', 'phone', 'alternative_phone', 'work_address', 'work_phone'),
            'classes': ('collapse',)
        }),
        ('الملاحظات والتوقيعات', {
            'fields': ('notes', 'internal_notes', 'customer_signature', 'signed_contract'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'due_date', 'amount', 'paid_amount', 'late_fee', 'status']
    list_filter = ['status', 'due_date', 'contract__plan']
    search_fields = ['contract__contract_number', 'contract__customer__name']
    date_hierarchy = 'due_date'
    inlines = [InstallmentPaymentInline]
    
    actions = ['mark_as_paid', 'calculate_late_fees']
    
    def mark_as_paid(self, request, queryset):
        count = queryset.update(status='paid', paid_amount=models.F('amount'))
        self.message_user(request, f'تم تحديث {count} قسط كمدفوع')
    mark_as_paid.short_description = 'تحديد كمدفوع'
    
    def calculate_late_fees(self, request, queryset):
        for inst in queryset:
            inst.late_fee = inst.calculate_late_fee()
            inst.save()
        self.message_user(request, f'تم حساب رسوم التأخير لـ {queryset.count()} قسط')
    calculate_late_fees.short_description = 'حساب رسوم التأخير'


@admin.register(InstallmentPayment)
class InstallmentPaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'installment', 'amount', 'payment_date', 'payment_method']
    list_filter = ['payment_date', 'payment_method']
    search_fields = ['receipt_number', 'installment__contract__contract_number']
    readonly_fields = ['receipt_number', 'created_at']


@admin.register(Guarantor)
class GuarantorAdmin(admin.ModelAdmin):
    list_display = ['name', 'contract', 'phone', 'relationship', 'job_title']
    list_filter = ['relationship']
    search_fields = ['name', 'national_id', 'phone', 'contract__contract_number']


@admin.register(InstallmentReminder)
class InstallmentReminderAdmin(admin.ModelAdmin):
    list_display = ['installment', 'reminder_type', 'channel', 'sent_at', 'delivered', 'read']
    list_filter = ['reminder_type', 'channel', 'delivered', 'read']
    date_hierarchy = 'sent_at'


@admin.register(InstallmentSettings)
class InstallmentSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('إعدادات التذكيرات', {
            'fields': ('auto_reminders_enabled', 'reminder_days_before', 'overdue_reminder_interval', 'max_reminders_per_installment')
        }),
        ('قنوات التذكير', {
            'fields': ('sms_enabled', 'whatsapp_enabled', 'email_enabled', 'push_enabled')
        }),
        ('قواعد التعثر', {
            'fields': ('default_after_days',)
        }),
        ('قوالب الرسائل', {
            'fields': ('upcoming_message_template', 'due_message_template', 'overdue_message_template'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # السماح بإضافة سجل واحد فقط
        return not InstallmentSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
