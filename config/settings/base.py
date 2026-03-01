"""
RITA ERP — الإعدادات الأساسية المشتركة
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ===== المسارات =====
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# تحميل ملف .env
load_dotenv(BASE_DIR / '.env')

# ===== الأمان =====
SECRET_KEY = os.getenv('SECRET_KEY', 'unsafe-default-secret-key-change-in-production')

# ===== التطبيقات =====
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'crispy_forms',
    'crispy_bootstrap5',
]

LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.inventory',
    'apps.production',
    'apps.sales',
    'apps.partners',
    'apps.purchases',
    'apps.authorization',
    'apps.reports',
    'apps.treasury',
    'apps.installments',
    'apps.printing',
    'apps.delivery',
    'apps.warranty',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ===== Middleware =====
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.authorization.middleware.AuditMiddleware',
    'apps.authorization.middleware.PermissionMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ===== Templates =====
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ===== نموذج المستخدم =====
AUTH_USER_MODEL = 'core.User'

# ===== كلمات المرور =====
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===== التوطين =====
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ===== الملفات الثابتة =====
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ===== ملفات الوسائط =====
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ===== المفتاح الافتراضي =====
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===== Crispy Forms =====
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ===== تسجيل الدخول =====
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'
