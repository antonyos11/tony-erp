"""
نظام الأمان المتقدم
Advanced Security System
"""

import hashlib
import hmac
import secrets
import time
import re
from functools import wraps
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponseForbidden, JsonResponse
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger('users.security')
User = get_user_model()


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """
    نظام تقييد معدل الطلبات
    """
    
    def __init__(self, key_prefix: str = 'rate_limit'):
        self.key_prefix = key_prefix
    
    def _get_key(self, identifier: str, action: str) -> str:
        return f"{self.key_prefix}:{action}:{identifier}"
    
    def is_rate_limited(
        self,
        identifier: str,
        action: str,
        max_attempts: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        فحص ما إذا كان المستخدم محدود
        Returns: (is_limited, remaining_attempts)
        """
        key = self._get_key(identifier, action)
        
        try:
            current = cache.get(key, 0)
            
            if current >= max_attempts:
                return True, 0
            
            return False, max_attempts - current
        except Exception:
            return False, max_attempts
    
    def record_attempt(
        self,
        identifier: str,
        action: str,
        window_seconds: int
    ) -> int:
        """تسجيل محاولة"""
        key = self._get_key(identifier, action)
        
        try:
            current = cache.get(key, 0)
            cache.set(key, current + 1, window_seconds)
            return current + 1
        except Exception:
            return 0
    
    def reset(self, identifier: str, action: str):
        """إعادة تعيين العداد"""
        key = self._get_key(identifier, action)
        try:
            cache.delete(key)
        except Exception:
            pass


# Singleton instance
rate_limiter = RateLimiter()


def rate_limit(
    max_attempts: int = 10,
    window_seconds: int = 60,
    action: str = 'default',
    by: str = 'ip'
):
    """
    Decorator لتقييد معدل الطلبات
    
    Usage:
        @rate_limit(max_attempts=5, window_seconds=300, action='login')
        def login_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            # تحديد المعرّف
            if by == 'ip':
                identifier = get_client_ip(request)
            elif by == 'user' and request.user.is_authenticated:
                identifier = str(request.user.pk)
            else:
                identifier = get_client_ip(request)
            
            is_limited, remaining = rate_limiter.is_rate_limited(
                identifier, action, max_attempts, window_seconds
            )
            
            if is_limited:
                logger.warning(
                    f"Rate limit exceeded for {identifier} on action {action}"
                )
                
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'error': 'too_many_requests',
                        'message': 'تم تجاوز الحد المسموح من المحاولات',
                        'retry_after': window_seconds
                    }, status=429)
                
                return HttpResponseForbidden(
                    'تم تجاوز الحد المسموح من المحاولات. حاول لاحقاً.'
                )
            
            # تسجيل المحاولة
            rate_limiter.record_attempt(identifier, action, window_seconds)
            
            response = view_func(request, *args, **kwargs)
            
            # إضافة headers
            response['X-RateLimit-Limit'] = str(max_attempts)
            response['X-RateLimit-Remaining'] = str(remaining - 1)
            
            return response
        return wrapper
    return decorator


# =============================================================================
# IP Security
# =============================================================================

def get_client_ip(request: HttpRequest) -> str:
    """الحصول على IP العميل الحقيقي"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip


def is_ip_blocked(ip: str) -> bool:
    """فحص ما إذا كان IP محظور"""
    key = f"blocked_ip:{ip}"
    return cache.get(key, False)


def block_ip(ip: str, duration_seconds: int = 3600, reason: str = ''):
    """حظر IP"""
    key = f"blocked_ip:{ip}"
    cache.set(key, {'reason': reason, 'blocked_at': time.time()}, duration_seconds)
    logger.warning(f"IP blocked: {ip}, reason: {reason}")


def unblock_ip(ip: str):
    """رفع الحظر عن IP"""
    key = f"blocked_ip:{ip}"
    cache.delete(key)


# =============================================================================
# Input Validation & Sanitization
# =============================================================================

class InputValidator:
    """
    مدقق ومنظف المدخلات
    """
    
    # أنماط خطرة
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(\bOR\b\s+\d+\s*=\s*\d+)",
        r"(\bAND\b\s+\d+\s*=\s*\d+)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """تنظيف سلسلة نصية"""
        if not isinstance(value, str):
            return str(value)[:max_length]
        
        # إزالة الأحرف غير المرئية الخطرة
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
        
        # قص الطول
        value = value[:max_length]
        
        return value.strip()
    
    @classmethod
    def check_sql_injection(cls, value: str) -> bool:
        """فحص محاولات SQL Injection"""
        if not isinstance(value, str):
            return False
        
        value_upper = value.upper()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def check_xss(cls, value: str) -> bool:
        """فحص محاولات XSS"""
        if not isinstance(value, str):
            return False
        
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """التحقق من صحة البريد الإلكتروني"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """التحقق من صحة رقم الهاتف"""
        # يقبل صيغ مختلفة
        pattern = r'^[\d\s\-\+\(\)]{8,20}$'
        return bool(re.match(pattern, phone))


# =============================================================================
# Password Security
# =============================================================================

class PasswordValidator:
    """
    مدقق قوة كلمة المرور
    """
    
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    
    SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    
    @classmethod
    def validate(cls, password: str) -> tuple[bool, List[str]]:
        """
        التحقق من قوة كلمة المرور
        Returns: (is_valid, list of errors)
        """
        errors = []
        
        if len(password) < cls.MIN_LENGTH:
            errors.append(f'كلمة المرور يجب أن تكون {cls.MIN_LENGTH} أحرف على الأقل')
        
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append('يجب أن تحتوي على حرف كبير واحد على الأقل')
        
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append('يجب أن تحتوي على حرف صغير واحد على الأقل')
        
        if cls.REQUIRE_DIGIT and not re.search(r'\d', password):
            errors.append('يجب أن تحتوي على رقم واحد على الأقل')
        
        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            errors.append('يجب أن تحتوي على رمز خاص واحد على الأقل')
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_strength_score(cls, password: str) -> int:
        """
        حساب درجة قوة كلمة المرور (0-100)
        """
        score = 0
        
        # الطول
        score += min(len(password) * 4, 40)
        
        # التنوع
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if any(c in cls.SPECIAL_CHARS for c in password):
            score += 15
        
        # التعقيد
        unique_chars = len(set(password))
        score += min(unique_chars * 2, 15)
        
        return min(score, 100)


# =============================================================================
# Session Security
# =============================================================================

class SessionSecurity:
    """
    نظام أمان الجلسات
    """
    
    @staticmethod
    def create_fingerprint(request: HttpRequest) -> str:
        """إنشاء بصمة للجلسة"""
        data = [
            request.META.get('HTTP_USER_AGENT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
        ]
        fingerprint = hashlib.sha256('|'.join(data).encode()).hexdigest()[:32]
        return fingerprint
    
    @staticmethod
    def verify_fingerprint(request: HttpRequest, stored_fingerprint: str) -> bool:
        """التحقق من بصمة الجلسة"""
        current = SessionSecurity.create_fingerprint(request)
        return hmac.compare_digest(current, stored_fingerprint)
    
    @staticmethod
    def regenerate_session(request: HttpRequest):
        """تجديد معرف الجلسة"""
        if hasattr(request, 'session'):
            request.session.cycle_key()


# =============================================================================
# CSRF Protection Enhancement
# =============================================================================

def generate_csrf_token() -> str:
    """توليد رمز CSRF آمن"""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    """التحقق من رمز CSRF"""
    if not token or not stored_token:
        return False
    return hmac.compare_digest(token, stored_token)


# =============================================================================
# Audit Logging
# =============================================================================

class SecurityAudit:
    """
    تسجيل أحداث الأمان
    """
    
    @staticmethod
    def log_login_success(request: HttpRequest, user):
        """تسجيل تسجيل دخول ناجح"""
        logger.info(
            f"Login success: user={user.username}, ip={get_client_ip(request)}"
        )
    
    @staticmethod
    def log_login_failure(request: HttpRequest, username: str, reason: str):
        """تسجيل فشل تسجيل الدخول"""
        logger.warning(
            f"Login failed: username={username}, ip={get_client_ip(request)}, reason={reason}"
        )
    
    @staticmethod
    def log_suspicious_activity(request: HttpRequest, activity_type: str, details: str):
        """تسجيل نشاط مشبوه"""
        logger.warning(
            f"Suspicious activity: type={activity_type}, ip={get_client_ip(request)}, details={details}"
        )
    
    @staticmethod
    def log_permission_denied(request: HttpRequest, resource: str):
        """تسجيل رفض الوصول"""
        user = request.user.username if request.user.is_authenticated else 'anonymous'
        logger.warning(
            f"Permission denied: user={user}, resource={resource}, ip={get_client_ip(request)}"
        )


# =============================================================================
# Middleware Helpers
# =============================================================================

def security_check_request(request: HttpRequest) -> Optional[Dict[str, Any]]:
    """
    فحص أمني شامل للطلب
    Returns: None if OK, or dict with error details
    """
    ip = get_client_ip(request)
    
    # فحص IP المحظور
    if is_ip_blocked(ip):
        return {'error': 'ip_blocked', 'message': 'IP address is blocked'}
    
    # فحص المدخلات
    for key, value in request.GET.items():
        if isinstance(value, str):
            if InputValidator.check_sql_injection(value):
                SecurityAudit.log_suspicious_activity(
                    request, 'sql_injection_attempt', f'param={key}'
                )
                return {'error': 'suspicious_input', 'message': 'Suspicious input detected'}
            
            if InputValidator.check_xss(value):
                SecurityAudit.log_suspicious_activity(
                    request, 'xss_attempt', f'param={key}'
                )
                return {'error': 'suspicious_input', 'message': 'Suspicious input detected'}
    
    return None
