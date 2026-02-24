"""
Decorators مخصصة للمتجر الإلكتروني
Custom decorators for the ecommerce store
"""
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _


def store_login_required(function=None):
    """
    Decorator يتطلب تسجيل دخول العميل
    يوجه المستخدم إلى صفحة تسجيل دخول المتجر (وليس النظام الرئيسي)
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # حفظ الصفحة المطلوبة للعودة إليها بعد تسجيل الدخول
            login_url = reverse('ecommerce:customer_login')
            next_url = request.get_full_path()
            
            messages.info(request, _('يرجى تسجيل الدخول للمتابعة'))
            
            return redirect(f"{login_url}?next={next_url}")
        
        return _wrapped_view
    
    if function:
        return decorator(function)
    return decorator


def admin_login_required(function=None):
    """
    Decorator يتطلب تسجيل دخول مدير المتجر
    يتحقق من صلاحيات الإدارة
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = reverse('accounts:login')  # صفحة تسجيل دخول النظام للموظفين
                next_url = request.get_full_path()
                return redirect(f"{login_url}?next={next_url}")
            
            # التحقق من صلاحيات الإدارة
            if not (request.user.is_staff or request.user.is_superuser):
                messages.error(request, _('ليس لديك صلاحية الوصول لهذه الصفحة'))
                return redirect('ecommerce:store_home')
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    
    if function:
        return decorator(function)
    return decorator
