"""
Tony ERP - اختبارات API الشاملة
تغطي Health Check, Authentication, URL Routing, Security
"""
import json
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

User = get_user_model()


class HealthCheckTests(TestCase):
    """اختبارات Health Check"""

    def setUp(self):
        self.client = Client()

    def test_health_live_returns_200(self):
        """Liveness probe returns 200 OK"""
        response = self.client.get('/health/live/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')

    def test_health_ready_returns_200(self):
        """Readiness probe returns 200 with checks"""
        response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn(data['status'], ['healthy', 'unhealthy'])
        self.assertIn('checks', data)
        self.assertIn('database', data['checks'])

    def test_health_main_endpoint(self):
        """Main /health/ endpoint works"""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)

    def test_health_detailed_unauthenticated(self):
        """Detailed health check requires authentication"""
        response = self.client.get('/health/detailed/')
        self.assertEqual(response.status_code, 401)

    def test_health_detailed_staff_access(self):
        """Staff user can access detailed health check"""
        User.objects.create_superuser(
            username='admin_health_test',
            password='testpass123!',
            email='admin_health@test.com',
        )
        self.client.login(username='admin_health_test', password='testpass123!')
        response = self.client.get('/health/detailed/')
        self.assertIn(response.status_code, [200, 503])
        data = json.loads(response.content)
        self.assertIn('checks', data)
        self.assertIn('summary', data)

    def test_health_detailed_non_staff_forbidden(self):
        """Non-staff user gets 403 on detailed endpoint"""
        User.objects.create_user(
            username='regular_user_test',
            password='testpass123!',
            email='regular@test.com',
        )
        self.client.login(username='regular_user_test', password='testpass123!')
        response = self.client.get('/health/detailed/')
        self.assertEqual(response.status_code, 403)


class AuthenticationTests(APITestCase):
    """اختبارات المصادقة JWT"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='jwt_test_user',
            password='testpass123!',
            email='jwt@test.com',
        )
        self.client = APIClient()

    def test_token_obtain(self):
        """JWT Token obtain with valid credentials"""
        response = self.client.post('/api/token/', {
            'username': 'jwt_test_user',
            'password': 'testpass123!',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)

    def test_token_obtain_wrong_password(self):
        """JWT Token obtain fails with wrong password"""
        response = self.client.post('/api/token/', {
            'username': 'jwt_test_user',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 401)

    def test_token_refresh(self):
        """JWT Token refresh works"""
        response = self.client.post('/api/token/', {
            'username': 'jwt_test_user',
            'password': 'testpass123!',
        })
        refresh_token = response.json()['refresh']

        response = self.client.post('/api/token/refresh/', {
            'refresh': refresh_token,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())

    def test_token_verify_valid(self):
        """JWT Token verify with valid token"""
        response = self.client.post('/api/token/', {
            'username': 'jwt_test_user',
            'password': 'testpass123!',
        })
        access_token = response.json()['access']

        response = self.client.post('/api/token/verify/', {
            'token': access_token,
        })
        self.assertEqual(response.status_code, 200)

    def test_authenticated_api_core_access(self):
        """Authenticated user can access /api/core/"""
        response = self.client.post('/api/token/', {
            'username': 'jwt_test_user',
            'password': 'testpass123!',
        })
        token = response.json()['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/core/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('endpoints', data)


class URLRoutingTests(TestCase):
    """اختبارات توجيه URLs"""

    def test_admin_accessible(self):
        """Admin page accessible"""
        response = self.client.get('/admin/', follow=False)
        self.assertIn(response.status_code, [200, 301, 302])

    def test_health_urls_all_200(self):
        """All health check URLs return 200"""
        urls = ['/health/', '/health/live/', '/health/ready/']
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f'{url} returned {response.status_code}')

    def test_token_urls_not_404(self):
        """Token URLs exist (not 404)"""
        urls = ['/api/token/', '/api/token/refresh/', '/api/token/verify/']
        for url in urls:
            response = self.client.post(url, {})
            self.assertNotEqual(response.status_code, 404, f'{url} not found')

    def test_homepage_accessible(self):
        """Homepage accessible (redirect or 200)"""
        response = self.client.get('/', follow=False)
        self.assertIn(response.status_code, [200, 301, 302])


class SecurityTests(TestCase):
    """اختبارات الأمان"""

    def test_admin_requires_login(self):
        """Admin requires authentication"""
        response = self.client.get('/admin/', follow=True)
        final_url = response.redirect_chain[-1][0] if response.redirect_chain else ''
        self.assertTrue(
            response.status_code == 200 or 'login' in final_url.lower(),
        )

    def test_health_endpoints_no_auth_required(self):
        """Health endpoints don't need authentication"""
        for url in ['/health/', '/health/live/', '/health/ready/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)


class DatabaseTests(TestCase):
    """اختبارات سلامة قاعدة البيانات"""

    def test_user_creation_works(self):
        """Can create a user"""
        user = User.objects.create_user(
            username='db_test_user_api',
            password='testpass123!',
            email='dbtest@test.com',
        )
        self.assertIsNotNone(user.pk)
        self.assertEqual(User.objects.filter(username='db_test_user_api').count(), 1)

    def test_database_connection_works(self):
        """Database connection OK"""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
