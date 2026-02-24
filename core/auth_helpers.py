"""
مساعد للمصادقة المزدوجة (Session + JWT)
Dual authentication helper (supports both session and JWT auth)
"""
from functools import wraps
from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


def login_or_jwt_required(view_func):
    """
    ديكوريتر يقبل المصادقة عبر الجلسة (Session) أو JWT Bearer Token.
    يُستخدم بدلاً من @login_required للـ API endpoints التي يجب أن تدعم كلا النوعين.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 1) إذا المستخدم مسجّل عبر الجلسة → سماح
        if request.user and request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

        # 2) محاولة المصادقة عبر JWT
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            jwt_auth = JWTAuthentication()
            try:
                validated = jwt_auth.authenticate(request)
                if validated:
                    request.user, _ = validated
                    return view_func(request, *args, **kwargs)
            except (InvalidToken, TokenError):
                return JsonResponse(
                    {'success': False, 'error': 'Invalid or expired token'},
                    status=401,
                )

        # 3) لا جلسة ولا JWT → 401
        return JsonResponse(
            {'success': False, 'error': 'Authentication required'},
            status=401,
        )

    return wrapper
