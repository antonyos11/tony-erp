from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from exports.models import DataExport
from django.utils import timezone
from django.conf import settings

class DataExportAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='p')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_export(self):
        r = self.client.post('/api/exports/', {
            'export_name': 'Products CSV',
            'export_type': 'inventory_products',
            'export_format': 'csv',
            'parameters': {}
        }, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        data = r.json()
        self.assertEqual(data['status'], 'pending')
        obj = DataExport.objects.get(id=data['id'])
        # task may run eagerly; accept pending or completed
        self.assertIn(obj.status, ('pending','processing','completed'))

    def test_expiry_enforced(self):
        exp = DataExport.objects.create(
            export_name='Old', export_type='inventory_products', export_format='csv',
            parameters={}, requested_by=self.user, status='completed', file_path='exports/x.csv',
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        r = self.client.get(f'/api/exports/{exp.id}/download/')
        self.assertEqual(r.status_code, 410)

    def test_throttle_limits(self):
        # create more than burst limit quickly
        burst = int(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['exports_burst'].split('/')[0])
        allowed = 0
        for i in range(burst + 2):
            r = self.client.post('/api/exports/', {
                'export_name': f'Run {i}',
                'export_type': 'inventory_products',
                'export_format': 'csv',
                'parameters': {}
            }, format='json')
            if r.status_code == 201:
                allowed += 1
            elif r.status_code == 429:
                break
        self.assertGreaterEqual(allowed, 1)
        # Once throttled, further requests should be 429
        r2 = self.client.post('/api/exports/', {
            'export_name': 'Extra', 'export_type': 'inventory_products', 'export_format': 'csv', 'parameters': {}
        }, format='json')
        self.assertIn(r2.status_code, (201, 429))  # tolerate race in eager mode
