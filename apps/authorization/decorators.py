"""
Decorators للصلاحيات — RITA ERP
"""
from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import render

from apps.authorization.services.permission_engine import PermissionEngine
from apps.authorization.services.audit import log_action, get_client_ip


def require_permission(module, action):
    """
    Decorator للتحقق من صلاحية محددة
    الاستخدام: @require_permission('sales', 'create')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # لو View بتاع class-based، الـ request هيكون أول argument
            # نتعامل مع الحالتين
            actual_request = request
            if hasattr(request, 'request'):
                actual_request = request.request

            if not actual_request.user or not actual_request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(actual_request.get_full_path())

            if actual_request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            if not PermissionEngine.has_permission(actual_request.user, module, action):
                # تسجيل رفض الصلاحية
                try:
                    log_action(
                        user=actual_request.user,
                        action='permission_denied',
                        module=module,
                        description=f'رفض وصول: {module}.{action}',
                        ip_address=get_client_ip(actual_request),
                        branch=getattr(actual_request.user, 'branch', None),
                    )
                except Exception:
                    pass

                return render(actual_request, 'authorization/permission_denied.html', {
                    'module': module,
                    'action': action,
                }, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def require_role(role_level):
    """
    Decorator للتحقق من أن المستخدم عنده دور بمستوى معين
    الاستخدام: @require_role('cfo')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            actual_request = request
            if hasattr(request, 'request'):
                actual_request = request.request

            if not actual_request.user or not actual_request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(actual_request.get_full_path())

            if actual_request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            if not PermissionEngine.has_role_level(actual_request.user, role_level):
                try:
                    log_action(
                        user=actual_request.user,
                        action='permission_denied',
                        module='authorization',
                        description=f'رفض وصول: يتطلب دور {role_level}',
                        ip_address=get_client_ip(actual_request),
                        branch=getattr(actual_request.user, 'branch', None),
                    )
                except Exception:
                    pass

                return render(actual_request, 'authorization/permission_denied.html', {
                    'required_role': role_level,
                }, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


class PermissionRequiredMixin:
    """
    Mixin للـ Class-Based Views للتحقق من الصلاحيات
    الاستخدام:
        class MyView(PermissionRequiredMixin, ListView):
            permission_module = 'sales'
            permission_action = 'view'
    """
    permission_module = None
    permission_action = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if self.permission_module and self.permission_action:
            if not PermissionEngine.has_permission(
                request.user, self.permission_module, self.permission_action
            ):
                try:
                    log_action(
                        user=request.user,
                        action='permission_denied',
                        module=self.permission_module,
                        description=f'رفض وصول: {self.permission_module}.{self.permission_action}',
                        ip_address=get_client_ip(request),
                        branch=getattr(request.user, 'branch', None),
                    )
                except Exception:
                    pass

                return render(request, 'authorization/permission_denied.html', {
                    'module': self.permission_module,
                    'action': self.permission_action,
                }, status=403)

        return super().dispatch(request, *args, **kwargs)
