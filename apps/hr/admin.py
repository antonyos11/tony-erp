"""
لوحة إدارة الموارد البشرية — RITA ERP
"""
from django.contrib import admin
from apps.hr.models import (
    Department, JobTitle, Employee, Attendance,
    LeaveRequest, LeaveBalance, Penalty, SalaryAdvance,
    Payroll, PayrollLine, ProductionPieceWork,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'branch', 'manager', 'parent', 'is_active']
    list_filter = ['branch', 'is_active']
    search_fields = ['name']
    ordering = ['name']


@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'min_salary', 'max_salary', 'is_active']
    list_filter = ['department', 'is_active']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_number', 'full_name_ar', 'branch', 'department',
                    'job_title', 'employment_type', 'hire_date', 'is_active']
    list_filter = ['branch', 'department', 'employment_type', 'is_active', 'gender']
    search_fields = ['employee_number', 'full_name_ar', 'national_id', 'phone']
    ordering = ['employee_number']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    fieldsets = (
        ('البيانات الشخصية', {
            'fields': (
                'user', 'employee_number', 'full_name_ar', 'full_name_en',
                'national_id', 'date_of_birth', 'gender', 'marital_status',
                'phone', 'phone2', 'address', 'governorate',
                'emergency_contact', 'emergency_phone', 'photo',
            )
        }),
        ('البيانات الوظيفية', {
            'fields': (
                'branch', 'department', 'job_title', 'employment_type',
                'hire_date', 'contract_end_date', 'direct_manager',
                'is_active', 'termination_date', 'termination_reason',
            )
        }),
        ('البيانات المالية', {
            'fields': (
                'basic_salary', 'housing_allowance', 'transport_allowance',
                'food_allowance', 'other_allowances',
                'social_insurance_number', 'social_insurance_deduction', 'tax_deduction',
                'bank_name', 'bank_account',
                'daily_rate', 'piece_rate', 'production_line',
            )
        }),
        ('معلومات التدقيق', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'status', 'check_in', 'check_out', 'overtime_hours', 'late_minutes']
    list_filter = ['status', 'date', 'employee__branch']
    search_fields = ['employee__full_name_ar', 'employee__employee_number']
    ordering = ['-date', 'employee']
    date_hierarchy = 'date'


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'days_count', 'status', 'approved_by']
    list_filter = ['leave_type', 'status', 'employee__branch']
    search_fields = ['employee__full_name_ar', 'employee__employee_number']
    ordering = ['-start_date']
    readonly_fields = ['approved_at']


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'year', 'annual_balance', 'used_annual', 'sick_balance', 'used_sick']
    list_filter = ['year']
    search_fields = ['employee__full_name_ar']
    ordering = ['-year', 'employee']


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ['employee', 'penalty_type', 'date', 'amount', 'days', 'approved_by']
    list_filter = ['penalty_type', 'employee__branch']
    search_fields = ['employee__full_name_ar', 'reason']
    ordering = ['-date']


@admin.register(SalaryAdvance)
class SalaryAdvanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'amount', 'monthly_deduction', 'remaining_amount', 'status']
    list_filter = ['status', 'employee__branch']
    search_fields = ['employee__full_name_ar']
    ordering = ['-date']
    readonly_fields = ['created_at', 'updated_at']


class PayrollLineInline(admin.TabularInline):
    model = PayrollLine
    extra = 0
    readonly_fields = ['employee', 'gross_salary', 'total_additions', 'total_deductions', 'net_salary']
    fields = ['employee', 'basic_salary', 'gross_salary', 'total_additions',
              'total_deductions', 'net_salary', 'absence_days']


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['month', 'year', 'branch', 'status', 'total_gross', 'total_net', 'paid_date']
    list_filter = ['status', 'branch', 'year']
    search_fields = ['branch__name']
    ordering = ['-year', '-month']
    readonly_fields = ['total_gross', 'total_deductions', 'total_net', 'total_bonuses', 'total_overtime']
    inlines = [PayrollLineInline]


@admin.register(PayrollLine)
class PayrollLineAdmin(admin.ModelAdmin):
    list_display = ['payroll', 'employee', 'basic_salary', 'gross_salary',
                    'total_deductions', 'net_salary', 'actual_days']
    list_filter = ['payroll__branch', 'payroll__year', 'payroll__month']
    search_fields = ['employee__full_name_ar', 'employee__employee_number']
    ordering = ['payroll', 'employee']


@admin.register(ProductionPieceWork)
class ProductionPieceWorkAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'product', 'quantity', 'rate', 'total', 'is_approved']
    list_filter = ['is_approved', 'employee__branch']
    search_fields = ['employee__full_name_ar', 'product__name']
    ordering = ['-date']
