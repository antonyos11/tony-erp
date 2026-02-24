from django.contrib import admin
from .models import FiscalYear, Budget, BudgetLine, BudgetAlert, BudgetTransfer

@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'start_date', 'end_date', 'status', 'is_current']
    list_filter = ['status', 'is_current']

class BudgetLineInline(admin.TabularInline):
    model = BudgetLine
    extra = 1

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'fiscal_year', 'budget_type', 'status', 'total_amount']
    list_filter = ['status', 'budget_type', 'fiscal_year']
    search_fields = ['code', 'name']
    inlines = [BudgetLineInline]

@admin.register(BudgetAlert)
class BudgetAlertAdmin(admin.ModelAdmin):
    list_display = ['budget', 'alert_type', 'message', 'is_read', 'created_at']
    list_filter = ['alert_type', 'is_read', 'is_resolved']

@admin.register(BudgetTransfer)
class BudgetTransferAdmin(admin.ModelAdmin):
    list_display = ['from_line', 'to_line', 'amount', 'status', 'requested_by']
    list_filter = ['status']
