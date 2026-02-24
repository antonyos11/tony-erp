from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class AssetDepreciationViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester','t@example.com','pw')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        # تعطيل إلزام تغيير كلمة المرور
        try:
            from users.models import UserProfile
            profile = UserProfile.objects.get(user=self.user)
            profile.must_change_password = False
            profile.is_approved = True
            profile.save()
        except Exception:
            pass
        self.client = Client()
        self.client.force_login(self.user)

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
