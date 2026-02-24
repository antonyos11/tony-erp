from django.contrib import admin
from .models import (
    ContractingProject, ContractingWorker, ContractingAttendance,
    ContractingMaterial, ContractingEquipment, ContractingExpense,
    ContractingReceipt, ContractingContract
)


@admin.register(ContractingProject)
class ContractingProjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'client_name', 'status', 'progress_percentage', 'contract_value', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'code', 'client_name']
    ordering = ['-created_at']


@admin.register(ContractingWorker)
class ContractingWorkerAdmin(admin.ModelAdmin):
    list_display = ['name', 'national_id', 'job_title', 'worker_type', 'daily_wage', 'is_active']
    list_filter = ['worker_type', 'is_active', 'current_project']
    search_fields = ['name', 'national_id', 'job_title']
    ordering = ['name']


@admin.register(ContractingAttendance)
class ContractingAttendanceAdmin(admin.ModelAdmin):
    list_display = ['worker', 'project', 'date', 'status', 'total_wage']
    list_filter = ['status', 'date', 'project']
    search_fields = ['worker__name']
    ordering = ['-date']
    date_hierarchy = 'date'


@admin.register(ContractingMaterial)
class ContractingMaterialAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'unit', 'unit_price', 'current_stock', 'is_active']
    list_filter = ['unit', 'is_active']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(ContractingEquipment)
class ContractingEquipmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'brand', 'status', 'current_project', 'daily_rental_rate']
    list_filter = ['status', 'current_project']
    search_fields = ['name', 'code', 'brand']
    ordering = ['name']


@admin.register(ContractingExpense)
class ContractingExpenseAdmin(admin.ModelAdmin):
    list_display = ['project', 'expense_type', 'description', 'amount', 'date']
    list_filter = ['expense_type', 'project', 'date']
    search_fields = ['description', 'project__name']
    ordering = ['-date']
    date_hierarchy = 'date'


@admin.register(ContractingReceipt)
class ContractingReceiptAdmin(admin.ModelAdmin):
    list_display = ['project', 'receipt_type', 'description', 'amount', 'date', 'payment_method']
    list_filter = ['receipt_type', 'payment_method', 'project', 'date']
    search_fields = ['description', 'project__name']
    ordering = ['-date']
    date_hierarchy = 'date'


@admin.register(ContractingContract)
class ContractingContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'title', 'project', 'contract_value', 'status', 'start_date']
    list_filter = ['status', 'project']
    search_fields = ['contract_number', 'title', 'contractor_name']
    ordering = ['-created_at']
