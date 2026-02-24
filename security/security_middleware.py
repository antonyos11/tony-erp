"""
Tony ERP - Security Middleware
تحسينات أمنية شاملة للنظام
"""
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
import logging
from datetime import datetime, timedelta
from typing import Optional
import hashlib

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """إضافة رؤوس أمنية للاستجابات HTTP"""
    
    def process_response(self, request, response):
        # Content Security Policy - مع دعم QZ Tray للطباعة الحرارية
        response['Content-Security-Policy'] = (
            "default-src 'self' data:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://code.jquery.com https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com data:; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' ws: wss: ws://localhost:* wss://localhost:* https://cdn.jsdelivr.net https://api.openai.com https://api.anthropic.com; "
            "media-src 'self' data: blob:; "
            "frame-ancestors 'none';"
        )
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature Policy)
        response['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )
        
        # HTTPS Strict Transport Security (only in production)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response


class LoginRateLimitMiddleware(MiddlewareMixin):
    """تحديد معدل محاولات تسجيل الدخول"""
    
    # تخزين محاولات تسجيل الدخول في الذاكرة (يُفضل استخدام Redis في الإنتاج)
    login_attempts = {}
    
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)
    
    def process_request(self, request):
        if request.path.endswith('/login/') and request.method == 'POST':
            ip_address = self.get_client_ip(request)
            
            # التحقق من حالة القفل
            if self.is_locked_out(ip_address):
                logger.warning(f"Login attempt from locked IP: {ip_address}")
                return HttpResponse(
                    "تم تجاوز الحد الأقصى لمحاولات تسجيل الدخول. يرجى المحاولة لاحقاً.",
                    status=429
                )
            
            # تسجيل المحاولة
            self.record_attempt(ip_address)
        
        return None
    
    def get_client_ip(self, request) -> str:
        """الحصول على IP العميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def is_locked_out(self, ip_address: str) -> bool:
        """التحقق من حالة القفل"""
        if ip_address not in self.login_attempts:
            return False
        
        attempts = self.login_attempts[ip_address]
        if len(attempts) < self.MAX_ATTEMPTS:
            return False
        
        # التحقق من انتهاء مدة القفل
        oldest_attempt = min(attempts)
        if datetime.now() - oldest_attempt > self.LOCKOUT_DURATION:
            # إعادة تعيين المحاولات
            self.login_attempts[ip_address] = []
            return False
        
        return True
    
    def record_attempt(self, ip_address: str):
        """تسجيل محاولة تسجيل دخول"""
        if ip_address not in self.login_attempts:
            self.login_attempts[ip_address] = []
        
        self.login_attempts[ip_address].append(datetime.now())
        
        # حذف المحاولات القديمة
        cutoff = datetime.now() - self.LOCKOUT_DURATION
        self.login_attempts[ip_address] = [
            attempt for attempt in self.login_attempts[ip_address]
            if attempt > cutoff
        ]


class SessionSecurityMiddleware(MiddlewareMixin):
    """تحسين أمان الجلسات"""
    
    SESSION_TIMEOUT = timedelta(hours=2)
    IDLE_TIMEOUT = timedelta(minutes=30)
    
    def process_request(self, request):
        if not isinstance(request.user, AnonymousUser) and request.user.is_authenticated:
            # التحقق من نشاط الجلسة
            last_activity = request.session.get('last_activity')
            
            if last_activity:
                last_activity_time = datetime.fromisoformat(last_activity)
                
                # التحقق من المهلة الخاملة
                if datetime.now() - last_activity_time > self.IDLE_TIMEOUT:
                    logger.info(f"Session timeout for user {request.user.username}")
                    from django.contrib.auth import logout
                    logout(request)
                    return HttpResponseRedirect('/login/?timeout=idle')
            
            # تحديث وقت النشاط
            request.session['last_activity'] = datetime.now().isoformat()
            
            # التحقق من مدة الجلسة الإجمالية
            session_start = request.session.get('session_start')
            if not session_start:
                request.session['session_start'] = datetime.now().isoformat()
            else:
                session_start_time = datetime.fromisoformat(session_start)
                if datetime.now() - session_start_time > self.SESSION_TIMEOUT:
                    logger.info(f"Session expired for user {request.user.username}")
                    from django.contrib.auth import logout
                    logout(request)
                    return HttpResponseRedirect('/login/?timeout=expired')
        
        return None


class AuditLogMiddleware(MiddlewareMixin):
    """تسجيل النشاطات الحساسة"""
    
    SENSITIVE_PATHS = [
        '/admin/',
        '/api/users/',
        '/api/permissions/',
        '/accounting/',
        '/sales/invoice/',
        '/purchases/',
    ]
    
    def process_request(self, request):
        # تسجيل العمليات الحساسة
        if any(request.path.startswith(path) for path in self.SENSITIVE_PATHS):
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                self.log_activity(request)
        
        return None
    
    def log_activity(self, request):
        """تسجيل النشاط"""
        user = request.user if not isinstance(request.user, AnonymousUser) else None
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'user': user.username if user else 'anonymous',
            'ip': self.get_client_ip(request),
            'method': request.method,
            'path': request.path,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
        
        logger.info(f"Audit: {log_data}")
        
        # يمكن حفظ في قاعدة البيانات
        try:
            from users.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action=f"{request.method} {request.path}",
                ip_address=log_data['ip'],
                user_agent=log_data['user_agent'],
            )
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")
    
    def get_client_ip(self, request) -> str:
        """الحصول على IP العميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
