"""
إدارة Django Admin لموديول الاستيراد والتصدير
"""
from django.contrib import admin
from .models import (
    ShippingAgent, ExportOrder, ExportOrderItem, ExportCertificate,
    FinancialApproval, PreExportInvoice, CustomsClearance,
    ImportOrder, ImportOrderItem, ImportCertificate,
    ReleaseOrder, ImportWaiver
)


class ExportOrderItemInline(admin.TabularInline):
    """عناصر أمر التصدير"""
    model = ExportOrderItem
    extra = 1
    fields = ['product', 'description', 'quantity', 'unit', 'unit_price', 'hs_code', 'weight']


class ImportOrderItemInline(admin.TabularInline):
    """عناصر أمر الاستيراد"""
    model = ImportOrderItem
    extra = 1
    fields = ['product', 'description', 'quantity', 'unit', 'unit_price', 'hs_code', 'customs_rate', 'weight']


class ExportCertificateInline(admin.TabularInline):
    """شهادات التصدير"""
    model = ExportCertificate
    extra = 0
    fields = ['certificate_type', 'certificate_number', 'issue_date', 'expiry_date']


class ImportCertificateInline(admin.TabularInline):
    """شهادات الاستيراد"""
    model = ImportCertificate
    extra = 0
    fields = ['certificate_type', 'certificate_number', 'issue_date', 'expiry_date']


@admin.register(ShippingAgent)
class ShippingAgentAdmin(admin.ModelAdmin):
    """إدارة وكلاء الشحن"""
    list_display = ['name', 'agent_type', 'phone', 'email', 'is_active', 'created_at']
    list_filter = ['agent_type', 'is_active']
    search_fields = ['name', 'phone', 'email', 'license_number']
    ordering = ['-created_at']
    
    fieldsets = (
        ('البيانات الأساسية', {
            'fields': ('name', 'agent_type', 'license_number', 'is_active')
        }),
        ('معلومات الاتصال', {
            'fields': ('phone', 'email', 'address')
        }),
        ('الملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ExportOrder)
class ExportOrderAdmin(admin.ModelAdmin):
    """إدارة أوامر التصدير"""
    list_display = ['order_number', 'customer', 'status', 'order_date', 'destination_country', 'total_value']
    list_filter = ['status', 'order_date', 'destination_country']
    search_fields = ['order_number', 'customer__name', 'destination_country']
    date_hierarchy = 'order_date'
    ordering = ['-order_date']
    inlines = [ExportOrderItemInline, ExportCertificateInline]
    
    fieldsets = (
        ('بيانات الأمر', {
            'fields': ('order_number', 'customer', 'status', 'order_date')
        }),
        ('بيانات الشحن', {
            'fields': ('shipping_agent', 'shipping_type', 'destination_country', 
                      'destination_port', 'shipping_date', 'expected_arrival')
        }),
        ('البيانات المالية', {
            'fields': ('currency', 'shipping_cost', 'insurance_cost', 'other_costs')
        }),
        ('الملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def total_value(self, obj):
        return f"{obj.total_cost:.2f} {obj.currency}"
    total_value.short_description = 'الإجمالي'


@admin.register(FinancialApproval)
class FinancialApprovalAdmin(admin.ModelAdmin):
    """إدارة الموافقات المالية"""
    list_display = ['export_order', 'amount', 'currency', 'status', 'created_at', 'approved_at']
    list_filter = ['status', 'currency']
    search_fields = ['export_order__order_number', 'bank_name']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('بيانات الموافقة', {
            'fields': ('export_order', 'amount', 'currency', 'payment_type', 'status')
        }),
        ('معلومات البنك', {
            'fields': ('bank_name', 'bank_account', 'swift_code', 'iban')
        }),
        ('الاعتماد', {
            'fields': ('approved_by', 'approved_at', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('الملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['approved_at']


@admin.register(PreExportInvoice)
class PreExportInvoiceAdmin(admin.ModelAdmin):
    """إدارة فواتير ما قبل التصدير"""
    list_display = ['invoice_number', 'export_order', 'amount', 'currency', 'issue_date', 'status']
    list_filter = ['status', 'issue_date']
    search_fields = ['invoice_number', 'export_order__order_number']
    date_hierarchy = 'issue_date'
    ordering = ['-issue_date']


@admin.register(CustomsClearance)
class CustomsClearanceAdmin(admin.ModelAdmin):
    """إدارة وكلاء التخليص الجمركي"""
    list_display = ['name', 'license_number', 'agent_type', 'clearance_fee', 'is_active']
    list_filter = ['agent_type', 'is_active']
    search_fields = ['name', 'license_number', 'phone']
    ordering = ['name']


@admin.register(ImportOrder)
class ImportOrderAdmin(admin.ModelAdmin):
    """إدارة أوامر الاستيراد"""
    list_display = ['order_number', 'supplier', 'status', 'order_date', 'origin_country', 'total_cost_display']
    list_filter = ['status', 'order_date', 'origin_country']
    search_fields = ['order_number', 'supplier__name', 'origin_country']
    date_hierarchy = 'order_date'
    ordering = ['-order_date']
    inlines = [ImportOrderItemInline, ImportCertificateInline]
    
    fieldsets = (
        ('بيانات الأمر', {
            'fields': ('order_number', 'supplier', 'status', 'order_date')
        }),
        ('بيانات الشحن', {
            'fields': ('shipping_agent', 'shipping_type', 'origin_country', 
                      'shipping_port', 'destination_port', 'expected_arrival')
        }),
        ('مستندات الشحن', {
            'fields': ('commercial_invoice_number', 'bill_of_lading_number', 'lc_number')
        }),
        ('التكاليف', {
            'fields': ('currency', 'shipping_cost', 'insurance_cost', 'customs_duty', 'other_costs')
        }),
        ('الملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def total_cost_display(self, obj):
        return f"{obj.total_cost:.2f} {obj.currency}"
    total_cost_display.short_description = 'الإجمالي'


@admin.register(ReleaseOrder)
class ReleaseOrderAdmin(admin.ModelAdmin):
    """إدارة أوامر الإفراج"""
    list_display = ['release_number', 'import_order', 'status', 'release_date', 'customs_value']
    list_filter = ['status', 'release_date']
    search_fields = ['release_number', 'import_order__order_number']
    date_hierarchy = 'release_date'
    ordering = ['-release_date']


@admin.register(ImportWaiver)
class ImportWaiverAdmin(admin.ModelAdmin):
    """إدارة إعفاءات الاستيراد"""
    list_display = ['waiver_number', 'import_order', 'waiver_type', 'amount', 'status', 'issue_date']
    list_filter = ['waiver_type', 'status', 'issue_date']
    search_fields = ['waiver_number', 'import_order__order_number']
    date_hierarchy = 'issue_date'
    ordering = ['-issue_date']
