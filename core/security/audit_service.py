"""
Enhanced Security & Audit Logging
نظام محسّن لتسجيل النشاط والأمان
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.db import transaction

from users.models import UserActivity, SecurityAlert


# إعداد loggers متخصصة
security_logger = logging.getLogger('security')
audit_logger = logging.getLogger('audit')
activity_logger = logging.getLogger('activity')


class AuditLevel:
    """مستويات التدقيق"""
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'


class SecurityAuditService:
    """
    خدمة محسّنة لتسجيل النشاط والأمان
    """
    
    @staticmethod
    def log_login(user: User, request: HttpRequest, success: bool, reason: str = ''):
        """
        تسجيل محاولة تسجيل دخول
        
        Args:
            user: المستخدم (أو username إذا فشل)
            request: الطلب
            success: نجح/فشل
            reason: سبب الفشل (إذا فشل)
        """
        ip_address = SecurityAuditService._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        if success:
            activity_logger.info(f"تسجيل دخول ناجح: {user.username} من {ip_address}")
            
            UserActivity.objects.create(
                user=user,
                action='تسجيل دخول',
                module='النظام',
                description=f'تسجيل دخول ناجح من {ip_address}',
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
            )
        else:
            security_logger.warning(f"فشل تسجيل دخول: {user if isinstance(user, str) else user.username} من {ip_address} - السبب: {reason}")
            
            SecurityAlert.objects.create(
                alert_type='failed_login',
                user=user if isinstance(user, User) else None,
                description=f'محاولة فشل تسجيل دخول من {ip_address} - {reason}',
                ip_address=ip_address,
            )
    
    @staticmethod
    def log_logout(user: User, request: HttpRequest):
        """تسجيل خروج"""
        ip_address = SecurityAuditService._get_client_ip(request)
        
        activity_logger.info(f"تسجيل خروج: {user.username}")
        
        UserActivity.objects.create(
            user=user,
            action='تسجيل خروج',
            module='النظام',
            description='تسجيل خروج',
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            success=True,
        )
    
    @staticmethod
    def log_critical_action(
        user: User,
        action: str,
        module: str,
        object_id: str,
        description: str,
        request: Optional[HttpRequest] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        تسجيل عملية حرجة (حذف، إلغاء، إقفال، إلخ)
        
        Args:
            user: المستخدم
            action: نوع العملية
            module: الوحدة
            object_id: معرف الكائن
            description: وصف العملية
            request: الطلب (اختياري)
            metadata: بيانات إضافية (اختياري)
        """
        ip_address = ''
        user_agent = ''
        
        if request:
            ip_address = SecurityAuditService._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # تسجيل في logger
        audit_logger.critical(
            f"عملية حرجة: {action} في {module} | المستخدم: {user.username} | الكائن: {object_id} | {description}"
        )
        
        # تسجيل في قاعدة البيانات
        UserActivity.objects.create(
            user=user,
            action=action,
            module=module,
            object_id=object_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        
        # إنشاء تنبيه أمني
        SecurityAlert.objects.create(
            alert_type='permission_violation',  # يمكن إضافة نوع جديد للعمليات الحرجة
            user=user,
            description=f'عملية حرجة: {description}',
            ip_address=ip_address,
        )
    
    @staticmethod
    def log_approval(
        user: User,
        action: str,
        module: str,
        object_type: str,
        object_id: str,
        amount: Optional[Decimal] = None,
        approved: bool = True,
        comment: str = '',
        request: Optional[HttpRequest] = None
    ):
        """
        تسجيل موافقة أو رفض
        
        Args:
            user: المستخدم
            action: نوع الموافقة (اعتماد/رفض)
            module: الوحدة
            object_type: نوع الكائن (فاتورة، قيد، إلخ)
            object_id: معرف الكائن
            amount: المبلغ (إذا وجد)
            approved: معتمد/مرفوض
            comment: تعليق
            request: الطلب
        """
        ip_address = ''
        if request:
            ip_address = SecurityAuditService._get_client_ip(request)
        
        status = 'اعتماد' if approved else 'رفض'
        amount_str = f' - المبلغ: {amount}' if amount else ''
        
        description = f'{status} {object_type} رقم {object_id}{amount_str}'
        if comment:
            description += f' - التعليق: {comment}'
        
        audit_logger.info(f"{description} | المستخدم: {user.username}")
        
        UserActivity.objects.create(
            user=user,
            action=action,
            module=module,
            object_id=object_id,
            description=description,
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
            success=True,
        )
    
    @staticmethod
    def log_data_export(
        user: User,
        export_type: str,
        module: str,
        record_count: int,
        request: Optional[HttpRequest] = None
    ):
        """
        تسجيل تصدير بيانات
        
        Args:
            user: المستخدم
            export_type: نوع التصدير (Excel, PDF, CSV)
            module: الوحدة
            record_count: عدد السجلات
            request: الطلب
        """
        ip_address = ''
        if request:
            ip_address = SecurityAuditService._get_client_ip(request)
        
        description = f'تصدير {record_count} سجل من {module} بصيغة {export_type}'
        
        audit_logger.info(f"تصدير بيانات: {description} | المستخدم: {user.username}")
        
        UserActivity.objects.create(
            user=user,
            action='تصدير',
            module=module,
            description=description,
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
            success=True,
        )
    
    @staticmethod
    def log_permission_violation(
        user: User,
        module: str,
        action: str,
        resource: Optional[str] = None,
        request: Optional[HttpRequest] = None
    ):
        """
        تسجيل انتهاك صلاحيات
        
        Args:
            user: المستخدم
            module: الوحدة
            action: العملية المطلوبة
            resource: المورد (اختياري)
            request: الطلب
        """
        ip_address = ''
        if request:
            ip_address = SecurityAuditService._get_client_ip(request)
        
        resource_str = f':{resource}' if resource else ''
        description = f'محاولة وصول غير مصرح: {module}{resource_str}.{action}'
        
        security_logger.warning(
            f"انتهاك صلاحيات: {description} | المستخدم: {user.username} | IP: {ip_address}"
        )
        
        SecurityAlert.objects.create(
            alert_type='permission_violation',
            user=user,
            description=description,
            ip_address=ip_address,
        )
    
    @staticmethod
    def log_data_modification(
        user: User,
        action: str,
        module: str,
        object_type: str,
        object_id: str,
        changes: Optional[Dict[str, Any]] = None,
        request: Optional[HttpRequest] = None
    ):
        """
        تسجيل تعديل بيانات
        
        Args:
            user: المستخدم
            action: نوع التعديل (إضافة/تعديل/حذف)
            module: الوحدة
            object_type: نوع الكائن
            object_id: معرف الكائن
            changes: التغييرات (قديم -> جديد)
            request: الطلب
        """
        ip_address = ''
        if request:
            ip_address = SecurityAuditService._get_client_ip(request)
        
        description = f'{action} {object_type} رقم {object_id}'
        
        if changes:
            changes_str = ', '.join([f'{k}: {v["old"]} → {v["new"]}' for k, v in changes.items()])
            description += f' | التغييرات: {changes_str}'
        
        activity_logger.info(f"{description} | المستخدم: {user.username}")
        
        UserActivity.objects.create(
            user=user,
            action=action,
            module=module,
            object_id=object_id,
            description=description,
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
            success=True,
        )
    
    @staticmethod
    def log_system_event(
        event_type: str,
        description: str,
        level: str = AuditLevel.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        تسجيل حدث نظام عام
        
        Args:
            event_type: نوع الحدث
            description: الوصف
            level: مستوى الأهمية
            metadata: بيانات إضافية
        """
        logger_func = audit_logger.info
        
        if level == AuditLevel.WARNING:
            logger_func = audit_logger.warning
        elif level == AuditLevel.CRITICAL:
            logger_func = audit_logger.critical
        
        logger_func(f"حدث نظام [{event_type}]: {description}")
    
    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """الحصول على عنوان IP الحقيقي للعميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


# ============================================================================
# Decorators للتسجيل التلقائي
# ============================================================================

def audit_critical_action(action: str, module: str):
    """
    ديكوريتر لتسجيل العمليات الحرجة تلقائياً
    
    الاستخدام:
        @audit_critical_action('إلغاء فاتورة', 'المبيعات')
        def cancel_invoice(request, invoice_id):
            ...
    """
    from functools import wraps
    
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            # تنفيذ الدالة
            result = view_func(request, *args, **kwargs)
            
            # تسجيل العملية
            object_id = kwargs.get('id') or kwargs.get('pk') or args[0] if args else 'unknown'
            
            SecurityAuditService.log_critical_action(
                user=request.user,
                action=action,
                module=module,
                object_id=str(object_id),
                description=f'{action} - {view_func.__name__}',
                request=request,
            )
            
            return result
        
        return _wrapped
    return decorator


def audit_data_modification(action: str, module: str, object_type: str):
    """
    ديكوريتر لتسجيل تعديل البيانات
    
    الاستخدام:
        @audit_data_modification('تعديل', 'المخزون', 'صنف')
        def update_product(request, product_id):
            ...
    """
    from functools import wraps
    
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            result = view_func(request, *args, **kwargs)
            
            object_id = kwargs.get('id') or kwargs.get('pk') or args[0] if args else 'unknown'
            
            SecurityAuditService.log_data_modification(
                user=request.user,
                action=action,
                module=module,
                object_type=object_type,
                object_id=str(object_id),
                request=request,
            )
            
            return result
        
        return _wrapped
    return decorator


