from django.contrib import admin
from .models import (
    TaxSettings, TaxCategory, TaxInvoice, TaxInvoiceLine,
    TaxPeriod, TaxPayment, TaxExemption
)


@admin.register(TaxSettings)
class TaxSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات الضرائب"""
    list_display = ['tax_registration_number', 'default_vat_rate', 'is_exempt']
    fieldsets = (
        ('معلومات التسجيل الضريبي', {
            'fields': ('tax_registration_number', 'tax_file_number', 'commercial_registration')
        }),
        ('نسب الضريبة', {
            'fields': ('default_vat_rate', 'exemption_threshold', 'is_exempt')
        }),
        ('إعدادات الفاتورة الإلكترونية', {
            'fields': ('einvoice_enabled', 'einvoice_api_key', 'einvoice_client_id', 
                      'einvoice_client_secret', 'einvoice_environment')
        }),
    )


@admin.register(TaxCategory)
class TaxCategoryAdmin(admin.ModelAdmin):
    """إدارة الفئات الضريبية"""
    list_display = ['name', 'code', 'rate', 'is_exempt', 'is_active']
    list_filter = ['is_exempt', 'is_active']
    search_fields = ['name', 'code']


class TaxInvoiceLineInline(admin.TabularInline):
    """بنود الفاتورة"""
    model = TaxInvoiceLine
    extra = 1
    fields = ['item_name', 'quantity', 'unit_price', 'discount', 'tax_rate', 'tax_amount', 'line_total']
    readonly_fields = ['tax_amount', 'line_total']


@admin.register(TaxInvoice)
class TaxInvoiceAdmin(admin.ModelAdmin):
    """إدارة الفواتير الضريبية"""
    list_display = ['invoice_number', 'invoice_type', 'partner_name', 'invoice_date', 
                    'subtotal', 'tax_amount', 'total', 'status']
    list_filter = ['invoice_type', 'status', 'invoice_date', 'tax_type']
    search_fields = ['invoice_number', 'partner_name', 'partner_tax_id']
    date_hierarchy = 'invoice_date'
    inlines = [TaxInvoiceLineInline]
    
    fieldsets = (
        ('معلومات الفاتورة', {
            'fields': ('invoice_number', 'invoice_type', 'internal_id', 'invoice_date')
        }),
        ('بيانات الطرف الآخر', {
            'fields': ('partner_name', 'partner_tax_id', 'partner_address')
        }),
        ('المبالغ', {
            'fields': ('subtotal', 'discount', 'tax_rate', 'tax_amount', 'total')
        }),
        ('الحالة', {
            'fields': ('tax_type', 'status', 'uuid', 'qr_code')
        }),
        ('بيانات الإرسال', {
            'fields': ('submitted_at', 'rejection_reason'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['uuid', 'tax_amount', 'total']


@admin.register(TaxPeriod)
class TaxPeriodAdmin(admin.ModelAdmin):
    """إدارة الفترات الضريبية"""
    list_display = ['name', 'period_type', 'start_date', 'end_date', 'total_output_tax', 
                    'total_input_tax', 'net_tax', 'status']
    list_filter = ['period_type', 'status']
    search_fields = ['name', 'reference_number']
    
    fieldsets = (
        ('بيانات الفترة', {
            'fields': ('name', 'period_type', 'start_date', 'end_date', 'due_date')
        }),
        ('الضرائب', {
            'fields': ('total_output_tax', 'total_input_tax', 'net_tax')
        }),
        ('الحالة', {
            'fields': ('status', 'reference_number', 'filed_at', 'filed_by')
        }),
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['total_output_tax', 'total_input_tax', 'net_tax', 'filed_at']


@admin.register(TaxPayment)
class TaxPaymentAdmin(admin.ModelAdmin):
    """إدارة مدفوعات الضرائب"""
    list_display = ['payment_date', 'period', 'amount', 'payment_type', 'reference_number']
    list_filter = ['payment_type', 'payment_date']
    search_fields = ['reference_number']


@admin.register(TaxExemption)
class TaxExemptionAdmin(admin.ModelAdmin):
    """إدارة الإعفاءات الضريبية"""
    list_display = ['exemption_type', 'name', 'start_date', 'end_date', 'is_active']
    list_filter = ['exemption_type', 'is_active']
    search_fields = ['name', 'legal_reference']
