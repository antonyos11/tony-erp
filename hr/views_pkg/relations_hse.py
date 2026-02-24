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

# العلاقات العمالية والسلامة المهنية

# === العلاقات العمالية ===

@login_required
def relations_dashboard(request):
    """لوحة العلاقات العمالية - عرض مختصر للشكاوى والمخالفات"""
    # إحصائيات حقيقية من الجداول
    from hr.models import Complaint, DisciplinaryAction
    context = {
        'complaints_count': Complaint.objects.count(),
        'disciplinary_count': DisciplinaryAction.objects.count(),
    }
    return render(request, 'hr/relations_dashboard.html', context)

@login_required
def complaint_list(request):
    """قائمة الشكاوى والملاحظات مع إنشاء وفلاتر بسيطة"""
    from hr.models import Complaint
    qs = Complaint.objects.select_related('employee')
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    form = ComplaintForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'تم حفظ الشكوى')
        return redirect('hr:complaint_list')
    context = { 'complaints': qs, 'form': form, 'status_filter': status }
    return render(request, 'hr/complaint_list.html', context)

@login_required
def disciplinary_list(request):
    """قائمة المخالفات والجزاءات مع إنشاء وفلاتر"""
    from hr.models import DisciplinaryAction
    qs = DisciplinaryAction.objects.select_related('employee')
    action_type = request.GET.get('type')
    if action_type:
        qs = qs.filter(action_type=action_type)
    form = DisciplinaryActionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'تم تسجيل الجزاء')
        return redirect('hr:disciplinary_list')
    context = { 'records': qs, 'form': form, 'type_filter': action_type }
    return render(request, 'hr/disciplinary_list.html', context)

# === السلامة والصحة المهنية HSE ===

@login_required
def hse_dashboard(request):
    """لوحة HSE"""
    context = {
        'incidents': 0,
        'inspections': 0,
        'safety_trainings': 0,
    }
    return render(request, 'hr/hse_dashboard.html', context)

@login_required
def hse_incident_list(request):
    """قائمة الحوادث والإصابات مع إنشاء وفلاتر"""
    from hr.models import HSEIncident
    incidents = HSEIncident.objects.select_related('employee','department')
    status = request.GET.get('status')
    if status:
        incidents = incidents.filter(status=status)
    form = HSEIncidentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'تم تسجيل الحادث')
        return redirect('hr:hse_incident_list')
    context = {'incidents': incidents, 'form': form, 'status_filter': status}
    return render(request, 'hr/hse_incident_list.html', context)

@login_required
def hse_inspection_list(request):
    """قائمة التفتيشات مع إنشاء"""
    from hr.models import HSEInspection
    inspections = HSEInspection.objects.all()
    form = HSEInspectionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'تم تسجيل التفتيش')
        return redirect('hr:hse_inspection_list')
    context = {'inspections': inspections,'form': form}
    return render(request, 'hr/hse_inspection_list.html', context)

@login_required
def hse_training_list(request):
    """تدريبات السلامة مع إنشاء"""
    from hr.models import HSETraining
    trainings = HSETraining.objects.prefetch_related('participants').all()
    form = HSETrainingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request,'تم تسجيل التدريب')
        return redirect('hr:hse_training_list')
    context = {'trainings': trainings,'form': form}
    return render(request, 'hr/hse_training_list.html', context)

# === السياسات واللوائح ===

@login_required
def policies(request):
    """صفحة سياسات ولوائح الموارد البشرية - قابلة للطباعة"""
    return render(request, 'hr/policies.html')

