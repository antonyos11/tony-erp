"""
Middleware لحل مشكلة CSRF مؤقتاً
"""
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.csrf import csrf_exempt


class DisableCSRFOnLogin(MiddlewareMixin):
    """تعطيل CSRF على صفحة تسجيل الدخول مؤقتاً"""
    
    CSRF_EXEMPT_PATHS = [
        '/accounts/login/',
        '/login/',
        '/api/auth/login/',
        '/api/token/',
        '/api/token/refresh/',
    ]
    
    def process_request(self, request):
        # تحقق من المسار
        path = request.path
        if any(path.startswith(exempt_path) or path == exempt_path for exempt_path in self.CSRF_EXEMPT_PATHS):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        # طريقة ثانية للتأكد من تعطيل CSRF
        path = request.path
        if any(path.startswith(exempt_path) or path == exempt_path for exempt_path in self.CSRF_EXEMPT_PATHS):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
