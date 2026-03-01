"""
تسجيل نماذج المحاسبة في لوحة الإدارة
"""
from django.contrib import admin
from .models import FiscalYear, Account, CostCenter, JournalEntry, JournalLine, TaxTransaction


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active', 'is_closed']
    list_filter = ['is_active', 'is_closed']
    search_fields = ['name']
    ordering = ['-start_date']


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'center_type', 'parent', 'is_active']
    list_filter = ['center_type', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['code']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'nature', 'parent', 'is_detail', 'is_active']
    list_filter = ['account_type', 'nature', 'is_active', 'is_detail', 'is_system']
    search_fields = ['code', 'name']
    ordering = ['code']


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 1


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'date', 'description', 'source', 'status', 'total_debit', 'total_credit']
    list_filter = ['source', 'status', 'fiscal_year']
    search_fields = ['entry_number', 'description']
    ordering = ['-date', '-entry_number']
    inlines = [JournalLineInline]


@admin.register(TaxTransaction)
class TaxTransactionAdmin(admin.ModelAdmin):
    list_display = ['tax_type', 'date', 'amount_before_tax', 'tax_rate', 'tax_amount', 'is_taxable_purchase', 'is_taxable_sale']
    list_filter = ['tax_type', 'is_taxable_purchase', 'is_taxable_sale']
    search_fields = ['journal_entry__entry_number']
    ordering = ['-date']

