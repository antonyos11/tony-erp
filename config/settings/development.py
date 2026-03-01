"""
RITA ERP — إعدادات بيئة التطوير
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

# ===== قاعدة بيانات التطوير (SQLite) =====
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ===== Django Debug Toolbar (اختياري) =====
# INSTALLED_APPS += ['debug_toolbar']
