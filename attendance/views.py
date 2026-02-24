"""
Views لنظام الحضور والانصراف - نسخة متطورة
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate, ExtractHour
from datetime import datetime, timedelta
from decimal import Decimal
from .models import (
    WorkLocation, EmployeeFaceData, AttendanceRecord,
    AttendanceRequest, AttendanceSettings, AttendanceReport,
    AttendanceMethod, AttendanceStatus
)

User = get_user_model()


@login_required
def dashboard(request):
    """لوحة تحكم نظام الحضور - متطورة"""
    today = timezone.now().date()
    now = timezone.now()
    
    # إحصائيات اليوم
    today_records = AttendanceRecord.objects.filter(date=today)
    total_employees = User.objects.filter(is_active=True).count()
    checked_in_today = today_records.count()
    present_count = today_records.filter(status=AttendanceStatus.PRESENT).count()
    late_count = today_records.filter(status=AttendanceStatus.LATE).count()
    absent_count = total_employees - checked_in_today
    
    # حساب معدل الحضور
    attendance_rate = round((checked_in_today / total_employees * 100), 1) if total_employees > 0 else 0
    
    # سجل حضور المستخدم الحالي
    my_attendance = AttendanceRecord.objects.filter(
        user=request.user,
        date=today
    ).first()
    
    # إحصائيات الأسبوع الحالي
    week_start = today - timedelta(days=today.weekday())
    week_records = AttendanceRecord.objects.filter(
        date__gte=week_start,
        date__lte=today
    )
    
    weekly_stats = {
        'total': week_records.count(),
        'present': week_records.filter(status=AttendanceStatus.PRESENT).count(),
        'late': week_records.filter(status=AttendanceStatus.LATE).count(),
        'avg_hours': week_records.aggregate(avg=Avg('total_hours'))['avg'] or Decimal('0'),
    }
    
    # بيانات الرسم البياني - آخر 7 أيام
    chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_records = AttendanceRecord.objects.filter(date=day)
        chart_data.append({
            'date': day.strftime('%a'),
            'full_date': day.strftime('%Y-%m-%d'),
            'present': day_records.filter(status=AttendanceStatus.PRESENT).count(),
            'late': day_records.filter(status=AttendanceStatus.LATE).count(),
            'absent': total_employees - day_records.count() if i > 0 else absent_count,
        })
    
    # الطلبات المعلقة
    pending_requests = AttendanceRequest.objects.filter(
        status='pending'
    ).select_related('user').order_by('-created_at')[:5]
    pending_count = AttendanceRequest.objects.filter(status='pending').count()
    
    # آخر السجلات
    recent_records = AttendanceRecord.objects.select_related(
        'user', 'location'
    ).order_by('-check_in_time')[:8]
    
    # أوائل الحاضرين اليوم
    early_birds = today_records.filter(
        check_in_time__isnull=False
    ).order_by('check_in_time')[:5]
    
    # أكثر المتأخرين هذا الأسبوع
    top_late = AttendanceRecord.objects.filter(
        date__gte=week_start,
        status=AttendanceStatus.LATE
    ).values('user__id', 'user__first_name', 'user__last_name').annotate(
        late_count=Count('id')
    ).order_by('-late_count')[:5]
    
    # إحصائيات ساعات العمل
    today_total_hours = today_records.aggregate(total=Sum('total_hours'))['total'] or Decimal('0')
    today_overtime = today_records.aggregate(total=Sum('overtime_hours'))['total'] or Decimal('0')
    
    # مواقع العمل الأكثر نشاطاً
    active_locations = WorkLocation.objects.filter(
        attendancerecord__date=today
    ).annotate(
        today_count=Count('attendancerecord')
    ).order_by('-today_count')[:5]
    
    context = {
        'page_title': 'نظام الحضور والانصراف',
        'today': today,
        'now': now,
        'total_employees': total_employees,
        'checked_in_today': checked_in_today,
        'present_count': present_count,
        'late_count': late_count,
        'absent_count': absent_count,
        'attendance_rate': attendance_rate,
        'my_attendance': my_attendance,
        'pending_requests': pending_requests,
        'pending_count': pending_count,
        'recent_records': recent_records,
        'weekly_stats': weekly_stats,
        'chart_data': chart_data,
        'early_birds': early_birds,
        'top_late': top_late,
        'today_total_hours': today_total_hours,
        'today_overtime': today_overtime,
        'active_locations': active_locations,
    }
    
    return render(request, 'attendance/dashboard.html', context)


@login_required
def check_in(request):
    """صفحة تسجيل الحضور"""
    today = timezone.now().date()
    
    # التحقق من وجود سجل لليوم
    existing_record = AttendanceRecord.objects.filter(
        user=request.user,
        date=today
    ).first()
    
    if existing_record and existing_record.check_in_time:
        messages.warning(request, 'لقد قمت بتسجيل الحضور بالفعل اليوم')
        return redirect('attendance:dashboard')
    
    if request.method == 'POST':
        method = request.POST.get('method', AttendanceMethod.MANUAL)
        location_id = request.POST.get('location')
        notes = request.POST.get('notes', '')
        
        # الحصول على الموقع
        location = None
        if location_id:
            location = WorkLocation.objects.filter(id=location_id).first()
        
        # إنشاء أو تحديث سجل الحضور
        if existing_record:
            record = existing_record
        else:
            record = AttendanceRecord(user=request.user, date=today)
        
        record.check_in_time = timezone.now()
        record.check_in_method = method
        record.location = location
        record.notes = notes
        record.check_in_ip = request.META.get('REMOTE_ADDR')
        
        # حفظ الصورة إذا تم رفعها
        if 'photo' in request.FILES:
            record.check_in_photo = request.FILES['photo']
        
        record.save()
        record.calculate_late_minutes()
        
        messages.success(request, 'تم تسجيل الحضور بنجاح')
        return redirect('attendance:dashboard')
    
    locations = WorkLocation.objects.filter(is_active=True)
    settings = AttendanceSettings.get_settings()
    
    context = {
        'page_title': 'تسجيل الحضور',
        'locations': locations,
        'settings': settings,
        'existing_record': existing_record,
    }
    
    return render(request, 'attendance/check_in.html', context)


@login_required
def check_out(request):
    """صفحة تسجيل الانصراف"""
    today = timezone.now().date()
    
    # التحقق من وجود سجل لليوم
    record = AttendanceRecord.objects.filter(
        user=request.user,
        date=today
    ).first()
    
    if not record or not record.check_in_time:
        messages.error(request, 'يجب تسجيل الحضور أولاً')
        return redirect('attendance:check_in')
    
    if record.check_out_time:
        messages.warning(request, 'لقد قمت بتسجيل الانصراف بالفعل')
        return redirect('attendance:dashboard')
    
    if request.method == 'POST':
        method = request.POST.get('method', AttendanceMethod.MANUAL)
        notes = request.POST.get('notes', '')
        
        record.check_out_time = timezone.now()
        record.check_out_method = method
        record.check_out_ip = request.META.get('REMOTE_ADDR')
        
        if notes:
            record.notes += '\n' + notes
        
        # حفظ الصورة إذا تم رفعها
        if 'photo' in request.FILES:
            record.check_out_photo = request.FILES['photo']
        
        record.save()
        record.calculate_hours()
        
        messages.success(request, 'تم تسجيل الانصراف بنجاح')
        return redirect('attendance:dashboard')
    
    settings = AttendanceSettings.get_settings()
    
    context = {
        'page_title': 'تسجيل الانصراف',
        'record': record,
        'settings': settings,
    }
    
    return render(request, 'attendance/check_out.html', context)


@login_required
def my_attendance(request):
    """سجلات حضور المستخدم"""
    records = AttendanceRecord.objects.filter(
        user=request.user
    ).select_related('location').order_by('-date')
    
    # الفلترة بالفترة الزمنية
    period = request.GET.get('period')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    today = timezone.now().date()
    
    if period == 'week':
        # بداية الأسبوع (السبت)
        start_of_week = today - timedelta(days=(today.weekday() + 2) % 7)
        records = records.filter(date__gte=start_of_week)
    elif period == 'month':
        # بداية الشهر
        start_of_month = today.replace(day=1)
        records = records.filter(date__gte=start_of_month)
    elif period == 'custom':
        if start_date:
            records = records.filter(date__gte=start_date)
        if end_date:
            records = records.filter(date__lte=end_date)
    
    # الإحصائيات
    stats = {
        'total_days': records.count(),
        'present_days': records.filter(status=AttendanceStatus.PRESENT).count(),
        'late_days': records.filter(status=AttendanceStatus.LATE).count(),
        'absent_days': records.filter(status=AttendanceStatus.ABSENT).count(),
        'total_hours': records.aggregate(total=Sum('total_hours'))['total'] or 0,
        'overtime_hours': records.aggregate(total=Sum('overtime_hours'))['total'] or 0,
    }
    
    context = {
        'page_title': 'سجلات حضوري',
        'records': records,
        'stats': stats,
    }
    
    return render(request, 'attendance/my_attendance.html', context)


@login_required
def attendance_list(request):
    """قائمة سجلات الحضور (للمشرفين)"""
    records = AttendanceRecord.objects.select_related(
        'user', 'location'
    ).order_by('-date', '-check_in_time')
    
    # الفلترة
    user_id = request.GET.get('user')
    location_id = request.GET.get('location')
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if user_id:
        records = records.filter(user_id=user_id)
    if location_id:
        records = records.filter(location_id=location_id)
    if status:
        records = records.filter(status=status)
    if start_date:
        records = records.filter(date__gte=start_date)
    if end_date:
        records = records.filter(date__lte=end_date)
    
    context = {
        'page_title': 'سجلات الحضور',
        'records': records,
        'locations': WorkLocation.objects.filter(is_active=True),
    }
    
    return render(request, 'attendance/attendance_list.html', context)


@login_required
def request_list(request):
    """قائمة طلبات تعديل الحضور"""
    if request.user.is_staff:
        # عرض جميع الطلبات للمشرفين
        requests = AttendanceRequest.objects.select_related('user').order_by('-created_at')
    else:
        # عرض طلبات المستخدم فقط
        requests = AttendanceRequest.objects.filter(user=request.user).order_by('-created_at')
    
    # الفلترة
    status = request.GET.get('status')
    if status:
        requests = requests.filter(status=status)
    
    context = {
        'page_title': 'طلبات تعديل الحضور',
        'requests': requests,
    }
    
    return render(request, 'attendance/request_list.html', context)


@login_required
def request_create(request):
    """إنشاء طلب تعديل حضور"""
    if request.method == 'POST':
        request_type = request.POST.get('request_type')
        date_str = request.POST.get('date')
        reason = request.POST.get('reason', '')
        
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # إنشاء الطلب
        attendance_request = AttendanceRequest.objects.create(
            user=request.user,
            request_type=request_type,
            date=date,
            reason=reason
        )
        
        # معالجة الأوقات المطلوبة
        if request_type in ['missing', 'correction']:
            check_in_str = request.POST.get('requested_check_in')
            check_out_str = request.POST.get('requested_check_out')
            
            if check_in_str:
                attendance_request.requested_check_in = datetime.strptime(
                    check_in_str, '%Y-%m-%dT%H:%M'
                )
            if check_out_str:
                attendance_request.requested_check_out = datetime.strptime(
                    check_out_str, '%Y-%m-%dT%H:%M'
                )
        
        # المرفقات
        if 'attachment' in request.FILES:
            attendance_request.attachment = request.FILES['attachment']
        
        attendance_request.save()
        
        messages.success(request, 'تم إرسال الطلب بنجاح')
        return redirect('attendance:request_list')
    
    context = {
        'page_title': 'طلب تعديل حضور',
    }
    
    return render(request, 'attendance/request_create.html', context)


@login_required
def locations_list(request):
    """قائمة مواقع العمل"""
    locations = WorkLocation.objects.all().order_by('name')
    
    context = {
        'page_title': 'مواقع العمل',
        'locations': locations,
    }
    
    return render(request, 'attendance/locations_list.html', context)


@login_required
def settings_view(request):
    """إعدادات نظام الحضور"""
    settings = AttendanceSettings.get_settings()
    
    if request.method == 'POST':
        # تحديث الإعدادات
        settings.enable_face_recognition = request.POST.get('enable_face_recognition') == 'on'
        settings.enable_gps_validation = request.POST.get('enable_gps_validation') == 'on'
        settings.enable_wifi_validation = request.POST.get('enable_wifi_validation') == 'on'
        settings.enable_ip_validation = request.POST.get('enable_ip_validation') == 'on'
        settings.allow_manual_checkin = request.POST.get('allow_manual_checkin') == 'on'
        settings.require_photo_on_checkin = request.POST.get('require_photo_on_checkin') == 'on'
        settings.require_photo_on_checkout = request.POST.get('require_photo_on_checkout') == 'on'
        settings.send_late_notifications = request.POST.get('send_late_notifications') == 'on'
        settings.send_absent_notifications = request.POST.get('send_absent_notifications') == 'on'
        
        settings.save()
        
        messages.success(request, 'تم تحديث الإعدادات بنجاح')
        return redirect('attendance:settings')
    
    context = {
        'page_title': 'إعدادات الحضور',
        'settings': settings,
    }
    
    return render(request, 'attendance/settings.html', context)
