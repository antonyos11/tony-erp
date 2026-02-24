"""
Pytest configuration for Tony ERP ecommerce tests
"""
import pytest
from django.conf import settings as django_settings


@pytest.fixture(autouse=True)
def ecommerce_test_settings(request):
    """
    Override ROOT_URLCONF and disable throttling for ALL ecommerce tests
    (including unittest-style APITestCase classes).
    We use Django's override_settings context manager so it applies
    to both pytest-style and unittest-style tests.
    """
    from django.test.utils import override_settings

    cur_rf = getattr(django_settings, 'REST_FRAMEWORK', {})

    # Strip out rate-limiting middleware entirely for ecommerce tests
    cur_mw = list(getattr(django_settings, 'MIDDLEWARE', []))
    clean_mw = [
        m for m in cur_mw
        if 'RateLimit' not in m and 'rate_limit' not in m.lower()
    ]

    ctx = override_settings(
        ROOT_URLCONF='ecommerce.tests.urls',
        RATE_LIMIT_ENABLED=False,          # disable middleware rate-limiter
        MIDDLEWARE=clean_mw,               # remove rate-limiter from middleware stack
        REST_FRAMEWORK={
            **cur_rf,
            'DEFAULT_THROTTLE_CLASSES': [],   # disable DRF throttling
            'DEFAULT_THROTTLE_RATES': {},
        },
    )
    ctx.enable()

    # Clear rate-limiter buckets so state from prior tests doesn't leak
    try:
        from core.middleware import AdvancedRateLimitMiddleware
        AdvancedRateLimitMiddleware._buckets.clear()
    except (ImportError, AttributeError):
        pass

    request.addfinalizer(ctx.disable)


@pytest.fixture
def api_client():
    """REST API test client"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_user(db, django_user_model):
    """Create and return an authenticated user"""
    user = django_user_model.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def api_client_authenticated(api_client, authenticated_user):
    """API client with JWT authentication"""
    from rest_framework_simplejwt.tokens import RefreshToken
    
    refresh = RefreshToken.for_user(authenticated_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = authenticated_user
    return api_client
