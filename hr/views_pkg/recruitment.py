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

# التوظيف

# === التوظيف ===

@login_required
def recruitment_dashboard(request):
    """لوحة تحكم التوظيف"""
    context = {
        'open_vacancies': JobVacancy.objects.filter(status='open').count(),
        'total_applications': JobApplication.objects.count(),
        'pending_applications': JobApplication.objects.filter(status='submitted').count(),
        'recent_applications': JobApplication.objects.select_related('vacancy').order_by('-application_date')[:10]
    }
    return render(request, 'hr/recruitment_dashboard.html', context)

@login_required
def job_vacancy_list(request):
    """قائمة الوظائف الشاغرة"""
    vacancies = JobVacancy.objects.select_related('position').order_by('-posting_date')
    form = JobVacancyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'تم إنشاء وظيفة شاغرة')
        return redirect('hr:job_vacancy_list')
    context = {'vacancies': vacancies,'form': form}
    return render(request, 'hr/job_vacancy_list.html', context)

@login_required
def job_vacancy_create(request):
    """إنشاء وظيفة شاغرة"""
    if request.method == 'POST':
        try:
            # استقبال البيانات من النموذج
            position_id = request.POST.get('position')
            title = request.POST.get('title')
            description = request.POST.get('description')
            requirements = request.POST.get('requirements')
            number_of_positions = int(request.POST.get('number_of_positions', 1))
            salary_range_min = float(request.POST.get('salary_range_min', 0))
            salary_range_max = float(request.POST.get('salary_range_max', 0))
            posting_date = request.POST.get('posting_date')
            closing_date = request.POST.get('closing_date')
            status = request.POST.get('status', 'open')
            
            # التحقق من صحة البيانات
            if not all([position_id, title, description, requirements, posting_date, closing_date]):
                messages.error(request, 'يرجى ملء جميع الحقول المطلوبة')
                context = {'positions': JobPosition.objects.filter(is_active=True)}
                return render(request, 'hr/job_vacancy_form.html', context)
            
            # إنشاء الوظيفة الشاغرة
            position = JobPosition.objects.get(id=position_id)
            vacancy = JobVacancy.objects.create(
                position=position,
                title=title,
                description=description,
                requirements=requirements,
                number_of_positions=number_of_positions,
                salary_range_min=salary_range_min,
                salary_range_max=salary_range_max,
                posting_date=posting_date,
                closing_date=closing_date,
                status=status
            )
            
            messages.success(request, 'تم إنشاء الوظيفة الشاغرة بنجاح')
            return redirect('hr:job_vacancy_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء الوظيفة: {str(e)}')
    
    context = {'positions': JobPosition.objects.filter(is_active=True)}
    return render(request, 'hr/job_vacancy_form.html', context)

@login_required
def job_application_list(request):
    """قائمة طلبات التوظيف"""
    qs = JobApplication.objects.select_related('vacancy').order_by('-application_date')
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    form = JobApplicationQuickForm(request.POST or None, files=request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'تم إضافة طلب توظيف')
        return redirect('hr:job_application_list')
    context = {
        'applications': qs,
        'status_choices': JobApplication.STATUS_CHOICES,
        'form': form,
        'status_filter': status,
    }
    return render(request, 'hr/job_application_list.html', context)

@login_required
def job_application_detail(request, pk):
    """تفاصيل طلب التوظيف"""
    application = get_object_or_404(JobApplication, pk=pk)
    context = {'application': application}
    return render(request, 'hr/job_application_detail.html', context)

# === العلاقات العمالية ===
