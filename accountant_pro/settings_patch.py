"""
Safety-net settings patch for Tony ERP.

This module is imported at the END of settings.py (or settings_production.py)
to apply mandatory safeguards that must always be active regardless of
environment configuration.

Usage in settings.py:
    try:
        from accountant_pro.settings_patch import *  # noqa: F401,F403
    except ImportError:
        pass
"""
import os
from django.conf import settings as _s

# ============================================================
# 1. Ensure SECRET_KEY is never the Django default
# ============================================================
_key = getattr(_s, 'SECRET_KEY', '')
if 'insecure' in _key.lower() or len(_key) < 40:
    import warnings
    warnings.warn(
        "SECRET_KEY is weak or default — generate a proper one with:\n"
        "  python3 -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"",
        RuntimeWarning,
        stacklevel=1,
    )

# ============================================================
# 2. Force critical security headers in non-DEBUG
# ============================================================
if not getattr(_s, 'DEBUG', True):
    # These should already be True in production settings,
    # but we enforce them as a safety net.
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True

# ============================================================
# 3. Sane defaults for file upload limits
# ============================================================
FILE_UPLOAD_MAX_MEMORY_SIZE = int(
    os.getenv('FILE_UPLOAD_MAX_MB', '10')
) * 1024 * 1024

DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE

# ============================================================
# 4. Session timeout defaults
# ============================================================
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', '86400'))  # 24h
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.getenv(
    'SESSION_EXPIRE_AT_BROWSER_CLOSE', 'False'
).lower() in ('1', 'true', 'yes')

# ============================================================
# 5. API throttle safety (DRF)
# ============================================================
REST_FRAMEWORK_THROTTLE = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('THROTTLE_ANON', '100/hour'),
        'user': os.getenv('THROTTLE_USER', '1000/hour'),
    },
}
