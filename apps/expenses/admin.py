"""
تسجيل نماذج تطبيق المصروفات في لوحة الإدارة
"""
from django.contrib import admin
from apps.expenses.models import (
    ExpenseCategory, Expense, RecurringExpense,
    PaymentVoucher, ReceiptVoucher,
    PettyCash, PettyCashTransaction,
)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'account', 'budget_monthly', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('expense_number', 'date', 'category', 'branch', 'amount', 'tax_amount', 'total', 'status')
    list_filter = ('status', 'category', 'branch', 'payment_method', 'is_taxable')
    search_fields = ('expense_number', 'description')
    date_hierarchy = 'date'
    ordering = ('-date',)
    readonly_fields = ('expense_number', 'journal_entry', 'approved_at')
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('expense_number', 'date', 'category', 'branch', 'department', 'description')
        }),
        ('المبالغ', {
            'fields': ('amount', 'tax_amount', 'total', 'is_taxable', 'payment_method')
        }),
        ('الاعتماد', {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('الربط المحاسبي', {
            'fields': ('journal_entry', 'supplier')
        }),
        ('أخرى', {
            'fields': ('receipt_image', 'notes')
        }),
    )


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'branch', 'amount', 'frequency', 'next_due_date', 'auto_approve', 'is_active')
    list_filter = ('frequency', 'is_active', 'auto_approve', 'branch')
    search_fields = ('name',)
    ordering = ('next_due_date',)


@admin.register(PaymentVoucher)
class PaymentVoucherAdmin(admin.ModelAdmin):
    list_display = ('voucher_number', 'date', 'branch', 'beneficiary_type', 'beneficiary_name', 'amount', 'payment_method', 'status')
    list_filter = ('status', 'beneficiary_type', 'payment_method', 'branch')
    search_fields = ('voucher_number', 'description', 'beneficiary_name')
    date_hierarchy = 'date'
    ordering = ('-date',)
    readonly_fields = ('voucher_number', 'journal_entry')


@admin.register(ReceiptVoucher)
class ReceiptVoucherAdmin(admin.ModelAdmin):
    list_display = ('voucher_number', 'date', 'branch', 'payer_type', 'payer_name', 'amount', 'payment_method', 'status')
    list_filter = ('status', 'payer_type', 'payment_method', 'branch')
    search_fields = ('voucher_number', 'description', 'payer_name')
    date_hierarchy = 'date'
    ordering = ('-date',)
    readonly_fields = ('voucher_number', 'journal_entry')


@admin.register(PettyCash)
class PettyCashAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'custodian', 'limit_amount', 'current_balance', 'account', 'is_active')
    list_filter = ('is_active', 'branch')
    search_fields = ('name',)


class PettyCashTransactionInline(admin.TabularInline):
    model = PettyCashTransaction
    extra = 0
    readonly_fields = ('date', 'transaction_type', 'amount', 'description', 'category', 'journal_entry')
    can_delete = False


@admin.register(PettyCashTransaction)
class PettyCashTransactionAdmin(admin.ModelAdmin):
    list_display = ('petty_cash', 'date', 'transaction_type', 'amount', 'description', 'category')
    list_filter = ('transaction_type', 'petty_cash', 'category')
    search_fields = ('description',)
    date_hierarchy = 'date'
    ordering = ('-date',)
    readonly_fields = ('journal_entry',)
