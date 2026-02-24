from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg, F, Max, Min
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import os
from functools import wraps

from hr.models import (
    Employee, Department, JobPosition, AttendanceRecord, WorkSchedule,
    LeaveRequest, LeaveType, Payroll, PerformanceReview, TrainingProgram,
    TrainingEnrollment, JobVacancy, JobApplication, HRSettings,
    PerformanceTarget, TargetCategory, TargetProgress, TeamTarget,
    TeamTargetMembership, PerformanceMetric, EmployeeMetricValue,
    WeekendDay, PublicHoliday, EmployeeAbsence,
    AllowanceType, DeductionType, EmployeeAllowance, EmployeeDeduction, PayrollItem
)
from accounting.models import JournalEntry, JournalEntryItem
from hr.forms import (
    ComplaintForm, DisciplinaryActionForm, HSEIncidentForm,
    HSEInspectionForm, HSETrainingForm,
    LeaveRequestForm, PerformanceReviewQuickForm, TrainingProgramForm,
    JobVacancyForm, JobApplicationQuickForm, PerformanceTargetQuickForm,
    TeamTargetQuickForm, AttendanceRecordQuickForm
)

# التقارير

# === التقارير ===


class HRReportBuilder:
    """تجميع بيانات تقارير الموارد البشرية من مصادر النظام."""

    def __init__(self, date_from, date_to, department_id=None):
        self.date_from = date_from
        self.date_to = date_to
        self.department_id = department_id
        self.department_name = None
        if department_id:
            self.department_name = Department.objects.filter(id=department_id).values_list('name', flat=True).first()
        self.employee_filter = Q()
        if department_id:
            self.employee_filter &= Q(department_id=department_id)

    # === مصادر البيانات المساعدة ===
    def _employees(self):
        return Employee.objects.select_related('department', 'position').filter(self.employee_filter)

    def _attendance_qs(self):
        qs = AttendanceRecord.objects.filter(date__range=(self.date_from, self.date_to))
        if self.department_id:
            qs = qs.filter(employee__department_id=self.department_id)
        return qs.select_related('employee', 'employee__department')

    def _absences_qs(self):
        qs = EmployeeAbsence.objects.filter(absence_date__range=(self.date_from, self.date_to))
        if self.department_id:
            qs = qs.filter(employee__department_id=self.department_id)
        return qs.select_related('employee', 'employee__department')

    def _payroll_qs(self):
        qs = Payroll.objects.filter(period_start__lte=self.date_to, period_end__gte=self.date_from)
        if self.department_id:
            qs = qs.filter(employee__department_id=self.department_id)
        return qs.select_related('employee', 'employee__department')

    def _leave_qs(self):
        qs = LeaveRequest.objects.filter(start_date__lte=self.date_to, end_date__gte=self.date_from)
        if self.department_id:
            qs = qs.filter(employee__department_id=self.department_id)
        return qs.select_related('employee', 'employee__department', 'leave_type')

    def _common_cards(self, summary):
        return [
            {'label': 'من تاريخ', 'value': self.date_from},
            {'label': 'إلى تاريخ', 'value': self.date_to},
            {'label': 'القسم', 'value': self.department_name or 'كل الأقسام'},
            *summary,
        ]

    # === مجمعات التقارير ===
    def build(self, report_type):
        handlers = {
            'attendance_summary': self._build_attendance_summary,
            'late_employees': self._build_late_employees,
            'overtime_report': self._build_overtime_report,
            'payroll_summary': self._build_payroll_summary,
            'payroll_details': self._build_payroll_details,
            'salary_analysis': self._build_salary_analysis,
            'leave_summary': self._build_leave_summary,
            'leave_balance': self._build_leave_balance,
            'leave_trends': self._build_leave_trends,
            'employee_profile': self._build_employee_profile,
            'department_analysis': self._build_department_analysis,
            'turnover_analysis': self._build_turnover_analysis,
            'performance_summary': self._build_performance_summary,
            'training_report': self._build_training_report,
            'skills_matrix': self._build_skills_matrix,
            'hr_costs': self._build_hr_costs,
            'budget_analysis': self._build_budget_analysis,
            'cost_per_employee': self._build_cost_per_employee,
        }
        handler = handlers.get(report_type, self._build_default)
        data = handler()
        data.setdefault('summary_cards', [])
        data.setdefault('tables', [])
        return data

    def _build_attendance_summary(self):
        attendance_qs = self._attendance_qs()
        checkins = attendance_qs.filter(record_type='check_in')
        absences_qs = self._absences_qs()

        attendance_by_day = list(checkins.values('date').annotate(count=Count('id')).order_by('date'))
        attendance_by_department = list(
            checkins.values('employee__department__name')
            .annotate(records=Count('id'), employees=Count('employee', distinct=True))
            .order_by('-records')
        )
        top_absent = list(
            absences_qs.values('employee__arabic_name', 'employee__department__name')
            .annotate(days=Count('id'))
            .order_by('-days')[:20]
        )

        summary = [
            {'label': 'إجمالي سجلات الحضور', 'value': attendance_qs.count()},
            {'label': 'سجلات الحضور (Check-in)', 'value': checkins.count()},
            {'label': 'عدد الموظفين المسجلين', 'value': checkins.values('employee_id').distinct().count()},
            {'label': 'حالات الغياب المسجلة', 'value': absences_qs.count()},
        ]

        tables = [
            {
                'title': 'الحضور حسب اليوم',
                'headers': ['التاريخ', 'عدد الحضور'],
                'rows': [[row['date'], row['count']] for row in attendance_by_day],
            },
            {
                'title': 'الحضور حسب القسم',
                'headers': ['القسم', 'سجلات الحضور', 'عدد الموظفين'],
                'rows': [
                    [row['employee__department__name'] or 'غير محدد', row['records'], row['employees']]
                    for row in attendance_by_department
                ],
            },
            {
                'title': 'أعلى الغياب',
                'headers': ['الموظف', 'القسم', 'أيام الغياب'],
                'rows': [
                    [row['employee__arabic_name'], row['employee__department__name'], row['days']]
                    for row in top_absent
                ],
            },
        ]

        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_late_employees(self):
        late_qs = self._absences_qs().filter(absence_type='late')
        late_by_employee = list(
            late_qs.values('employee__arabic_name', 'employee__department__name')
            .annotate(late_count=Count('id'), last_date=Max('absence_date'))
            .order_by('-late_count')
        )
        employee_count = late_by_employee.__len__()
        total_late = late_qs.count()
        summary = [
            {'label': 'حالات التأخير', 'value': total_late},
            {'label': 'عدد الموظفين المتأخرين', 'value': employee_count},
            {'label': 'متوسط التأخير لكل موظف', 'value': f"{(total_late/employee_count):.1f}" if employee_count else 0},
        ]
        tables = [
            {
                'title': 'تفاصيل التأخير',
                'headers': ['الموظف', 'القسم', 'عدد مرات التأخير', 'آخر تأخير'],
                'rows': [
                    [row['employee__arabic_name'], row['employee__department__name'], row['late_count'], row['last_date']]
                    for row in late_by_employee
                ],
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_overtime_report(self):
        payroll_qs = self._payroll_qs()
        totals = payroll_qs.aggregate(
            hours=Sum('overtime_hours'),
            amount=Sum('overtime_amount'),
            employees=Count('employee', distinct=True),
        )
        overtime_by_employee = list(
            payroll_qs.values('employee__arabic_name', 'employee__department__name')
            .annotate(hours=Sum('overtime_hours'), amount=Sum('overtime_amount'), payrolls=Count('id'))
            .order_by('-hours')
        )
        overtime_by_department = list(
            payroll_qs.values('employee__department__name')
            .annotate(hours=Sum('overtime_hours'), amount=Sum('overtime_amount'))
            .order_by('-hours')
        )
        summary = [
            {'label': 'إجمالي الساعات الإضافية', 'value': totals.get('hours') or 0},
            {'label': 'إجمالي تكلفة الساعات الإضافية', 'value': totals.get('amount') or 0},
            {'label': 'عدد الموظفين المشمولين', 'value': totals.get('employees') or 0},
        ]
        tables = [
            {
                'title': 'الساعات الإضافية حسب الموظف',
                'headers': ['الموظف', 'القسم', 'الساعات', 'المبلغ', 'عدد كشوف الرواتب'],
                'rows': [
                    [row['employee__arabic_name'], row['employee__department__name'], row['hours'] or 0, row['amount'] or 0, row['payrolls']]
                    for row in overtime_by_employee
                ],
            },
            {
                'title': 'الساعات الإضافية حسب القسم',
                'headers': ['القسم', 'الساعات', 'المبلغ'],
                'rows': [
                    [row['employee__department__name'] or 'غير محدد', row['hours'] or 0, row['amount'] or 0]
                    for row in overtime_by_department
                ],
            },
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_payroll_summary(self):
        payroll_qs = self._payroll_qs()
        totals = payroll_qs.aggregate(
            gross=Sum('gross_salary'),
            net=Sum('net_salary'),
            deductions=Sum('total_deductions'),
            overtime=Sum('overtime_amount'),
        )
        payroll_by_department = list(
            payroll_qs.values('employee__department__name')
            .annotate(
                gross=Sum('gross_salary'),
                net=Sum('net_salary'),
                deductions=Sum('total_deductions'),
                headcount=Count('employee', distinct=True),
            )
            .order_by('-net')
        )
        summary = [
            {'label': 'إجمالي إجمالي الرواتب', 'value': totals.get('gross') or 0},
            {'label': 'إجمالي صافي الرواتب', 'value': totals.get('net') or 0},
            {'label': 'إجمالي الخصومات', 'value': totals.get('deductions') or 0},
            {'label': 'مبالغ الساعات الإضافية', 'value': totals.get('overtime') or 0},
        ]
        tables = [
            {
                'title': 'ملخص الرواتب حسب القسم',
                'headers': ['القسم', 'إجمالي الرواتب', 'صافي الرواتب', 'الخصومات', 'عدد الموظفين'],
                'rows': [
                    [row['employee__department__name'] or 'غير محدد', row['gross'] or 0, row['net'] or 0, row['deductions'] or 0, row['headcount']]
                    for row in payroll_by_department
                ],
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_payroll_details(self):
        payroll_qs = self._payroll_qs().order_by('-period_start')
        payrolls = payroll_qs[:200]
        totals = payroll_qs.aggregate(
            gross=Sum('gross_salary'), net=Sum('net_salary'), deductions=Sum('total_deductions')
        )
        summary = [
            {'label': 'عدد سجلات الرواتب', 'value': payroll_qs.count()},
            {'label': 'إجمالي إجمالي الرواتب', 'value': totals.get('gross') or 0},
            {'label': 'إجمالي الخصومات', 'value': totals.get('deductions') or 0},
            {'label': 'إجمالي الصافي', 'value': totals.get('net') or 0},
        ]
        rows = [
            [
                p.employee.arabic_name,
                p.employee.department.name if p.employee.department else 'غير محدد',
                f"{p.period_start} → {p.period_end}",
                p.gross_salary,
                p.total_deductions,
                p.net_salary,
                p.overtime_amount,
                p.status,
            ]
            for p in payrolls
        ]
        tables = [
            {
                'title': 'تفاصيل الرواتب',
                'headers': ['الموظف', 'القسم', 'الفترة', 'إجمالي', 'الخصومات', 'الصافي', 'الساعات الإضافية', 'الحالة'],
                'rows': rows,
                'subtitle': 'أول 200 سجل في النطاق المحدد',
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_salary_analysis(self):
        employees = list(self._employees())
        headcount = len(employees)
        salary_expr = F('basic_salary') + F('housing_allowance') + F('transportation_allowance') + F('other_allowances')
        aggregates = self._employees().aggregate(
            avg_basic=Avg('basic_salary'),
            avg_total=Avg(salary_expr),
            max_total=Max(salary_expr),
            min_total=Min(salary_expr),
            total_basic=Sum('basic_salary'),
            total_allowances=Sum(F('housing_allowance') + F('transportation_allowance') + F('other_allowances')),
        )

        salary_bands = [
            {'label': 'أقل من 3000', 'min': Decimal('0'), 'max': Decimal('3000'), 'count': 0},
            {'label': '3000 - 6000', 'min': Decimal('3000'), 'max': Decimal('6000'), 'count': 0},
            {'label': '6000 - 9000', 'min': Decimal('6000'), 'max': Decimal('9000'), 'count': 0},
            {'label': 'أكثر من 9000', 'min': Decimal('9000'), 'max': None, 'count': 0},
        ]
        for emp in employees:
            total = emp.total_salary
            for band in salary_bands:
                if band['max'] is None and total >= band['min']:
                    band['count'] += 1
                    break
                if band['min'] <= total < band['max']:
                    band['count'] += 1
                    break

        summary = [
            {'label': 'عدد الموظفين', 'value': headcount},
            {'label': 'متوسط الراتب الأساسي', 'value': aggregates.get('avg_basic') or 0},
            {'label': 'متوسط إجمالي الرواتب', 'value': aggregates.get('avg_total') or 0},
            {'label': 'أعلى إجمالي', 'value': aggregates.get('max_total') or 0},
            {'label': 'أقل إجمالي', 'value': aggregates.get('min_total') or 0},
        ]
        tables = [
            {
                'title': 'مكونات الرواتب',
                'headers': ['إجمالي الأساسي', 'إجمالي البدلات', 'متوسط الأساسي', 'متوسط الإجمالي'],
                'rows': [[
                    aggregates.get('total_basic') or 0,
                    aggregates.get('total_allowances') or 0,
                    aggregates.get('avg_basic') or 0,
                    aggregates.get('avg_total') or 0,
                ]],
            },
            {
                'title': 'توزيع الرواتب حسب الشرائح',
                'headers': ['الشريحة', 'عدد الموظفين'],
                'rows': [[band['label'], band['count']] for band in salary_bands],
            },
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_leave_summary(self):
        leave_qs = self._leave_qs()
        totals = leave_qs.aggregate(total_days=Sum('days_requested'))
        status_counts = leave_qs.values('status').annotate(count=Count('id')).order_by('-count')
        type_counts = leave_qs.values('leave_type__name').annotate(days=Sum('days_requested'), requests=Count('id')).order_by('-days')
        summary = [
            {'label': 'إجمالي طلبات الإجازة', 'value': leave_qs.count()},
            {'label': 'إجمالي الأيام المطلوبة', 'value': totals.get('total_days') or 0},
            {'label': 'طلبات موافق عليها', 'value': next((s['count'] for s in status_counts if s['status'] == 'approved'), 0)},
            {'label': 'طلبات معلقة', 'value': next((s['count'] for s in status_counts if s['status'] == 'pending'), 0)},
        ]
        tables = [
            {
                'title': 'الإجازات حسب النوع',
                'headers': ['النوع', 'عدد الطلبات', 'الأيام المطلوبة'],
                'rows': [[row['leave_type__name'], row['requests'], row['days'] or 0] for row in type_counts],
            },
            {
                'title': 'الإجازات حسب الحالة',
                'headers': ['الحالة', 'عدد الطلبات'],
                'rows': [[row['status'], row['count']] for row in status_counts],
            },
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_leave_balance(self):
        leave_qs = self._leave_qs().filter(status='approved')
        usage = leave_qs.values('employee_id', 'leave_type_id').annotate(used=Sum('days_requested'))
        usage_map = {(u['employee_id'], u['leave_type_id']): u['used'] for u in usage}
        employees = list(self._employees())
        leave_types = list(LeaveType.objects.all())
        rows = []
        for emp in employees:
            for leave_type in leave_types:
                used = usage_map.get((emp.id, leave_type.id), 0) or 0
                balance = max(leave_type.days_per_year - used, 0)
                rows.append([
                    emp.arabic_name,
                    emp.department.name if emp.department else 'غير محدد',
                    leave_type.name,
                    used,
                    balance,
                ])
        summary = [
            {'label': 'عدد الموظفين', 'value': len(employees)},
            {'label': 'أنواع الإجازات', 'value': len(leave_types)},
            {'label': 'طلبات إجازة معتمدة في الفترة', 'value': leave_qs.count()},
        ]
        tables = [
            {
                'title': 'أرصدة الإجازات',
                'headers': ['الموظف', 'القسم', 'نوع الإجازة', 'أيام مستخدمة', 'الرصيد المتبقي'],
                'rows': rows,
                'subtitle': 'الحساب يعتمد على الأيام المسموحة لكل نوع ناقص الأيام المستخدمة في الفترة المحددة',
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_leave_trends(self):
        leave_qs = self._leave_qs().filter(status='approved')
        monthly = leave_qs.annotate(month=TruncMonth('start_date')).values('month').annotate(
            requests=Count('id'), days=Sum('days_requested')
        ).order_by('month')
        summary = [
            {'label': 'طلبات معتمدة', 'value': leave_qs.count()},
            {'label': 'أيام الإجازات المعتمدة', 'value': leave_qs.aggregate(total=Sum('days_requested')).get('total') or 0},
        ]
        tables = [
            {
                'title': 'الاتجاه الشهري للإجازات',
                'headers': ['الشهر', 'عدد الطلبات', 'مجموع الأيام'],
                'rows': [[row['month'].date() if hasattr(row['month'], 'date') else row['month'], row['requests'], row['days'] or 0] for row in monthly],
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_employee_profile(self):
        employees = self._employees()
        headcount = employees.count()
        active_count = employees.filter(status='active').count()
        rows = [
            [
                emp.arabic_name,
                emp.department.name if emp.department else 'غير محدد',
                emp.position.title if emp.position else 'غير محدد',
                emp.hire_date,
                emp.status,
                emp.total_salary,
            ]
            for emp in employees
        ]
        summary = [
            {'label': 'عدد الموظفين', 'value': headcount},
            {'label': 'الموظفون النشطون', 'value': active_count},
            {'label': 'متوسط مدة الخدمة (سنوات)', 'value': f"{(sum([emp.years_of_service for emp in employees]) / headcount):.1f}" if headcount else 0},
        ]
        tables = [
            {
                'title': 'بيانات الموظفين',
                'headers': ['الموظف', 'القسم', 'المنصب', 'تاريخ التعيين', 'الحالة', 'إجمالي الراتب'],
                'rows': rows,
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_department_analysis(self):
        departments = Department.objects.filter(is_active=True)
        if self.department_id:
            departments = departments.filter(id=self.department_id)
        salary_expr = F('employee__basic_salary') + F('employee__housing_allowance') + F('employee__transportation_allowance') + F('employee__other_allowances')
        departments = departments.annotate(
            headcount=Count('employee', distinct=True),
            total_salary=Sum(salary_expr),
            avg_salary=Avg(salary_expr),
        )
        rows = [
            [dept.name, dept.headcount, dept.total_salary or 0, dept.avg_salary or 0, dept.budget]
            for dept in departments
        ]
        summary = [
            {'label': 'عدد الأقسام', 'value': departments.count()},
            {'label': 'إجمالي الموظفين', 'value': sum([dept.headcount for dept in departments])},
            {'label': 'متوسط الراتب الكلي', 'value': (sum([(dept.avg_salary or 0) for dept in departments]) / departments.count()) if departments else 0},
        ]
        tables = [
            {
                'title': 'تحليل الأقسام',
                'headers': ['القسم', 'عدد الموظفين', 'إجمالي الرواتب', 'متوسط الراتب', 'الميزانية'],
                'rows': rows,
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_turnover_analysis(self):
        employees = Employee.objects.all()
        if self.department_id:
            employees = employees.filter(department_id=self.department_id)
        hires = employees.filter(hire_date__range=(self.date_from, self.date_to))
        exits = employees.filter(termination_date__range=(self.date_from, self.date_to))
        headcount_start = employees.filter(hire_date__lte=self.date_from).exclude(status='terminated').count()
        headcount_end = employees.filter(hire_date__lte=self.date_to).exclude(status='terminated', termination_date__lt=self.date_to).count()
        average_headcount = (headcount_start + headcount_end) / 2 if (headcount_start + headcount_end) else 0
        turnover_rate = (exits.count() / average_headcount) * 100 if average_headcount else 0
        summary = [
            {'label': 'المعينون الجدد', 'value': hires.count()},
            {'label': 'المغادرون', 'value': exits.count()},
            {'label': 'متوسط عدد الموظفين', 'value': average_headcount},
            {'label': 'معدل الدوران %', 'value': f"{turnover_rate:.1f}"},
        ]
        tables = [
            {
                'title': 'المعينون الجدد',
                'headers': ['الموظف', 'القسم', 'تاريخ التعيين'],
                'rows': [[e.arabic_name, e.department.name if e.department else 'غير محدد', e.hire_date] for e in hires],
            },
            {
                'title': 'المغادرون',
                'headers': ['الموظف', 'القسم', 'تاريخ نهاية الخدمة'],
                'rows': [[e.arabic_name, e.department.name if e.department else 'غير محدد', e.termination_date] for e in exits],
            },
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_performance_summary(self):
        reviews = PerformanceReview.objects.filter(review_period_start__lte=self.date_to, review_period_end__gte=self.date_from)
        if self.department_id:
            reviews = reviews.filter(employee__department_id=self.department_id)
        aggregates = reviews.aggregate(avg_rating=Avg('overall_rating'), total=Count('id'))
        rating_breakdown = reviews.values('overall_rating').annotate(count=Count('id')).order_by('-overall_rating')
        top_performers = reviews.select_related('employee').order_by('-overall_rating', '-review_period_end')[:20]
        summary = [
            {'label': 'عدد التقييمات', 'value': aggregates.get('total') or 0},
            {'label': 'متوسط التقييم', 'value': aggregates.get('avg_rating') or 0},
            {'label': 'أفضل تقييم', 'value': top_performers[0].overall_rating if top_performers else 0},
        ]
        tables = [
            {
                'title': 'توزيع التقييمات',
                'headers': ['التقييم', 'عدد الموظفين'],
                'rows': [[row['overall_rating'], row['count']] for row in rating_breakdown],
            },
            {
                'title': 'أفضل المؤدين',
                'headers': ['الموظف', 'التقييم', 'فترة التقييم'],
                'rows': [
                    [rev.employee.arabic_name, rev.overall_rating, f"{rev.review_period_start} → {rev.review_period_end}"]
                    for rev in top_performers
                ],
            },
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_training_report(self):
        programs = TrainingProgram.objects.filter(end_date__gte=self.date_from, start_date__lte=self.date_to)
        if self.department_id:
            programs = programs.filter(enrollments__employee__department_id=self.department_id).distinct()
        programs = programs.annotate(
            enrollments_count=Count('enrollments', distinct=True),
            completed_count=Count('enrollments', filter=Q(enrollments__status='completed'), distinct=True),
        )
        enrollments = TrainingEnrollment.objects.filter(training_program__in=programs)
        if self.department_id:
            enrollments = enrollments.filter(employee__department_id=self.department_id)
        summary = [
            {'label': 'عدد البرامج التدريبية', 'value': programs.count()},
            {'label': 'إجمالي التسجيلات', 'value': enrollments.count()},
            {'label': 'تسجيلات مكتملة', 'value': enrollments.filter(status='completed').count()},
        ]
        tables = [
            {
                'title': 'البرامج التدريبية',
                'headers': ['البرنامج', 'المزود', 'الفترة', 'التكلفة', 'التسجيلات', 'المكتمل'],
                'rows': [
                    [
                        program.title,
                        program.provider,
                        f"{program.start_date} → {program.end_date}",
                        program.cost,
                        program.enrollments_count,
                        program.completed_count,
                    ]
                    for program in programs
                ],
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_skills_matrix(self):
        metrics_qs = EmployeeMetricValue.objects.filter(period_start__lte=self.date_to, period_end__gte=self.date_from)
        if self.department_id:
            metrics_qs = metrics_qs.filter(employee__department_id=self.department_id)
        metric_summary = metrics_qs.values('metric__name').annotate(avg_value=Avg('value'), samples=Count('id')).order_by('-samples')
        employee_summary = metrics_qs.values('employee__arabic_name').annotate(avg_value=Avg('value'), samples=Count('id')).order_by('-avg_value')
        summary = [
            {'label': 'عدد المقاييس المقاسة', 'value': metric_summary.count()},
            {'label': 'عدد القراءات', 'value': metrics_qs.count()},
            {'label': 'أفضل متوسط', 'value': (employee_summary[0]['avg_value'] if employee_summary else 0)},
        ]
        tables = [
            {
                'title': 'المقاييس',
                'headers': ['المقياس', 'متوسط القيمة', 'عدد القراءات'],
                'rows': [[row['metric__name'], row['avg_value'] or 0, row['samples']] for row in metric_summary],
            },
            {
                'title': 'متوسط القيم حسب الموظف',
                'headers': ['الموظف', 'متوسط القيمة', 'عدد القراءات'],
                'rows': [[row['employee__arabic_name'], row['avg_value'] or 0, row['samples']] for row in employee_summary],
            },
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_hr_costs(self):
        payroll_qs = self._payroll_qs()
        totals = payroll_qs.aggregate(
            net=Sum('net_salary'),
            gross=Sum('gross_salary'),
            overtime=Sum('overtime_amount'),
            bonus=Sum('bonus_amount'),
            deductions=Sum('total_deductions'),
        )
        cost_by_department = list(
            payroll_qs.values('employee__department__name')
            .annotate(net=Sum('net_salary'), gross=Sum('gross_salary'), headcount=Count('employee', distinct=True))
            .order_by('-net')
        )
        summary = [
            {'label': 'إجمالي التكلفة الصافية', 'value': totals.get('net') or 0},
            {'label': 'إجمالي التكلفة الإجمالية', 'value': totals.get('gross') or 0},
            {'label': 'الساعات الإضافية', 'value': totals.get('overtime') or 0},
            {'label': 'المكافآت', 'value': totals.get('bonus') or 0},
            {'label': 'الخصومات', 'value': totals.get('deductions') or 0},
        ]
        tables = [
            {
                'title': 'تكلفة الموارد البشرية حسب القسم',
                'headers': ['القسم', 'إجمالي', 'صافي', 'عدد الموظفين'],
                'rows': [[row['employee__department__name'] or 'غير محدد', row['gross'] or 0, row['net'] or 0, row['headcount']] for row in cost_by_department],
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_budget_analysis(self):
        payroll_qs = self._payroll_qs()
        spent_by_department = payroll_qs.values('employee__department_id').annotate(spent=Sum('net_salary'))
        spent_map = {row['employee__department_id']: row['spent'] for row in spent_by_department}
        departments = Department.objects.filter(is_active=True)
        if self.department_id:
            departments = departments.filter(id=self.department_id)
        rows = []
        total_budget = Decimal('0')
        total_spent = Decimal('0')
        for dept in departments:
            spent = spent_map.get(dept.id, Decimal('0')) or Decimal('0')
            variance = (dept.budget or Decimal('0')) - spent
            total_budget += dept.budget or Decimal('0')
            total_spent += spent
            rows.append([dept.name, dept.budget, spent, variance])
        summary = [
            {'label': 'إجمالي الميزانية', 'value': total_budget},
            {'label': 'المصروف الفعلي', 'value': total_spent},
            {'label': 'الفائض/العجز', 'value': total_budget - total_spent},
        ]
        tables = [
            {
                'title': 'تحليل الميزانية حسب القسم',
                'headers': ['القسم', 'الميزانية', 'المصروف', 'الفائض/العجز'],
                'rows': rows,
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_cost_per_employee(self):
        payroll_qs = self._payroll_qs()
        total_cost = payroll_qs.aggregate(total=Sum('net_salary')).get('total') or Decimal('0')
        headcount = self._employees().count()
        cost_per_employee = (total_cost / headcount) if headcount else Decimal('0')
        cost_by_department = list(
            payroll_qs.values('employee__department__name').annotate(total=Sum('net_salary'), employees=Count('employee', distinct=True))
        )
        summary = [
            {'label': 'إجمالي التكلفة', 'value': total_cost},
            {'label': 'عدد الموظفين', 'value': headcount},
            {'label': 'التكلفة لكل موظف', 'value': cost_per_employee},
        ]
        tables = [
            {
                'title': 'التكلفة لكل قسم',
                'headers': ['القسم', 'إجمالي التكلفة', 'عدد الموظفين', 'متوسط التكلفة'],
                'rows': [
                    [row['employee__department__name'] or 'غير محدد', row['total'] or 0, row['employees'], (row['total'] / row['employees']) if row['employees'] else 0]
                    for row in cost_by_department
                ],
            }
        ]
        return {'summary_cards': self._common_cards(summary), 'tables': tables}

    def _build_default(self):
        return {'summary_cards': [], 'tables': []}

@login_required
def reports_dashboard(request):
    """لوحة تحكم التقارير"""
    context = {
        'date_from': date.today().replace(day=1).strftime('%Y-%m-%d'),
        'date_to': date.today().strftime('%Y-%m-%d'),
        'departments': Department.objects.filter(is_active=True).order_by('name'),
    }
    return render(request, 'hr/reports_dashboard.html', context)

@login_required
def generate_report(request):
    """توليد التقارير"""
    report_type = request.GET.get('type') or 'attendance_summary'
    date_from_param = request.GET.get('dateFrom')
    date_to_param = request.GET.get('dateTo')
    department = request.GET.get('department')
    format_type = request.GET.get('format', 'html')

    def _parse_date(value, default):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except Exception:
            return default

    today = date.today()
    default_from = today.replace(day=1)
    date_from = _parse_date(date_from_param, default_from)
    date_to = _parse_date(date_to_param, today)

    builder = HRReportBuilder(date_from, date_to, department)
    report_data = builder.build(report_type)

    context = {
        'report_type': report_type,
        'date_from': date_from,
        'date_to': date_to,
        'department': builder.department_name or 'كل الأقسام',
        'format_type': format_type,
        **report_data,
    }

    return render(request, f'hr/reports/{report_type}.html', context)

@login_required
def attendance_report(request):
    """تقرير الحضور والانصراف"""
    # منطق تقرير الحضور
    context = {}
    return render(request, 'hr/attendance_report.html', context)

@login_required
def payroll_report(request):
    """تقرير الرواتب"""
    # منطق تقرير الرواتب
    context = {}
    return render(request, 'hr/payroll_report.html', context)

@login_required
def employee_summary_report(request):
    """تقرير ملخص الموظفين"""
    context = {
        'total_employees': Employee.objects.filter(status='active').count(),
        'departments_summary': Department.objects.annotate(
            employee_count=Count('employee')
        ),
        'gender_distribution': Employee.objects.values('gender').annotate(count=Count('id')),
    }
    return render(request, 'hr/employee_summary_report.html', context)

# === API للأجهزة الخارجية ===
