"""
Tony ERP - Employee Portal Views
بوابة الموظفين - الوصول للنظام من المتجر الإلكتروني
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.utils import timezone
from django.db.models import Q
from datetime import date, datetime, timedelta
import json
import logging

from .decorators import admin_login_required

logger = logging.getLogger(__name__)


# ==========================================
# صفحة تسجيل الدخول للموظفين من المتجر
# ==========================================

@csrf_protect
@never_cache
def employee_portal_login(request):
    """
    صفحة تسجيل الدخول للموظفين من المتجر الإلكتروني
    """
    if request.user.is_authenticated:
        # السماح لمدير النظام بالدخول مباشرة
        if request.user.is_superuser or request.user.is_staff:
            return redirect('home')
        # التحقق من أن المستخدم موظف
        try:
            from hr.models import Employee
            employee = request.user.employee_profile
            return redirect('ecommerce:employee_welcome')
        except:
            pass
    
    if request.method == 'POST':
        login_method = request.POST.get('login_method', 'password')
        
        if login_method == 'password':
            # تسجيل الدخول التقليدي
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            
            if not username or not password:
                messages.error(request, _('يرجى إدخال اسم المستخدم وكلمة المرور'))
                return render(request, 'ecommerce/employee_portal/login.html')
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # السماح للمديرين بالدخول مباشرة أولاً
                if user.is_superuser or user.is_staff:
                    login(request, user)
                    logger.info(f"Admin {user.username} logged in via employee portal")
                    return redirect('home')
                
                # التحقق من أن المستخدم موظف
                try:
                    from hr.models import Employee
                    employee = user.employee_profile
                    if employee.status != 'active':
                        messages.error(request, _('حسابك غير نشط. يرجى مراجعة إدارة الموارد البشرية.'))
                        return render(request, 'ecommerce/employee_portal/login.html')
                    
                    login(request, user)
                    request.session['employee_id'] = employee.id
                    request.session['attendance_registered'] = False
                    
                    logger.info(f"Employee {employee.employee_id} logged in via password")
                    return redirect('ecommerce:employee_welcome')
                    
                except:
                    messages.error(request, _('هذا الحساب غير مرتبط بملف موظف'))
            else:
                messages.error(request, _('اسم المستخدم أو كلمة المرور غير صحيحة'))
        
        elif login_method == 'card':
            # تسجيل الدخول ببطاقة ID
            card_id = request.POST.get('card_id', '').strip()
            
            if not card_id:
                messages.error(request, _('يرجى مسح البطاقة أو إدخال رقم البطاقة'))
                return render(request, 'ecommerce/employee_portal/login.html')
            
            try:
                from hr.models import Employee
                # البحث عن الموظف ببطاقة RFID أو رقم الموظف
                employee = Employee.objects.get(
                    Q(rfid_card_number=card_id) | Q(employee_id=card_id),
                    status='active'
                )
                
                user = employee.user
                login(request, user)
                request.session['employee_id'] = employee.id
                request.session['attendance_registered'] = False
                request.session['login_method'] = 'card'
                
                logger.info(f"Employee {employee.employee_id} logged in via card ID")
                return redirect('ecommerce:employee_welcome')
                
            except:
                messages.error(request, _('البطاقة غير مسجلة في النظام'))
    
    return render(request, 'ecommerce/employee_portal/login.html')


@admin_login_required
def employee_portal_logout(request):
    """تسجيل خروج الموظف"""
    logout(request)
    messages.info(request, _('تم تسجيل الخروج بنجاح'))
    return redirect('ecommerce:employee_portal_login')


# ==========================================
# صفحة الترحيب بالموظف
# ==========================================

@admin_login_required
def employee_welcome(request):
    """صفحة الترحيب بالموظف"""
    # السماح للمديرين بالتوجه للنظام مباشرة
    if request.user.is_superuser or request.user.is_staff:
        return redirect('home')
    
    try:
        from hr.models import Employee, AttendanceRecord
        employee = request.user.employee_profile
    except:
        messages.error(request, _('لا يوجد ملف موظف مرتبط بحسابك'))
        return redirect('ecommerce:employee_portal_login')
    
    # التحقق من حالة الحضور اليوم
    today = date.today()
    today_attendance = AttendanceRecord.objects.filter(
        employee=employee,
        date=today
    ).order_by('-time')
    
    checked_in = today_attendance.filter(record_type='check_in').exists()
    checked_out = today_attendance.filter(record_type='check_out').exists()
    
    last_record = today_attendance.first()
    
    # تحديد نوع الموظف
    employee_type = get_employee_type(employee)
    
    # الحصول على المهام الوظيفية
    job_duties = get_job_duties(employee)
    
    context = {
        'employee': employee,
        'employee_type': employee_type,
        'job_duties': job_duties,
        'checked_in': checked_in,
        'checked_out': checked_out,
        'last_record': last_record,
        'today': today,
        'current_time': timezone.now(),
    }
    
    return render(request, 'ecommerce/employee_portal/welcome.html', context)


# ==========================================
# نظام تسجيل الحضور والانصراف
# ==========================================

@admin_login_required
@csrf_protect
def register_attendance(request):
    """تسجيل الحضور"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        from hr.models import Employee, AttendanceRecord
        employee = request.user.employee_profile
    except:
        return JsonResponse({'success': False, 'message': 'لا يوجد ملف موظف'}, status=400)
    
    record_type = request.POST.get('type', 'check_in')
    latitude = request.POST.get('latitude')
    longitude = request.POST.get('longitude')
    
    today = date.today()
    now = timezone.now()
    
    # التحقق من عدم تسجيل حضور مكرر
    existing_record = AttendanceRecord.objects.filter(
        employee=employee,
        date=today,
        record_type=record_type
    ).first()
    
    if existing_record and record_type == 'check_in':
        return JsonResponse({
            'success': False, 
            'message': 'تم تسجيل الحضور مسبقاً اليوم'
        }, status=400)
    
    # إنشاء سجل الحضور
    attendance = AttendanceRecord.objects.create(
        employee=employee,
        date=today,
        time=now.time(),
        record_type=record_type,
        source='web',
        device_info=request.META.get('HTTP_USER_AGENT', '')[:100],
        latitude=latitude if latitude else None,
        longitude=longitude if longitude else None,
        created_by=request.user
    )
    
    request.session['attendance_registered'] = (record_type == 'check_in')
    
    employee_type = get_employee_type(employee)
    
    if record_type == 'check_in' and employee_type in ['driver', 'sales_rep']:
        request.session['tracking_enabled'] = True
    elif record_type == 'check_out' and employee_type in ['driver', 'sales_rep']:
        request.session['tracking_enabled'] = False
    
    message = 'تم تسجيل الحضور بنجاح' if record_type == 'check_in' else 'تم تسجيل الانصراف بنجاح'
    
    return JsonResponse({
        'success': True,
        'message': message,
        'record_id': attendance.id,
        'time': now.strftime('%H:%M:%S'),
    })


@admin_login_required
def check_attendance_status(request):
    """التحقق من حالة الحضور"""
    try:
        from hr.models import Employee, AttendanceRecord
        employee = request.user.employee_profile
    except:
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


@admin_login_required
def access_system(request):
    """الوصول للنظام"""
    # السماح للمديرين مباشرة
    if request.user.is_superuser or request.user.is_staff:
        return redirect('home')
    
    try:
        from hr.models import Employee, AttendanceRecord
        employee = request.user.employee_profile
    except:
        messages.error(request, _('لا يوجد ملف موظف مرتبط بحسابك'))
        return redirect('ecommerce:employee_portal_login')
    
    today = date.today()
    check_in = AttendanceRecord.objects.filter(employee=employee, date=today, record_type='check_in').exists()
    check_out = AttendanceRecord.objects.filter(employee=employee, date=today, record_type='check_out').exists()
    
    if not check_in:
        messages.warning(request, _('يجب تسجيل الحضور أولاً للدخول إلى النظام'))
        return redirect('ecommerce:employee_welcome')
    
    if check_out:
        messages.warning(request, _('تم تسجيل انصرافك. لا يمكنك الدخول للنظام.'))
        return redirect('ecommerce:employee_welcome')
    
    request.session['attendance_registered'] = True
    request.session['system_access_granted'] = True
    
    return redirect('home')


@admin_login_required
@csrf_protect
def update_location(request):
    """تحديث موقع السائق/المندوب"""
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    
    try:
        from hr.models import Employee
        employee = request.user.employee_profile
        employee_type = get_employee_type(employee)
        
        if employee_type not in ['driver', 'sales_rep']:
            return JsonResponse({'success': False, 'message': 'غير مصرح'}, status=403)
        
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not latitude or not longitude:
            return JsonResponse({'success': False, 'message': 'إحداثيات غير صالحة'}, status=400)
        
        # يمكن حفظ الموقع هنا
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@admin_login_required
def sales_rep_dashboard(request):
    """لوحة تحكم المندوب"""
    try:
        from hr.models import Employee
        employee = request.user.employee_profile
    except:
        return redirect('ecommerce:employee_portal_login')
    
    employee_type = get_employee_type(employee)
    if employee_type != 'sales_rep':
        messages.error(request, _('هذه الصفحة مخصصة لمندوبي المبيعات فقط'))
        return redirect('ecommerce:employee_welcome')
    
    context = {
        'employee': employee,
        'today_visits': 0,
        'today': date.today(),
    }
    
    return render(request, 'ecommerce/employee_portal/sales_rep_dashboard.html', context)


@admin_login_required
@csrf_protect
def submit_visit_report(request):
    """إرسال تقرير زيارة"""
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    
    try:
        from hr.models import Employee
        employee = request.user.employee_profile
        
        data = json.loads(request.body)
        # يمكن حفظ تقرير الزيارة هنا
        
        return JsonResponse({'success': True, 'message': 'تم حفظ تقرير الزيارة بنجاح'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ==========================================
# دوال مساعدة
# ==========================================

def get_employee_type(employee):
    """تحديد نوع الموظف"""
    position_title = employee.position.title.lower() if employee.position else ''
    
    driver_keywords = ['سائق', 'driver', 'توصيل', 'delivery']
    for keyword in driver_keywords:
        if keyword in position_title:
            return 'driver'
    
    sales_rep_keywords = ['مندوب', 'sales rep', 'مبيعات خارجي', 'external sales']
    for keyword in sales_rep_keywords:
        if keyword in position_title:
            return 'sales_rep'
    
    return 'regular'


def get_job_duties(employee):
    """الحصول على المهام الوظيفية"""
    duties = []
    
    if employee.position and employee.position.description:
        lines = employee.position.description.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:
                duties.append(line)
    
    if not duties:
        dept_name = employee.department.name.lower() if employee.department else ''
        
        if 'مبيعات' in dept_name or 'sales' in dept_name:
            duties = ['متابعة العملاء', 'إتمام الصفقات', 'تحقيق الأهداف البيعية']
        elif 'محاسب' in dept_name or 'accounting' in dept_name:
            duties = ['مراجعة القيود', 'إعداد التقارير المالية', 'متابعة الحسابات']
        else:
            duties = ['أداء المهام المطلوبة', 'التنسيق مع الفريق', 'تحقيق الأهداف']
    
    return duties[:5]
