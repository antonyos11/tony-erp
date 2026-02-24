from django.contrib import admin
from .models import BankStatement, BankStatementLine, Reconciliation, ReconciliationItem

class BankStatementLineInline(admin.TabularInline):
    model = BankStatementLine
    extra = 0
    readonly_fields = ['is_matched', 'matched_at', 'matched_by']

@admin.register(BankStatement)
class BankStatementAdmin(admin.ModelAdmin):
    list_display = ['bank_account', 'statement_date', 'opening_balance', 'closing_balance', 'status']
    list_filter = ['status', 'bank_account', 'statement_date']
    inlines = [BankStatementLineInline]

class ReconciliationItemInline(admin.TabularInline):
    model = ReconciliationItem
    extra = 0

@admin.register(Reconciliation)
class ReconciliationAdmin(admin.ModelAdmin):
    list_display = ['bank_account', 'reconciliation_date', 'book_balance', 'bank_balance', 'difference', 'status']
    list_filter = ['status', 'bank_account']
    inlines = [ReconciliationItemInline]
