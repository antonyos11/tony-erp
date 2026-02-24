"""
إعدادات الأمان الإضافية - Tony ERP
Security hardening settings - imported in settings.py

الاستخدام في settings.py:
    from accountant_pro.settings_security import apply_security_settings, validate_secret_key
    apply_security_settings(globals())
    validate_secret_key(SECRET_KEY)
"""
import os
import warnings


def apply_security_settings(settings_dict):
    """
    تطبيق إعدادات الأمان على الإعدادات الرئيسية.
    يُستدعى في نهاية settings.py.

    Args:
        settings_dict: globals() من settings.py
    """
    debug = settings_dict.get('DEBUG', False)

    if not debug:
        # =====================================================
        # HTTPS - إجباري في الإنتاج
        # =====================================================
        settings_dict.setdefault('SECURE_SSL_REDIRECT', True)
        settings_dict.setdefault('SECURE_PROXY_SSL_HEADER', ('HTTP_X_FORWARDED_PROTO', 'https'))
        settings_dict.setdefault('SESSION_COOKIE_SECURE', True)
        settings_dict.setdefault('CSRF_COOKIE_SECURE', True)

        # HSTS - HTTP Strict Transport Security
        settings_dict.setdefault('SECURE_HSTS_SECONDS', 31536000)  # سنة واحدة
        settings_dict.setdefault('SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
        settings_dict.setdefault('SECURE_HSTS_PRELOAD', True)

        # Security Headers
        settings_dict.setdefault('SECURE_CONTENT_TYPE_NOSNIFF', True)
        settings_dict.setdefault('SECURE_BROWSER_XSS_FILTER', True)
        settings_dict.setdefault('X_FRAME_OPTIONS', 'DENY')

    # =====================================================
    # Session Security - تطبق دائماً
    # =====================================================
    settings_dict.setdefault('SESSION_COOKIE_HTTPONLY', True)
    settings_dict.setdefault('SESSION_COOKIE_AGE', 28800)  # 8 ساعات
    settings_dict.setdefault('SESSION_EXPIRE_AT_BROWSER_CLOSE', True)
    settings_dict.setdefault('SESSION_SAVE_EVERY_REQUEST', True)

    # =====================================================
    # Password Validation - تعزيز المتطلبات
    # =====================================================
    if not debug:
        settings_dict['AUTH_PASSWORD_VALIDATORS'] = [
            {
                'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
            },
            {
                'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
                'OPTIONS': {'min_length': 10},
            },
            {
                'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
            },
            {
                'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
            },
        ]

    return settings_dict


def validate_secret_key(secret_key):
    """
    التحقق من أن SECRET_KEY ليس القيمة الافتراضية أو ضعيفاً.

    Args:
        secret_key: قيمة SECRET_KEY

    Returns:
        bool: True إذا كان المفتاح آمناً
    """
    if not secret_key:
        warnings.warn(
            '⚠️ SECRET_KEY غير معرّف!',
            UserWarning,
            stacklevel=2,
        )
        return False

    INSECURE_PATTERNS = [
        'django-insecure-',
        'change-me',
        'your-secret-key',
        'secret-key-here',
        'changeme',
        'test-secret-key',
        'temporary-key',
    ]

    for pattern in INSECURE_PATTERNS:
        if pattern in secret_key.lower():
            warnings.warn(
                f'⚠️ SECRET_KEY غير آمن (يحتوي على: {pattern})! '
                'يجب تغييره قبل النشر في الإنتاج. '
                'استخدم: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"',
                UserWarning,
                stacklevel=2,
            )
            return False

    if len(secret_key) < 32:
        warnings.warn(
            f'⚠️ SECRET_KEY قصير جداً ({len(secret_key)} حرف). يُنصح بـ 50+ حرف.',
            UserWarning,
            stacklevel=2,
        )
        return False

    return True
