"""Production overrides for Tony ERP.

Use with DJANGO_SETTINGS_MODULE=accountant_pro.settings_production.
These settings harden security for internet-facing deployments.

Usage:
    export DJANGO_SETTINGS_MODULE=accountant_pro.settings_production
    python manage.py runserver  # or gunicorn
"""
from .settings import *  # noqa: F401,F403
import os

# ============================================================
# 🔴 Core Security
# ============================================================
DEBUG = False
ENVIRONMENT = 'production'

# Hosts and origins
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()] or ['localhost']
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]

# SECRET_KEY validation - must be set and strong in production
_prod_key = os.getenv('DJANGO_SECRET_KEY') or os.getenv('SECRET_KEY', '')
if 'insecure' in _prod_key.lower() or len(_prod_key) < 40:
    import warnings
    warnings.warn(
        "⚠️ SECRET_KEY غير آمن للإنتاج! "
        "ولّد مفتاح جديد: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"",
        RuntimeWarning,
        stacklevel=1,
    )

# ============================================================
# 🔒 HTTPS Hardening
# ============================================================
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('1', 'true', 'yes')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Cookies
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# ============================================================
# 🗄️ Database - PostgreSQL recommended for production
# ============================================================
# If DB_ENGINE=postgresql is set in .env, the base settings.py
# already configures PostgreSQL. Here we add production-specific
# connection pooling settings.
_db_engine = DATABASES.get('default', {}).get('ENGINE', '')
if 'sqlite3' in _db_engine:
    import warnings
    warnings.warn(
        "⚠️ SQLite detected in production! Strongly recommend PostgreSQL. "
        "Set DB_ENGINE=postgresql in your .env file.",
        RuntimeWarning,
        stacklevel=1,
    )

# Add connection persistence for PostgreSQL
if 'postgresql' in _db_engine:
    DATABASES['default']['CONN_MAX_AGE'] = int(os.getenv('DB_CONN_MAX_AGE', '600'))
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS']['connect_timeout'] = 10

# ============================================================
# 📦 Redis Cache - Production configuration
# ============================================================
# If Redis is available (detected by base settings), enhance config
if REDIS_AVAILABLE:
    CACHES['default']['OPTIONS'] = {
        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        'CONNECTION_POOL_KWARGS': {
            'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', '50')),
            'retry_on_timeout': True,
        },
        'SOCKET_CONNECT_TIMEOUT': 5,
        'SOCKET_TIMEOUT': 5,
        'IGNORE_EXCEPTIONS': True,
    }
    CACHES['default']['TIMEOUT'] = 300
    CACHES['default']['KEY_PREFIX'] = 'tony_erp_prod'

    # Use Redis for sessions in production
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'

# ============================================================
# 📊 Logging - Production: reduce noise, keep warnings/errors
# ============================================================
LOGGING['handlers']['console']['level'] = 'WARNING'
LOGGING['root']['level'] = 'WARNING'
LOGGING['loggers']['django']['level'] = 'WARNING'

# Add production-specific error notification handler
ADMINS = []
_admin_email = os.getenv('ADMIN_EMAIL')
if _admin_email:
    ADMINS.append(('Tony ERP Admin', _admin_email))
    LOGGING['handlers']['mail_admins'] = {
        'level': 'ERROR',
        'class': 'django.utils.log.AdminEmailHandler',
        'include_html': False,
    }
    LOGGING['loggers']['django.request'] = {
        'handlers': ['error_file', 'mail_admins'],
        'level': 'ERROR',
        'propagate': False,
    }

MANAGERS = ADMINS

# ============================================================
# 🚀 Performance
# ============================================================
# Remove debug toolbar if present
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'debug_toolbar']
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m]

# Template caching
for _tmpl in TEMPLATES:
    _tmpl_opts = _tmpl.get('OPTIONS', {})
    if _tmpl.get('APP_DIRS'):
        _tmpl['OPTIONS']['loaders'] = [
            ('django.template.loaders.cached.Loader', [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]),
        ]
        _tmpl.pop('APP_DIRS', None)

# File upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ============================================================
# 📧 Email - Production SMTP
# ============================================================
if os.getenv('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes')
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@tony-erp.com')
    SERVER_EMAIL = os.getenv('SERVER_EMAIL', 'server@tony-erp.com')

# Static files: base settings already configure STATIC_ROOT/STATICFILES_STORAGE via Whitenoise
