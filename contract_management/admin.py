"""
إدارة العقود والمستندات
Contract Management Admin Interface
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Contract, ContractMilestone, ContractAmendment, ContractClause


class ContractMilestoneInline(admin.TabularInline):
    model = ContractMilestone
    extra = 1
    fields = ['name', 'due_date', 'status', 'milestone_value']


class ContractClauseInline(admin.TabularInline):
    model = ContractClause
    extra = 1
    fields = ['clause_number', 'title', 'category']


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'contract_type', 'party_a', 'status', 'end_date']
    list_filter = ['status', 'contract_type', 'end_date']
    search_fields = ['contract_number', 'title', 'party_a', 'party_b']
    readonly_fields = ['id', 'document_hash', 'created_at', 'updated_at']
    # inlines = [ContractMilestoneInline, ContractClauseInline]  # Temporarily disabled for migration
    
    fieldsets = (
        (_('معلومات العقد'), {
            'fields': ('contract_number', 'contract_type', 'title')
        }),
        (_('الأطراف'), {
            'fields': ('party_a', 'party_b')
        }),
        (_('البيانات المالية'), {
            'fields': ('contract_value', 'currency')
        }),
        (_('التواريخ'), {
            'fields': ('start_date', 'end_date')
        }),
        (_('المستندات'), {
            'fields': ('document', 'document_hash', 'attachments')
        }),
        (_('التوقيع الرقمي'), {
            'fields': ('is_digitally_signed', 'signature_date', 'signed_by')
        }),
        (_('الموافقة'), {
            'fields': ('status', 'owner', 'approver', 'approval_date')
        }),
        (_('الوصف والشروط'), {
            'fields': ('description', 'terms_and_conditions')
        }),
        (_('معلومات النظام'), {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ContractMilestone)
class ContractMilestoneAdmin(admin.ModelAdmin):
    list_display = ['contract', 'name', 'due_date', 'status', 'milestone_value']
    list_filter = ['status', 'due_date']
    search_fields = ['contract__contract_number', 'name']


@admin.register(ContractAmendment)
class ContractAmendmentAdmin(admin.ModelAdmin):
    list_display = ['contract', 'amendment_number', 'amendment_date', 'is_signed']
    list_filter = ['amendment_date', 'is_signed']
    search_fields = ['contract__contract_number', 'amendment_number']
    readonly_fields = ['id', 'created_at']


@admin.register(ContractClause)
class ContractClauseAdmin(admin.ModelAdmin):
    list_display = ['contract', 'clause_number', 'title', 'category']
    list_filter = ['category']
    search_fields = ['contract__contract_number', 'title', 'clause_number']
    readonly_fields = ['id', 'created_at']
