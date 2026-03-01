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

# ===== إعدادات الأمان =====
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
