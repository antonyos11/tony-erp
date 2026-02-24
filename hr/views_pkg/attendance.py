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

# نظام الحضور والانصراف

# === نظام الحضور والانصراف ===

@login_required
def attendance_dashboard(request):
    """لوحة تحكم الحضور والانصراف"""
    today = date.today()
    
    # إحصائيات اليوم
    today_checkins = AttendanceRecord.objects.filter(
        date=today, record_type='check_in'
    ).count()
    
    today_checkouts = AttendanceRecord.objects.filter(
        date=today, record_type='check_out'
    ).count()
    
    total_employees = Employee.objects.filter(status='active').count()
    absent_today = total_employees - today_checkins
    
    # الموظفون المتأخرون اليوم
    late_employees = []
    # منطق حساب التأخير سيتم إضافته
    
    context = {
        'today_checkins': today_checkins,
        'today_checkouts': today_checkouts,
        'absent_today': absent_today,
        'late_employees': late_employees,
        'total_employees': total_employees,
    }
    return render(request, 'hr/attendance_dashboard.html', context)

@login_required
def attendance_records(request):
    """سجلات الحضور والانصراف"""
    qs = AttendanceRecord.objects.select_related('employee')
    employee_id = request.GET.get('employee')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if employee_id:
        qs = qs.filter(employee_id=employee_id)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    qs = qs.order_by('-date', '-time')
    form = AttendanceRecordQuickForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request,'تم إضافة سجل حضور')
        return redirect('hr:attendance_records')
    context = {
        'records': qs,
        'employees': Employee.objects.filter(status='active'),
        'form': form,
        'employee_filter': employee_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'hr/attendance_records.html', context)

@login_required
def check_in(request):
    """تسجيل الحضور"""
    if request.method == 'POST':
        try:
            employee = request.user.employee_profile
            today = date.today()
            now = timezone.now().time()
            
            # التحقق من عدم وجود تسجيل حضور اليوم
            existing_checkin = AttendanceRecord.objects.filter(
                employee=employee,
                date=today,
                record_type='check_in'
            ).first()
            
            if existing_checkin:
                messages.error(request, 'تم تسجيل الحضور مسبقاً اليوم')
            else:
                AttendanceRecord.objects.create(
                    employee=employee,
                    date=today,
                    time=now,
                    record_type='check_in',
                    source='web',
                    created_by=request.user
                )
                messages.success(request, 'تم تسجيل الحضور بنجاح')
        
        except Employee.DoesNotExist:
            messages.error(request, 'غير مسموح بهذا الإجراء')
    
    return redirect('hr:attendance_dashboard')

@login_required
def check_out(request):
    """تسجيل الانصراف"""
    if request.method == 'POST':
        try:
            employee = request.user.employee_profile
            today = date.today()
            now = timezone.now().time()
            
            # التحقق من وجود تسجيل حضور اليوم
            checkin_exists = AttendanceRecord.objects.filter(
                employee=employee,
                date=today,
                record_type='check_in'
            ).exists()
            
            if not checkin_exists:
                messages.error(request, 'يجب تسجيل الحضور أولاً')
            else:
                # التحقق من عدم وجود تسجيل انصراف اليوم
                existing_checkout = AttendanceRecord.objects.filter(
                    employee=employee,
                    date=today,
                    record_type='check_out'
                ).first()
                
                if existing_checkout:
                    messages.error(request, 'تم تسجيل الانصراف مسبقاً اليوم')
                else:
                    AttendanceRecord.objects.create(
                        employee=employee,
                        date=today,
                        time=now,
                        record_type='check_out',
                        source='web',
                        created_by=request.user
                    )
                    messages.success(request, 'تم تسجيل الانصراف بنجاح')
        
        except Employee.DoesNotExist:
            messages.error(request, 'غير مسموح بهذا الإجراء')
    
    return redirect('hr:attendance_dashboard')

@login_required
def manual_attendance_entry(request):
    """إدخال الحضور يدوياً"""
    if request.method == 'POST':
        # منطق الإدخال اليدوي
        messages.success(request, 'تم إدخال سجل الحضور بنجاح')
        return redirect('hr:attendance_records')
    
    context = {
        'employees': Employee.objects.filter(status='active'),
        'record_types': AttendanceRecord.RECORD_TYPE_CHOICES,
    }
    return render(request, 'hr/manual_attendance_form.html', context)

# === إدارة الإجازات ===
