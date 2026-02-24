import threading
import time
import uuid
import logging

from django.contrib.sessions.exceptions import SessionInterrupted
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


_local = threading.local()
logger = logging.getLogger(__name__)


def get_current_request():
    return getattr(_local, 'request', None)


def get_current_user():
    req = get_current_request()
    if req and hasattr(req, 'user') and getattr(req.user, 'is_authenticated', False):
        return req.user
    return None


class CurrentRequestMiddleware:
    """يحفظ الطلب الحالي في local thread ليتمكن signals من معرفة المستخدم و IP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            response = self.get_response(request)
        finally:
            # تنظيف بعد انتهاء الطلب
            try:
                del _local.request
            except AttributeError:
                pass
        return response


class RequestIDMiddleware:
    """يضيف معرف فريد لكل طلب ويوفره في header وللسجلات."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = uuid.uuid4().hex
        request.request_id = rid
        _local.request_id = rid
        start = time.perf_counter()
        try:
            response = self.get_response(request)
        finally:
            # expose timing data for logging filter
            duration_ms = (time.perf_counter() - start) * 1000
            _local.request_path = getattr(request, 'path', None)
            _local.request_duration_ms = duration_ms
        response["X-Request-ID"] = rid
        return response


class RequestTimingMiddleware:
    """يحفظ زمن التنفيذ النهائي في header (اختياري)."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response["X-Exec-Time-ms"] = f"{duration_ms:.1f}"
        return response


class SimpleRateLimitMiddleware:
    """محدد معدل بسيط يعتمد الذاكرة (DEV فقط).

    - يطبق حدًا افتراضيًا: 100 طلب / 60 ثانية لكل (IP + مسار مبسط) للمستخدم المجهول
      و 300 طلب / 60 ثانية للمستخدم المسجل.
    - في حالة تجاوز الحد يعاد 429.
    ملاحظات:
      * غير مناسب للإنتاج (لا يعتمد Redis / توزيع أفقي).
      * يتم تبسيط المسار بإزالة الأرقام (لتقليل التفريغ)."""

    WINDOW = 60
    LIMIT_ANON = 100
    LIMIT_AUTH = 300
    _buckets = {}

    def __init__(self, get_response):
        self.get_response = get_response

    def _key(self, request):
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        path = request.path
        # تبسيط: إزالة أرقام (IDs) لتجميع أفضل
        import re
        simple_path = re.sub(r'/\d+/', '/{id}/', path)
        user_part = 'auth' if getattr(request, 'user', None) and request.user.is_authenticated else 'anon'
        return f"{user_part}:{ip}:{simple_path}"

    def __call__(self, request):
        from django.conf import settings
        if not getattr(settings, 'DEBUG', False):
            return self.get_response(request)  # تفعيل فقط في التطوير حالياً
        key = self._key(request)
        now = time.time()
        bucket = self._buckets.get(key)
        limit = self.LIMIT_AUTH if (getattr(request, 'user', None) and request.user.is_authenticated) else self.LIMIT_ANON
        if not bucket:
            bucket = {'start': now, 'count': 0}
            self._buckets[key] = bucket
        # إعادة ضبط النافذة إذا انتهت
        if now - bucket['start'] > self.WINDOW:
            bucket['start'] = now
            bucket['count'] = 0
        bucket['count'] += 1
        if bucket['count'] > limit:
            from django.http import JsonResponse
            retry_after = int(self.WINDOW - (now - bucket['start']))
            return JsonResponse({'detail': 'Too Many Requests', 'retry_after': retry_after}, status=429)
        return self.get_response(request)

class AdvancedRateLimitMiddleware:
    """
    محدد معدل متقدم مع دعم:
    - حدود مختلفة حسب نوع المسار (API vs Web)
    - حماية من هجمات Brute Force على تسجيل الدخول
    - تنظيف تلقائي للذاكرة
    - دعم Redis في الإنتاج (اختياري)
    """
    
    # إعدادات افتراضية
    WINDOW = 60  # ثانية
    
    # حدود حسب نوع المسار
    LIMITS = {
        'api': {'anon': 60, 'auth': 300},       # API endpoints
        'login': {'anon': 5, 'auth': 20},        # محاولات تسجيل الدخول
        'password': {'anon': 3, 'auth': 10},     # طلبات إعادة كلمة المرور
        'default': {'anon': 100, 'auth': 500},   # صفحات الويب العادية
    }
    
    # مسارات حساسة
    SENSITIVE_PATHS = [
        '/accounts/login/',
        '/api/token/',
        '/api/auth/',
        '/accounts/password/',
    ]
    
    _buckets = {}
    _last_cleanup = time.time()
    CLEANUP_INTERVAL = 300  # تنظيف كل 5 دقائق
    
    def __init__(self, get_response):
        self.get_response = get_response
        self._lock = threading.Lock()
    
    def _get_client_ip(self, request):
        """الحصول على IP العميل الحقيقي (مع دعم Proxy)"""
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
    
    def _get_path_type(self, path):
        """تحديد نوع المسار للحصول على الحد المناسب"""
        if any(path.startswith(p) for p in self.SENSITIVE_PATHS):
            if 'login' in path or 'token' in path or 'auth' in path:
                return 'login'
            if 'password' in path:
                return 'password'
        if path.startswith('/api/'):
            return 'api'
        return 'default'
    
    def _key(self, request):
        ip = self._get_client_ip(request)
        path_type = self._get_path_type(request.path)
        user_type = 'auth' if getattr(request, 'user', None) and request.user.is_authenticated else 'anon'
        return f"{path_type}:{user_type}:{ip}"
    
    def _cleanup_old_buckets(self):
        """تنظيف البيانات القديمة لتقليل استخدام الذاكرة"""
        now = time.time()
        if now - self._last_cleanup < self.CLEANUP_INTERVAL:
            return
        
        with self._lock:
            if now - self._last_cleanup < self.CLEANUP_INTERVAL:
                return  # double check after lock
            
            keys_to_delete = []
            for key, bucket in self._buckets.items():
                if now - bucket.get('start', 0) > self.WINDOW * 2:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self._buckets[key]
            
            self._last_cleanup = now
    
    def __call__(self, request):
        from django.conf import settings
        
        # تفعيل/تعطيل من الإعدادات
        if not getattr(settings, 'RATE_LIMIT_ENABLED', True):
            return self.get_response(request)
        
        # تنظيف دوري
        self._cleanup_old_buckets()
        
        key = self._key(request)
        path_type = self._get_path_type(request.path)
        user_type = 'auth' if getattr(request, 'user', None) and request.user.is_authenticated else 'anon'
        
        # صفحات تسجيل الدخول وكلمة المرور: احسب فقط POST (محاولات الدخول الفعلية)
        # GET requests (مجرد فتح الصفحة أو redirect) لا تُعدّ كمحاولة
        if path_type in ('login', 'password') and request.method != 'POST':
            return self.get_response(request)
        
        limit = self.LIMITS.get(path_type, self.LIMITS['default']).get(user_type, 100)
        
        now = time.time()
        
        with self._lock:
            bucket = self._buckets.get(key)
            
            if not bucket:
                bucket = {'start': now, 'count': 0}
                self._buckets[key] = bucket
            
            # إعادة ضبط النافذة إذا انتهت
            if now - bucket['start'] > self.WINDOW:
                bucket['start'] = now
                bucket['count'] = 0
            
            bucket['count'] += 1
            current_count = bucket['count']
        
        if current_count > limit:
            from django.http import JsonResponse
            import logging
            
            retry_after = int(self.WINDOW - (now - bucket['start']))
            ip = self._get_client_ip(request)
            
            # تسجيل محاولات التجاوز للمراقبة الأمنية
            logging.getLogger('security').warning(
                f"Rate limit exceeded: {ip} on {request.path} "
                f"({current_count}/{limit} requests in {self.WINDOW}s)"
            )
            
            response = JsonResponse({
                'detail': 'طلبات كثيرة جداً. يرجى الانتظار.',
                'detail_en': 'Too Many Requests',
                'retry_after': retry_after
            }, status=429)
            response['Retry-After'] = str(retry_after)
            return response
        
        response = self.get_response(request)
        
        # إضافة headers معلوماتية
        response['X-RateLimit-Limit'] = str(limit)
        response['X-RateLimit-Remaining'] = str(max(0, limit - current_count))
        
        return response


# ============================================================================
# Strip Hidden Characters Middleware
# ============================================================================

class StripHiddenCharsMiddleware:
    """
    Strip invisible Unicode characters from request paths.
    
    This middleware removes zero-width characters and directional marks
    that can be accidentally included when copying URLs from RTL editors
    or documents with bidirectional text.
    """
    
    # Common invisible characters that can cause URL issues
    ZERO_WIDTH_CHARS = {
        "\u200e",  # Left-to-Right Mark (LRM)
        "\u200f",  # Right-to-Left Mark (RLM)
        "\ufeff",  # Zero Width No-Break Space (BOM)
        "\u200b",  # Zero Width Space
        "\u200c",  # Zero Width Non-Joiner
        "\u200d",  # Zero Width Joiner
        "\u2066",  # Left-to-Right Isolate
        "\u2067",  # Right-to-Left Isolate
        "\u2068",  # First Strong Isolate
        "\u2069",  # Pop Directional Isolate
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        from django.http import HttpResponsePermanentRedirect
        
        # Clean the path by removing invisible characters
        original_path = request.path_info
        cleaned_path = "".join(
            char for char in original_path 
            if char not in self.ZERO_WIDTH_CHARS
        )
        
        # If the path changed, redirect to the cleaned version
        if cleaned_path != original_path:
            # Preserve query string if present
            cleaned_url = cleaned_path
            if request.META.get('QUERY_STRING'):
                cleaned_url = f"{cleaned_path}?{request.META['QUERY_STRING']}"
            
            return HttpResponsePermanentRedirect(cleaned_url or "/")
        
        return self.get_response(request)


class SessionRecoveryMiddleware:
    """
    Middleware لمعالجة خطأ SessionInterrupted بشكل سلس.
    
    يحدث هذا الخطأ عندما:
    - يتم حذف الجلسة من قاعدة البيانات أثناء معالجة الطلب
    - المستخدم يسجل الخروج في طلب متزامن
    - الجلسة انتهت صلاحيتها
    
    الحل: إنشاء جلسة جديدة وإعادة تحميل الصفحة.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except SessionInterrupted:
            # تسجيل الحدث
            logger.warning(
                f"SessionInterrupted caught for path: {request.path}. "
                f"Creating new session."
            )
            
            # إنشاء جلسة جديدة
            request.session.create()
            
            # إعادة التوجيه لنفس الصفحة
            redirect_url = request.get_full_path()
            return HttpResponseRedirect(redirect_url)
    
    def process_exception(self, request, exception):
        """معالجة الاستثناء إذا حدث في مكان آخر"""
        if isinstance(exception, SessionInterrupted):
            logger.warning(
                f"SessionInterrupted exception for path: {request.path}. "
                f"Recovering session."
            )
            
            try:
                # محاولة إنشاء جلسة جديدة
                request.session.create()
            except Exception as e:
                logger.error(f"Failed to create new session: {e}")
            
            # إعادة التوجيه
            redirect_url = request.get_full_path()
            return HttpResponseRedirect(redirect_url)
        
        return None


class PerformanceMonitorMiddleware:
    """
    يجمع مقاييس أداء كل طلب ويسجلها في السجلات.
    Performance monitoring middleware that logs slow requests.
    """
    SLOW_THRESHOLD_MS = 500  # تحذير إذا تجاوز هذا الحد

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # تسجيل الطلبات البطيئة
        if duration_ms > self.SLOW_THRESHOLD_MS:
            logger.warning(
                "Slow request: %s %s took %.0fms (threshold: %dms)",
                request.method, request.path, duration_ms, self.SLOW_THRESHOLD_MS,
            )

        # إضافة header الأداء
        response['X-Response-Time'] = f"{duration_ms:.1f}ms"
        return response


class SecurityHeadersMiddleware:
    """
    يضيف security headers إضافية لكل استجابة.
    Extra security headers beyond Django's built-in SecurityMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Prevent MIME type sniffing
        response.setdefault('X-Content-Type-Options', 'nosniff')
        # Prevent clickjacking
        response.setdefault('X-Frame-Options', 'DENY')
        # XSS protection
        response.setdefault('X-XSS-Protection', '1; mode=block')
        # Referrer policy
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        # Permissions policy (disallow sensitive features by default)
        response.setdefault(
            'Permissions-Policy',
            'camera=(), microphone=(), geolocation=(self), payment=()'
        )
        return response


class SetupCheckMiddleware:
    """
    يتحقق من اكتمال إعداد النظام عند أول زيارة للمشرف.
    Shows setup warnings to admin users if critical config is missing.
    """

    # مسارات يتم تجاهلها
    SKIP_PATHS = ('/static/', '/media/', '/health/', '/api/', '/favicon.ico')

    def __init__(self, get_response):
        self.get_response = get_response
        self._checked = False

    def __call__(self, request):
        if (
            not self._checked
            and request.user.is_authenticated
            and request.user.is_staff
            and not any(request.path.startswith(p) for p in self.SKIP_PATHS)
        ):
            self._run_checks(request)
            self._checked = True  # فحص مرة واحدة فقط لكل عملية
        return self.get_response(request)

    def _run_checks(self, request):
        from django.conf import settings as _s
        import os

        warnings_list = []

        # فحص SECRET_KEY
        key = getattr(_s, 'SECRET_KEY', '')
        if 'insecure' in key.lower() or len(key) < 40:
            warnings_list.append('SECRET_KEY ضعيف — يرجى توليد مفتاح جديد.')

        # فحص DEBUG
        if getattr(_s, 'DEBUG', False):
            warnings_list.append('DEBUG مفعّل — يجب تعطيله في الإنتاج.')

        # فحص ALLOWED_HOSTS
        hosts = getattr(_s, 'ALLOWED_HOSTS', [])
        if '*' in hosts:
            warnings_list.append('ALLOWED_HOSTS يحتوي على * — يجب تحديد النطاقات.')

        # فحص قاعدة البيانات
        db_engine = _s.DATABASES.get('default', {}).get('ENGINE', '')
        if 'sqlite3' in db_engine and not getattr(_s, 'DEBUG', False):
            warnings_list.append('SQLite في الإنتاج — يُنصح بـ PostgreSQL.')

        for w in warnings_list:
            messages.warning(request, f'⚠️ {w}')


class ForcePasswordChangeMiddleware:
    """
    يفرض على المستخدمين تغيير كلمة المرور الافتراضية عند أول دخول.
    Forces users to change default passwords on first login.
    
    كلمات المرور الافتراضية المعروفة: admin123, password, 123456, admin, changeme
    """

    # كلمات المرور الافتراضية المعروفة
    DEFAULT_PASSWORDS = ['admin123', 'password', '123456', 'admin', 'changeme']

    # المسارات المسموح بها حتى بدون تغيير كلمة المرور
    EXEMPT_URLS = [
        '/admin/password_change/',
        '/accounts/password/change/',
        '/admin/logout/',
        '/accounts/logout/',
        '/static/',
        '/media/',
        '/health/',
        '/api/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        # Cache to avoid checking password on every request
        self._checked_users = set()

    def __call__(self, request):
        if request.user.is_authenticated:
            # Skip exempt URLs
            path = request.path
            for exempt_url in self.EXEMPT_URLS:
                if path.startswith(exempt_url):
                    return self.get_response(request)

            # Only check if not already verified in this session
            session_key = f'_pw_checked_{request.user.pk}'
            if not request.session.get(session_key):
                if self._needs_password_change(request.user):
                    messages.warning(
                        request,
                        '⚠️ يجب تغيير كلمة المرور الافتراضية لأسباب أمنية. '
                        'Please change your default password for security reasons.'
                    )
                    try:
                        return redirect(reverse('admin:password_change'))
                    except Exception:
                        return redirect('/admin/password_change/')
                else:
                    # Mark as checked so we don't re-check every request
                    request.session[session_key] = True

        return self.get_response(request)

    def _needs_password_change(self, user):
        """التحقق مما إذا كان المستخدم يستخدم كلمة مرور افتراضية"""
        for default_pw in self.DEFAULT_PASSWORDS:
            if user.check_password(default_pw):
                return True
        return False