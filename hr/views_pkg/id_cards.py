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

# بطاقات الهوية ومسح QR


# =====================
# بطاقات الهوية
# =====================

@login_required
def employee_id_cards_list(request):
    """قائمة بطاقات هوية الموظفين"""
    from hr.models import EmployeeIDCard
    from django.db.models import Q
    
    cards = EmployeeIDCard.objects.select_related(
        'employee__position',
        'employee__department'
    ).order_by('-issue_date')
    
    today = date.today()
    
    # إحصائيات
    total_cards = cards.count()
    active_cards = cards.filter(status='active', expiry_date__gte=today).count()
    expired_cards = cards.filter(Q(status='expired') | Q(status='revoked') | Q(expiry_date__lt=today)).count()
    expiring_soon = cards.filter(
        status='active',
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=30)
    ).count()
    
    # فلترة حسب الحالة
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        cards = cards.filter(status='active', expiry_date__gte=today)
    elif status_filter == 'expired':
        cards = cards.filter(Q(status='inactive') | Q(status='expired') | Q(expiry_date__lt=today))
    elif status_filter == 'expiring':
        cards = cards.filter(status='active', expiry_date__gte=today, expiry_date__lte=today + timedelta(days=30))
    
    # بحث
    search = request.GET.get('search')
    if search:
        cards = cards.filter(
            Q(employee__first_name__icontains=search) |
            Q(employee__last_name__icontains=search) |
            Q(card_number__icontains=search)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(cards, 12)  # 12 بطاقة لكل صفحة
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    context = {
        'cards': page_obj,
        'object_list': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'is_paginated': paginator.num_pages > 1,
        'today': today,
        # إحصائيات
        'total_cards': total_cards,
        'active_cards': active_cards,
        'expired_cards': expired_cards,
        'expiring_soon': expiring_soon,
    }
    return render(request, 'hr/employee_id_cards_list.html', context)


@login_required
@transaction.atomic
def generate_employee_id_card(request, employee_id):
    """إنشاء بطاقة هوية جديدة للموظف"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    from hr.hr_utils import create_employee_id_card
    
    try:
        card = create_employee_id_card(employee, expiry_months=12)
        messages.success(request, f'تم إنشاء بطاقة هوية جديدة للموظف {employee}')
        
        # إعادة التوجيه لصفحة طباعة البطاقة
        return redirect('hr:print_employee_id_card', card_id=card.id)
    
    except Exception as e:
        messages.error(request, f'حدث خطأ: {str(e)}')
        return redirect('hr:employee_detail', employee_id=employee_id)


@login_required
def print_employee_id_card(request, card_id):
    """طباعة بطاقة هوية موظف"""
    from hr.models import EmployeeIDCard
    
    card = get_object_or_404(EmployeeIDCard, id=card_id)
    
    # زيادة عداد الطباعة
    if request.method == 'POST':
        card.increment_print_count()
        card.printed_by = request.user
        card.save()
        
        messages.success(request, 'تمت الطباعة بنجاح')
    
    # الحصول على شعار الشركة
    company_logo = None
    try:
        hr_settings = HRSettings.objects.first()
        company_name = hr_settings.company_name if hr_settings else 'شركتنا'
    except:
        company_name = 'شركتنا'
    
    context = {
        'card': card,
        'employee': card.employee,
        'company_name': company_name,
        'company_logo': company_logo,
    }
    return render(request, 'hr/id_card_print.html', context)


@login_required
def qr_login_scanner(request):
    """صفحة مسح QR Code للدخول"""
    if request.method == 'POST':
        token = request.POST.get('token')
        
        if not token:
            return JsonResponse({'success': False, 'message': 'QR Code فارغ'}, status=400)
        
        from hr.hr_utils import verify_qr_login_token
        from django.contrib.auth import login
        
        success, result = verify_qr_login_token(token)
        
        if success:
            # تسجيل الدخول
            login(request, result)
            
            # تحديث عداد المسح
            try:
                from hr.models import EmployeeIDCard
                card = EmployeeIDCard.objects.filter(
                    qr_code_data=token,
                    status='active'
                ).first()
                
                if card:
                    card.increment_scan_count()
            except:
                pass
            
            return JsonResponse({
                'success': True,
                'message': f'مرحباً {result.username}',
                'redirect_url': '/hr/employee-portal/'
            })
        else:
            return JsonResponse({'success': False, 'message': result}, status=400)
    
    return render(request, 'hr/qr_login_scanner.html')


@csrf_exempt
@require_POST
def qr_attendance_action(request):
    """تسجيل حضور/انصراف وعرض بيانات الموظف عبر QR/Barcode"""
    # قراءة البيانات سواء جاءت كـ form-data أو JSON
    body_data = {}
    if request.content_type and 'application/json' in request.content_type:
        try:
            body_data = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            body_data = {}

    token = request.POST.get('token') or body_data.get('token')

    # دعم تمرير رقم البطاقة/الباركود وتحويله إلى token فعلي
    if token and len(str(token)) < 50:
        try:
            from hr.models import EmployeeIDCard, Employee
            card_lookup = EmployeeIDCard.objects.filter(
                Q(id__iexact=str(token)) | Q(card_number__iexact=str(token))
            ).exclude(status='revoked').first()

            # لو أدخل رقم الموظف، نجلب أحدث بطاقة نشطة له
            if not card_lookup:
                emp = Employee.objects.filter(employee_id__iexact=str(token)).first()
                if emp:
                    card_lookup = EmployeeIDCard.objects.filter(employee=emp, status='active').order_by('-issue_date').first()

            if card_lookup and card_lookup.qr_code_data:
                token = card_lookup.qr_code_data
        except Exception:
            pass
    action = (request.POST.get('action') or body_data.get('action') or 'status').lower()

    if not token:
        return JsonResponse({'success': False, 'message': 'QR/Barcode مفقود'}, status=400)

    from hr.hr_utils import verify_qr_login_token, calculate_employee_leave_balance
    from hr.models import EmployeeIDCard
    from django.contrib.auth import login

    user = None
    employee = None
    
    # أولاً: محاولة التحقق من JWT token
    success, result = verify_qr_login_token(token)
    if success:
        user = result
        employee = getattr(user, 'employee_profile', None)
    else:
        # ثانياً: البحث بواسطة رقم البطاقة أو qr_code_data
        card = EmployeeIDCard.objects.filter(
            status='active'
        ).filter(
            Q(card_number__iexact=token) |
            Q(qr_code_data=token) |
            Q(card_number__icontains=token)
        ).select_related('employee', 'employee__user').first()
        
        if card and card.employee:
            employee = card.employee
            user = employee.user
            # تحديث عداد المسح
            card.increment_scan_count()
    
    if not user or not employee:
        return JsonResponse({'success': False, 'message': 'البطاقة غير صالحة أو منتهية الصلاحية'}, status=400)

    # تسجيل الدخول بالجلسة الحالية لفتح البوابة فوراً
    login(request, user)

    today = date.today()
    now_time = timezone.now().time()

    checkin_record = AttendanceRecord.objects.filter(
        employee=employee, date=today, record_type='check_in'
    ).order_by('-time').first()
    checkout_record = AttendanceRecord.objects.filter(
        employee=employee, date=today, record_type='check_out'
    ).order_by('-time').first()

    attendance_data = {
        'today_check_in': checkin_record.time.strftime('%H:%M') if checkin_record else None,
        'today_check_out': checkout_record.time.strftime('%H:%M') if checkout_record else None,
    }

    action_performed = None
    message = 'تم التحقق من QR'

    def _create_record(record_type):
        rec = AttendanceRecord.objects.create(
            employee=employee,
            date=today,
            time=now_time,
            record_type=record_type,
            source='qr',
            created_by=user if user.is_authenticated else None,
        )
        return rec

    if action == 'auto':
        if not attendance_data['today_check_in']:
            rec = _create_record('check_in')
            attendance_data['today_check_in'] = rec.time.strftime('%H:%M')
            action_performed = 'check_in'
            message = 'تم تسجيل الحضور تلقائياً عبر QR'
        elif not attendance_data['today_check_out']:
            rec = _create_record('check_out')
            attendance_data['today_check_out'] = rec.time.strftime('%H:%M')
            action_performed = 'check_out'
            message = 'تم تسجيل الانصراف تلقائياً عبر QR'
        else:
            message = 'تم تسجيل الحضور والانصراف مسبقاً اليوم'

    elif action == 'check_in':
        if attendance_data['today_check_in']:
            message = 'تم تسجيل الحضور مسبقاً اليوم'
        else:
            rec = _create_record('check_in')
            attendance_data['today_check_in'] = rec.time.strftime('%H:%M')
            action_performed = 'check_in'
            message = 'تم تسجيل الحضور عبر QR'

    elif action == 'check_out':
        if not attendance_data['today_check_in']:
            return JsonResponse({'success': False, 'message': 'يجب تسجيل الحضور أولاً'}, status=400)
        if attendance_data['today_check_out']:
            message = 'تم تسجيل الانصراف مسبقاً اليوم'
        else:
            rec = _create_record('check_out')
            attendance_data['today_check_out'] = rec.time.strftime('%H:%M')
            action_performed = 'check_out'
            message = 'تم تسجيل الانصراف عبر QR'

    # تجميع أرصدة الإجازات
    leave_balances = []
    for leave_type in LeaveType.objects.all():
        balance = calculate_employee_leave_balance(employee, leave_type)
        leave_balances.append({
            'type': leave_type.name,
            'remaining_days': balance.get('remaining_days', 0),
            'used_days': balance.get('used_days', 0),
            'total_days': balance.get('total_days', 0),
        })

    # آخر راتب
    last_payroll = Payroll.objects.filter(employee=employee).order_by('-period_start').first()
    payroll_info = None
    if last_payroll:
        payroll_info = {
            'id': last_payroll.id,
            'period_start': last_payroll.period_start.isoformat(),
            'period_end': last_payroll.period_end.isoformat(),
            'net_salary': str(last_payroll.net_salary),
            'status': last_payroll.status,
        }

    response = {
        'success': True,
        'message': message,
        'action': action,
        'action_performed': action_performed,
        'employee': {
            'id': employee.id,
            'employee_id': employee.employee_id,
            'name': employee.arabic_name or f"{employee.first_name} {employee.last_name}",
            'department': employee.department.name if employee.department else None,
            'position': employee.position.title if employee.position else None,
        },
        'attendance': attendance_data,
        'leave_balances': leave_balances,
        'last_payroll': payroll_info,
        'redirect_url': reverse('hr:employee_portal'),
        'portal_links': {
            'payroll': reverse('hr:payroll_employee', args=[employee.id]),
            'leaves': reverse('hr:leave_employee', args=[employee.id]),
            'attendance': reverse('hr:attendance_employee', args=[employee.id]),
        }
    }

    return JsonResponse(response)


# ============================================================================
# Auto Payroll Calculator Views
# ============================================================================
