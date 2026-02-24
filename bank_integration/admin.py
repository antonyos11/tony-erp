"""
إدارة التكامل البنكي
Bank Integration Admin
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse
from .models import BankAccount, BankTransaction, BankReconciliation, BankTransactionMapping, BankFee
from .services import bank_sync_service, reconciliation_service, bank_analytics_service


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['bank_name', 'account_number', 'account_type', 'current_balance', 'status', 'last_sync']
    list_filter = ['status', 'account_type', 'currency', 'created_at']
    search_fields = ['bank_name', 'account_number', 'account_holder', 'iban']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_sync']
    
    fieldsets = (
        (_('معلومات البنك'), {
            'fields': ('bank_name', 'account_number', 'account_holder', 'account_type', 'currency')
        }),
        (_('تفاصيل الحساب'), {
            'fields': ('iban', 'swift_code', 'bank_code', 'branch_code')
        }),
        (_('الرصيد والحالة'), {
            'fields': ('current_balance', 'status')
        }),
        (_('بيانات API'), {
            'fields': ('api_key', 'api_secret', 'webhook_url'),
            'classes': ('collapse',)
        }),
        (_('إعدادات المزامنة'), {
            'fields': ('sync_enabled', 'auto_reconcile', 'last_sync')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
        (_('معلومات النظام'), {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['sync_transactions', 'reconcile_transactions']
    
    def sync_transactions(self, request, queryset):
        """مزامنة العمليات"""
        for account in queryset:
            result = bank_sync_service.sync_account_transactions(account)
            if result['success']:
                self.message_user(request, f"تم مزامنة {result['created']} عملية جديدة")
    sync_transactions.short_description = _('مزامنة العمليات')
    
    def reconcile_transactions(self, request, queryset):
        """مطابقة العمليات"""
        for account in queryset:
            result = reconciliation_service.auto_reconcile(account)
            if result['success']:
                self.message_user(request, f"تم مطابقة {result['matched']} عملية")
    reconcile_transactions.short_description = _('مطابقة العمليات')


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'account', 'transaction_date', 'amount', 'transaction_type', 'status']
    list_filter = ['status', 'transaction_type', 'transaction_date', 'account']
    search_fields = ['reference_number', 'description', 'counterparty_name', 'bank_reference']
    readonly_fields = ['id', 'created_at', 'matching_score']
    
    fieldsets = (
        (_('معلومات العملية'), {
            'fields': ('reference_number', 'bank_reference', 'account', 'transaction_type')
        }),
        (_('التواريخ والمبلغ'), {
            'fields': ('transaction_date', 'value_date', 'amount')
        }),
        (_('التفاصيل'), {
            'fields': ('description', 'counterparty_name', 'counterparty_account')
        }),
        (_('المطابقة'), {
            'fields': ('status', 'matched_invoice', 'matched_payment', 'matching_score')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
        (_('معلومات النظام'), {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['reference_number', 'account']
        return self.readonly_fields


@admin.register(BankReconciliation)
class BankReconciliationAdmin(admin.ModelAdmin):
    list_display = ['account', 'statement_date', 'statement_balance', 'system_balance', 'difference', 'status']
    list_filter = ['status', 'account', 'statement_date']
    readonly_fields = ['id', 'difference', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('معلومات كشف الحساب'), {
            'fields': ('account', 'statement_date')
        }),
        (_('الأرصدة'), {
            'fields': ('statement_balance', 'system_balance', 'difference')
        }),
        (_('العمليات'), {
            'fields': ('reconciled_transactions', 'unreconciled_transactions')
        }),
        (_('المطابقة'), {
            'fields': ('status', 'reconciled_by', 'reconciled_at')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
        (_('معلومات النظام'), {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    filter_horizontal = ['reconciled_transactions', 'unreconciled_transactions']


@admin.register(BankTransactionMapping)
class BankTransactionMappingAdmin(admin.ModelAdmin):
    list_display = ['bank_transaction', 'journal_entry', 'matching_confidence', 'auto_matched', 'created_at']
    list_filter = ['auto_matched', 'matching_confidence', 'created_at']
    readonly_fields = ['id', 'created_at']
    search_fields = ['bank_transaction__reference_number', 'journal_entry__id']


@admin.register(BankFee)
class BankFeeAdmin(admin.ModelAdmin):
    list_display = ['account', 'fee_type', 'amount', 'fee_date', 'frequency']
    list_filter = ['frequency', 'fee_date', 'account']
    search_fields = ['fee_type', 'description']
    readonly_fields = ['id', 'created_at']
