from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from apps.core.models import User


class APITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='api_user', password='test123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_products_list(self):
        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, 200)

    def test_customers_list(self):
        response = self.client.get('/api/v1/customers/')
        self.assertEqual(response.status_code, 200)

    def test_quick_create_customer(self):
        response = self.client.post('/api/v1/customers/quick_create/', {
            'name': 'عميل تجريبي',
            'phone': '01012345678',
        })
        self.assertEqual(response.status_code, 201)

    def test_dashboard_api(self):
        response = self.client.get('/api/v1/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_access_denied(self):
        self.client.logout()
        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, 403)
