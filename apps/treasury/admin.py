from django.contrib import admin
from apps.treasury.models import BankAccount, CashBox, Check, MoneyTransfer


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'account_number', 'branch', 'current_balance', 'is_active']
    list_filter = ['is_active', 'branch']
    search_fields = ['name', 'account_number']


@admin.register(CashBox)
class CashBoxAdmin(admin.ModelAdmin):
    list_display = ['name', 'branch', 'current_balance', 'responsible']
    list_filter = ['branch']
    search_fields = ['name']


@admin.register(Check)
class CheckAdmin(admin.ModelAdmin):
    list_display = ['check_number', 'check_type', 'status', 'amount', 'due_date', 'partner_name']
    list_filter = ['check_type', 'status']
    search_fields = ['check_number', 'partner_name']
    date_hierarchy = 'due_date'


@admin.register(MoneyTransfer)
class MoneyTransferAdmin(admin.ModelAdmin):
    list_display = ['date', 'from_account_type', 'to_account_type', 'amount']
    list_filter = ['from_account_type', 'to_account_type']
    date_hierarchy = 'date'
