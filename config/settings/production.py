"""
RITA ERP — إعدادات بيئة الإنتاج
"""
import os
from .base import *

DEBUG = False

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

# ===== قاعدة بيانات الإنتاج (PostgreSQL) =====
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'rita_erp_db'),
        'USER': os.getenv('DB_USER', 'rita_erp_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# ===== الملفات الثابتة والوسائط =====
STATIC_ROOT  = '/var/www/rita-erp/staticfiles/'
MEDIA_ROOT   = '/var/www/rita-erp/media/'
STATIC_URL   = '/static/'
MEDIA_URL    = '/media/'

# ===== إعدادات الأمان — Sprint 25 =====
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTPS Enforcement
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000          # سنة كاملة
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",   # Bootstrap + inline scripts
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "fonts.googleapis.com",
)
CSP_FONT_SRC = (
    "'self'",
    "fonts.gstatic.com",
    "cdnjs.cloudflare.com",
)
CSP_IMG_SRC = ("'self'", "data:", "blob:")
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)

# Brute Force — إعدادات Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'rita-erp-cache',
        'TIMEOUT': 3600,
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
        },
    }
}

# Session Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
