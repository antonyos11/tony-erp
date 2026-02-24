from django.contrib import admin
from .models import ZATCAConfiguration, EInvoice, EInvoiceLog


@admin.register(ZATCAConfiguration)
class ZATCAConfigurationAdmin(admin.ModelAdmin):
    list_display = ['company', 'vat_number', 'environment', 'is_active', 'is_certified']
    list_filter = ['environment', 'is_active', 'is_certified']
    search_fields = ['company__name', 'vat_number', 'crn']
    
    fieldsets = (
        ('معلومات الشركة', {
            'fields': ('company', 'vat_number', 'crn')
        }),
        ('إعدادات الاتصال', {
            'fields': ('environment', 'api_base_url', 'compliance_csid', 'production_csid')
        }),
        ('الشهادات الرقمية', {
            'fields': ('certificate', 'private_key', 'certificate_password'),
            'classes': ('collapse',)
        }),
        ('الحالة', {
            'fields': ('is_active', 'is_certified', 'certification_date')
        }),
        ('العنوان', {
            'fields': ('seller_name', 'building_number', 'street_name', 'district', 'city', 'postal_code'),
            'classes': ('collapse',)
        }),
    )


class EInvoiceLogInline(admin.TabularInline):
    model = EInvoiceLog
    extra = 0
    readonly_fields = ['action', 'success', 'created_at']
    fields = ['action', 'success', 'error_message', 'created_at']
    can_delete = False


@admin.register(EInvoice)
class EInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'invoice_type', 'status', 'reported_at', 'cleared_at']
    list_filter = ['status', 'invoice_type']
    search_fields = ['invoice__invoice_number', 'uuid']
    readonly_fields = ['uuid', 'invoice_hash', 'qr_code', 'zatca_response', 'reported_at', 'cleared_at']
    inlines = [EInvoiceLogInline]
    
    fieldsets = (
        ('معلومات الفاتورة', {
            'fields': ('invoice', 'uuid', 'invoice_counter', 'invoice_type', 'status')
        }),
        ('التشفير', {
            'fields': ('invoice_hash', 'previous_invoice_hash')
        }),
        ('QR Code', {
            'fields': ('qr_code', 'qr_code_image')
        }),
        ('XML', {
            'fields': ('xml_invoice', 'signed_xml'),
            'classes': ('collapse',)
        }),
        ('ZATCA', {
            'fields': ('zatca_response', 'reported_at', 'cleared_at')
        }),
        ('الأخطاء', {
            'fields': ('error_message', 'validation_errors'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['generate_qr_codes', 'generate_xml', 'report_to_zatca']
    
    def generate_qr_codes(self, request, queryset):
        count = 0
        for einvoice in queryset:
            einvoice.generate_qr_code()
            count += 1
        self.message_user(request, f'تم توليد QR Code لـ {count} فاتورة')
    generate_qr_codes.short_description = 'توليد QR Code'
    
    def generate_xml(self, request, queryset):
        count = 0
        for einvoice in queryset:
            einvoice.generate_xml_invoice()
            einvoice.generate_hash()
            count += 1
        self.message_user(request, f'تم توليد XML لـ {count} فاتورة')
    generate_xml.short_description = 'توليد XML و Hash'
    
    def report_to_zatca(self, request, queryset):
        # هذا يحتاج تطوير كامل للاتصال بـ ZATCA API
        self.message_user(request, 'ميزة الإبلاغ لـ ZATCA قيد التطوير')
    report_to_zatca.short_description = 'إبلاغ ZATCA'


@admin.register(EInvoiceLog)
class EInvoiceLogAdmin(admin.ModelAdmin):
    list_display = ['einvoice', 'action', 'success', 'created_at']
    list_filter = ['action', 'success']
    search_fields = ['einvoice__invoice__invoice_number']
    readonly_fields = ['created_at']
