"""
Middleware للصلاحيات وسجل التدقيق — RITA ERP
"""
import logging

from django.http import HttpResponseForbidden
from django.shortcuts import render

from apps.authorization.services.audit import log_action, get_client_ip

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """يسجل كل request في سجل التدقيق (POST/PUT/PATCH/DELETE فقط)"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # نسجل فقط الـ requests اللي بتعدل بيانات
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            if request.user and request.user.is_authenticated:
                try:
                    # نتجاهل بعض المسارات (مثل static, admin)
                    path = request.path
                    if not path.startswith(('/static/', '/media/', '/admin/jsi18n/')):
                        action = 'create' if request.method == 'POST' else 'update'
                        if request.method == 'DELETE':
                            action = 'delete'

                        log_action(
                            user=request.user,
                            action=action,
                            module=self._get_module_from_path(path),
                            model_name=path,
                            description=f'{request.method} {path}',
                            ip_address=get_client_ip(request),
                            branch=getattr(request.user, 'branch', None),
                        )
                except Exception as e:
                    logger.error(f'خطأ في AuditMiddleware: {e}')

        return response

    @staticmethod
    def _get_module_from_path(path):
        """استخراج اسم القسم من المسار"""
        parts = path.strip('/').split('/')
        if parts:
            module_map = {
                'accounts': 'accounts',
                'inventory': 'inventory',
                'production': 'production',
                'sales': 'sales',
                'purchases': 'purchases',
                'authorization': 'settings',
                'admin': 'settings',
                'auth': 'settings',
            }
            return module_map.get(parts[0], parts[0])
        return 'unknown'


# ═══════════════════════════════════════════════════════════════
# Sprint 22A — ServerEnforcementMiddleware
# ═══════════════════════════════════════════════════════════════

class ServerEnforcementMiddleware:
    """
    طبقة الحماية في السيرفر
    ══════════════════════════════
    حتى لو حد كتب URL يدوي — النظام يمنعه
    """

    MODULE_MAP = {
        '/accounts/': 'accounts',
        '/inventory/': 'inventory',
        '/production/': 'production',
        '/sales/': 'sales',
        '/purchases/': 'purchases',
        '/hr/': 'hr',
        '/crm/': 'crm',
        '/quotations/': 'quotations',
        '/treasury/': 'treasury',
        '/expenses/': 'expenses',
        '/delivery/': 'delivery',
        '/warranty/': 'warranty',
        '/reports/': 'reports',
        '/authorization/': 'authorization',
        '/notifications/': 'notifications',
    }

    EXEMPT_PREFIXES = [
        '/', '/auth/', '/admin/', '/api/', '/static/', '/media/',
        '/search/', '/profile/', '/switch-branch/', '/production/display/',
        '/authorization/',  # Sprint 22A Part 2 exemption added below
        '/users/', '/delegations/',  # يُدار بـ DelegationEngine   # تُدار صلاحياتها على مستوى الـ views مثل PermissionMiddleware القديم
    ]
    EXEMPT_EXACT = ['/', '/auth/login/', '/auth/logout/']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        if request.user.is_superuser:
            return self.get_response(request)

        path = request.path

        if path in self.EXEMPT_EXACT:
            return self.get_response(request)
        for prefix in self.EXEMPT_PREFIXES:
            if path == prefix or (prefix != '/' and path.startswith(prefix)):
                return self.get_response(request)

        module = None
        for prefix, mod in self.MODULE_MAP.items():
            if path.startswith(prefix):
                module = mod
                break

        if path.startswith('/branches/') or path.startswith('/warehouses/') or path.startswith('/users/'):
            module = 'settings'

        if not module:
            return self.get_response(request)

        action = 'view' if request.method == 'GET' else 'create'

        from apps.authorization.services.permission_engine import PermissionEngine
        from django.contrib import messages
        from django.shortcuts import redirect

        if not PermissionEngine.has_any_module_access(request.user, module):
            PermissionEngine.log_violation(
                user=request.user,
                url=path,
                module=module,
                action=action,
                request=request,
            )
            messages.error(request, "⛔ ليس لديك صلاحية للوصول لهذا القسم")
            return redirect('core:dashboard')

        return self.get_response(request)


class PermissionMiddleware:
    """يتحقق من الصلاحيات حسب الـ URL"""

    # تعيين المسارات للوحدات والإجراءات
    URL_PERMISSION_MAP = {
        # accounts
        '/accounts/': ('accounts', 'view'),
        '/accounts/account/create/': ('accounts', 'create'),
        '/accounts/journals/create/': ('accounts', 'create'),
        '/accounts/reports/': ('reports', 'view'),
        # inventory
        '/inventory/': ('inventory', 'view'),
        '/inventory/products/create/': ('inventory', 'create'),
        '/inventory/receive/': ('inventory', 'create'),
        '/inventory/issue/': ('inventory', 'create'),
        '/inventory/transfer/': ('inventory', 'edit'),
        '/inventory/adjustment/': ('inventory', 'edit'),
        # production
        '/production/': ('production', 'view'),
        '/production/orders/create/': ('production', 'create'),
        # sales
        '/sales/': ('sales', 'view'),
        '/sales/invoices/create/': ('sales', 'create'),
        '/sales/customers/create/': ('sales', 'create'),
        '/sales/returns/create/': ('sales', 'create'),
        # purchases
        '/purchases/': ('purchases', 'view'),
        '/purchases/orders/create/': ('purchases', 'create'),
        '/purchases/suppliers/create/': ('purchases', 'create'),
    }

    # المسارات اللي ما محتاجة صلاحيات
    EXEMPT_PATHS = [
        '/',
        '/auth/',
        '/admin/',
        '/static/',
        '/media/',
        '/authorization/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # تجاهل المسارات المستثناة
        path = request.path
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt) or path == '/':
                return self.get_response(request)

        # تجاهل المستخدمين غير المسجلين (LoginRequired هيتعامل معاهم)
        if not request.user or not request.user.is_authenticated:
            return self.get_response(request)

        # المشرفون لديهم كل الصلاحيات
        if request.user.is_superuser:
            return self.get_response(request)

        # التحقق من الصلاحيات بناءً على المسار
        from apps.authorization.services.permission_engine import PermissionEngine

        # نبحث عن أطول مسار مطابق
        matched_permission = None
        matched_length = 0
        for url_pattern, perm in self.URL_PERMISSION_MAP.items():
            if path.startswith(url_pattern) and len(url_pattern) > matched_length:
                matched_permission = perm
                matched_length = len(url_pattern)

        if matched_permission:
            module, action = matched_permission
            if not PermissionEngine.has_permission(request.user, module, action):
                # تسجيل محاولة الوصول المرفوضة
                try:
                    log_action(
                        user=request.user,
                        action='permission_denied',
                        module=module,
                        model_name=path,
                        description=f'رفض وصول: {module}.{action} — {path}',
                        ip_address=get_client_ip(request),
                        branch=getattr(request.user, 'branch', None),
                    )
                except Exception:
                    pass

                return render(request, 'authorization/permission_denied.html', {
                    'module': module,
                    'action': action,
                    'path': path,
                }, status=403)

        return self.get_response(request)


# ═══════════════════════════════════════════════════════════════
# Sprint 25 — Content Security Policy Middleware
# ═══════════════════════════════════════════════════════════════

class ContentSecurityPolicyMiddleware:
    """
    إضافة Content-Security-Policy headers إلى كل Response
    يحمي من XSS وCode Injection
    """

    CSP_POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com; "
        "font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = self.CSP_POLICY
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response


# ═══════════════════════════════════════════════════════════════
# Sprint 25 — Brute Force Request Middleware
# ═══════════════════════════════════════════════════════════════

class BruteForceMiddleware:
    """
    Middleware يعترض طلبات تسجيل الدخول ويتحقق من قفل الحساب
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        """قبل تنفيذ الـ view — تحقق من قفل الحساب"""
        if request.method == 'POST' and request.path in ('/auth/login/', '/accounts/login/'):
            username = request.POST.get('username', '')
            ip = get_client_ip(request)
            from apps.authorization.security import check_brute_force
            state = check_brute_force(username, ip)
            if state['locked']:
                from django.contrib import messages
                messages.error(
                    request,
                    f"⛔ تم تجميد الحساب بسبب تكرار المحاولات الخاطئة. "
                    f"يُرجى المحاولة بعد {state['remaining_minutes']} دقيقة."
                )
                return render(request, 'registration/login.html', {
                    'locked': True,
                    'remaining_minutes': state['remaining_minutes'],
                }, status=429)
        return None
