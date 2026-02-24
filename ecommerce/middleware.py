"""
Tony ERP - Employee Attendance Middleware
Middleware للتحقق من تسجيل الحضور قبل الوصول للنظام
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _
from datetime import date
import re


class AttendanceRequiredMiddleware:
    """
    Middleware يتحقق من أن الموظف سجل حضوره قبل الوصول للنظام
    - يستثني صفحات معينة (المتجر، صفحة تسجيل الدخول، الـ API، الملفات الثابتة)
    - يمنع الوصول للنظام إذا لم يسجل الموظف حضوره
    - يمنع الوصول للنظام إذا سجل الموظف انصرافه
    """
    
    # URLs المستثناة من التحقق
    EXCLUDED_PATTERNS = [
        r'^/store/',           # المتجر الإلكتروني
        r'^/admin/',           # لوحة إدارة Django
        r'^/api/',             # API endpoints
        r'^/static/',          # الملفات الثابتة
        r'^/media/',           # الوسائط
        r'^/accounts/',        # صفحات المصادقة
        r'^/login/',           # تسجيل الدخول
        r'^/logout/',          # تسجيل الخروج
        r'^/__debug__/',       # Debug toolbar
        r'^/employee-portal/', # بوابة الموظفين (داخل المتجر)
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Compile patterns for efficiency
        self.excluded_patterns = [re.compile(pattern) for pattern in self.EXCLUDED_PATTERNS]
    
    def __call__(self, request):
        # تخطي للمستخدمين غير المسجلين
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # تخطي للـ superuser
        if request.user.is_superuser:
            return self.get_response(request)
        
        # تخطي للـ URLs المستثناة
        path = request.path
        for pattern in self.excluded_patterns:
            if pattern.match(path):
                return self.get_response(request)
        
        # التحقق من وجود ملف موظف
        try:
            from hr.models import Employee, AttendanceRecord
            employee = request.user.employee_profile
        except:
            # ليس موظفاً - السماح بالمرور
            return self.get_response(request)
        
        # التحقق من تسجيل الحضور
        today = date.today()
        
        check_in = AttendanceRecord.objects.filter(
            employee=employee,
            date=today,
            record_type='check_in'
        ).exists()
        
        check_out = AttendanceRecord.objects.filter(
            employee=employee,
            date=today,
            record_type='check_out'
        ).exists()
        
        # إذا لم يسجل حضور
        if not check_in:
            messages.warning(request, _('يجب تسجيل الحضور أولاً للدخول إلى النظام'))
            return redirect('ecommerce:employee_welcome')
        
        # إذا سجل انصراف
        if check_out:
            messages.warning(request, _('تم تسجيل انصرافك. لا يمكنك الدخول للنظام حتى يوم العمل التالي.'))
            return redirect('ecommerce:employee_welcome')
        
        return self.get_response(request)


class EmployeeTrackingMiddleware:
    """
    Middleware لتتبع السائقين والمندوبين
    يسجل آخر نشاط ويتحقق من حالة التتبع
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # تخطي للمستخدمين غير المسجلين
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # التحقق من وجود ملف موظف
        try:
            from hr.models import Employee
            employee = request.user.employee_profile
            
            # تحديث آخر نشاط في الجلسة
            request.session['last_activity'] = str(date.today())
            
        except:
            pass
        
        return self.get_response(request)
