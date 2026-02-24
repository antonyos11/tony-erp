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

# التدريب والتطوير

# === التدريب والتطوير ===

@login_required
def training_dashboard(request):
    """لوحة تحكم التدريب والتطوير"""
    import json
    from django.db.models import Count
    
    total_enrollments = TrainingEnrollment.objects.count()
    completed_enrollments = TrainingEnrollment.objects.filter(status='completed').count()
    completion_rate = round((completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0, 1)
    
    # Top trainees by enrollment count
    top_trainees = list(
        TrainingEnrollment.objects.values(
            'employee__first_name', 'employee__last_name', 'employee__job_title'
        ).annotate(course_count=Count('id')).order_by('-course_count')[:5]
    )
    
    # Monthly chart data (last 6 months)
    chart_labels = []
    chart_trainees = []
    chart_programs = []
    month_names = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                   'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
    today = date.today()
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        chart_labels.append(month_names[m - 1])
        chart_trainees.append(
            TrainingEnrollment.objects.filter(enrollment_date__year=y, enrollment_date__month=m).count()
        )
        chart_programs.append(
            TrainingProgram.objects.filter(start_date__year=y, start_date__month=m).count()
        )
    
    context = {
        'active_programs': TrainingProgram.objects.filter(
            start_date__lte=date.today(),
            end_date__gte=date.today()
        ).count(),
        'upcoming_programs': TrainingProgram.objects.filter(
            start_date__gt=date.today()
        ).count(),
        'total_enrollments': total_enrollments,
        'completion_rate': completion_rate,
        'top_trainees': top_trainees,
        'chart_labels': json.dumps(chart_labels),
        'chart_trainees': json.dumps(chart_trainees),
        'chart_programs': json.dumps(chart_programs),
        'recent_programs': TrainingProgram.objects.order_by('-start_date')[:5]
    }
    return render(request, 'hr/training_dashboard.html', context)

@login_required
def training_program_list(request):
    """قائمة البرامج التدريبية"""
    programs = TrainingProgram.objects.all().order_by('-start_date')
    form = TrainingProgramForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'تم إضافة برنامج تدريبي')
        return redirect('hr:training_program_list')
    context = {'programs': programs,'form': form}
    return render(request, 'hr/training_program_list.html', context)

@login_required
def training_program_create(request):
    """إنشاء برنامج تدريبي"""
    if request.method == 'POST':
        try:
            training_program = TrainingProgram.objects.create(
                title=request.POST['title'],
                description=request.POST['description'],
                provider=request.POST['provider'],
                start_date=request.POST['start_date'],
                end_date=request.POST['end_date'],
                duration_hours=int(request.POST['duration_hours']),
                location=request.POST['location'],
                cost=float(request.POST['cost']),
                max_participants=int(request.POST['max_participants']),
            )
            messages.success(request, 'تم إنشاء البرنامج التدريبي بنجاح')
            return redirect('hr:training_program_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ في إنشاء البرنامج: {str(e)}')
    
    return render(request, 'hr/training_program_form.html')

@login_required
def training_program_detail(request, pk):
    """تفاصيل البرنامج التدريبي"""
    program = get_object_or_404(TrainingProgram, pk=pk)
    enrollments = TrainingEnrollment.objects.filter(training_program=program).select_related('employee')
    
    context = {
        'program': program,
        'enrollments': enrollments,
    }
    return render(request, 'hr/training_program_detail.html', context)

@login_required
def training_enroll(request):
    """تسجيل في برنامج تدريبي"""
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(id=request.POST['employee'])
            training_program = TrainingProgram.objects.get(id=request.POST['training_program'])
            
            enrollment, created = TrainingEnrollment.objects.get_or_create(
                employee=employee,
                training_program=training_program,
                defaults={'status': 'enrolled'}
            )
            
            if created:
                messages.success(request, f'تم تسجيل {employee.arabic_name} في البرنامج التدريبي بنجاح')
            else:
                messages.warning(request, f'{employee.arabic_name} مسجل بالفعل في هذا البرنامج')
                
            return redirect('hr:training_program_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ في التسجيل: {str(e)}')
    
    context = {
        'programs': TrainingProgram.objects.filter(
            start_date__gt=date.today()
        ),
        'employees': Employee.objects.filter(status='active'),
    }
    return render(request, 'hr/training_enroll_form.html', context)

# === التوظيف ===
