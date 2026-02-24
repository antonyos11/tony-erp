from django.contrib import admin
from django.utils.html import format_html
from .models import (
    HRSettings, Department, JobPosition, Employee, AttendanceRecord,
    WorkSchedule, EmployeeSchedule, LeaveType, LeaveRequest, Payroll,
    PerformanceReview, TrainingProgram, TrainingEnrollment,
    JobVacancy, JobApplication, WeekendDay, PublicHoliday,
    Complaint, DisciplinaryAction, HSEIncident, HSEInspection, HSETraining,
    AbsencePolicy, EmployeeAbsence, EmployeeIDCard,
    EmployeeLoan, LoanInstallment
)

@admin.register(HRSettings)
class HRSettingsAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'working_hours_per_day', 'working_days_per_week', 'overtime_rate']
    fieldsets = (
        ('إعدادات عامة', {
            'fields': ('company_name', 'working_hours_per_day', 'working_days_per_week', 'overtime_rate', 'late_penalty_per_minute')
        }),
        ('الحسابات المحاسبية', {
            'fields': ('salary_expense_account', 'salary_payable_account', 'overtime_expense_account', 'bonus_expense_account')
        }),
    )

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'head', 'budget', 'cost_center', 'is_active']
    search_fields = ['name', 'code']
    list_filter = ['cost_center', 'is_active']

@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'department', 'min_salary', 'max_salary', 'is_active']
    list_filter = ['department', 'is_active']
    search_fields = ['title', 'code']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'arabic_name', 'department', 'position', 'status', 'hire_date', 'total_salary_display']
    list_filter = ['department', 'position', 'status', 'gender', 'marital_status']
    search_fields = ['employee_id', 'arabic_name', 'first_name', 'last_name', 'national_id']
    readonly_fields = ['years_of_service_display', 'total_salary_display']
    
    fieldsets = (
        ('البيانات الأساسية', {
            'fields': ('employee_id', 'user')
        }),
        ('البيانات الشخصية', {
            'fields': ('first_name', 'last_name', 'arabic_name', 'national_id', 'passport_number', 
                      'gender', 'birth_date', 'marital_status')
        }),
        ('معلومات الاتصال', {
            'fields': ('phone', 'email', 'address', 'emergency_contact_name', 'emergency_contact_phone')
        }),
        ('معلومات العمل', {
            'fields': ('department', 'position', 'hire_date', 'termination_date', 'status')
        }),
        ('معلومات الراتب', {
            'fields': ('basic_salary', 'housing_allowance', 'transportation_allowance', 'other_allowances', 'total_salary_display')
        }),
        ('إعدادات الحضور', {
            'fields': ('fingerprint_id', 'rfid_card_number')
        }),
        ('معلومات البنك', {
            'fields': ('bank_name', 'bank_account_number', 'iban')
        }),
        ('الملفات', {
            'fields': ('photo', 'cv_file', 'contract_file')
        }),
        ('معلومات إضافية', {
            'fields': ('years_of_service_display',)
        }),
    )
    
    def total_salary_display(self, obj):
        from django.conf import settings
        symbol = getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', '')
        return f"{obj.total_salary:,.2f} {symbol}"
    total_salary_display.short_description = "إجمالي الراتب"
    
    def years_of_service_display(self, obj):
        return f"{obj.years_of_service:.1f} سنة"
    years_of_service_display.short_description = "سنوات الخدمة"

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'time', 'record_type', 'source']
    list_filter = ['record_type', 'source', 'date']
    search_fields = ['employee__arabic_name', 'employee__employee_id']
    date_hierarchy = 'date'

@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_default', 'grace_period_minutes', 'break_duration_minutes']
    list_filter = ['is_default']

@admin.register(EmployeeSchedule)
class EmployeeScheduleAdmin(admin.ModelAdmin):
    list_display = ['employee', 'schedule', 'start_date', 'end_date', 'is_active']
    list_filter = ['schedule', 'is_active']
    search_fields = ['employee__arabic_name']

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'days_per_year', 'is_paid', 'carry_forward', 'requires_approval']
    list_filter = ['is_paid', 'carry_forward', 'requires_approval']

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'days_requested', 'status', 'status_badge']
    list_filter = ['status', 'leave_type', 'start_date']
    search_fields = ['employee__arabic_name', 'employee__employee_id']
    readonly_fields = ['days_requested']
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'cancelled': 'gray',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = "حالة الطلب"


@admin.register(WeekendDay)
class WeekendDayAdmin(admin.ModelAdmin):
    list_display = ['day_of_week', 'is_active']
    list_filter = ['is_active']


@admin.register(PublicHoliday)
class PublicHolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'is_recurring']
    list_filter = ['is_recurring', 'date']
    search_fields = ['name']

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['employee', 'period_start', 'period_end', 'gross_salary', 'net_salary', 'status', 'status_badge']
    list_filter = ['status', 'period_start']
    search_fields = ['employee__arabic_name', 'employee__employee_id']
    readonly_fields = ['gross_salary', 'total_deductions', 'net_salary']
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('employee', 'period_start', 'period_end', 'status')
        }),
        ('الراتب والبدلات', {
            'fields': ('basic_salary', 'housing_allowance', 'transportation_allowance', 'other_allowances')
        }),
        ('الساعات الإضافية والمكافآت', {
            'fields': ('overtime_hours', 'overtime_amount', 'bonus_amount')
        }),
        ('الخصومات', {
            'fields': ('late_penalty', 'absence_deduction', 'other_deductions')
        }),
        ('المجاميع', {
            'fields': ('gross_salary', 'total_deductions', 'net_salary')
        }),
        ('معلومات الاعتماد', {
            'fields': ('approved_by', 'approved_at')
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'calculated': 'blue',
            'approved': 'green',
            'paid': 'darkgreen',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = "الحالة"

@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ['employee', 'reviewer', 'review_period_start', 'review_period_end', 'overall_rating', 'status']
    list_filter = ['status', 'overall_rating', 'review_period_start']
    search_fields = ['employee__arabic_name', 'reviewer__arabic_name']
    readonly_fields = ['overall_rating']

@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
    list_display = ['title', 'provider', 'start_date', 'end_date', 'duration_hours', 'cost', 'max_participants']
    list_filter = ['provider', 'start_date']
    search_fields = ['title', 'provider']

@admin.register(TrainingEnrollment)
class TrainingEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'training_program', 'enrollment_date', 'status', 'completion_date', 'score']
    list_filter = ['status', 'training_program', 'enrollment_date']
    search_fields = ['employee__arabic_name', 'training_program__title']

@admin.register(JobVacancy)
class JobVacancyAdmin(admin.ModelAdmin):
    list_display = ['title', 'position', 'number_of_positions', 'posting_date', 'closing_date', 'status']
    list_filter = ['status', 'position__department', 'posting_date']
    search_fields = ['title', 'position__title']

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'vacancy', 'application_date', 'status', 'interview_date']
    list_filter = ['status', 'vacancy', 'application_date']
    search_fields = ['first_name', 'last_name', 'email']
    readonly_fields = ['application_date']
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "الاسم الكامل"


# === العلاقات العمالية و HSE ===
@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['employee', 'subject', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['employee__arabic_name', 'subject']

@admin.register(DisciplinaryAction)
class DisciplinaryActionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'action_type', 'date']
    list_filter = ['action_type', 'date']
    search_fields = ['employee__arabic_name']

@admin.register(HSEIncident)
class HSEIncidentAdmin(admin.ModelAdmin):
    list_display = ['date', 'employee', 'department', 'status']
    list_filter = ['status', 'department', 'date']
    search_fields = ['employee__arabic_name', 'department__name']

@admin.register(HSEInspection)
class HSEInspectionAdmin(admin.ModelAdmin):
    list_display = ['date', 'location']
    list_filter = ['date']
    search_fields = ['location']

@admin.register(HSETraining)
class HSETrainingAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'status']
    list_filter = ['status', 'date']
    search_fields = ['title']

# === إدارة نظام الأهداف والتارجت المتطور ===

from .models import (
    TargetCategory, PerformanceTarget, TargetProgress, TeamTarget, 
    TeamTargetMembership, PerformanceMetric, EmployeeMetricValue
)

@admin.register(TargetCategory)
class TargetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'is_active']
    list_filter = ['category_type', 'is_active']
    search_fields = ['name']


@admin.register(PerformanceTarget)
class PerformanceTargetAdmin(admin.ModelAdmin):
    list_display = ['employee', 'title', 'category', 'target_period', 'achievement_percentage_display', 
                    'status', 'start_date', 'end_date', 'priority_badge']
    list_filter = ['status', 'category', 'target_period', 'priority', 'start_date']
    search_fields = ['title', 'employee__arabic_name', 'category__name']
    readonly_fields = ['achievement_percentage_display', 'remaining_days_display', 'performance_level_display']
    
    fieldsets = (
        ('معلومات الهدف', {
            'fields': ('employee', 'category', 'title', 'description')
        }),
        ('تفاصيل الهدف', {
            'fields': ('target_period', 'target_type', 'target_value', 'current_value', 'unit')
        }),
        ('التواريخ', {
            'fields': ('start_date', 'end_date', 'remaining_days_display')
        }),
        ('الأهمية والأوزان', {
            'fields': ('weight', 'priority')
        }),
        ('المعايير والمكافآت', {
            'fields': ('min_acceptable', 'excellence_threshold', 'reward_amount')
        }),
        ('الحالة والمتابعة', {
            'fields': ('status', 'assigned_by')
        }),
        ('الحساب التلقائي', {
            'fields': ('auto_calculate', 'calculation_query')
        }),
        ('معلومات الأداء', {
            'fields': ('achievement_percentage_display', 'performance_level_display')
        }),
    )
    
    def achievement_percentage_display(self, obj):
        percentage = obj.achievement_percentage
        color = 'green' if percentage >= 100 else 'orange' if percentage >= 80 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, percentage
        )
    achievement_percentage_display.short_description = "نسبة الإنجاز"
    
    def remaining_days_display(self, obj):
        days = obj.remaining_days
        color = 'red' if days <= 3 else 'orange' if days <= 7 else 'green'
        return format_html(
            '<span style="color: {};">{} يوم</span>',
            color, days
        )
    remaining_days_display.short_description = "الأيام المتبقية"
    
    def performance_level_display(self, obj):
        level = obj.performance_level
        colors = {
            'excellence': 'darkgreen',
            'achieved': 'green', 
            'acceptable': 'orange',
            'below_target': 'red'
        }
        labels = {
            'excellence': 'متميز',
            'achieved': 'محقق', 
            'acceptable': 'مقبول',
            'below_target': 'دون المستوى'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(level, 'gray'),
            labels.get(level, level)
        )
    performance_level_display.short_description = "مستوى الأداء"
    
    def priority_badge(self, obj):
        colors = {
            'low': 'gray',
            'medium': 'blue',
            'high': 'orange', 
            'critical': 'red'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.priority, 'gray'),
            obj.get_priority_display()
        )
    priority_badge.short_description = "الأولوية"


@admin.register(TargetProgress)
class TargetProgressAdmin(admin.ModelAdmin):
    list_display = ['target', 'previous_value', 'new_value', 'change_amount', 'updated_by', 'timestamp']
    list_filter = ['timestamp', 'target__category']
    search_fields = ['target__title', 'target__employee__arabic_name']
    readonly_fields = ['change_amount']
    date_hierarchy = 'timestamp'


@admin.register(TeamTarget)
class TeamTargetAdmin(admin.ModelAdmin):
    list_display = ['team_name', 'department', 'title', 'achievement_percentage_display', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'department', 'category', 'start_date']
    search_fields = ['team_name', 'title', 'department__name']
    
    def achievement_percentage_display(self, obj):
        percentage = obj.achievement_percentage
        color = 'green' if percentage >= 100 else 'orange' if percentage >= 80 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, percentage
        )
    achievement_percentage_display.short_description = "نسبة الإنجاز"


@admin.register(TeamTargetMembership)
class TeamTargetMembershipAdmin(admin.ModelAdmin):
    list_display = ['team_target', 'employee', 'contribution_weight', 'individual_target']
    list_filter = ['team_target']
    search_fields = ['employee__arabic_name', 'team_target__title']


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    list_display = ['name', 'metric_type', 'unit', 'benchmark_value', 'target_value', 'is_higher_better', 'is_active']
    list_filter = ['metric_type', 'is_higher_better', 'is_active']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('معلومات المقياس', {
            'fields': ('name', 'metric_type', 'description', 'unit')
        }),
        ('معادلة الحساب', {
            'fields': ('calculation_formula', 'data_source')
        }),
        ('القيم المرجعية', {
            'fields': ('benchmark_value', 'target_value', 'is_higher_better')
        }),
        ('الحالة', {
            'fields': ('is_active',)
        }),
    )


@admin.register(EmployeeMetricValue)
class EmployeeMetricValueAdmin(admin.ModelAdmin):
    list_display = ['employee', 'metric', 'value', 'period_start', 'period_end', 'recorded_by', 'timestamp']
    list_filter = ['metric', 'period_start', 'timestamp']
    search_fields = ['employee__arabic_name', 'metric__name']
    date_hierarchy = 'timestamp'


# =====================
# إدارة سياسات الغياب والخصم
# =====================

@admin.register(AbsencePolicy)
class AbsencePolicyAdmin(admin.ModelAdmin):
    list_display = ['name', 'deduct_from_leave_first', 'salary_deduction_percentage', 'unauthorized_absence_multiplier', 'is_default', 'is_active']
    list_filter = ['is_active', 'is_default', 'deduct_from_leave_first']
    search_fields = ['name']
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'description', 'is_active', 'is_default')
        }),
        ('سياسة الخصم', {
            'fields': ('deduct_from_leave_first', 'salary_deduction_per_day', 'salary_deduction_percentage', 'warning_days')
        }),
        ('الغياب بدون عذر', {
            'fields': ('unauthorized_absence_multiplier',)
        }),
    )


@admin.register(EmployeeAbsence)
class EmployeeAbsenceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'absence_date', 'absence_type', 'deducted_from_leave', 'leave_days_deducted', 'deducted_from_salary', 'salary_deduction_amount', 'is_processed']
    list_filter = ['absence_type', 'is_processed', 'deducted_from_leave', 'deducted_from_salary', 'absence_date']
    search_fields = ['employee__arabic_name', 'employee__employee_id']
    date_hierarchy = 'absence_date'
    readonly_fields = ['processed_at', 'processed_by']
    
    fieldsets = (
        ('معلومات الغياب', {
            'fields': ('employee', 'absence_date', 'absence_type', 'notes')
        }),
        ('الخصومات', {
            'fields': ('deducted_from_leave', 'leave_days_deducted', 'deducted_from_salary', 'salary_deduction_amount')
        }),
        ('المعالجة', {
            'fields': ('is_processed', 'processed_at', 'processed_by')
        }),
    )


@admin.register(EmployeeIDCard)
class EmployeeIDCardAdmin(admin.ModelAdmin):
    list_display = ['card_number', 'employee', 'issue_date', 'expiry_date', 'status', 'print_count', 'scan_count']
    list_filter = ['status', 'issue_date', 'expiry_date']
    search_fields = ['card_number', 'employee__arabic_name', 'employee__employee_id']
    readonly_fields = ['qr_code_image', 'printed_at', 'printed_by', 'last_scan_at', 'print_count', 'scan_count']
    date_hierarchy = 'issue_date'
    
    fieldsets = (
        ('معلومات البطاقة', {
            'fields': ('employee', 'card_number', 'status')
        }),
        ('QR Code', {
            'fields': ('qr_code_data', 'qr_code_image')
        }),
        ('التواريخ', {
            'fields': ('issue_date', 'expiry_date')
        }),
        ('إحصائيات الطباعة', {
            'fields': ('print_count', 'printed_at', 'printed_by'),
            'classes': ('collapse',)
        }),
        ('إحصائيات الاستخدام', {
            'fields': ('scan_count', 'last_scan_at'),
            'classes': ('collapse',)
        }),
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def qr_code_preview(self, obj):
        if obj.qr_code_image:
            return format_html('<img src="{}" width="150" />', obj.qr_code_image.url)
        return "لا توجد صورة"
    qr_code_preview.short_description = "معاينة QR Code"


# === إدارة سلف الموظفين ===

class LoanInstallmentInline(admin.TabularInline):
    """عرض الأقساط داخل صفحة السلفة"""
    model = LoanInstallment
    extra = 0
    readonly_fields = ['installment_number', 'amount', 'due_date', 'status', 'deduction_date', 'payroll']
    can_delete = False
    
    fields = ['installment_number', 'amount', 'due_date', 'status', 'deduction_date', 'payroll', 'notes']


@admin.register(EmployeeLoan)
class EmployeeLoanAdmin(admin.ModelAdmin):
    list_display = [
        'loan_number', 'employee', 'amount', 'status', 
        'installments_count', 'paid_amount', 'remaining_amount',
        'progress_display', 'request_date'
    ]
    list_filter = ['status', 'is_emergency', 'request_date', 'approved_at']
    search_fields = ['loan_number', 'employee__arabic_name', 'employee__employee_id', 'reason']
    readonly_fields = [
        'loan_number', 'request_date', 'monthly_installment', 
        'remaining_amount', 'progress_percentage', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'request_date'
    inlines = [LoanInstallmentInline]
    
    fieldsets = (
        ('معلومات السلفة', {
            'fields': ('loan_number', 'employee', 'amount', 'reason', 'is_emergency')
        }),
        ('خطة السداد', {
            'fields': (
                'installments_count', 'monthly_installment', 
                'start_deduction_date', 'paid_amount', 'remaining_amount'
            )
        }),
        ('الحالة والموافقات', {
            'fields': (
                'status', 'approved_by', 'approved_at', 
                'rejection_reason'
            )
        }),
        ('الربط المحاسبي', {
            'fields': ('journal_entry',),
            'classes': ('collapse',)
        }),
        ('معلومات إضافية', {
            'fields': ('notes', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_display(self, obj):
        """عرض تقدم السداد بشكل مرئي"""
        percentage = obj.progress_percentage
        if percentage < 30:
            color = 'red'
        elif percentage < 70:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<div style="width:100px; background:#ddd; border-radius:5px;">'
            '<div style="width:{}%; background:{}; height:20px; border-radius:5px; text-align:center; color:white;">{:.1f}%</div>'
            '</div>',
            percentage, color, percentage
        )
    progress_display.short_description = "نسبة السداد"
    
    def get_readonly_fields(self, request, obj=None):
        """تعديل الحقول حسب حالة السلفة"""
        readonly = list(self.readonly_fields)
        if obj and obj.status != 'pending':
            readonly.extend(['employee', 'amount', 'installments_count', 'start_deduction_date'])
        return readonly


@admin.register(LoanInstallment)
class LoanInstallmentAdmin(admin.ModelAdmin):
    list_display = [
        'loan', 'installment_number', 'amount', 
        'due_date', 'status', 'deduction_date', 'payroll'
    ]
    list_filter = ['status', 'due_date', 'deduction_date']
    search_fields = [
        'loan__loan_number', 'loan__employee__arabic_name', 
        'loan__employee__employee_id'
    ]
    readonly_fields = ['loan', 'installment_number', 'created_at', 'updated_at']
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('معلومات القسط', {
            'fields': ('loan', 'installment_number', 'amount', 'due_date')
        }),
        ('حالة السداد', {
            'fields': ('status', 'deduction_date', 'payroll')
        }),
        ('التأجيل', {
            'fields': ('deferred_to_date', 'deferment_reason'),
            'classes': ('collapse',)
        }),
        ('ملاحظات', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """منع التعديل بعد الخصم"""
        readonly = list(self.readonly_fields)
        if obj and obj.status == 'deducted':
            readonly.extend(['amount', 'due_date', 'status'])
        return readonly
