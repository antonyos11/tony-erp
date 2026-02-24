from django.contrib import admin
from .models import PaymentMethod, Loan, LoanInstallment, PaymentTransaction, PaymentReminder


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'is_active']
    list_filter = ['type', 'is_active']
    search_fields = ['name']


class LoanInstallmentInline(admin.TabularInline):
    model = LoanInstallment
    extra = 0
    readonly_fields = ['installment_number']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['loan_number', 'borrower', 'principal_amount', 'status', 'start_date']
    list_filter = ['status', 'loan_type', 'start_date']
    search_fields = ['loan_number', 'borrower__name']
    readonly_fields = ['created_at', 'total_amount', 'total_interest']
    inlines = [LoanInstallmentInline]


@admin.register(LoanInstallment)
class LoanInstallmentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'installment_number', 'due_date', 'amount', 'status']
    list_filter = ['status', 'due_date']
    search_fields = ['loan__loan_number']


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_number', 'transaction_type', 'amount', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['transaction_number', 'reference_number']


@admin.register(PaymentReminder)
class PaymentReminderAdmin(admin.ModelAdmin):
    list_display = ['installment', 'reminder_date', 'status', 'delivery_attempts']
    list_filter = ['status', 'reminder_date']