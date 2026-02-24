from functools import wraps
from typing import Optional, Callable

from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect


def _wants_json(request: HttpRequest) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept or request.headers.get("x-requested-with") == "XMLHttpRequest" or \
        request.path.startswith("/api/")


def _forbidden_response(request: HttpRequest, message: str = 'غير مسموح لك بالوصول لهذه الصفحة') -> HttpResponse:
    if _wants_json(request):
        return JsonResponse({'error': message, 'code': 'permission_denied'}, status=403)
    return HttpResponseForbidden(message)


def require_module_perm(module: str, action: str) -> Callable:
    """Decorator: require module-level permission (users.models.user_has_permission).

    Usage:
        @require_module_perm('sales', 'view')
        def my_view(request): ...
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs):
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                # Redirect to login for normal requests, 403 for API
                if _wants_json(request):
                    return _forbidden_response(request)
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())

            try:
                from users.models import ModulePermission, UserProfile
                profile = UserProfile.objects.select_related('role').filter(user=user).first()
                if profile and profile.role:
                    allowed = ModulePermission.objects.filter(
                        role=profile.role, module=module, action=action, is_allowed=True
                    ).exists()
                elif user.is_superuser:
                    allowed = True
                else:
                    allowed = False
            except Exception:
                allowed = False

            if not allowed:
                return _forbidden_response(request)
            return view_func(request, *args, **kwargs)

        return _wrapped
    return decorator


def require_resource_perm(module: str, resource: str, action: str) -> Callable:
    """Decorator: require resource-level permission when defined, with fallback to module-level.

    Usage:
        @require_resource_perm('sales', 'invoice_create', 'add')
        def create_invoice(request): ...
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs):
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                if _wants_json(request):
                    return _forbidden_response(request)
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())

            try:
                from users.models import ResourcePermission, UserProfile
                profile = UserProfile.objects.select_related('role').filter(user=user).first()
                if profile and profile.role:
                    allowed = ResourcePermission.objects.filter(
                        role=profile.role, module=module, resource=resource, action=action, is_allowed=True
                    ).exists()
                elif user.is_superuser:
                    allowed = True
                else:
                    allowed = False
            except Exception:
                allowed = False

            if not allowed:
                return _forbidden_response(request)
            return view_func(request, *args, **kwargs)

        return _wrapped
    return decorator


class PermissionRequiredMixin:
    """CBV mixin to enforce permissions.

    Set either:
      - permission_module and permission_action (module-level), or
      - permission_module, permission_resource and permission_action (resource-level)
    """

    permission_module: Optional[str] = None
    permission_action: Optional[str] = None
    permission_resource: Optional[str] = None

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        module = getattr(self, 'permission_module', None)
        action = getattr(self, 'permission_action', None)
        resource = getattr(self, 'permission_resource', None)

        if not module or not action:
            # If not configured, allow through (developer oversight). Prefer explicit.
            return super().dispatch(request, *args, **kwargs)

        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            if _wants_json(request):
                return _forbidden_response(request)
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        try:
            if resource:
                allowed = user.has_resource_permission(module, resource, action)
            else:
                allowed = user.has_module_permission(module, action)
        except Exception:
            allowed = False

        if not allowed:
            return _forbidden_response(request)

        return super().dispatch(request, *args, **kwargs)
