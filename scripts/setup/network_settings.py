# إعدادات خاصة بالشبكة المحلية
"""
هذا الملف يحتوي على إعدادات Django المحسنة للعمل على الشبكة المحلية
يتم استيراده تلقائياً عند تشغيل النظام على الشبكة
"""

# إعدادات الأمان للشبكة المحلية
from pathlib import Path

# تعريف BASE_DIR بشكل صحيح
BASE_DIR = Path(__file__).resolve().parent

DEBUG = False  # حتى في الشبكة المحلية، نبقي DEBUG مغلق للأمان

# السماح بجميع العناوين على الشبكة المحلية
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    # عناوين الشبكة المحلية الشائعة
    '192.168.1.*',
    '192.168.0.*',
    '192.168.100.*',
    '10.0.0.*',
    '172.16.*',
]

# إعدادات الجلسة للشبكة المحلية
SESSION_COOKIE_AGE = 8 * 60 * 60  # 8 ساعات
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # عدم انتهاء الجلسة عند إغلاق المتصفح
SESSION_SAVE_EVERY_REQUEST = True

# إعدادات الأمان المناسبة للشبكة المحلية
SECURE_SSL_REDIRECT = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'  # السماح بـ frames من نفس الموقع

# إعدادات قاعدة البيانات محسنة للشبكة المحلية
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,  # زيادة timeout للشبكة
        }
    }
}

# إعدادات التخزين المؤقت للشبكة المحلية
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'local-network-cache',
        'TIMEOUT': 300,  # 5 دقائق
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# إعدادات التسجيل المحسنة للشبكة المحلية
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} [{name}] {message}',
            'style': '{',
        },
        'network': {
            'format': '[{asctime}] {levelname} - {message} (IP: {extra[ip]|default:"unknown"})',
            'style': '{',
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'network_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'network.log',
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'network_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.security': {
            'handlers': ['console', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'network': {
            'handlers': ['console', 'network_file'],
            'level': 'INFO',
            'propagate': False,
        }
    },
}

# إعدادات إضافية للأداء على الشبكة المحلية
USE_TZ = True
TIME_ZONE = 'Africa/Cairo'

# ضغط الاستجابات لتحسين الأداء على الشبكة
USE_GZIP = True

# إعدادات المحتوى الثابت
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# إعدادات خاصة بالمستخدمين على الشبكة المحلية
USER_SESSION_TIMEOUT = 8 * 60 * 60  # 8 ساعات
MAX_FAILED_LOGIN_ATTEMPTS = 10  # زيادة عدد المحاولات المسموحة
LOCKOUT_TIME = 30 * 60  # 30 دقيقة

# إعدادات التحقق من IP للشبكة المحلية
ALLOWED_IP_RANGES = [
    '192.168.0.0/16',   # شبكات محلية
    '10.0.0.0/8',       # شبكات محلية
    '172.16.0.0/12',    # شبكات محلية
    '127.0.0.0/8',      # localhost
]

# تخصيص رسائل النظام
SYSTEM_MESSAGES = {
    'welcome': 'مرحباً بك في نظام الشامل للمحاسبة والإدارة',
    'network_mode': 'النظام يعمل في وضع الشبكة المحلية',
    'admin_contact': 'للدعم التقني، يرجى التواصل مع مدير النظام',
}

# إعدادات النسخ الاحتياطي التلقائي (اختيارية)
AUTO_BACKUP = {
    'enabled': True,
    'interval_hours': 24,  # كل 24 ساعة
    'backup_path': BASE_DIR / 'backups',
    'keep_backups': 7,  # الاحتفاظ بـ 7 نسخ
}

def get_client_ip(request):
    """دالة مساعدة للحصول على IP العميل في الشبكة المحلية"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def is_local_network_ip(ip):
    """فحص إذا كان IP ضمن الشبكة المحلية"""
    import ipaddress
    
    try:
        ip_addr = ipaddress.ip_address(ip)
        for range_str in ALLOWED_IP_RANGES:
            if ip_addr in ipaddress.ip_network(range_str):
                return True
        return False
    except:
        return False