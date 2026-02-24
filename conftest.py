"""
Root-level pytest configuration for Tony ERP.
Ensures middleware rate-limiter state doesn't leak between tests.
"""
import sys
import os
import pytest

# ✅ إضافة مسار المشروع لـ sys.path حتى يجد pytest الـ modules
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ✅ إيقاف جمع ملفات الاختبار في المجلدات غير المرغوبة
collect_ignore_glob = [
    "*/migrations/*.py",
    "*/management/*.py",
    "accounting/test_new_dashboard.py",
]


@pytest.fixture(autouse=True)
def _disable_ssl_redirect(settings):
    """
    تعطيل SECURE_SSL_REDIRECT في الاختبارات لتجنب ردود 301 غير متوقعة.
    Django test client لا يرسل HTTPS فعلياً، فيسبب SSL redirect ارتباكاً.
    """
    settings.SECURE_SSL_REDIRECT = False
    settings.SESSION_COOKIE_SECURE = False
    settings.CSRF_COOKIE_SECURE = False


@pytest.fixture(autouse=True)
def _clear_rate_limiter_buckets():
    """Clear AdvancedRateLimitMiddleware class-level _buckets before each test
    so accumulated request counts from prior tests don't cause spurious 429s."""
    try:
        from core.middleware import AdvancedRateLimitMiddleware
        AdvancedRateLimitMiddleware._buckets.clear()
    except (ImportError, AttributeError):
        pass
    yield
    # Also clear after, in case the test itself triggers many requests
    try:
        from core.middleware import AdvancedRateLimitMiddleware
        AdvancedRateLimitMiddleware._buckets.clear()
    except (ImportError, AttributeError):
        pass
