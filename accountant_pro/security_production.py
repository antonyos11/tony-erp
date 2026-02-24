"""
إعدادات أمان بيئة الإنتاج - Tony ERP
يتم تفعيلها فقط عندما DJANGO_ENV=production

الاستخدام: أضف في نهاية settings.py:
    try:
        from accountant_pro.security_production import *  # noqa: F401,F403
    except ImportError:
        pass
"""
import os

if os.environ.get('DJANGO_ENV') == 'production':
    # HTTPS / HSTS
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # سنة
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Cookies
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_AGE = 28800  # 8 ساعات
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True

    # Security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

    # Debug OFF
    DEBUG = False

    # Secret key from environment
    _sk = os.environ.get('DJANGO_SECRET_KEY')
    if _sk:
        SECRET_KEY = _sk

    # Allowed hosts from environment
    _hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
    if _hosts:
        ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',') if h.strip()]
