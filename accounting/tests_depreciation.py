from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class AssetDepreciationViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester','t@example.com','pw')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client = Client(); self.client.login(username='tester', password='pw')

    def test_depreciation_json_basic(self):
        url = reverse('accounting:asset_depreciation') + '?format=json'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for key in ['count','totals','results','pagination','maintenance_available']:
            self.assertIn(key, data)
        self.assertIn('purchase', data['totals'])

    def test_depreciation_pagination(self):
        url = reverse('accounting:asset_depreciation') + '?format=json&page=1&page_size=50'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn('pagination', data)
        self.assertGreaterEqual(data['pagination']['page'],1)
