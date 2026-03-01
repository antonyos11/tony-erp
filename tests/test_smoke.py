"""
اختبارات الدخان للتحقق من سلامة البنية الأساسية — RITA ERP
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class BaseTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            is_staff=True,
        )
        self.client.login(username='testuser', password='TestPass123!')


class AuthSmokeTest(BaseTestCase):
    def test_login_page_accessible(self):
        self.client.logout()
        response = self.client.get('/auth/login/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)

    def test_dashboard_accessible_after_login(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)


class AdminSmokeTest(BaseTestCase):
    def test_admin_accessible(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
