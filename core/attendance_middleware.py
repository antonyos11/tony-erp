# -*- coding: utf-8 -*-
"""
Middleware لإلزام الموظفين بتسجيل الحضور قبل الوصول للنظام
"""
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from datetime import date


class AttendanceGateMiddleware:
    """
    Middleware يمنع الموظفين غير المستثنين من الوصول للنظام
    إلا بعد تسجيل الحضور، ويمنع تسجيل الخروج قبل تسجيل الانصراف.
    """

    # المسارات المسموح بها بدون تسجيل حضور
    EXEMPT_PATHS = [
        '/accounts/login/',
        '/accounts/logout/',
        '/login/',
        '/logout/',
        '/admin/',
        '/api/',
        '/static/',
        '/media/',
        '/hr/welcome/',
        '/hr/portal/',
        '/ecommerce/employee-portal/',
        '/offline/',
        '/health/',
        '/favicon.ico',
        '/__debug__/',
    ]

    # المسارات التي تتطلب تسجيل انصراف قبل الوصول
    LOGOUT_PATHS = [
        '/logout/',
        '/accounts/logout/',
        '/core/logout/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # تجاهل المستخدمين غير المسجلين
        if not request.user.is_authenticated:
            return self.get_response(request)

        # تجاهل المسؤولين (superuser / staff)
        if request.user.is_superuser or request.user.is_staff:
            return self.get_response(request)

        # التحقق من المسارات المستثناة
        path = request.path
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return self.get_response(request)

        # محاولة جلب ملف الموظف
        try:
            from hr.models import AttendanceRecord
            employee = getattr(request.user, 'employee_profile', None)
        except Exception:
            return self.get_response(request)

        if not employee:
            return self.get_response(request)

        # الموظفون المستثنون يمرون مباشرة
        if getattr(employee, 'attendance_exempt', False):
            return self.get_response(request)

        today = date.today()

        try:
            checked_in = AttendanceRecord.objects.filter(
                employee=employee, date=today, record_type='check_in'
            ).exists()
            checked_out = AttendanceRecord.objects.filter(
                employee=employee, date=today, record_type='check_out'
            ).exists()
        except Exception:
            return self.get_response(request)

        welcome_url = reverse('hr:employee_welcome')

        # منع الخروج قبل تسجيل الانصراف
        if any(path.startswith(lp) for lp in self.LOGOUT_PATHS):
            if checked_in and not checked_out:
                messages.warning(request, 'لا يمكن تسجيل الخروج قبل تسجيل الانصراف')
                return redirect(welcome_url)
            return self.get_response(request)

        # إذا لم يسجل حضور، وجّه لصفحة الترحيب
        if not checked_in:
            messages.warning(request, 'يجب تسجيل الحضور أولاً للدخول إلى النظام')
            return redirect(welcome_url)

        # إذا سجل انصراف، امنع الدخول
        if checked_out:
            messages.warning(request, 'تم تسجيل انصرافك اليوم. لا يمكنك الدخول للنظام.')
            return redirect(welcome_url)

        return self.get_response(request)
