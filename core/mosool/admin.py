# -*- coding: utf-8 -*-
"""
Admin موصول التحضير والاستماد
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    PreparationRequest, PreparationItem, PreparationApproval,
    ApprovalDocument, ApprovalDocumentItem, DocumentApproval,
    ApprovalWorkflow
)


class PreparationItemInline(admin.TabularInline):
    model = PreparationItem
    extra = 1
    fields = ['description', 'product', 'quantity_requested', 'unit', 'estimated_unit_price', 'is_approved', 'quantity_approved']
    readonly_fields = ['is_approved', 'quantity_approved']


class PreparationApprovalInline(admin.TabularInline):
    model = PreparationApproval
    extra = 0
    readonly_fields = ['approved_by', 'action', 'notes', 'created_at']
    can_delete = False


@admin.register(PreparationRequest)
class PreparationRequestAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'request_type', 'status', 'priority', 'estimated_total', 'requested_by', 'request_date']
    list_filter = ['status', 'request_type', 'priority', 'department']
    search_fields = ['number', 'title', 'description']
    readonly_fields = ['number', 'estimated_total', 'created_at', 'updated_at']
    date_hierarchy = 'request_date'
    inlines = [PreparationItemInline, PreparationApprovalInline]
    
    fieldsets = (
        (_('البيانات الأساسية'), {
            'fields': ('number', 'request_type', 'title', 'description')
        }),
        (_('التفاصيل'), {
            'fields': ('request_date', 'required_date', 'priority', 'status')
        }),
        (_('الجهة'), {
            'fields': ('department', 'cost_center', 'project')
        }),
        (_('المسؤولين'), {
            'fields': ('requested_by', 'assigned_to')
        }),
        (_('المالية'), {
            'fields': ('estimated_total',)
        }),
        (_('ملاحظات'), {
            'fields': ('notes', 'attachments'),
            'classes': ('collapse',)
        }),
        (_('التتبع'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ApprovalDocumentItemInline(admin.TabularInline):
    model = ApprovalDocumentItem
    extra = 1
    fields = ['description', 'product', 'account', 'quantity', 'unit', 'unit_price']


class DocumentApprovalInline(admin.TabularInline):
    model = DocumentApproval
    extra = 0
    readonly_fields = ['approved_by', 'approval_level', 'action', 'amount_approved', 'notes', 'created_at']
    can_delete = False


@admin.register(ApprovalDocument)
class ApprovalDocumentAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'document_type', 'status_badge', 'total_amount', 'approved_amount', 'approval_progress', 'created_by', 'document_date']
    list_filter = ['status', 'document_type', 'department', 'current_approval_level']
    search_fields = ['number', 'title', 'description']
    readonly_fields = ['number', 'total_amount', 'approved_amount', 'current_approval_level', 'required_approval_level', 'submitted_at', 'approved_at', 'created_at', 'updated_at']
    date_hierarchy = 'document_date'
    inlines = [ApprovalDocumentItemInline, DocumentApprovalInline]
    
    fieldsets = (
        (_('البيانات الأساسية'), {
            'fields': ('number', 'document_type', 'title', 'description', 'preparation_request')
        }),
        (_('التواريخ'), {
            'fields': ('document_date', 'due_date')
        }),
        (_('المالية'), {
            'fields': ('total_amount', 'approved_amount', 'currency')
        }),
        (_('الاعتماد'), {
            'fields': ('status', 'current_approval_level', 'required_approval_level')
        }),
        (_('الجهة'), {
            'fields': ('department', 'cost_center', 'budget_item')
        }),
        (_('الأطراف'), {
            'fields': ('created_by', 'supplier', 'employee')
        }),
        (_('ملاحظات'), {
            'fields': ('notes', 'attachments'),
            'classes': ('collapse',)
        }),
        (_('التتبع'), {
            'fields': ('submitted_at', 'approved_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'pending': 'warning',
            'partial': 'info',
            'approved': 'success',
            'rejected': 'danger',
            'cancelled': 'dark',
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = _('الحالة')
    
    def approval_progress(self, obj):
        return format_html(
            '<span class="badge bg-info">{}/{}</span>',
            obj.current_approval_level,
            obj.required_approval_level
        )
    approval_progress.short_description = _('مستوى الاعتماد')


@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):
    list_display = ['document_type', 'approval_level', 'approver', 'approver_role', 'department', 'min_amount', 'max_amount', 'is_active']
    list_filter = ['document_type', 'approval_level', 'is_active']
    search_fields = ['approver__username', 'approver_role__name']
    ordering = ['document_type', 'approval_level', 'min_amount']


# تسجيل باقي الموديلات للمراجعة
@admin.register(PreparationItem)
class PreparationItemAdmin(admin.ModelAdmin):
    list_display = ['preparation', 'description', 'quantity_requested', 'estimated_unit_price', 'is_approved']
    list_filter = ['is_approved', 'preparation__status']


@admin.register(ApprovalDocumentItem)
class ApprovalDocumentItemAdmin(admin.ModelAdmin):
    list_display = ['document', 'description', 'quantity', 'unit_price']
    list_filter = ['document__status']
