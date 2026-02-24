from django.contrib import admin
from .models import (
    Account, JournalEntry, JournalEntryItem, FiscalYear,
    CostCenter, CostCenterBudget, JournalEntryTemplate, JournalEntryTemplateItem,
    Revenue, Expense, Bank, Loan, LoanPayment, AccountingSettings, Cheque, AccountEntry,
    ElectronicAccount, Treasury, FawryMachine, VisaMachine, AccountTransfer,
    # الميزات الجديدة
    BankReconciliation, RecurringJournalEntry, BudgetItem, Asset, DepreciationEntry,
    AccountingAuditLog, AccountingApprovalWorkflow, PeriodClose, CustomReport, ReceivableAging
)
from .models import CashFlowAccountMapping


class JournalEntryItemInline(admin.TabularInline):
    model = JournalEntryItem
    extra = 2


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'parent', 'is_active', 'can_post')
    list_filter = ('account_type', 'is_active', 'can_post', 'requires_cost_center')
    search_fields = ('code', 'name', 'description')
    list_editable = ('is_active', 'can_post')
    ordering = ('code',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('code', 'name', 'account_type', 'parent', 'description')
        }),
        ('الإعدادات', {
            'fields': ('is_active', 'can_post', 'requires_cost_center', 'default_cost_center', 'credit_limit')
        }),
    )


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('number', 'date', 'entry_type', 'description', 'total_debit', 'is_posted', 'created_by')
    list_filter = ('entry_type', 'is_posted', 'date', 'created_by')
    search_fields = ('number', 'description', 'reference')
    date_hierarchy = 'date'
    readonly_fields = ('number', 'created_at', 'updated_at')
    inlines = [JournalEntryItemInline]
    
    fieldsets = (
        ('معلومات القيد', {
            'fields': ('number', 'date', 'entry_type', 'description', 'reference')
        }),
        ('الربط', {
            'fields': ('invoice', 'purchase_bill')
        }),
        ('الحالة', {
            'fields': ('is_posted', 'created_by', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(JournalEntryItem)
class JournalEntryItemAdmin(admin.ModelAdmin):
    list_display = ('journal_entry', 'account', 'type', 'amount', 'cost_center', 'description')
    list_filter = ('type', 'journal_entry__entry_type', 'cost_center')
    search_fields = ('journal_entry__number', 'account__code', 'account__name', 'description')


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'parent', 'manager', 'is_active', 'total_expenses')
    list_filter = ('is_active', 'parent', 'manager')
    search_fields = ('code', 'name', 'description')
    list_editable = ('is_active',)
    ordering = ('code',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('code', 'name', 'parent', 'description')
        }),
        ('الإدارة', {
            'fields': ('manager', 'is_active')
        }),
    )


class JournalEntryTemplateItemInline(admin.TabularInline):
    model = JournalEntryTemplateItem
    extra = 2


@admin.register(JournalEntryTemplate)
class JournalEntryTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'is_active', 'auto_apply', 'created_by')
    list_filter = ('template_type', 'is_active', 'auto_apply')
    search_fields = ('name', 'description')
    inlines = [JournalEntryTemplateItemInline]
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(JournalEntryTemplateItem)
class JournalEntryTemplateItemAdmin(admin.ModelAdmin):
    list_display = ('template', 'account', 'type', 'amount_type', 'fixed_amount', 'percentage', 'sequence')
    list_filter = ('type', 'amount_type', 'template__template_type')
    search_fields = ('template__name', 'account__code', 'account__name')


@admin.register(CostCenterBudget)
class CostCenterBudgetAdmin(admin.ModelAdmin):
    list_display = ('cost_center', 'fiscal_year', 'total_budget', 'actual_expenses', 'remaining_budget', 'budget_utilization_percentage')
    list_filter = ('fiscal_year', 'cost_center')
    search_fields = ('cost_center__name', 'fiscal_year__name')


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active', 'is_closed')
    list_filter = ('is_active', 'is_closed')
    search_fields = ('name',)
    date_hierarchy = 'start_date'


# النماذج القديمة للتوافق
@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ("date", "description", "amount", "supplier", "journal_entry")
    search_fields = ("description",)
    list_filter = ("date", "supplier")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "description", "amount", "journal_entry")
    search_fields = ("description",)
    list_filter = ("date",)


# === قيود الحسابات (إيراد ومنصرف) ===
@admin.register(AccountEntry)
class AccountEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'entry_type', 'date', 'amount', 'supplier', 'ledger_account', 'created_by')
    list_filter = ('entry_type', 'date', 'supplier', 'ledger_account')
    search_fields = ('description',)
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('entry_type', 'date', 'amount', 'description')
        }),
        ('التصنيفات', {
            'fields': ('ledger_account', 'financial_analysis_1', 'financial_analysis_2', 'cost_center', 'supplier')
        }),
        ('معلومات النظام', {
            'fields': ('journal_entry', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# === إدارة القروض البنكية ===

@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'account_number', 'current_balance', 'contact_person', 'phone', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'account_number', 'contact_person')
    list_editable = ('is_active',)


@admin.register(ElectronicAccount)
class ElectronicAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'account_type', 'phone_number', 'current_balance', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('name', 'code', 'phone_number', 'account_id', 'email')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'code', 'account_type')
        }),
        ('معلومات الاتصال', {
            'fields': ('phone_number', 'email', 'account_id')
        }),
        ('المعلومات المالية', {
            'fields': ('current_balance', 'linked_account')
        }),
        ('إعدادات', {
            'fields': ('is_active', 'notes')
        }),
    )


@admin.register(Treasury)
class TreasuryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'location', 'responsible_person', 'current_balance', 'showroom', 'is_active')
    list_filter = ('is_active', 'showroom')
    search_fields = ('name', 'code', 'location')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'code', 'location')
        }),
        ('الإدارة', {
            'fields': ('responsible_person', 'showroom')
        }),
        ('المعلومات المالية', {
            'fields': ('current_balance', 'linked_account')
        }),
        ('إعدادات', {
            'fields': ('is_active', 'notes')
        }),
    )


@admin.register(FawryMachine)
class FawryMachineAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'machine_id', 'phone_number', 'current_balance', 'showroom', 'is_active')
    list_filter = ('is_active', 'showroom')
    search_fields = ('name', 'code', 'machine_id', 'phone_number')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'code', 'machine_id')
        }),
        ('معلومات الاتصال', {
            'fields': ('phone_number', 'location')
        }),
        ('الإدارة', {
            'fields': ('responsible_person', 'showroom')
        }),
        ('المعلومات المالية', {
            'fields': ('current_balance', 'commission_rate', 'linked_account')
        }),
        ('إعدادات', {
            'fields': ('is_active', 'notes')
        }),
    )


@admin.register(VisaMachine)
class VisaMachineAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'terminal_id', 'machine_type', 'bank', 'current_balance', 'showroom', 'is_active')
    list_filter = ('is_active', 'machine_type', 'bank', 'showroom')
    search_fields = ('name', 'code', 'terminal_id', 'merchant_id')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'code', 'terminal_id', 'merchant_id', 'machine_type')
        }),
        ('الربط البنكي', {
            'fields': ('bank', 'commission_rate')
        }),
        ('الموقع والإدارة', {
            'fields': ('location', 'responsible_person', 'showroom')
        }),
        ('المعلومات المالية', {
            'fields': ('current_balance', 'linked_account')
        }),
        ('إعدادات', {
            'fields': ('is_active', 'notes')
        }),
    )


@admin.register(Loan)  
class LoanAdmin(admin.ModelAdmin):
    list_display = ('loan_number', 'bank', 'principal_amount', 'interest_rate', 'status', 'disbursement_date')
    list_filter = ('status', 'bank', 'disbursement_date')
    search_fields = ('loan_number',)
    
@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ('loan', 'payment_date', 'amount', 'principal_portion', 'interest_portion')
    list_filter = ('payment_date', 'loan__bank')


@admin.register(AccountingSettings)
class AccountingSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('الضرائب', {
            'fields': ('enable_vat', 'default_vat_rate', 'vat_input_account', 'vat_output_account')
        }),
        ('الحسابات الافتراضية', {
            'fields': ('inventory_account', 'ap_account', 'cash_account')
        }),
    )
    list_display = ('enable_vat', 'default_vat_rate', 'inventory_account', 'ap_account', 'cash_account')


@admin.register(Cheque)
class ChequeAdmin(admin.ModelAdmin):
    list_display = ('number', 'cheque_type', 'status', 'partner', 'amount', 'bank_name', 'due_date', 'created_at')
    list_filter = ('cheque_type', 'status', 'bank_name')
    search_fields = ('number', 'partner__name', 'bank_name', 'notes')
    date_hierarchy = 'due_date'
    readonly_fields = ('created_at',)


@admin.register(CashFlowAccountMapping)
class CashFlowAccountMappingAdmin(admin.ModelAdmin):
    list_display = ('account','category','note','updated_at')
    list_filter = ('category',)
    search_fields = ('account__code','account__name','note')


@admin.register(AccountTransfer)
class AccountTransferAdmin(admin.ModelAdmin):
    list_display = ('transfer_number', 'date', 'from_type', 'to_type', 'amount', 'fees', 'status', 'created_by')
    list_filter = ('status', 'from_type', 'to_type', 'date')
    search_fields = ('transfer_number', 'reference_number', 'description')
    date_hierarchy = 'date'
    readonly_fields = ('transfer_number', 'created_at', 'updated_at')
    
    fieldsets = (
        ('معلومات التحويل', {
            'fields': ('transfer_number', 'date', 'amount', 'fees', 'status')
        }),
        ('المصدر (من)', {
            'fields': ('from_type', 'from_treasury', 'from_bank', 'from_electronic', 'from_fawry', 'from_visa')
        }),
        ('الوجهة (إلى)', {
            'fields': ('to_type', 'to_treasury', 'to_bank', 'to_electronic', 'to_fawry', 'to_visa')
        }),
        ('معلومات إضافية', {
            'fields': ('reference_number', 'description', 'created_by', 'created_at', 'updated_at')
        }),
    )


# ==================== الميزات الجديدة المتقدمة ====================

@admin.register(BankReconciliation)
class BankReconciliationAdmin(admin.ModelAdmin):
    list_display = ('bank', 'period_start', 'period_end', 'status', 'auto_matched_count', 
                   'manual_matched_count', 'difference_amount', 'created_by')
    list_filter = ('status', 'bank', 'period_start')
    search_fields = ('bank__name', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'auto_matched_count', 'manual_matched_count')
    date_hierarchy = 'period_end'
    
    fieldsets = (
        ('معلومات التسوية', {
            'fields': ('bank', 'bank_statement', 'period_start', 'period_end', 'status')
        }),
        ('الأرصدة', {
            'fields': ('opening_balance', 'closing_balance', 'difference_amount')
        }),
        ('المطابقة', {
            'fields': ('auto_matched_count', 'manual_matched_count', 'unmatched_items', 'matched_items')
        }),
        ('الاعتماد', {
            'fields': ('created_by', 'approved_by', 'notes')
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RecurringJournalEntry)
class RecurringJournalEntryAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'frequency', 'next_execution', 'is_active', 
                   'auto_post', 'execution_count')
    list_filter = ('frequency', 'is_active', 'auto_post')
    search_fields = ('name', 'template__name')
    readonly_fields = ('execution_count', 'last_execution', 'created_at', 'updated_at')
    
    fieldsets = (
        ('معلومات القيد المتكرر', {
            'fields': ('name', 'template', 'frequency')
        }),
        ('الجدولة', {
            'fields': ('start_date', 'end_date', 'next_execution', 'last_execution')
        }),
        ('الإعدادات', {
            'fields': ('is_active', 'auto_post', 'notify_before_days')
        }),
        ('الإحصائيات', {
            'fields': ('execution_count', 'created_by')
        }),
    )


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ('account', 'cost_center', 'fiscal_year', 'month', 
                   'budgeted_amount', 'actual_amount', 'variance_amount', 
                   'variance_percentage', 'is_locked')
    list_filter = ('fiscal_year', 'month', 'is_locked', 'account__account_type')
    search_fields = ('account__name', 'cost_center__name', 'notes')
    readonly_fields = ('variance_amount', 'variance_percentage', 'created_at', 'updated_at')
    list_editable = ('is_locked',)
    
    fieldsets = (
        ('التصنيف', {
            'fields': ('account', 'cost_center', 'fiscal_year', 'month')
        }),
        ('المبالغ', {
            'fields': ('budgeted_amount', 'actual_amount', 'variance_amount', 'variance_percentage')
        }),
        ('الملاحظات', {
            'fields': ('is_locked', 'notes')
        }),
    )


class DepreciationEntryInline(admin.TabularInline):
    model = DepreciationEntry
    extra = 0
    readonly_fields = ('depreciation_date', 'depreciation_amount', 
                      'accumulated_depreciation_before', 'accumulated_depreciation_after')


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account', 'purchase_date', 'purchase_cost', 
                   'accumulated_depreciation', 'book_value', 'status')
    list_filter = ('status', 'depreciation_method', 'purchase_date')
    search_fields = ('code', 'name', 'serial_number', 'supplier')
    readonly_fields = ('book_value', 'created_at', 'updated_at')
    inlines = [DepreciationEntryInline]
    
    fieldsets = (
        ('معلومات الأصل', {
            'fields': ('name', 'code', 'account', 'cost_center')
        }),
        ('حسابات الإهلاك', {
            'fields': ('accumulated_depreciation_account', 'depreciation_expense_account')
        }),
        ('تفاصيل الشراء', {
            'fields': ('purchase_date', 'purchase_cost', 'salvage_value', 'supplier')
        }),
        ('الإهلاك', {
            'fields': ('depreciation_method', 'depreciation_rate', 'useful_life_years', 
                      'useful_life_months', 'accumulated_depreciation', 'book_value', 
                      'last_depreciation_date')
        }),
        ('معلومات إضافية', {
            'fields': ('status', 'location', 'serial_number', 'warranty_expiry', 'notes')
        }),
    )


@admin.register(DepreciationEntry)
class DepreciationEntryAdmin(admin.ModelAdmin):
    list_display = ('asset', 'depreciation_date', 'depreciation_amount', 
                   'accumulated_depreciation_after', 'journal_entry')
    list_filter = ('depreciation_date', 'asset__depreciation_method')
    search_fields = ('asset__name', 'asset__code', 'notes')
    readonly_fields = ('created_at',)
    date_hierarchy = 'depreciation_date'


@admin.register(AccountingAuditLog)
class AccountingAuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'content_type', 'object_repr', 
                   'timestamp', 'ip_address')
    list_filter = ('action_type', 'content_type', 'timestamp')
    search_fields = ('user__username', 'object_repr', 'ip_address')
    readonly_fields = ('user', 'action_type', 'content_type', 'object_id', 
                      'object_repr', 'changes', 'ip_address', 'user_agent', 'timestamp')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AccountingApprovalWorkflow)
class AccountingApprovalWorkflowAdmin(admin.ModelAdmin):
    list_display = ('requested_by', 'current_approver', 'status', 'approval_level',
                   'total_levels', 'request_date', 'approved_date')
    list_filter = ('status', 'approval_level', 'request_date')
    search_fields = ('requested_by__username', 'current_approver__username', 'notes')
    readonly_fields = ('request_date', 'approved_date')
    
    fieldsets = (
        ('معلومات الموافقة', {
            'fields': ('content_type', 'object_id', 'requested_by', 'current_approver')
        }),
        ('الحالة', {
            'fields': ('status', 'approval_level', 'total_levels')
        }),
        ('التواريخ', {
            'fields': ('request_date', 'approved_date', 'notes')
        }),
    )


@admin.register(PeriodClose)
class PeriodCloseAdmin(admin.ModelAdmin):
    list_display = ('fiscal_year', 'period_type', 'period_number', 'period_start', 
                   'period_end', 'status', 'checklist_completed', 'closed_by')
    list_filter = ('status', 'period_type', 'fiscal_year', 'checklist_completed')
    search_fields = ('notes', 'reopen_reason')
    readonly_fields = ('created_at', 'closed_at', 'reopened_at')
    
    fieldsets = (
        ('الفترة', {
            'fields': ('fiscal_year', 'period_type', 'period_number', 'period_start', 'period_end')
        }),
        ('الحالة', {
            'fields': ('status', 'checklist_completed', 'closing_entries_created')
        }),
        ('الإقفال', {
            'fields': ('closed_by', 'closed_at', 'notes')
        }),
        ('إعادة الفتح', {
            'fields': ('reopened_by', 'reopened_at', 'reopen_reason'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CustomReport)
class CustomReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'created_by', 'is_public', 
                   'schedule_enabled', 'execution_count', 'last_execution')
    list_filter = ('is_public', 'schedule_enabled', 'report_type')
    search_fields = ('name', 'description')
    readonly_fields = ('execution_count', 'last_execution', 'created_at', 'updated_at')
    
    fieldsets = (
        ('معلومات التقرير', {
            'fields': ('name', 'description', 'report_type', 'created_by', 'is_public')
        }),
        ('التكوين', {
            'fields': ('filters', 'columns', 'grouping', 'sorting')
        }),
        ('الجدولة', {
            'fields': ('schedule_enabled', 'schedule_frequency', 'schedule_recipients')
        }),
        ('الإحصائيات', {
            'fields': ('execution_count', 'last_execution')
        }),
    )


@admin.register(ReceivableAging)
class ReceivableAgingAdmin(admin.ModelAdmin):
    list_display = ('partner', 'invoice_number', 'invoice_date', 'due_date', 
                   'total_amount', 'balance', 'days_overdue', 'aging_bucket')
    list_filter = ('aging_bucket', 'snapshot_date', 'invoice_date')
    search_fields = ('partner__name', 'invoice_number')
    readonly_fields = ('snapshot_date', 'days_overdue')
    date_hierarchy = 'due_date'
    
    def has_add_permission(self, request):
        return False


# Import advanced admin registrations
try:
    from . import admin_advanced  # noqa: F401
except ImportError:
    pass