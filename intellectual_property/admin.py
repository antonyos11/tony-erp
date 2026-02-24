"""
إدارة الملكية الفكرية
Intellectual Property Admin
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Patent, Trademark, CopyrightWork, IPLicense


@admin.register(Patent)
class PatentAdmin(admin.ModelAdmin):
    list_display = ['patent_number', 'title', 'patent_type', 'status', 'expiry_date']
    list_filter = ['status', 'patent_type', 'expiry_date']
    search_fields = ['patent_number', 'title', 'inventors']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معرف البراءة'), {
            'fields': ('patent_number', 'application_number', 'patent_type')
        }),
        (_('البيانات'), {
            'fields': ('title', 'description', 'technical_field', 'classification')
        }),
        (_('الملكية'), {
            'fields': ('inventors', 'patent_owner')
        }),
        (_('التواريخ'), {
            'fields': ('filing_date', 'publication_date', 'approval_date', 'expiry_date')
        }),
        (_('الحالة'), {
            'fields': ('status',)
        }),
        (_('الوثائق'), {
            'fields': ('specification_document', 'drawings', 'claims')
        }),
        (_('الحماية'), {
            'fields': ('protected_countries',)
        }),
        (_('الرسوم'), {
            'fields': ('registration_fee_paid', 'annual_fees_paid', 'next_renewal_date')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
    )


@admin.register(Trademark)
class TrademarkAdmin(admin.ModelAdmin):
    list_display = ['trademark_number', 'name', 'status', 'expiry_date']
    list_filter = ['status']
    search_fields = ['trademark_number', 'name']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        (_('معرف العلامة'), {
            'fields': ('trademark_number', 'name')
        }),
        (_('الوصف'), {
            'fields': ('description', 'logo_image')
        }),
        (_('التصنيف'), {
            'fields': ('goods_and_services', 'nice_classification')
        }),
        (_('الملكية'), {
            'fields': ('owner', 'owner_address')
        }),
        (_('التواريخ'), {
            'fields': ('registration_date', 'renewal_date', 'expiry_date')
        }),
        (_('الحماية'), {
            'fields': ('status', 'protected_countries')
        }),
    )


@admin.register(CopyrightWork)
class CopyrightWorkAdmin(admin.ModelAdmin):
    list_display = ['title', 'work_type', 'author', 'expiry_date']
    list_filter = ['work_type']
    search_fields = ['title', 'author']
    readonly_fields = ['id', 'created_at', 'registration_date']


@admin.register(IPLicense)
class IPLicenseAdmin(admin.ModelAdmin):
    list_display = ['license_number', 'license_type', 'licensor', 'licensee', 'end_date']
    list_filter = ['license_type']
    search_fields = ['license_number', 'licensor', 'licensee']
    readonly_fields = ['id', 'created_at']
