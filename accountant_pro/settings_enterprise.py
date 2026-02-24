# ====================================================================
# Tony ERP - Enterprise Settings
# إعدادات الشركات الكبيرة - High Performance & Scalability
# ====================================================================
# هذا الملف مُعد للشركات الكبيرة التي تحتاج:
# - أداء عالي جداً
# - آلاف المستخدمين المتزامنين  
# - ملايين السجلات
# - فروع/معارض متعددة
# - تدقيق شامل وأمان متقدم
# ====================================================================

import os
from .settings import *

# ====================================================================
# 🏢 Enterprise Mode
# ====================================================================
ENTERPRISE_MODE = True
ENVIRONMENT = 'enterprise'

# ====================================================================
# 🔐 الأمان المتقدم - ADVANCED SECURITY
# ====================================================================

DEBUG = False

# أوقات انتهاء الجلسة
SESSION_COOKIE_AGE = 3600  # ساعة واحدة
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# HTTPS فقط
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# حماية إضافية
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_HTTPONLY = True

# تشفير كلمات المرور المتقدم
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

# ====================================================================
# 🗄️ قاعدة البيانات - PostgreSQL Enterprise
# ====================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'tony_erp'),
        'USER': os.environ.get('DB_USER', 'tony_erp'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        
        # Connection Pooling للأداء العالي
        'CONN_MAX_AGE': 600,  # إعادة استخدام الاتصالات 10 دقائق
        'CONN_HEALTH_CHECKS': True,
        
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30 ثانية timeout
        },
    },
    
    # قاعدة بيانات للقراءة فقط (Replica) - اختياري
    # 'replica': {
    #     'ENGINE': 'django.db.backends.postgresql',
    #     'NAME': os.environ.get('DB_NAME', 'tony_erp'),
    #     'USER': os.environ.get('DB_REPLICA_USER', 'tony_erp_read'),
    #     'PASSWORD': os.environ.get('DB_REPLICA_PASSWORD'),
    #     'HOST': os.environ.get('DB_REPLICA_HOST', 'localhost'),
    #     'PORT': os.environ.get('DB_REPLICA_PORT', '5432'),
    # },
}

# ====================================================================
# ⚡ التخزين المؤقت - Redis Enterprise
# ====================================================================

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'tony_erp',
        'TIMEOUT': 300,  # 5 دقائق افتراضي
    },
    
    # Cache خاص للجلسات
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_SESSIONS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'session',
        'TIMEOUT': 3600,
    },
    
    # Cache للتقارير الثقيلة
    'reports': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_REPORTS_URL', 'redis://localhost:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'report',
        'TIMEOUT': 3600,  # ساعة للتقارير
    },
}

# استخدام Redis للجلسات
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'

# ====================================================================
# 🔄 Celery - المهام الخلفية
# ====================================================================

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/3')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/4')

# إعدادات متقدمة
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = 300  # 5 دقائق
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 دقائق

# قوائم انتظار متعددة
CELERY_TASK_ROUTES = {
    'reports.*': {'queue': 'reports'},
    'notifications.*': {'queue': 'notifications'},
    'backups.*': {'queue': 'backups'},
    '*': {'queue': 'default'},
}

# مهام مجدولة
CELERY_BEAT_SCHEDULE = {
    'daily-backup': {
        'task': 'core.tasks.daily_backup',
        'schedule': 86400,  # يومياً
    },
    'cleanup-old-sessions': {
        'task': 'core.tasks.cleanup_sessions',
        'schedule': 3600,  # كل ساعة
    },
    'generate-daily-reports': {
        'task': 'reports.tasks.generate_daily_reports',
        'schedule': 86400,
    },
}

# ====================================================================
# 📊 تحسينات الأداء
# ====================================================================

# Query Optimization
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760

# Template Caching
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# ====================================================================
# 🏪 دعم الفروع المتعددة - Multi-Branch
# ====================================================================

MULTI_BRANCH_ENABLED = True
MAX_BRANCHES_PER_COMPANY = 100
BRANCH_DATA_ISOLATION = True  # عزل البيانات بين الفروع

# ====================================================================
# 📝 التدقيق الشامل - Audit Logging
# ====================================================================

AUDIT_LOGGING_ENABLED = True
AUDIT_LOG_ALL_MODELS = True
AUDIT_LOG_RETENTION_DAYS = 365 * 5  # 5 سنوات
AUDIT_LOG_INCLUDE_REQUEST_DATA = True

# ====================================================================
# 🔒 Rate Limiting - تحديد معدل الطلبات
# ====================================================================

# إضافة throttling للـ API
REST_FRAMEWORK.update({
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'reports': '50/hour',  # التقارير الثقيلة
        'exports': '20/hour',  # تصدير البيانات
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,
    'MAX_PAGE_SIZE': 500,
})

# ====================================================================
# 📧 البريد الإلكتروني - Enterprise Email
# ====================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@tonyerp.com')

# ====================================================================
# 📁 التخزين - Cloud Storage (اختياري)
# ====================================================================

# AWS S3 للملفات (اختياري)
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
# AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_BUCKET_NAME')
# AWS_S3_REGION_NAME = os.environ.get('AWS_REGION', 'me-south-1')

# ====================================================================
# 📋 التسجيل - Enterprise Logging
# ====================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'enterprise.log',
            'maxBytes': 52428800,  # 50MB
            'backupCount': 20,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'maxBytes': 52428800,
            'backupCount': 50,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 52428800,
            'backupCount': 100,
            'formatter': 'json',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'audit': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ====================================================================
# 👥 المسؤولين - Admins
# ====================================================================

ADMINS = [
    ('System Admin', os.environ.get('ADMIN_EMAIL', 'admin@company.com')),
]
MANAGERS = ADMINS

# ====================================================================
# 🎯 ميزات Enterprise
# ====================================================================

ENTERPRISE_FEATURES = {
    'two_factor_auth': True,
    'ip_whitelist': True,
    'advanced_permissions': True,
    'custom_roles': True,
    'data_encryption': True,
    'audit_trail': True,
    'multi_currency': True,
    'multi_language': True,
    'api_access': True,
    'custom_reports': True,
    'scheduled_reports': True,
    'data_export': True,
    'bulk_operations': True,
    'approval_workflows': True,
}

print("=" * 70)
print("🏢 ENTERPRISE MODE ACTIVE - Tony ERP")
print("   High Performance | Multi-Branch | Advanced Security")
print("=" * 70)
