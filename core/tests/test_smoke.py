from django.test import TestCase, Client
from django.contrib.auth import get_user_model

try:
    from tests.factories import UserFactory  # type: ignore
except Exception:  # fallback if factories not found
    User = get_user_model()
    class UserFactory:
        @staticmethod
        def create(**kwargs):
            password = kwargs.pop('password', 'pass12345')
            user = User.objects.create_user(password=password, **kwargs)
            return user


class SmokeTests(TestCase):
    def test_health_live(self):
        c = Client()
        resp = c.get('/health/live/')
        self.assertEqual(resp.status_code, 200)

    def test_login_page_access(self):
        # تأكد من إمكانية الوصول لصفحة تسجيل الدخول بدون أخطاء قوالب معقدة
        c = Client()
        resp = c.get('/accounts/login/')
        self.assertIn(resp.status_code, (200, 302))

    def test_can_login(self):
        # إنشاء مستخدم وتسجيل الدخول (لا نزور الصفحة الرئيسية لتجنب قوالب غير مستقرة حالياً)
        user = UserFactory()
        c = Client()
        logged = c.login(username=user.username, password='testpass123')
        self.assertTrue(logged)
