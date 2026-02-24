"""
Django settings for accountant_pro project.

نظام Tony ERP - إعدادات شاملة للإنتاج والتطوير
"""

from pathlib import Path
import os
import sys
try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    from typing import IO
    from os import PathLike
    # Provide an identical signature to the real python-dotenv load_dotenv to satisfy mypy conditional definition rules
    def load_dotenv(
        dotenv_path: str | PathLike[str] | None = None,
        stream: IO[str] | None = None,
        verbose: bool = False,
        override: bool = False,
        interpolate: bool = True,
        encoding: str | None = None,
    ) -> bool:  # fallback no-op
        return False
from datetime import timedelta
import dj_database_url
import logging
import json
try:
    from core.utils.console import safe_print
except Exception:  # fallback minimal
    from typing import Any
    def safe_print(*args: Any, **kwargs: Any) -> None:  # pragma: no cover
        try:
            print(*args, **kwargs)
        except UnicodeEncodeError:
            cleaned = []
            for a in args:
                try:
                    s = str(a)
                except Exception:
                    s = repr(a)
                s2 = ''.join(ch for ch in s if ord(ch) < 128 or s.isalnum() or s.isspace())
                cleaned.append(s2)
            try:
                print(*cleaned, **kwargs)
            except Exception:
                pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
env_path = BASE_DIR / ".env"
if os.environ.get('ERP_STARTUP_DEBUG'):
    safe_print('[settings] BASE_DIR =', BASE_DIR)
    safe_print('[settings] Attempting to load .env at', env_path)
loaded_env = load_dotenv(env_path)
if os.environ.get('ERP_STARTUP_DEBUG'):
    safe_print(f'[settings] .env exists? {env_path.exists()} loaded={loaded_env}')

# Force UTF-8 console where possible (Windows PowerShell / cmd often default cp1252)
try:  # pragma: no cover - environment dependent
    if hasattr(sys.stdout, "reconfigure"):
            if hasattr(sys.stdout, "reconfigure") and callable(getattr(sys.stdout, "reconfigure", None)): sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # pragma: no cover
    if hasattr(sys.stderr, "reconfigure"):
            if hasattr(sys.stderr, "reconfigure") and callable(getattr(sys.stderr, "reconfigure", None)): sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # pragma: no cover
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
except Exception:
    pass

# تحقق من وجود ملف البيئة
# في CI/الاختبارات قد لا يوجد ملف .env، لذا نسمح بالعمل طالما يوجد مفتاح سري عبر env
_env_secret_key = os.getenv('DJANGO_SECRET_KEY') or os.getenv('SECRET_KEY')
_is_ci = bool(os.getenv('CI') or os.getenv('GITHUB_ACTIONS'))
_is_test_run = ('pytest' in sys.modules) or ('test' in sys.argv)

if not env_path.exists() and not _env_secret_key and not _is_ci and not _is_test_run:
    safe_print("تحذير: لم يتم العثور على ملف .env")
    safe_print("يرجى تشغيل setup_windows.bat أو setup_unix.sh لإعداد النظام")
    if os.environ.get('ERP_STARTUP_DEBUG'):
        safe_print('[settings] EXIT due to missing .env and DJANGO_SECRET_KEY')
    if '--help' not in sys.argv and 'help' not in sys.argv:
        sys.exit(1)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY is now REQUIRED from environment in normal runs.
# For compatibility with existing CI configs, we also accept SECRET_KEY.
SECRET_KEY = _env_secret_key
if not SECRET_KEY:
    # Allow tests/CI/help to run without a real secret key.
    if _is_ci or _is_test_run:
        SECRET_KEY = 'test-secret-key-not-for-production'
    elif '--help' in sys.argv or 'help' in sys.argv:
        SECRET_KEY = 'temporary-key-for-help-command-only'
    else:
        safe_print("خطأ أمني حرج: DJANGO_SECRET_KEY غير معرف في ملف .env")
        safe_print("يرجى إضافة DJANGO_SECRET_KEY في ملف .env (أو SECRET_KEY في CI)")
        sys.exit(1)

# SECURITY WARNING: don't run with debug turned on in production!
# Changed default to '0' (False) for production safety
DEBUG = os.getenv('DEBUG', '0').lower() in ('1', 'true', 'yes')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

# وضع Enterprise للشركات الكبيرة (تصميم متقدم)
ENTERPRISE_MODE = os.getenv('ENTERPRISE_MODE', '1').lower() in ('1', 'true', 'yes')

# تفعيل الواجهة الجديدة (base_v2.html + sidebar_v3) افتراضياً
UI_NEW_DEFAULT = os.getenv('UI_NEW_DEFAULT', '1').lower() in ('1', 'true', 'yes')

# Rate Limiting - تفعيل محدد المعدل في الإنتاج
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', '1').lower() in ('1', 'true', 'yes')

# Inventory Management Settings
ALLOW_NEGATIVE_INVENTORY = os.getenv('ALLOW_NEGATIVE_INVENTORY', '0').lower() in ('1', 'true', 'yes')

# ALLOWED_HOSTS - safer default (localhost only)
# In production, explicitly set ALLOWED_HOSTS in .env
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# إضافة testserver للاختبارات
if 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')

# إضافة IP الخادم للاختبارات الخارجية
if '72.62.176.249' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('72.62.176.249')

# Public base URL (used for QR codes / customer-facing links)
# مثال: https://kayanac.com أو http://192.168.1.10:8000
PUBLIC_SITE_URL = (os.getenv('PUBLIC_SITE_URL', '') or '').rstrip('/')

# إعدادات إضافية للشبكة المحلية
import socket

# إضافة عناوين الشبكة المحلية الشائعة
LOCAL_NETWORK_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '192.168.1.*',
    '192.168.0.*',
    '192.168.100.*',
    '10.0.0.*',
    '172.16.*',
]

# دعم wildcard domains للشبكة المحلية  
if '*' in ALLOWED_HOSTS:
    ALLOWED_HOSTS.extend(LOCAL_NETWORK_HOSTS)
    
# إضافة IP المحلي تلقائياً
local_ip = None
try:
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    if local_ip not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(local_ip)
except:
    pass


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # لوسوم القوالب humanize في التقارير
    'django.contrib.sitemaps',

    
    # Third-party packages
    'django_prometheus',  # Prometheus monitoring - معطل مؤقتاً
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # Token blacklisting support
    'django_filters',
    'corsheaders',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',

    # Forms (crispy)
    'crispy_forms',
    'crispy_bootstrap5',
    
    # Email queue system - Week 1 Phase 1 (Egypt)
    'post_office',  # django-post_office for email queue management - تم تعطيله مؤقتاً
    
    # Local apps
    'users',  # نظام المستخدمين والصلاحيات المتقدم
    'accounts',  # نظام المصادقة الثنائية (Two-Factor Authentication)
    'core',
    'inventory',
    'sales.apps.SalesConfig',
    'purchases',
    'accounting',
    'partners',
    'reports',
    'api',
    'hr',
    'production',
    'payments',  # نظام المدفوعات والقروض
    'installments',  # نظام التقسيط الذكي
    'exports',  # نظام التصدير والنسخ الاحتياطي
    'showrooms',  # legacy - UI merged into branches
    'approvals',  # نظام الموافقات الجديد
    'notifications',  # نظام الإشعارات الداخلي
    'fixed_assets',  # إدارة الأصول الثابتة
    'shipping',  # نظام إدارة الشحن
    'taxes',  # نظام إدارة الضرائب والفاتورة الإلكترونية
    'data_import',  # نظام استيراد البيانات من Excel
    'printing',  # نظام الطباعة الموحد (ZPL / ESC-POS / PDF)
    'attendance',  # نظام الحضور والانصراف المتقدم
    'branches',  # نظام إدارة الفروع المتعددة
    'budgeting',  # إدارة الميزانيات
    'quality_control',  # إدارة الجودة
    'dashboard',  # لوحة المعلومات المحسنة (KPIs + Cache)
    'tasks',  # نظام المهام والتذكيرات ✅

    # ======== نظام بناء المراتب المخصصة ========
    'mattress_builder',  # Custom Mattress Builder - تصميم المراتب التفاعلي 🛏️
    # ====================================

    'django_celery_beat',  # جدولة مهام Celery

    # 🔴 DISABLED APPS - Phase 2: Will be re-enabled after core stabilization

    # 🔴 DISABLED - Phase 2: Re-enable when core is stable
    # Duplicates:
    'advanced_notifications',  # الإشعارات والرسائل المتقدمة ✨ (duplicate of notifications)
    'advanced_crm',  # نظام CRM المتقدم ✨ (duplicate of crm)
    'tax_system',  # نظام الضرائب المتقدم ✨ (duplicate of taxes)
    'custom_dashboard',  # لوحة تحكم قابلة للتخصيص 📊 (duplicate of dashboard)
    'sound_notifications',  # نظام الإشعارات الصوتية 🔔 (duplicate of notifications)

    # 🔴 DISABLED - Phase 2: Re-enable when core is stable
    # CRM (partners module is sufficient for now):
    'crm',

    # 🔴 DISABLED - Phase 2: Re-enable when core is stable
    # AI features (not priority):
    'ai_assistant',  # المساعد الذكي بالذكاء الاصطناعي
    'ai_analytics',  # تحليلات الذكاء الاصطناعي 🤖
    'voice_assistant',  # المساعد الصوتي الذكي 🎤
    'smart_pricing',  # التسعير الذكي بالذكاء الاصطناعي 🆕
    'sales_forecasting',  # التنبؤ بالمبيعات والطلب 📈
    'business_intelligence',  # الذكاء الاصطناعي والبيانات الضخمة ✨

    # 🔴 DISABLED - Phase 2: Re-enable when core is stable
    # Technology not needed now:
    'video_calls',  # مكالمات الفيديو 📹
    'internal_chat',  # نظام الدردشة الداخلية 💬
    'collaborative_docs',  # المستندات التعاونية 📄
    'smartwatch',  # تكامل الساعات الذكية ⌚
    'cloud_backup',  # النسخ الاحتياطي السحابي ☁️
    'digital_signatures',  # التوقيعات الرقمية ✍️
    'cms',  # نظام إدارة المحتوى 🌐

    # 🔴 DISABLED - Phase 2: Re-enable when core is stable
    # Not related to mattress business:
    'fleet',  # نظام إدارة الأسطول (مركبات، سائقون، رحلات)
    'contracting',  # نظام إدارة المقاولات والمشاريع
    'eservices',  # الخدمات الإلكترونية
    'home_services',  # خدمات الصيانة والنظافة المنزلية
    'tender_bidding',  # المناقصات والعطاءات 📋
    'energy_management',  # إدارة الطاقة والاستهلاك ⚡
    'intellectual_property',  # الملكية الفكرية والبراءات ✨
    'license_management',  # إدارة التراخيص والتصاريح 📜
    'competitive_intelligence',  # تحليل المنافسين 🎯
    'compliance_management',  # إدارة الامتثال والمراجعة ✅
    'correspondence_management',  # إدارة المراسلات ✨

    # 🔴 DISABLED - Phase 2: Re-enable when core is stable
    # Can be added later:
    'woocommerce_integration',  # تكامل WooCommerce
    'ecommerce',  # المتجر الإلكتروني المتكامل
    'whatsapp_integration',  # تكامل واتساب مع n8n 📱
    'whatsapp_ai',  # واتساب AI مع n8n وCRM 🤖
    'bank_integration',  # التكامل البنكي ✨
    'bank_reconciliation',  # مطابقة البنوك
    'risk_management',  # إدارة المخاطر والتأمين ✨
    'contract_management',  # إدارة العقود والمستندات ✨
    'treasury_management',  # الشؤون المالية والسيولة ✨
    'warranty_management',  # إدارة الضمانات 🛡️
    'customer_profitability',  # تحليل ربحية العملاء 💎
    'complaint_management',  # إدارة الشكاوى والتحسين المستمر 📞
    'marketing_campaigns',  # إدارة الحملات التسويقية 📣
    'loyalty',  # برنامج الولاء
    'helpdesk',  # مركز الدعم الفني
    'subscriptions',  # إدارة الباقات والاشتراكات 🆕
    'zatca_integration',  # الفوترة الإلكترونية ZATCA المرحلة 2 🆕
    'shipment_tracking',  # Shipment Tracking - تتبع الشحنات مع GPS وإشعارات 📦
    'product_reviews',  # Product Reviews - تقييمات ومراجعات المنتجات ⭐
    'monitoring',  # نظام المراقبة وكشف الشذوذات 🔍
    'theme_system',  # الوضع المظلم والفاتح 🌙
    'report_builder',  # منشئ التقارير المرئي 📈
    'quick_access',  # نظام الوصول السريع والإنتاجية 🚀
    'projects',  # نظام إدارة المشاريع
    'maintenance',  # نظام إدارة الصيانة والمعدات
    'pos',  # نظام نقاط البيع الجديد
]

IS_RUNNING_TESTS = 'test' in sys.argv
# تم تعطيل Django Debug Toolbar بناءً على طلب المستخدم ("شلها").
# إذا رغبت بإرجاعها لاحقاً: أعد إضافة الكود التالي:
# if DEBUG and not IS_RUNNING_TESTS:
#     INSTALLED_APPS.append('debug_toolbar')

# Try to enable Channels only if it's installed (avoid ModuleNotFoundError during tests/CI)
try:
    import channels  # noqa: F401
    INSTALLED_APPS.append('channels')
    CHANNELS_AVAILABLE = True
except Exception:
    CHANNELS_AVAILABLE = False

MIDDLEWARE = [
    # 'django_prometheus.middleware.PrometheusBeforeMiddleware',  # معطل مؤقتاً
    'core.debug_request_middleware.DebugRequestMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.StripHiddenCharsMiddleware',  # Strip invisible Unicode chars from URLs
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'csp.middleware.CSPMiddleware',  # Content Security Policy
    'core.middleware_security.SecurityHeadersMiddleware',  # Security Headers متقدمة
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'core.middleware.SessionRecoveryMiddleware',  # معالجة SessionInterrupted
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'core.csrf_fix_middleware.DisableCSRFOnLogin',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'core.middleware.CurrentRequestMiddleware',
    'showrooms.middleware.ActiveShowroomMiddleware',
    'accounts.middleware_branch.BranchFilterMiddleware',  # تحديد الفرع الحالي تلقائياً
    'django.contrib.messages.middleware.MessageMiddleware',
    'users.middleware.SecurityMiddleware',  # نظام الأمان المتقدم
    'users.middleware.PermissionMiddleware',  # نظام الصلاحيات
    'users.middleware.ApprovalMiddleware',  # نظام الموافقات
    'core.attendance_middleware.AttendanceGateMiddleware',  # إلزام الحضور قبل الدخول للنظام
    'printing.middleware.StationDetectionMiddleware',  # كشف محطة الطباعة تلقائياً
    'core.middleware.AdvancedRateLimitMiddleware',  # Rate limiting متقدم (يدعم الإنتاج)
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.ForcePasswordChangeMiddleware',  # فرض تغيير كلمة المرور الافتراضية
    'core.middleware.RequestIDMiddleware',
    'core.middleware.RequestTimingMiddleware',
    # تحسينات الأداء الجديدة
    'core.middleware_performance.ResponseTimeMiddleware',  # قياس زمن الاستجابة
    'core.middleware_performance.CompressionOptimizationMiddleware',  # تحسين الضغط
    # 'django_prometheus.middleware.PrometheusAfterMiddleware',  # معطل مؤقتاً
]

# (أُزيل middleware الخاص بالـ Debug Toolbar)

ROOT_URLCONF = 'accountant_pro.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.system_info',
                'core.context_processors.user_permissions',
                'core.sidebar_processor.sidebar_menu',  # القائمة الجانبية المنظمة
                'core.sidebar_processor_v3.sidebar_menu_v3',  # القائمة الجانبية v3 - 6 مجموعات
                'branches.context_processors.branch_context',  # الفروع الموحدة (يحل محل showrooms)
                'notifications.context_processors.unread_notifications',
                'core.context_processors.currency.active_currency',
                'accounting.navigation.navigation_context',  # إضافة قائمة المحاسبة الموحدة
                'accounting.context_processors.page_help',  # شرح سياقي لصفحات المحاسبة
                'accounting.context_processors.payment_destinations',  # وجهات الدفع (خزائن، بنوك، حسابات إلكترونية)
                'ecommerce.context_processors.store_context',  # سياق المتجر الإلكتروني
                'data_import.context_processors.setup_prompt',  # إشعار الإعداد الأولي
            ],
            # Make frequently used custom template tag libraries globally available so
            # templates don't need an explicit `{% load money_tags %}` / `{% load currency_tags %}`.
            # This prevents TemplateSyntaxError: Invalid filter 'money' when a template
            # forgets to load the library but uses |money or related tags.
            'builtins': [
                'core.templatetags.money_tags',
                'core.templatetags.currency_tags',
                'core.templatetags.tony_erb_tags',
                'users.templatetags.user_extras',
            ],
        },
    },
]

# Crispy Forms configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

WSGI_APPLICATION = 'accountant_pro.wsgi.application'


# Database Configuration
# يدعم SQLite للتطوير وPostgreSQL للإنتاج

# Database Configuration
# يدعم SQLite للتطوير وPostgreSQL للإنتاج

import os
db_engine = os.getenv('DB_ENGINE', 'sqlite')

if db_engine == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'tony_erp_db'),
            'USER': os.getenv('DB_USER', 'tony_erp_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': {
                'connect_timeout': 10,
            },
            'CONN_MAX_AGE': 600,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

# Use isolated test database to avoid leaking prod/dev data into tests
if _is_test_run:
    DATABASES['default'].setdefault('TEST', {})
    DATABASES['default']['TEST']['NAME'] = os.getenv('TEST_DB_NAME', str(BASE_DIR / 'db.test.sqlite3'))
    class _DisableMigrations(dict):
        def __contains__(self, item):  # type: ignore[override]
            return True
        def __getitem__(self, item):  # type: ignore[override]
            return None
    MIGRATION_MODULES = _DisableMigrations()

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

from typing import Any as _AnyType  # local alias for annotations only

AUTH_PASSWORD_VALIDATORS: list[dict[str, _AnyType]] = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

# Default interface language.
# If you want English UI by default leave it 'en' and provide Arabic translations.
# Override by setting env var LANGUAGE_CODE=ar (or en) in the .env file.
LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', 'en')

TIME_ZONE = os.getenv('TIME_ZONE', 'Africa/Cairo')

USE_I18N = True

USE_TZ = True

# Internationalization languages & locales
# Order languages with the preferred default first (helps in some language selectors/UI lists)
LANGUAGES = [
    ('en', 'English'),
    ('ar', 'Arabic'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
# Project static directories
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # مجلد static داخل app
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
TESTING = _is_test_run

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # SessionAuthentication removed to avoid CSRF issues on API endpoints
        # 'rest_framework.authentication.SessionAuthentication',
        # BasicAuthentication kept for backward compatibility but discouraged
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('API_THROTTLE_RATE', '200/hour'),  # تحسين من 100/day
        'user': os.getenv('API_MOBILE_THROTTLE_RATE', '2000/hour'),  # تحسين من 1000/day
        'reports': os.getenv('API_REPORTS_THROTTLE_RATE', '120/hour'),  # تحسين من 60/min
        # معدلات خاصة بالتصدير (يتم استهلاكها عبر كلاس مخصص)
        'exports_burst': os.getenv('API_EXPORTS_BURST_RATE', '10/min'),  # تحسين من 5/min
        'exports_day': os.getenv('API_EXPORTS_DAILY_RATE', '50/day'),  # تحسين من 25/day
    },
    # معالج استثناءات مخصص لإرجاع JSON دائماً
    'EXCEPTION_HANDLER': 'core.exception_handlers.custom_exception_handler',
}

# تفعيل مخطط OpenAPI تلقائياً إذا كانت drf_spectacular مثبّتة
try:  # pragma: no cover - اختياري
    import drf_spectacular  # noqa: F401
    # إضافة التطبيق إذا لم يكن مُضافاً يدوياً
    if 'drf_spectacular' not in INSTALLED_APPS:
        INSTALLED_APPS.append('drf_spectacular')
    REST_FRAMEWORK.setdefault('DEFAULT_SCHEMA_CLASS', 'drf_spectacular.openapi.AutoSchema')
    _SPECTACULAR_ENABLED = True
except Exception:
    _SPECTACULAR_ENABLED = False

SPECTACULAR_SETTINGS = {
    'TITLE': 'Tony ERP - API',
    'DESCRIPTION': 'واجهة برمجية لنظام Tony ERP - إدارة الأعمال الشامل\n\n'
                   '## الأقسام الرئيسية\n'
                   '- **المحاسبة**: دليل الحسابات، القيود، التقارير المالية\n'
                   '- **المبيعات**: الفواتير، العملاء، نقاط البيع\n'
                   '- **المشتريات**: أوامر الشراء، الموردين\n'
                   '- **المخزون**: المنتجات، المستودعات، الجرد\n'
                   '- **الموارد البشرية**: الموظفين، الحضور، الرواتب\n'
                   '- **الإنتاج**: أوامر التصنيع، المواد الخام\n',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/',
    'TAGS': [
        {'name': 'المحاسبة', 'description': 'العمليات المحاسبية'},
        {'name': 'المبيعات', 'description': 'إدارة المبيعات والفواتير'},
        {'name': 'المشتريات', 'description': 'إدارة المشتريات'},
        {'name': 'المخزون', 'description': 'إدارة المخزون والمستودعات'},
        {'name': 'الموارد البشرية', 'description': 'إدارة الموظفين والرواتب'},
        {'name': 'المصادقة', 'description': 'تسجيل الدخول وJWT'},
    ],
    # كتم تحذيرات توليد المخطط - هذه تحذيرات توثيق فقط ولا تؤثر على عمل النظام
    'DISABLE_ERRORS_AND_WARNINGS': True,
}

# كتم تحذيرات drf_spectacular - تحذيرات توثيق API فقط لا تؤثر على النظام
SILENCED_SYSTEM_CHECKS = [
    'drf_spectacular.W001',
    'drf_spectacular.W002',
]

# Force default auth backend only (avoid lockout backends if installed globally)
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# If django-axes is installed globally, keep it disabled in this project
AXES_ENABLED = False

# تعطيل قفل الحساب عند محاولات تسجيل الدخول الفاشلة (مفيد لبيئة الاختبار الآلي)
# يمكن تعطيلها بوضع DISABLE_LOGIN_LOCKOUT=1 في متغيرات البيئة
DISABLE_LOGIN_LOCKOUT = os.getenv('DISABLE_LOGIN_LOCKOUT', '0').lower() in ('1', 'true', 'yes')

# Auth redirects
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Custom User Model - Commented temporarily for migration
# AUTH_USER_MODEL = 'users.CustomUser'

# Session Settings
SESSION_COOKIE_AGE = 3600  # جلسة لمدة ساعة واحدة
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# Security Settings for Local Network
SECURE_SSL_REDIRECT = False  # لأن النظام على شبكة داخلية
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Content Security Policy (CSP) Settings
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",  # للسماح بـ inline scripts في Django templates
    "'unsafe-eval'",    # لـ Chart.js والمكتبات التفاعلية
    "https://cdn.jsdelivr.net",
    "https://code.jquery.com",
    "https://cdn.datatables.net",
    "https://cdnjs.cloudflare.com",
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",  # للسماح بـ inline styles في Bootstrap
    "https://cdn.jsdelivr.net",
    "https://cdnjs.cloudflare.com",
    "https://fonts.googleapis.com",
)
CSP_FONT_SRC = (
    "'self'",
    "https://cdn.jsdelivr.net",
    "https://cdnjs.cloudflare.com",
    "https://fonts.gstatic.com",
    "data:",
)
CSP_IMG_SRC = (
    "'self'",
    "data:",
    "https:",  # للسماح بجميع الصور من HTTPS
    "blob:",
)
CSP_CONNECT_SRC = (
    "'self'",
    "https://api.openai.com",  # للمساعد الذكي
    "https://api.anthropic.com",
    "wss:",  # WebSocket للإشعارات الفورية
    "ws:",   # WebSocket لـ QZ Tray (طباعة حرارية)
    "ws://localhost:*",  # QZ Tray local connection
    "wss://localhost:*", # QZ Tray secure local
    "https://cdn.jsdelivr.net",  # CDN resources
)
CSP_FRAME_ANCESTORS = ("'none'",)  # منع تضمين الموقع في iframe
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)

# Additional Security Headers
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
PERMISSIONS_POLICY = {
    'geolocation': [],
    'microphone': [],
    'camera': [],
    'payment': ['self'],
    'usb': [],
    'magnetometer': [],
    'gyroscope': [],
    'accelerometer': [],
}

# HSTS Settings (for production with HTTPS)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True  # تفعيل في production فقط

# Password validation for stronger security
AUTH_PASSWORD_VALIDATORS = [  # redefinition keeps same annotation; mypy treats same name reassignment consistently
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# إنشاء مجلد السجلات
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

class _JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            'ts': self.formatTime(record, datefmt='%Y-%m-%dT%H:%M:%S'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', None),
            'path': getattr(record, 'path', None),
        }
        if record.exc_info:
            data['exc'] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'request_id': {'()': 'core.logging_filters.RequestIDFilter'},
    },
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
        'json': {'()': _JsonFormatter},
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'filters': ['request_id'],
        },
        'main_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
            'maxBytes': 1024*1024*15,
            'backupCount': 10,
            'formatter': 'verbose',
            'filters': ['request_id'],
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 1024*1024*10,
            'backupCount': 5,
            'formatter': 'verbose',
            'filters': ['request_id'],
        },
        'user_activity_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'user_activity.log',
            'maxBytes': 1024*1024*10,
            'backupCount': 5,
            'formatter': 'verbose',
            'filters': ['request_id'],
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'maxBytes': 1024*1024*10,
            'backupCount': 5,
            'formatter': 'verbose',
            'filters': ['request_id'],
        },
    },
    'root': {
        'handlers': ['console', 'main_file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {'handlers': ['console', 'main_file'], 'level': 'INFO', 'propagate': False},
        'django.request': {'handlers': ['error_file'], 'level': 'ERROR', 'propagate': False},
        'users.security': {'handlers': ['security_file'], 'level': 'INFO', 'propagate': True},
        'users.activity': {'handlers': ['user_activity_file'], 'level': 'INFO', 'propagate': True},
        'celery': {'handlers': ['console', 'main_file'], 'level': 'INFO', 'propagate': False},
        'django.utils.autoreload': {'handlers': ['main_file'], 'level': 'ERROR', 'propagate': False},
        'reports.variance': {'handlers': ['console', 'main_file'], 'level': 'WARNING', 'propagate': False},
        'reports.snapshot': {'handlers': ['console', 'main_file'], 'level': 'INFO', 'propagate': False},
    },
}

# =============================================================================
# الإعدادات الإضافية للإنتاج
# =============================================================================

# JWT Authentication Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', '60'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', '7'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SECRET_KEY', SECRET_KEY),
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Redis Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')

try:
    import redis
    # اختبار الاتصال بـ Redis
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False
    if not DEBUG:
        safe_print("تحذير: لا يمكن الاتصال بـ Redis")

# Cache Configuration
if REDIS_AVAILABLE:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'tony_erb',
            'TIMEOUT': 300,
            'VERSION': 1,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'tony_erb_cache',
        }
    }

# Celery Configuration
if REDIS_AVAILABLE:
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = TIME_ZONE
    CELERY_ENABLE_UTC = True
    CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
    # تسجيل صريح للمهام خارج التطبيقات المسجلة
    CELERY_IMPORTS = (
        'purchasing.sla_tracker',
    )

    # إعدادات المهام المجدولة
    from celery.schedules import crontab
    CELERY_BEAT_SCHEDULE = {
        'daily-backup': {
            'task': 'core.tasks.create_daily_backup',
            'schedule': crontab(hour=int(os.getenv('BACKUP_SCHEDULE_HOUR', '2')), minute=0),
        },
        'cleanup-logs': {
            'task': 'core.tasks.cleanup_old_logs',
            'schedule': crontab(hour=3, minute=0),  # كل يوم الساعة 3 صباحاً
        },
        'send-reminders': {
            'task': 'payments.tasks.send_payment_reminders',
            'schedule': crontab(hour=9, minute=0),  # كل يوم الساعة 9 صباحاً
        },
        'purge-audit-logs': {
            'task': 'core.tasks.purge_old_audit_logs',
            'schedule': crontab(hour=4, minute=0),  # تنظيف يومي مبكر
        },
        'create-daily-report-snapshot': {
            'task': 'reports.create_daily_snapshot_task',
            'schedule': crontab(hour=1, minute=10),  # التقاط لقطة اليوم السابق بعد منتصف الليل
        },
        'cleanup-expired-exports': {
            'task': 'exports.tasks_cleanup.cleanup_expired_exports',
            'schedule': crontab(hour='*/6', minute=5),  # كل 6 ساعات
        },
        'archive-audit-logs': {
            'task': 'core.tasks.archive_old_audit_logs',
            # أرشفة أسبوعية (تحفظ ثم الحذف تتم عبر متغير حذف اختياري False افتراضياً)
            'schedule': crontab(hour=2, minute=30, day_of_week='*/1'),  # يومي حالياً لضمان الاختبار (يمكن جعلها weekly)
            'options': {'queue': 'default'},
        },
        # ===== التحسينات الجديدة - UAT 10/10 =====
        'check-delayed-orders': {
            'task': 'notifications.enhanced_service.check_delayed_orders',
            'schedule': crontab(hour=9, minute=0),  # يومياً 9 صباحاً
        },
        'check-low-stock': {
            'task': 'notifications.enhanced_service.check_low_stock',
            'schedule': crontab(hour=8, minute=0),  # يومياً 8 صباحاً
        },
        'send-daily-summary': {
            'task': 'notifications.enhanced_service.send_daily_summary',
            'schedule': crontab(hour=18, minute=0),  # يومياً 6 مساءً
        },
        'cleanup-dashboard-cache': {
            'task': 'dashboard.cache_optimizer.cleanup_old_cache',
            'schedule': crontab(minute=0, hour='*/6'),  # كل 6 ساعات
        },
        'update-kpis': {
            'task': 'dashboard.enhanced_kpis.update_kpis',
            'schedule': crontab(minute=0),  # كل ساعة
        },
        'stock-alerts': {
            'task': 'inventory.stock_alerts.send_stock_alerts',
            'schedule': crontab(minute=0, hour='*/4'),  # كل 4 ساعات
        },
        'sla-alerts': {
            'task': 'purchasing.sla_tracker.send_sla_alerts',
            'schedule': crontab(minute=30, hour='*/2'),  # كل ساعتين
        },
    }
else:
    # استخدام Celery بدون Redis (في الذاكرة فقط للتطوير)
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# Email Configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'post_office.EmailBackend')  # django-post_office queue
if os.getenv('EMAIL_BACKEND', 'post_office.EmailBackend') != 'django.core.mail.backends.console.EmailBackend':
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.sendgrid.net')  # SendGrid SMTP
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', '1').lower() in ('1', 'true', 'yes')
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'apikey')  # SendGrid uses "apikey" as username
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')  # SendGrid API key
    EMAIL_FROM = os.getenv('EMAIL_FROM', 'noreply@tonyerp.com')
    DEFAULT_FROM_EMAIL = EMAIL_FROM

# django-post_office settings
POST_OFFICE = {
    'BACKENDS': {
        'default': 'django.core.mail.backends.smtp.EmailBackend'
    },
    'DEFAULT_PRIORITY': 'now',  # 'now', 'high', 'medium', 'low'
    'BATCH_SIZE': 50,  # Send 50 emails per batch
    'MAX_RETRIES': 3,
    'RETRY_INTERVAL': timedelta(minutes=15),
    'LOG_LEVEL': 1,  # 0=none, 1=failed, 2=all
    'TEMPLATE_ENGINE': 'django',  # Use Django template system
}

# django-fernet-fields encryption keys
FERNET_KEYS = os.getenv('FERNET_KEYS', '').split(',') if os.getenv('FERNET_KEYS') else []
if not FERNET_KEYS and not _is_test_run:
    safe_print("⚠️ Warning: FERNET_KEYS not configured. Payment gateway credentials will not be encrypted!")

# CORS Configuration (للـ API)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

if DEBUG and not IS_RUNNING_TESTS:
    CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', '3600'))  # ساعة واحدة
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', '0') == '1'  # تفعيل فقط مع HTTPS

# CSRF Configuration
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', '0') == '1'  # تفعيل فقط مع HTTPS
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS: list[str] = ["http://127.0.0.1:8000", "http://localhost:8000"]
# إضافة منفذ التشغيل الفعلي إذا كان مختلفاً عن 8000 (يُمرّر من start_anywhere/start_network_server عبر env PORT)
try:
    _run_port = os.getenv('PORT')
    if _run_port and _run_port.isdigit() and _run_port != '8000':
        _p = _run_port
        for host in ("127.0.0.1", "localhost"):
            origin = f"http://{host}:{_p}"
            if origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(origin)
except Exception:
    pass
# إضافة الـ IP المحلي الفعلي (لأجهزة الموبايل على نفس الشبكة)
try:
    if local_ip and local_ip not in ('127.0.0.1', 'localhost'):
        # أصل افتراضي 8000
        origin = f"http://{local_ip}:8000"
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)
        # إضافة المنفذ الحالي إذا مختلف
        _run_port = os.getenv('PORT')
        if _run_port and _run_port.isdigit() and _run_port != '8000':
            origin2 = f"http://{local_ip}:{_run_port}"
            if origin2 not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(origin2)
except Exception:
    pass

# إضافة اسم المضيف المحلي (hostname) كأصل موثوق به، لدعم الوصول عبر اسم الجهاز ضمن الشبكة المحلية
try:
    _hostname = socket.gethostname()
    if _hostname:
        # المنفذ الافتراضي 8000 + منفذ التشغيل الحالي إن وُجد
        for _p in ("8000", os.getenv('PORT')):
            if _p and str(_p).isdigit():
                origin_h = f"http://{_hostname}:{_p}"
                if origin_h not in CSRF_TRUSTED_ORIGINS:
                    CSRF_TRUSTED_ORIGINS.append(origin_h)
        # في بعض البيئات يظهر .local في الاسم
        origin_h_local = f"http://{_hostname}.local:8000"
        if origin_h_local not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin_h_local)
        _p = os.getenv('PORT')
        if _p and str(_p).isdigit():
            origin_h_local_p = f"http://{_hostname}.local:{_p}"
            if origin_h_local_p not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS.append(origin_h_local_p)
except Exception:
    pass

# Security Settings
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))  # 1 year for production
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', '1') == '1'
    SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', '1') == '1'
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', '0') == '1'
    
    # Proxy SSL Header - مهم لأن Gunicorn يعمل خلف Nginx
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Enhanced security for production payment processing (Egypt deployment)
    # تفعيل HTTPS cookies فقط لما يكون في SSL مركب
    SESSION_COOKIE_SECURE = os.getenv('SECURE_SSL_REDIRECT', '0') == '1'
    CSRF_COOKIE_SECURE = os.getenv('SECURE_SSL_REDIRECT', '0') == '1'
    CSRF_COOKIE_HTTPONLY = True  # Prevent JavaScript access to CSRF token
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('MAX_UPLOAD_SIZE_MB', '10')) * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE
ALLOWED_FILE_EXTENSIONS = os.getenv('ALLOWED_FILE_TYPES', 'pdf,doc,docx,xls,xlsx,jpg,jpeg,png').split(',')

# Health Checks
HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # النسبة المئوية القصوى لاستخدام القرص
    'MEMORY_MIN': 100,     # الحد الأدنى للذاكرة المتاحة (بالميجابايت)
}

# Backup Settings
BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
AUTO_BACKUP_ENABLED = os.getenv('AUTO_BACKUP_ENABLED', '1') == '1'

# Development Settings
SHOW_WELCOME_BANNER = False
if DEBUG:
    SHOW_WELCOME_BANNER = True
    # لم يعد يتم تحميل debug_toolbar؛ لضبطه مجدداً أضف INTERNAL_IPS و DEBUG_TOOLBAR_CONFIG هنا.

_safe_console_print = safe_print  # Backward compatibility alias

# طباعة معلومات التكوين عند بدء التطبيق (مع حماية من أخطاء الترميز في بعض محطات Windows)
if DEBUG and not IS_RUNNING_TESTS and SHOW_WELCOME_BANNER:
    banner_lines = [
        "\n" + "="*80,
        "مرحباً بك في Tony ERP - نظام إدارة الأعمال الشامل",
        "="*80,
    f"البيئة: {ENVIRONMENT}",
    f"قاعدة البيانات: {str(DATABASES.get('default', {}).get('ENGINE', '')).split('.')[-1] or 'unknown'}",
        f"Redis متوفر: {'نعم' if REDIS_AVAILABLE else 'لا'}",
        f"العنوان: http://127.0.0.1:8000",
        f"API Docs: http://127.0.0.1:8000/api/docs/",
        f"Admin: http://127.0.0.1:8000/admin/",
    ]
    if REDIS_AVAILABLE:
        banner_lines.append("Flower: http://127.0.0.1:5555")
    banner_lines += [
        "="*80,
    "نصائح سريعة:",
    "   - المستخدم الافتراضي: superadmin / admin123",
    "   - لإنشاء بيانات تجريبية: python manage.py load_sample_data",
    "   - لفحص النظام: python manage.py system_self_check",
    "   - لعمل نسخة احتياطية: python manage.py backup_now",
        "="*80 + "\n",
    ]
    for line in banner_lines:
        _safe_console_print(line)

# =========================
# UI / Branding Configuration
# =========================
# تخصيص بطاقات KPI عبر متغير بيئي بسيط (قائمة مفصولة بفواصل)
_raw_kpi_keys = os.getenv('KPI_VISIBLE_KEYS', 'sales,purchases,profit,low_stock')
KPI_VISIBLE_KEYS: list[str] = [k.strip() for k in _raw_kpi_keys.split(',') if k.strip()]

# إعدادات العملة الافتراضية للاستخدام في فلاتر العرض
DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'EGP')  # كود العملة (عدّلنا الافتراضي من EGP إلى EGP)
DEFAULT_CURRENCY_SYMBOL = os.getenv('DEFAULT_CURRENCY_SYMBOL', 'ج.م')  # رمز العملة (جنيه مصري افتراضياً)
SUPPORTED_CURRENCIES = {}
_supported_env = os.getenv('SUPPORTED_CURRENCIES', 'EGP:ج.م,USD:$,EUR:€')
for _item in _supported_env.split(','):
    _item = _item.strip()
    if not _item:
        continue
    if ':' in _item:
        code, sym = _item.split(':', 1)
        code = code.strip().upper()
        sym = sym.strip()
        if code:
            SUPPORTED_CURRENCIES[code] = sym or code
    else:
        SUPPORTED_CURRENCIES[_item.upper()] = _item.upper()

DEFAULT_MONEY_DECIMALS = int(os.getenv('DEFAULT_MONEY_DECIMALS', '2'))
if DEFAULT_MONEY_DECIMALS < 0:
    DEFAULT_MONEY_DECIMALS = 0
if DEFAULT_MONEY_DECIMALS > 6:
    DEFAULT_MONEY_DECIMALS = 6

# علم (Feature Flag) لتفعيل الواجهة الجديدة القائمة على Bootstrap (نسخة حديثة)
# يمكن ضبطه عبر متغير بيئة UI_NEW=1 أو من خلال الجلسة (session) عبر معامل الاستعلام ?ui=new
UI_NEW_DEFAULT = os.getenv('UI_NEW', '0').lower() in ('1', 'true', 'yes', 'on')

# =============================================================================
# WebSocket & Channels Configuration
# =============================================================================
ASGI_APPLICATION = 'accountant_pro.asgi.application'

if REDIS_AVAILABLE:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
                'prefix': 'tony_erb:',
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Notifications Configuration
NOTIFICATIONS_NOTIFICATION_MODEL = 'notifications.Notification'
NOTIFICATIONS_SOFT_DELETE = True
NOTIFICATIONS_USE_JSONFIELD = True

# =============================================================================
# Low Stock Alert Configuration
# =============================================================================
LOW_STOCK_THRESHOLD_DEFAULT = int(os.getenv('LOW_STOCK_THRESHOLD', '10'))
STOCK_ALERT_ENABLED = os.getenv('STOCK_ALERT_ENABLED', '1') == '1'

# =========================
# Export / Data Retention
# =========================
EXPORT_EXPIRY_HOURS = int(os.getenv('EXPORT_EXPIRY_HOURS', '24'))  # صلاحية ملف التصدير
EXPORT_CLEANUP_ENABLED = os.getenv('EXPORT_CLEANUP_ENABLED', '1') == '1'

# Arabic PDF font configuration (used by InventoryExporter)
# Override via environment: ARABIC_TTF_PATH=/path/to/font.ttf
ARABIC_TTF_PATH = os.getenv('ARABIC_TTF_PATH', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')

# اختبار: تجاوز تخفيض المخزون في بعض سيناريوهات الاختبار الخاصة بالمبيعات (يستخدمه sales.models.reduce_stock_on_sale)
SALES_SKIP_STOCK_DECREMENT_FOR_TESTS = True  # FLAG: SALES_SKIP_STOCK_DECREMENT_FOR_TESTS

# Force add server IP to CSRF_TRUSTED_ORIGINS
_server_origins = [
    "http://72.62.176.249:8000",
    "https://72.62.176.249:8000",
    "http://72.62.176.249",
    "https://72.62.176.249", 
    "http://srv1239682.hstgr.cloud",
    "https://srv1239682.hstgr.cloud",
]
for _origin in _server_origins:
    if _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)


# إعدادات تطوير آمنة: لا تلمس الإنتاج
if DEBUG:
    # Disable CSRF cookie secure for HTTP during local development
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_HTTPONLY = False

    # تعطيل CSRF للتطوير مؤقتاً
    CSRF_COOKIE_SAMESITE = 'Lax'
    CSRF_USE_SESSIONS = False
    SESSION_COOKIE_SAMESITE = 'Lax'

    # إضافة كل الأصول المحتملة
    CSRF_TRUSTED_ORIGINS += [
        "http://72.62.176.249:8000",
        "https://72.62.176.249:8000",
        "http://72.62.176.249",
        "https://72.62.176.249",
    ]

    # Disable browser caching for development فقط
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

# Disable COOP header when not using HTTPS (avoids browser warning on HTTP)
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# Reload trigger

# =====================================================
# تطبيق إعدادات الأمان المتقدمة
# Apply security hardening settings
# =====================================================
try:
    from accountant_pro.settings_security import apply_security_settings, validate_secret_key
    apply_security_settings(globals())
    validate_secret_key(SECRET_KEY)
except ImportError:
    pass

# Production Security (activated when DJANGO_ENV=production)
try:
    from accountant_pro.security_production import *  # noqa: F401,F403
except ImportError:
    pass

# Monitoring
try:
    from accountant_pro.monitoring import setup_sentry
    setup_sentry()
except ImportError:
    pass

# Celery Settings
import os as _os
CELERY_BROKER_URL = _os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = _os.getenv('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Cairo'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

for _celery_app in ['django_celery_beat', 'django_celery_results']:
    if _celery_app not in INSTALLED_APPS:
        INSTALLED_APPS.append(_celery_app)
