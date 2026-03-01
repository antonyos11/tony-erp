from django.contrib import admin
from apps.installments.models import InstallmentPlan, Installment


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0
    fields = ['installment_number', 'due_date', 'amount', 'paid_amount', 'paid_date', 'status']
    readonly_fields = ['installment_number']


@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = ['customer', 'invoice', 'total_amount', 'number_of_installments', 'status', 'start_date']
    list_filter = ['status']
    search_fields = ['customer__name', 'invoice__invoice_number']
    inlines = [InstallmentInline]


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ['plan', 'installment_number', 'due_date', 'amount', 'paid_amount', 'status']
    list_filter = ['status']
    date_hierarchy = 'due_date'
