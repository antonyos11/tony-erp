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
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'corsheaders',
    'drf_spectacular',
]

LOCAL_APPS = [
    'apps.core',
    'apps.api',
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
    'apps.hr',
    'apps.quotations',
    'apps.expenses',
    'apps.notifications',
    'apps.crm',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ===== Middleware =====
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.authorization.middleware.AuditMiddleware',
    'apps.authorization.middleware.BruteForceMiddleware',
    'apps.authorization.middleware.ContentSecurityPolicyMiddleware',
    'apps.authorization.middleware.ServerEnforcementMiddleware',
    'apps.authorization.middleware.PermissionMiddleware',
    'apps.core.middleware.BranchMiddleware',
    'apps.core.middleware.SetupWizardMiddleware',
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
                'apps.core.context_processors.branch_context',
                'apps.core.context_processors.notification_context',
                'apps.core.context_processors.dynamic_menu',
                'apps.core.context_processors.company_context',
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

# ===== Django REST Framework =====
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8080',
]

# ===== drf-spectacular =====
SPECTACULAR_SETTINGS = {
    'TITLE': 'RITA ERP API',
    'DESCRIPTION': 'API لنظام RITA ERP الصناعي',
    'VERSION': '1.0.0',
}

# ===== تسجيل الدخول =====
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# ===== Session (Sprint 20) =====
SESSION_COOKIE_AGE = 3600 * 8   # 8 ساعات
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ===== Cache — Sprint 25 =====
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'rita-erp-cache',
        'TIMEOUT': 1800,
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
        },
    }
}

# ===== Logging — Sprint 25 =====
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file_security': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': str(BASE_DIR / 'logs' / 'security.log'),
            'formatter': 'verbose',
        },
        'file_app': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': str(BASE_DIR / 'logs' / 'app.log'),
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'apps.authorization': {
            'handlers': ['file_security', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['file_app'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
