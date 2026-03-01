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
