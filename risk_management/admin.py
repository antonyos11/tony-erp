"""
إدارة أنظمة التأمين والمخاطر
Risk Management & Insurance Admin Interface
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Risk, RiskCategory, InsurancePolicy, InsuranceClaim, CoverageAnalysis


@admin.register(RiskCategory)
class RiskCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_code']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at']


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'probability', 'impact', 'risk_score', 'status']
    list_filter = ['status', 'probability', 'impact', 'category']
    search_fields = ['title', 'description']
    readonly_fields = ['risk_score', 'id', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معلومات المخاطرة'), {
            'fields': ('category', 'title', 'description')
        }),
        (_('التقييم'), {
            'fields': ('probability', 'impact', 'risk_score')
        }),
        (_('التأثير المالي'), {
            'fields': ('potential_loss',)
        }),
        (_('خطة التخفيف'), {
            'fields': ('mitigation_plan', 'mitigation_owner')
        }),
        (_('الحالة والتواريخ'), {
            'fields': ('status', 'identified_date', 'review_date', 'closure_date')
        }),
        (_('المرفقات'), {
            'fields': ('attachments',)
        }),
        (_('معلومات النظام'), {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_mitigated']
    
    def mark_as_mitigated(self, request, queryset):
        queryset.update(status='mitigated')
    mark_as_mitigated.short_description = _('وضع علامة كممكن تقليل الأثر')


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_number', 'policy_type', 'insurer_name', 'status', 'end_date']
    list_filter = ['status', 'policy_type', 'end_date']
    search_fields = ['policy_number', 'insurer_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معلومات البوليصة'), {
            'fields': ('policy_number', 'policy_type', 'insurer_name')
        }),
        (_('المبالغ'), {
            'fields': ('premium', 'coverage_amount', 'deductible')
        }),
        (_('التواريخ'), {
            'fields': ('start_date', 'end_date')
        }),
        (_('التفاصيل'), {
            'fields': ('coverage_details', 'status', 'notes')
        }),
        (_('معلومات النظام'), {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_number', 'policy', 'claim_date', 'claim_amount', 'status']
    list_filter = ['status', 'claim_date', 'policy']
    search_fields = ['claim_number', 'description']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        (_('معلومات المطالبة'), {
            'fields': ('claim_number', 'policy')
        }),
        (_('الحادث'), {
            'fields': ('incident_date', 'description')
        }),
        (_('المبالغ'), {
            'fields': ('claim_amount', 'approved_amount')
        }),
        (_('الحالة'), {
            'fields': ('status', 'claim_date', 'submitted_by')
        }),
        (_('المستندات'), {
            'fields': ('attachment',)
        }),
        (_('معلومات النظام'), {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CoverageAnalysis)
class CoverageAnalysisAdmin(admin.ModelAdmin):
    list_display = ['title', 'analysis_date', 'created_by']
    list_filter = ['analysis_date']
    readonly_fields = ['id']
    filter_horizontal = ['identified_risks', 'policies']
    
    fieldsets = (
        (_('معلومات التحليل'), {
            'fields': ('title', 'analysis_date', 'created_by')
        }),
        (_('المخاطر والبوالص'), {
            'fields': ('identified_risks', 'policies')
        }),
        (_('الفجوات والتوصيات'), {
            'fields': ('coverage_gaps', 'recommendations')
        }),
    )
