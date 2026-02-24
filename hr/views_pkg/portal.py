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

# بوابة الموظفين - الخدمة الذاتية


# =====================
# بوابة الموظفين - الخدمة الذاتية
# =====================

@login_required
def employee_portal(request):
    """بوابة الخدمة الذاتية للموظفين"""
    try:
        employee = request.user.employee_profile
    except Exception as e:
        messages.error(request, 'لا يوجد ملف موظف مرتبط بحسابك. يرجى التواصل مع قسم الموارد البشرية لإنشاء ملف موظف.')
        return redirect('hr:dashboard')
    
    # إحصائيات الموظف
    from hr.hr_utils import calculate_employee_leave_balance
    
    # رصيد الإجازات
    leave_types = LeaveType.objects.all()
    leave_balances = []
    for leave_type in leave_types:
        balance = calculate_employee_leave_balance(employee, leave_type)
        leave_balances.append({
            'type': leave_type,
            'balance': balance
        })
    
    # طلبات الإجازة الأخيرة
    recent_leave_requests = LeaveRequest.objects.filter(
        employee=employee
    ).order_by('-created_at')[:5]
    
    # سجل الحضور الأخير
    recent_attendance = AttendanceRecord.objects.filter(
        employee=employee
    ).order_by('-date')[:10]
    
    # آخر راتب
    last_payroll = Payroll.objects.filter(
        employee=employee
    ).order_by('-period_start').first()
    
    # حالة الحضور اليوم
    today = date.today()
    today_checkin = AttendanceRecord.objects.filter(
        employee=employee, date=today, record_type='check_in'
    ).order_by('-time').first()
    today_checkout = AttendanceRecord.objects.filter(
        employee=employee, date=today, record_type='check_out'
    ).order_by('-time').first()
    
    # إضافة معلومات الحضور للموظف
    employee.checked_in_today = today_checkin is not None
    employee.checked_out_today = today_checkout is not None
    employee.check_in_time = today_checkin.time.strftime('%H:%M') if today_checkin else None
    employee.check_out_time = today_checkout.time.strftime('%H:%M') if today_checkout else None
    
    context = {
        'employee': employee,
        'leave_balances': leave_balances,
        'recent_leave_requests': recent_leave_requests,
        'recent_attendance': recent_attendance,
        'last_payroll': last_payroll,
        'today': today,
    }
    return render(request, 'hr/employee_portal.html', context)


@login_required
def employee_submit_leave_request(request):
    """تقديم طلب إجازة من قبل الموظف"""
    try:
        employee = request.user.employee_profile
    except:
        messages.error(request, 'لا يوجد ملف موظف مرتبط بحسابك')
        return redirect('hr:employee_portal')
    
    if request.method == 'POST':
        leave_type_id = request.POST.get('leave_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason', '')
        replacement_employee_id = request.POST.get('replacement_employee') or None
        
        # التحقق من البيانات
        if not all([leave_type_id, start_date, end_date]):
            messages.error(request, 'جميع الحقول مطلوبة')
            return redirect('hr:employee_submit_leave_request')
        
        try:
            leave_type = LeaveType.objects.get(id=leave_type_id)
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start_date > end_date:
                messages.error(request, 'تاريخ البداية يجب أن يكون قبل تاريخ النهاية')
                return redirect('hr:employee_submit_leave_request')
            
            # حساب عدد الأيام
            from .leave_utils import calculate_working_days
            days_requested = calculate_working_days(start_date, end_date)
            
            # فحص الرصيد
            from hr.hr_utils import calculate_employee_leave_balance
            balance = calculate_employee_leave_balance(employee, leave_type)
            
            if balance['remaining_days'] < days_requested:
                messages.error(request, f'رصيد الإجازات غير كافي. الرصيد المتبقي: {balance["remaining_days"]} يوم')
                return redirect('hr:employee_submit_leave_request')
            
            # إنشاء الطلب
            replacement_employee = None
            if replacement_employee_id:
                replacement_employee = Employee.objects.filter(id=replacement_employee_id).first()

            leave_request = LeaveRequest.objects.create(
                employee=employee,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                days_requested=days_requested,
                reason=reason,
                replacement_employee=replacement_employee,
                status='pending'
            )
            
            messages.success(request, 'تم تقديم طلب الإجازة بنجاح وبانتظار الموافقة')
            return redirect('hr:employee_portal')
        
        except LeaveType.DoesNotExist:
            messages.error(request, 'نوع الإجازة غير موجود')
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
        
        return redirect('hr:employee_submit_leave_request')
    
    # GET request
    leave_types = LeaveType.objects.all()
    possible_replacements = Employee.objects.filter(
        status='active',
        department=employee.department,
    ).exclude(id=employee.id).select_related('department')
    context = {
        'employee': employee,
        'leave_types': leave_types,
        'possible_replacements': possible_replacements,
    }
    return render(request, 'hr/employee_submit_leave.html', context)


@login_required
def leave_approval_dashboard(request):
    """لوحة تحكم الموافقة على الإجازات للمدراء"""
    # فحص صلاحيات المستخدم
    if not request.user.is_staff:
        messages.error(request, 'ليس لديك صلاحية الوصول لهذه الصفحة')
        return redirect('hr:hr_dashboard')
    
    # طلبات الإجازة المعلقة
    pending_requests = LeaveRequest.objects.filter(
        status='pending'
    ).select_related('employee', 'leave_type').order_by('start_date')
    
    # إحصائيات
    total_pending = pending_requests.count()
    approved_today = LeaveRequest.objects.filter(
        status='approved',
        approved_at__date=date.today()
    ).count()
    rejected_today = LeaveRequest.objects.filter(
        status='rejected',
        approved_at__date=date.today()
    ).count()
    
    context = {
        'pending_requests': pending_requests,
        'total_pending': total_pending,
        'approved_today': approved_today,
        'rejected_today': rejected_today,
    }
    return render(request, 'hr/leave_approval_dashboard.html', context)


@login_required
@transaction.atomic
def approve_leave_request(request, request_id):
    """الموافقة على طلب إجازة"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'ليس لديك صلاحية'}, status=403)
    
    leave_request = get_object_or_404(LeaveRequest, id=request_id)
    
    if leave_request.status != 'pending':
        return JsonResponse({'success': False, 'message': 'الطلب تمت معالجته مسبقاً'}, status=400)
    
    # الموافقة
    leave_request.status = 'approved'
    leave_request.approved_by = request.user
    leave_request.approved_at = timezone.now()
    leave_request.save()
    
    messages.success(request, f'تمت الموافقة على إجازة {leave_request.employee}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('hr:leave_approval_dashboard')


@login_required
@transaction.atomic
def reject_leave_request(request, request_id):
    """رفض طلب إجازة"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'ليس لديك صلاحية'}, status=403)
    
    leave_request = get_object_or_404(LeaveRequest, id=request_id)
    
    if leave_request.status != 'pending':
        return JsonResponse({'success': False, 'message': 'الطلب تمت معالجته مسبقاً'}, status=400)
    
    rejection_reason = request.POST.get('rejection_reason', 'لم يتم تحديد سبب')
    
    # الرفض
    leave_request.status = 'rejected'
    leave_request.approved_by = request.user
    leave_request.approved_at = timezone.now()
    leave_request.rejection_reason = rejection_reason
    leave_request.save()
    
    # معالجة الغياب إذا كان الموظف قد غاب بالفعل
    if leave_request.start_date <= date.today():
        from hr.hr_utils import process_unauthorized_absence
        from datetime import timedelta
        
        current_date = leave_request.start_date
        while current_date <= min(leave_request.end_date, date.today()):
            process_unauthorized_absence(leave_request.employee, current_date, 'leave_exhausted')
            current_date += timedelta(days=1)
    
    messages.warning(request, f'تم رفض إجازة {leave_request.employee}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('hr:leave_approval_dashboard')


# =====================
# بطاقات الهوية
# =====================
