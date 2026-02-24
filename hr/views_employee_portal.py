# -*- coding: utf-8 -*-
"""
بوابة الموظف - Employee Self-Service Portal
صفحة خاصة للعمال والموظفين لإدارة شؤونهم اليومية
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import json

from .models import (
    Employee, LeaveRequest, LeaveType, AttendanceRecord,
    PerformanceReview, PerformanceTarget, TargetProgress
)
from production.models import WorkerProductionEntry, ProductionWorkCenter
from inventory.models import Product


def get_employee_for_user(user):
    """الحصول على ملف الموظف للمستخدم الحالي"""
    try:
        return Employee.objects.select_related('department', 'position').get(user=user)
    except Employee.DoesNotExist:
        return None


def get_greeting_message(employee):
    """رسالة ترحيبية حسب الوقت والتخصص"""
    hour = timezone.now().hour
    
    if hour < 12:
        time_greeting = "صباح الخير"
    elif hour < 17:
        time_greeting = "مساء الخير"
    else:
        time_greeting = "مساء النور"
    
    # تحديد نوع العمل
    position_title = employee.position.title if employee.position else ""
    department_name = employee.department.name if employee.department else ""
    
    # رسائل مخصصة حسب التخصص
    job_messages = {
        'ماكينة': f"جاهز لوردية إنتاج رائعة اليوم! 🏭",
        'مشرف': f"فريقك بانتظارك لقيادة يوم ناجح! 👔",
        'مندوب': f"موسم مبيعات موفق اليوم! 💼",
        'محاسب': f"أرقام دقيقة ليوم ناجح! 📊",
        'مخزن': f"المخزون بانتظارك! 📦",
        'سائق': f"رحلة آمنة وموفقة! 🚚",
    }
    
    job_message = "نتمنى لك يوماً إنتاجياً ممتازاً! ⭐"
    for key, msg in job_messages.items():
        if key in position_title or key in department_name:
            job_message = msg
            break
    
    return {
        'time_greeting': time_greeting,
        'job_message': job_message,
        'full_greeting': f"{time_greeting} يا {employee.first_name}! {job_message}"
    }


def calculate_performance_metrics(employee):
    """حساب مؤشرات الأداء للموظف"""
    today = date.today()
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # إنتاجية هذا الشهر
    production_this_month = WorkerProductionEntry.objects.filter(
        employee=employee,
        date__gte=month_start,
        status='approved'
    ).aggregate(
        total_qty=Sum('quantity'),
        total_hours=Sum('hours_worked'),
        entry_count=Count('id')
    )
    
    # إنتاجية الشهر الماضي للمقارنة
    production_last_month = WorkerProductionEntry.objects.filter(
        employee=employee,
        date__gte=last_month_start,
        date__lt=month_start,
        status='approved'
    ).aggregate(
        total_qty=Sum('quantity')
    )
    
    # حساب نسبة التغير
    this_month_qty = production_this_month['total_qty'] or Decimal('0')
    last_month_qty = production_last_month['total_qty'] or Decimal('0')
    
    if last_month_qty > 0:
        change_percent = ((this_month_qty - last_month_qty) / last_month_qty) * 100
    else:
        change_percent = 100 if this_month_qty > 0 else 0
    
    # الحضور هذا الشهر
    attendance_this_month = AttendanceRecord.objects.filter(
        employee=employee,
        date__gte=month_start,
        record_type='check_in'
    ).count()
    
    # أيام العمل المتوقعة (22 يوم تقريباً)
    working_days_expected = 22
    attendance_rate = (attendance_this_month / working_days_expected) * 100 if working_days_expected > 0 else 0
    attendance_rate = min(attendance_rate, 100)  # الحد الأقصى 100%
    
    # الإجازات المستخدمة
    leaves_used = LeaveRequest.objects.filter(
        employee=employee,
        status='approved',
        start_date__year=today.year
    ).aggregate(total_days=Sum('days_requested'))['total_days'] or 0
    
    # رصيد الإجازات (افتراضي 21 يوم)
    total_leave_balance = 21
    leaves_remaining = max(0, total_leave_balance - leaves_used)
    
    # تقييم الأداء العام (مقياس من 5)
    # حسب معادلة: الحضور * 0.3 + الإنتاجية * 0.5 + عدم الإجازات * 0.2
    attendance_score = min(attendance_rate, 100) / 20  # Max 5
    production_score = min(float(this_month_qty) / 100, 5) if this_month_qty else 2.5  # تقدير
    leave_score = 5 - (leaves_used / 5)  # كلما قلت الإجازات ارتفعت النقطة
    
    overall_score = (attendance_score * 0.3) + (production_score * 0.5) + (max(leave_score, 0) * 0.2)
    overall_score = min(max(overall_score, 0), 5)  # بين 0 و 5
    
    return {
        'production': {
            'this_month': this_month_qty,
            'last_month': last_month_qty,
            'change_percent': round(change_percent, 1),
            'hours_worked': production_this_month['total_hours'] or 0,
            'entries_count': production_this_month['entry_count'] or 0,
            'is_positive': change_percent >= 0,
        },
        'attendance': {
            'days_present': attendance_this_month,
            'rate': round(attendance_rate, 1),
            'expected_days': working_days_expected,
        },
        'leaves': {
            'used': leaves_used,
            'remaining': leaves_remaining,
            'total': total_leave_balance,
        },
        'overall_score': round(overall_score, 1),
        'score_label': get_score_label(overall_score),
        'score_color': get_score_color(overall_score),
    }


def get_score_label(score):
    """تصنيف الدرجة"""
    if score >= 4.5:
        return "ممتاز"
    elif score >= 3.5:
        return "جيد جداً"
    elif score >= 2.5:
        return "جيد"
    elif score >= 1.5:
        return "مقبول"
    else:
        return "يحتاج تحسين"


def get_score_color(score):
    """لون الدرجة"""
    if score >= 4.5:
        return "success"
    elif score >= 3.5:
        return "info"
    elif score >= 2.5:
        return "primary"
    elif score >= 1.5:
        return "warning"
    else:
        return "danger"


@login_required
def employee_portal(request):
    """الصفحة الرئيسية لبوابة الموظف"""
    employee = get_employee_for_user(request.user)
    
    if not employee:
        messages.error(request, "لم يتم العثور على ملف موظف مرتبط بحسابك. يرجى التواصل مع الإدارة.")
        return redirect('core:dashboard')
    
    # الترحيب
    greeting = get_greeting_message(employee)
    
    # مؤشرات الأداء
    metrics = calculate_performance_metrics(employee)
    
    # أنواع الإجازات المتاحة
    leave_types = LeaveType.objects.all()
    
    # طلبات الإجازة الأخيرة
    recent_leaves = LeaveRequest.objects.filter(
        employee=employee
    ).order_by('-created_at')[:5]
    
    # إنتاجية آخر 7 أيام
    last_7_days = date.today() - timedelta(days=7)
    recent_production = WorkerProductionEntry.objects.filter(
        employee=employee,
        date__gte=last_7_days
    ).order_by('-date')[:10]
    
    # مراكز العمل والمنتجات للإنتاجية
    work_centers = ProductionWorkCenter.objects.filter(is_active=True)
    products = Product.objects.all()[:100]  # أول 100 منتج
    
    context = {
        'employee': employee,
        'greeting': greeting,
        'metrics': metrics,
        'leave_types': leave_types,
        'recent_leaves': recent_leaves,
        'recent_production': recent_production,
        'work_centers': work_centers,
        'products': products,
        'today': date.today(),
    }
    
    return render(request, 'hr/employee_portal.html', context)


def _get_today_attendance(employee):
    """جلب حالة الحضور اليومية للموظف"""
    today = date.today()
    records = AttendanceRecord.objects.filter(employee=employee, date=today).order_by('-time')
    checked_in = records.filter(record_type='check_in').exists()
    checked_out = records.filter(record_type='check_out').exists()
    last_record = records.first()
    return {
        'today': today,
        'records': records,
        'checked_in': checked_in,
        'checked_out': checked_out,
        'last_record': last_record,
    }


@login_required
def employee_welcome(request):
    """صفحة ترحيب الموظف قبل الدخول للنظام"""
    employee = get_employee_for_user(request.user)
    if not employee:
        messages.error(request, "لم يتم العثور على ملف موظف مرتبط بحسابك. يرجى التواصل مع الإدارة.")
        return redirect('core:dashboard')

    if employee.attendance_exempt:
        return redirect('core:dashboard')

    attendance_info = _get_today_attendance(employee)

    # رصيد الإجازات
    from .hr_utils import calculate_employee_leave_balance
    leave_balances = []
    for leave_type in LeaveType.objects.all():
        balance = calculate_employee_leave_balance(employee, leave_type)
        leave_balances.append({
            'type': leave_type,
            'balance': balance
        })

    # الأهداف النشطة
    today = date.today()
    targets = PerformanceTarget.objects.filter(
        employee=employee,
        status__in=['active', 'completed'],
        start_date__lte=today,
        end_date__gte=today
    ).order_by('priority', '-start_date')

    context = {
        'employee': employee,
        'today': attendance_info['today'],
        'checked_in': attendance_info['checked_in'],
        'checked_out': attendance_info['checked_out'],
        'last_record': attendance_info['last_record'],
        'leave_balances': leave_balances,
        'leave_types': LeaveType.objects.all(),
        'targets': targets,
        'current_time': timezone.now(),
    }

    return render(request, 'hr/employee_welcome.html', context)


@login_required
def register_attendance(request):
    """تسجيل حضور/انصراف للموظف"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

    employee = get_employee_for_user(request.user)
    if not employee:
        return JsonResponse({'success': False, 'message': 'لا يوجد ملف موظف'}, status=400)

    if employee.attendance_exempt:
        return JsonResponse({'success': False, 'message': 'الموظف مستثنى من إلزام الحضور'}, status=400)

    record_type = request.POST.get('type', 'check_in')
    if record_type not in ['check_in', 'check_out']:
        return JsonResponse({'success': False, 'message': 'نوع غير صالح'}, status=400)

    today = date.today()
    now = timezone.now()

    existing_check_in = AttendanceRecord.objects.filter(
        employee=employee, date=today, record_type='check_in'
    ).first()
    existing_check_out = AttendanceRecord.objects.filter(
        employee=employee, date=today, record_type='check_out'
    ).first()

    if record_type == 'check_in' and existing_check_in:
        return JsonResponse({'success': False, 'message': 'تم تسجيل الحضور مسبقاً اليوم'}, status=400)

    if record_type == 'check_out':
        if not existing_check_in:
            return JsonResponse({'success': False, 'message': 'يجب تسجيل الحضور أولاً'}, status=400)
        if existing_check_out:
            return JsonResponse({'success': False, 'message': 'تم تسجيل الانصراف مسبقاً اليوم'}, status=400)

    attendance = AttendanceRecord.objects.create(
        employee=employee,
        date=today,
        time=now.time(),
        record_type=record_type,
        source='web',
        device_info=request.META.get('HTTP_USER_AGENT', '')[:100],
        created_by=request.user
    )

    message = 'تم تسجيل الحضور بنجاح' if record_type == 'check_in' else 'تم تسجيل الانصراف بنجاح'

    return JsonResponse({
        'success': True,
        'message': message,
        'record_id': attendance.id,
        'time': now.strftime('%H:%M:%S'),
    })


@login_required
def check_attendance_status(request):
    """التحقق من حالة الحضور للموظف"""
    employee = get_employee_for_user(request.user)
    if not employee:
        return JsonResponse({'error': 'لا يوجد ملف موظف'}, status=400)

    today = date.today()
    records = AttendanceRecord.objects.filter(employee=employee, date=today).order_by('time')

    check_in = records.filter(record_type='check_in').first()
    check_out = records.filter(record_type='check_out').last()

    return JsonResponse({
        'checked_in': check_in is not None,
        'checked_out': check_out is not None,
        'check_in_time': check_in.time.strftime('%H:%M') if check_in else None,
        'check_out_time': check_out.time.strftime('%H:%M') if check_out else None,
    })


@login_required
def submit_leave_request(request):
    """تقديم طلب إجازة (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'}, status=405)
    
    employee = get_employee_for_user(request.user)
    if not employee:
        return JsonResponse({'success': False, 'error': 'لم يتم العثور على ملف الموظف'}, status=400)
    
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        leave_type_id = data.get('leave_type')
        manual_leave_type = (data.get('manual_leave_type') or '').strip()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        reason = data.get('reason', '')
        
        if not all([start_date, end_date]):
            return JsonResponse({'success': False, 'error': 'جميع الحقول مطلوبة'}, status=400)
        
        leave_type = None
        if leave_type_id and str(leave_type_id) != '__manual__':
            leave_type = get_object_or_404(LeaveType, id=leave_type_id)
        elif manual_leave_type:
            leave_type, _ = LeaveType.objects.get_or_create(
                name=manual_leave_type,
                defaults={
                    'days_per_year': 30,
                    'is_paid': True,
                    'carry_forward': False,
                    'max_carry_forward_days': 0,
                    'requires_approval': True,
                }
            )

        if not leave_type:
            return JsonResponse({'success': False, 'error': 'يرجى اختيار نوع الإجازة أو كتابته يدوياً'}, status=400)
        
        # حساب عدد الأيام
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        days_requested = (end - start).days + 1
        
        if days_requested <= 0:
            return JsonResponse({'success': False, 'error': 'تاريخ النهاية يجب أن يكون بعد تاريخ البداية'}, status=400)
        
        # إنشاء الطلب
        leave_request = LeaveRequest.objects.create(
            employee=employee,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            days_requested=days_requested,
            reason=reason,
            status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'تم تقديم طلب الإجازة بنجاح! رقم الطلب: {leave_request.id}',
            'leave_id': leave_request.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def submit_production_entry(request):
    """تسجيل إنتاجية يومية (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'}, status=405)
    
    employee = get_employee_for_user(request.user)
    if not employee:
        return JsonResponse({'success': False, 'error': 'لم يتم العثور على ملف الموظف'}, status=400)
    
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        product_id = data.get('product')
        quantity = data.get('quantity')
        work_center_id = data.get('work_center')
        machine_code = data.get('machine_code', '')
        shift = data.get('shift', '')
        notes = data.get('notes', '')
        
        if not all([product_id, quantity]):
            return JsonResponse({'success': False, 'error': 'المنتج والكمية مطلوبان'}, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        work_center = None
        if work_center_id:
            work_center = ProductionWorkCenter.objects.filter(id=work_center_id).first()
        
        # إنشاء تسجيل الإنتاج
        entry = WorkerProductionEntry.objects.create(
            employee=employee,
            date=date.today(),
            product=product,
            quantity=Decimal(str(quantity)),
            work_center=work_center,
            machine_code=machine_code,
            shift=shift,
            notes=notes,
            status='submitted'  # مقدم للمراجعة
        )
        
        return JsonResponse({
            'success': True,
            'message': f'تم تسجيل إنتاجك بنجاح! الكمية: {quantity}',
            'entry_id': entry.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def get_production_stats(request):
    """إحصائيات الإنتاج للموظف (AJAX)"""
    employee = get_employee_for_user(request.user)
    if not employee:
        return JsonResponse({'success': False, 'error': 'لم يتم العثور على ملف الموظف'}, status=400)
    
    # إحصائيات آخر 30 يوم
    last_30_days = date.today() - timedelta(days=30)
    
    daily_production = WorkerProductionEntry.objects.filter(
        employee=employee,
        date__gte=last_30_days,
        status='approved'
    ).values('date').annotate(
        total_qty=Sum('quantity')
    ).order_by('date')
    
    # تحويل لتنسيق الرسم البياني
    chart_data = {
        'labels': [entry['date'].strftime('%d/%m') for entry in daily_production],
        'values': [float(entry['total_qty']) for entry in daily_production]
    }
    
    return JsonResponse({'success': True, 'chart_data': chart_data})


@login_required
def upload_employee_photo(request):
    """رفع/تحديث صورة الموظف (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'}, status=405)
    
    employee = get_employee_for_user(request.user)
    if not employee:
        return JsonResponse({'success': False, 'error': 'لم يتم العثور على ملف الموظف'}, status=400)
    
    try:
        photo = request.FILES.get('photo')
        
        if not photo:
            return JsonResponse({'success': False, 'error': 'لم يتم اختيار صورة'}, status=400)
        
        # التحقق من نوع الملف
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if photo.content_type not in allowed_types:
            return JsonResponse({'success': False, 'error': 'نوع الملف غير مسموح. يرجى رفع صورة (JPG, PNG, GIF, WebP)'}, status=400)
        
        # التحقق من حجم الملف (max 5MB)
        if photo.size > 5 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'حجم الصورة كبير جداً (الحد الأقصى 5MB)'}, status=400)
        
        # حذف الصورة القديمة إذا وجدت
        if employee.photo:
            try:
                employee.photo.delete(save=False)
            except:
                pass
        
        # حفظ الصورة الجديدة
        employee.photo = photo
        employee.save(update_fields=['photo'])
        
        return JsonResponse({
            'success': True,
            'message': 'تم تحديث الصورة بنجاح!',
            'photo_url': employee.photo.url if employee.photo else None
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'حدث خطأ: {str(e)}'}, status=400)
