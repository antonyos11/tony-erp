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

# API للأجهزة الخارجية

# === API للأجهزة الخارجية ===

def require_device_token(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        expected = os.getenv('FINGERPRINT_TOKEN', '')
        provided = request.headers.get('X-Device-Token', '')
        if expected and provided == expected:
            return view_func(request, *args, **kwargs)
        return JsonResponse({'status': 'error', 'message': 'غير مصرح للجهاز'}, status=401)
    return _wrapped

@require_device_token
def api_check_in(request):
    """API تسجيل الحضور للأجهزة الخارجية"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fingerprint_id = data.get('fingerprint_id')
            device_info = data.get('device_info', '')
            
            employee = Employee.objects.get(fingerprint_id=fingerprint_id)
            today = date.today()
            now = timezone.now().time()
            
            # التحقق من عدم وجود تسجيل حضور اليوم
            existing_checkin = AttendanceRecord.objects.filter(
                employee=employee,
                date=today,
                record_type='check_in'
            ).first()
            
            if not existing_checkin:
                AttendanceRecord.objects.create(
                    employee=employee,
                    date=today,
                    time=now,
                    record_type='check_in',
                    source='fingerprint',
                    device_info=device_info
                )
                return JsonResponse({'status': 'success', 'message': 'تم تسجيل الحضور'})
            else:
                return JsonResponse({'status': 'error', 'message': 'تم تسجيل الحضور مسبقاً'})
                
        except Employee.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'موظف غير موجود'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'طريقة غير مسموحة'})

@require_device_token
def api_check_out(request):
    """API تسجيل الانصراف للأجهزة الخارجية"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fingerprint_id = data.get('fingerprint_id')
            device_info = data.get('device_info', '')
            
            employee = Employee.objects.get(fingerprint_id=fingerprint_id)
            today = date.today()
            now = timezone.now().time()
            
            # التحقق من وجود تسجيل حضور اليوم
            checkin_exists = AttendanceRecord.objects.filter(
                employee=employee,
                date=today,
                record_type='check_in'
            ).exists()
            
            if checkin_exists:
                existing_checkout = AttendanceRecord.objects.filter(
                    employee=employee,
                    date=today,
                    record_type='check_out'
                ).first()
                
                if not existing_checkout:
                    AttendanceRecord.objects.create(
                        employee=employee,
                        date=today,
                        time=now,
                        record_type='check_out',
                        source='fingerprint',
                        device_info=device_info
                    )
                    return JsonResponse({'status': 'success', 'message': 'تم تسجيل الانصراف'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'تم تسجيل الانصراف مسبقاً'})
            else:
                return JsonResponse({'status': 'error', 'message': 'لم يتم تسجيل الحضور اليوم'})
                
        except Employee.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'موظف غير موجود'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'طريقة غير مسموحة'})

def api_employee_lookup(request):
    """API للبحث عن الموظف"""
    if request.method == 'GET':
        fingerprint_id = request.GET.get('fingerprint_id')
        rfid_card = request.GET.get('rfid_card')
        
        try:
            employee = None
            if fingerprint_id:
                employee = Employee.objects.get(fingerprint_id=fingerprint_id)
            elif rfid_card:
                employee = Employee.objects.get(rfid_card_number=rfid_card)
            
            if employee:
                return JsonResponse({
                    'status': 'success',
                    'employee': {
                        'id': employee.employee_id,
                        'name': employee.arabic_name,
                        'department': employee.department.name,
                        'status': employee.status
                    }
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'موظف غير موجود'})
                
        except Employee.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'موظف غير موجود'})
    
    return JsonResponse({'status': 'error', 'message': 'طريقة غير مسموحة'})

# === views إضافية للموظفين ===

@login_required
def attendance_employee(request, employee_id):
    """سجل حضور موظف محدد"""
    employee = get_object_or_404(Employee, pk=employee_id)
    attendance_records = AttendanceRecord.objects.filter(employee=employee).order_by('-date')[:30]
    
    context = {
        'employee': employee,
        'attendance_records': attendance_records,
    }
    return render(request, 'hr/attendance_employee.html', context)

@login_required  
def leave_employee(request, employee_id):
    """إجازات موظف محدد"""
    employee = get_object_or_404(Employee, pk=employee_id)
    leave_requests = LeaveRequest.objects.filter(employee=employee).order_by('-created_at')
    
    context = {
        'employee': employee,
        'leave_requests': leave_requests,
    }
    return render(request, 'hr/leave_employee.html', context)

@login_required
def payroll_employee(request, employee_id):
    """رواتب موظف محدد"""
    employee = get_object_or_404(Employee, pk=employee_id)
    payrolls = Payroll.objects.filter(employee=employee).order_by('-period_start')[:12]
    
    context = {
        'employee': employee,
        'payrolls': payrolls,
    }
    return render(request, 'hr/payroll_employee.html', context)


# =====================
