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

# إدارة الرواتب

# === إدارة الرواتب ===

@login_required
def payroll_dashboard(request):
    """لوحة تحكم الرواتب"""
    current_month = date.today().replace(day=1)
    
    context = {
        'current_month_payrolls': Payroll.objects.filter(period_start=current_month).count(),
        'approved_payrolls': Payroll.objects.filter(
            period_start=current_month, 
            status='approved'
        ).count(),
        'total_salary_expense': Payroll.objects.filter(
            period_start=current_month,
            status__in=['approved', 'paid']
        ).aggregate(total=Sum('net_salary'))['total'] or 0,
    }
    return render(request, 'hr/payroll_dashboard.html', context)

@login_required
def payroll_generate(request):
    """توليد الرواتب مع تحققات وأdefaults لفترة الشهر الحالي"""
    # احسب بداية ونهاية الشهر الحالي كقِيَم افتراضية
    today = date.today()
    first_day = today.replace(day=1)
    next_month_first = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_day = next_month_first - timedelta(days=1)

    if request.method == 'POST':
        ps_raw = (request.POST.get('period_start') or '').strip()
        pe_raw = (request.POST.get('period_end') or '').strip()

        # حاول تحويل التواريخ
        try:
            ps = date.fromisoformat(ps_raw)
            pe = date.fromisoformat(pe_raw)
        except ValueError:
            messages.error(request, 'صيغة التواريخ غير صحيحة. الرجاء استخدام اختيار التاريخ.')
            context = {
                'period_start': ps_raw or first_day.isoformat(),
                'period_end': pe_raw or last_day.isoformat(),
            }
            return render(request, 'hr/payroll_generate.html', context)

        # تحققات منطقية
        if pe < ps:
            messages.error(request, 'تاريخ النهاية يجب أن يكون بعد أو يساوي تاريخ البداية.')
            context = {
                'period_start': ps.isoformat(),
                'period_end': pe.isoformat(),
            }
            return render(request, 'hr/payroll_generate.html', context)

        # منطق توليد الرواتب
        generated_count = 0
        for employee in Employee.objects.filter(status='active'):
            payroll, created = Payroll.objects.get_or_create(
                employee=employee,
                period_start=ps,
                period_end=pe,
                defaults={
                    'basic_salary': employee.basic_salary,
                    'housing_allowance': employee.housing_allowance,
                    'transportation_allowance': employee.transportation_allowance,
                    'other_allowances': employee.other_allowances,
                }
            )
            if created:
                generated_count += 1

        messages.success(
            request,
            f'تم توليد {generated_count} راتب للفترة من {ps.isoformat()} إلى {pe.isoformat()}'
        )
        return redirect('hr:payroll_list')

    # GET: أعرض النموذج مع تعبئة تلقائية لفترة الشهر الحالي
    context = {
        'period_start': first_day.isoformat(),
        'period_end': last_day.isoformat(),
    }
    return render(request, 'hr/payroll_generate.html', context)

@login_required
def payroll_list(request):
    """قائمة الرواتب"""
    payrolls = Payroll.objects.select_related('employee').all()
    
    # فلترة
    period = request.GET.get('period')
    if period:
        payrolls = payrolls.filter(period_start=period)
    
    payrolls = payrolls.order_by('-period_start', 'employee__arabic_name')
    
    context = {'payrolls': payrolls}
    return render(request, 'hr/payroll_list.html', context)

@login_required
def payroll_detail(request, pk):
    """تفاصيل الراتب"""
    payroll = get_object_or_404(Payroll, pk=pk)
    context = {'payroll': payroll}
    return render(request, 'hr/payroll_detail.html', context)

@login_required
def payroll_payslip_pdf(request, pk):
    """توليد إيصال راتب كـ PDF/HTML مبسّط حالياً"""
    payroll = get_object_or_404(Payroll, pk=pk)

    # يمكن لاحقاً استبدال هذا بتوليد PDF فعلي عبر reportlab or xhtml2pdf
    context = {
        'payroll': payroll,
        'company_name': 'شركة {{ SYSTEM_NAME }}',  # سيتم استبداله فعلياً في القالب الأساسي إذا لزم
    }

    response = HttpResponse(content_type='text/html')
    response['Content-Disposition'] = f'inline; filename="payslip_{payroll.pk}.html"'

    html_content = render_to_string('hr/payslip_pdf.html', context)
    response.write(html_content)

    return response

@login_required
def payroll_approve(request, pk):
    """اعتماد الراتب وإنشاء القيد المحاسبي"""
    payroll = get_object_or_404(Payroll, pk=pk)
    
    if request.method == 'POST':
        with transaction.atomic():
            # تحديث حالة الراتب
            payroll.status = 'approved'
            payroll.approved_by = request.user.employee_profile
            payroll.approved_at = timezone.now()
            
            # إنشاء القيد المحاسبي
            hr_settings = HRSettings.objects.first()
            if hr_settings and hr_settings.salary_expense_account and hr_settings.salary_payable_account:
                journal_entry = JournalEntry.objects.create(
                    description=f'راتب {payroll.employee.arabic_name} للفترة من {payroll.period_start} إلى {payroll.period_end}',
                    date=date.today(),
                    created_by=request.user
                )
                
                # قيد المصروف (مدين)
                JournalEntryItem.objects.create(
                    journal_entry=journal_entry,
                    account=hr_settings.salary_expense_account,
                    type='debit',
                    amount=payroll.net_salary,
                    description=f'راتب {payroll.employee.arabic_name}',
                    cost_center=payroll.employee.department.cost_center
                )
                
                # قيد الخصم (دائن)
                JournalEntryItem.objects.create(
                    journal_entry=journal_entry,
                    account=hr_settings.salary_payable_account,
                    type='credit',
                    amount=payroll.net_salary,
                    description=f'راتب مستحق لـ {payroll.employee.arabic_name}',
                    cost_center=payroll.employee.department.cost_center
                )
                
                payroll.journal_entry = journal_entry
            
            payroll.save()
            
            messages.success(request, 'تم اعتماد الراتب وإنشاء القيد المحاسبي بنجاح')
    
    return redirect('hr:payroll_detail', pk=pk)

# === تقييم الأداء ===
