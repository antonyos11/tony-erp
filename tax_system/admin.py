"""
إدارة نظام الضرائب
Tax System Admin Interface
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import TaxType, TaxCalculation, TaxReport, TaxCompliance


@admin.register(TaxType)
class TaxTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'tax_rate', 'applicable_on', 'active']
    list_filter = ['active', 'applicable_on']
    search_fields = ['code', 'name']
    readonly_fields = ['id', 'created_at']


@admin.register(TaxCalculation)
class TaxCalculationAdmin(admin.ModelAdmin):
    list_display = ['calculation_type', 'taxable_amount', 'tax_rate', 'tax_amount', 'is_paid', 'calculation_date']
    list_filter = ['calculation_type', 'is_paid', 'calculation_date']
    search_fields = ['invoice__number', 'journal_entry__id']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        (_('نوع الضريبة'), {
            'fields': ('tax_type', 'calculation_type')
        }),
        (_('الحسابات'), {
            'fields': ('taxable_amount', 'tax_rate', 'tax_amount')
        }),
        (_('الربط'), {
            'fields': ('invoice', 'journal_entry')
        }),
        (_('الدفع'), {
            'fields': ('is_paid', 'payment_date')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
    )


@admin.register(TaxReport)
class TaxReportAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'period_end', 'status', 'total_tax_liability', 'tax_payable']
    list_filter = ['report_type', 'status', 'period_end']
    search_fields = ['reference_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معلومات التقرير'), {
            'fields': ('report_type', 'period_type', 'status')
        }),
        (_('الفترة'), {
            'fields': ('period_start', 'period_end')
        }),
        (_('البيانات المالية'), {
            'fields': ('total_taxable_income', 'total_deductions', 'taxable_profit')
        }),
        (_('الالتزام الضريبي'), {
            'fields': ('total_tax_liability', 'tax_paid', 'tax_payable')
        }),
        (_('الإرسال'), {
            'fields': ('submission_date', 'reference_number', 'report_document')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
    )


@admin.register(TaxCompliance)
class TaxComplianceAdmin(admin.ModelAdmin):
    list_display = ['taxpayer_name', 'compliance_status', 'next_return_due_date', 'is_current']
    list_filter = ['compliance_status', 'is_current']
    search_fields = ['taxpayer_id', 'taxpayer_name']
    readonly_fields = ['id', 'updated_at']
    
    fieldsets = (
        (_('معلومات المكلف'), {
            'fields': ('taxpayer_id', 'taxpayer_name')
        }),
        (_('الإقرارات'), {
            'fields': ('last_return_filed_date', 'next_return_due_date')
        }),
        (_('الرصيد'), {
            'fields': ('tax_balance',)
        }),
        (_('الامتثال'), {
            'fields': ('compliance_status', 'is_current')
        }),
        (_('التدقيق'), {
            'fields': ('last_audit_date', 'audit_findings')
        }),
    )
