"""
Tony ERP - اختبارات المصادقة والتفويض عبر API
Tests for JWT authentication, permissions, and token lifecycle.
"""
import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class JWTAuthenticationTests(TestCase):
    """JWT token obtain / refresh / verify."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='auth_test_user',
            password='S3cureP@ss!2024',
            email='auth_test@tony-erp.local',
        )

    def setUp(self):
        self.client = APIClient()

    # --------------------------------------------------
    # Token Obtain
    # --------------------------------------------------
    def test_obtain_token_success(self):
        """Valid credentials return access + refresh tokens."""
        resp = self.client.post('/api/token/', {
            'username': 'auth_test_user',
            'password': 'S3cureP@ss!2024',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)

    def test_obtain_token_wrong_password(self):
        """Wrong password is rejected."""
        resp = self.client.post('/api/token/', {
            'username': 'auth_test_user',
            'password': 'wrong',
        }, format='json')
        self.assertIn(resp.status_code, [400, 401])

    def test_obtain_token_nonexistent_user(self):
        """Nonexistent user is rejected."""
        resp = self.client.post('/api/token/', {
            'username': 'nobody_here',
            'password': 'irrelevant',
        }, format='json')
        self.assertIn(resp.status_code, [400, 401])

    # --------------------------------------------------
    # Token Refresh
    # --------------------------------------------------
    def test_refresh_token(self):
        """Refresh token returns a new access token."""
        # First get tokens
        resp = self.client.post('/api/token/', {
            'username': 'auth_test_user',
            'password': 'S3cureP@ss!2024',
        }, format='json')
        refresh = resp.json()['refresh']
        # Refresh
        resp2 = self.client.post('/api/token/refresh/', {
            'refresh': refresh,
        }, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp2.json())

    def test_refresh_with_invalid_token(self):
        """Invalid refresh token is rejected."""
        resp = self.client.post('/api/token/refresh/', {
            'refresh': 'not.a.valid.token',
        }, format='json')
        self.assertIn(resp.status_code, [400, 401])

    # --------------------------------------------------
    # Token Verify
    # --------------------------------------------------
    def test_verify_valid_token(self):
        """Valid access token passes verification."""
        resp = self.client.post('/api/token/', {
            'username': 'auth_test_user',
            'password': 'S3cureP@ss!2024',
        }, format='json')
        access = resp.json()['access']
        resp2 = self.client.post('/api/token/verify/', {
            'token': access,
        }, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)

    def test_verify_invalid_token(self):
        """Invalid token fails verification."""
        resp = self.client.post('/api/token/verify/', {
            'token': 'fake.token.value',
        }, format='json')
        self.assertIn(resp.status_code, [400, 401])


class ProtectedEndpointTests(TestCase):
    """Access control tests for protected API endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='perm_test_user',
            password='S3cureP@ss!2024',
            email='perm_test@tony-erp.local',
        )
        cls.admin = User.objects.create_superuser(
            username='perm_test_admin',
            password='Adm1nP@ss!2024',
            email='perm_admin@tony-erp.local',
        )

    def setUp(self):
        self.client = APIClient()

    def _get_token(self, username, password):
        resp = self.client.post('/api/token/', {
            'username': username, 'password': password,
        }, format='json')
        return resp.json().get('access')

    def test_api_core_requires_auth(self):
        """GET /api/core/ without token returns 401/403."""
        resp = self.client.get('/api/core/')
        self.assertIn(resp.status_code, [401, 403])

    def test_api_core_with_valid_token(self):
        """Authenticated user can access /api/core/."""
        token = self._get_token('perm_test_user', 'S3cureP@ss!2024')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        resp = self.client.get('/api/core/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_health_detailed_admin_only(self):
        """Only staff/admin can access /health/detailed/."""
        # Regular user token
        token = self._get_token('perm_test_user', 'S3cureP@ss!2024')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        resp = self.client.get('/health/detailed/')
        self.assertIn(resp.status_code, [401, 403])
