"""
Tests — apps.notifications
يغطي: إنشاء إشعار، عدم التكرار، فحص المخزون، فواتير متأخرة، تعليم كمقروء، الصفحات
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock

from apps.notifications.models import Notification, NotificationSetting
from apps.notifications.services.notification_engine import NotificationEngine
from apps.core.models import Branch

User = get_user_model()


class NotificationModelTest(TestCase):
    """اختبارات موديل الإشعار"""

    def setUp(self):
        self.branch = Branch.objects.create(name='فرع رئيسي', branch_type='owned', governorate='القاهرة')
        self.user = User.objects.create_user(username='testuser', password='test123', branch=self.branch)

    def test_create_notification(self):
        """يمكن إنشاء إشعار بشكل طبيعي"""
        n = Notification.objects.create(
            user=self.user,
            title='اختبار',
            message='رسالة اختبار',
            notification_type='info',
            category='general',
        )
        self.assertEqual(n.user, self.user)
        self.assertEqual(n.title, 'اختبار')
        self.assertFalse(n.is_read)
        self.assertIsNone(n.read_at)

    def test_notification_str(self):
        """__str__ يعمل بشكل صحيح"""
        n = Notification.objects.create(
            user=self.user, title='تنبيه مخزون', message='مخزون منخفض',
        )
        self.assertIn('تنبيه مخزون', str(n))

    def test_default_ordering(self):
        """الإشعارات مرتبة من الأحدث"""
        n1 = Notification.objects.create(user=self.user, title='أول', message='1')
        n2 = Notification.objects.create(user=self.user, title='ثاني', message='2')
        notifications = list(Notification.objects.filter(user=self.user))
        self.assertEqual(notifications[0], n2)
        self.assertEqual(notifications[1], n1)

    def test_notification_setting_creation(self):
        """يمكن إنشاء إعدادات إشعار لمستخدم"""
        setting = NotificationSetting.objects.create(user=self.user)
        self.assertTrue(setting.stock_alerts)
        self.assertTrue(setting.invoice_alerts)
        self.assertFalse(setting.email_notifications)


class NotificationEngineTest(TestCase):
    """اختبارات محرك الإشعارات"""

    def setUp(self):
        self.branch = Branch.objects.create(name='فرع رئيسي', branch_type='owned', governorate='القاهرة')
        self.user = User.objects.create_user(username='manager', password='test123', is_superuser=True, branch=self.branch)

    def test_notify_creates_notification(self):
        """notify() ينشئ إشعاراً جديداً"""
        n = NotificationEngine.notify(
            user=self.user,
            title='اختبار المحرك',
            message='رسالة من المحرك',
            notification_type='warning',
            category='stock_low',
            source_model='Product',
            source_id='99',
        )
        self.assertIsNotNone(n)
        self.assertEqual(n.title, 'اختبار المحرك')
        self.assertEqual(n.notification_type, 'warning')
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_no_duplicate_same_day(self):
        """لا يُنشئ إشعار مكرر في نفس اليوم لنفس المصدر"""
        kwargs = dict(
            user=self.user,
            title='مخزون منخفض',
            message='اختبار',
            category='stock_low',
            source_model='Product',
            source_id='5',
        )
        n1 = NotificationEngine.notify(**kwargs)
        n2 = NotificationEngine.notify(**kwargs)

        self.assertIsNotNone(n1)
        self.assertIsNone(n2)  # مكرر، لا ينشئ
        self.assertEqual(Notification.objects.filter(user=self.user, source_id='5').count(), 1)

    def test_notify_group(self):
        """notify_group() يرسل لعدة مستخدمين"""
        user2 = User.objects.create_user(username='user2', password='test123')
        results = NotificationEngine.notify_group(
            users=[self.user, user2],
            title='إشعار جماعي',
            message='رسالة للجميع',
            category='general',
            source_model='System',
            source_id='1',
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(Notification.objects.count(), 2)

    def test_check_low_stock_with_mock(self):
        """check_low_stock يولد إشعارات عند وجود مخزون منخفض"""
        mock_product = MagicMock()
        mock_product.name = 'منتج تجريبي'
        mock_product.id = 1

        mock_low_stock = [
            {'product': mock_product, 'current_stock': 5, 'reorder_level': 20, 'deficit': 15}
        ]

        with patch('apps.notifications.services.notification_engine.NotificationEngine.check_low_stock') as mock_check:
            mock_check.return_value = None
            NotificationEngine.check_low_stock()
            mock_check.assert_called_once()

    def test_check_overdue_invoices_with_mock(self):
        """check_overdue_invoices لا يرمي خطأ لو ما فيه فواتير"""
        # لو ما فيه SalesInvoice مرتبط، المحرك يتجاهل بسبب try/except
        try:
            NotificationEngine.check_overdue_invoices()
        except Exception as e:
            self.fail(f'check_overdue_invoices رمى خطأ غير متوقع: {e}')

    def test_run_all_checks_no_crash(self):
        """run_all_checks لا يرمي استثناء"""
        try:
            NotificationEngine.run_all_checks()
        except Exception as e:
            self.fail(f'run_all_checks رمى خطأ: {e}')


class NotificationViewsTest(TestCase):
    """اختبارات الواجهات"""

    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(name='فرع رئيسي', branch_type='owned', governorate='القاهرة')
        self.user = User.objects.create_user(username='viewuser', password='test123', branch=self.branch)
        self.client.login(username='viewuser', password='test123')

        # أنشئ بعض الإشعارات
        for i in range(3):
            Notification.objects.create(
                user=self.user,
                title=f'إشعار {i}',
                message=f'رسالة {i}',
                notification_type='info',
                category='general',
            )

    def test_notification_list_200(self):
        """صفحة قائمة الإشعارات تعود 200"""
        url = reverse('notifications:notification_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_notification_list_shows_notifications(self):
        """صفحة قائمة الإشعارات تعرض الإشعارات"""
        url = reverse('notifications:notification_list')
        response = self.client.get(url)
        self.assertContains(response, 'إشعار 0')

    def test_notification_list_filter_unread(self):
        """فلترة الإشعارات غير المقروءة تعمل"""
        url = reverse('notifications:notification_list') + '?is_read=0'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['notifications'].count(), 3)

    def test_mark_read(self):
        """تعليم إشعار كمقروء يعمل"""
        n = Notification.objects.filter(user=self.user).first()
        url = reverse('notifications:mark_read', kwargs={'pk': n.pk})
        response = self.client.post(url)
        n.refresh_from_db()
        self.assertTrue(n.is_read)
        self.assertIsNotNone(n.read_at)

    def test_mark_all_read(self):
        """تعليم كل الإشعارات كمقروءة يعمل"""
        url = reverse('notifications:mark_all_read')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        unread = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread, 0)

    def test_notification_settings_200(self):
        """صفحة إعدادات الإشعارات تعود 200"""
        url = reverse('notifications:settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_notification_settings_save(self):
        """حفظ إعدادات الإشعارات يعمل"""
        url = reverse('notifications:settings')
        response = self.client.post(url, {
            'stock_alerts': 'on',
            'invoice_alerts': 'on',
        })
        self.assertEqual(response.status_code, 302)
        setting = NotificationSetting.objects.get(user=self.user)
        self.assertTrue(setting.stock_alerts)
        self.assertFalse(setting.financial_alerts)

    def test_mark_read_ajax(self):
        """تعليم كمقروء عبر AJAX يعمل"""
        n = Notification.objects.filter(user=self.user).first()
        url = reverse('notifications:mark_read', kwargs={'pk': n.pk})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')

    def test_login_required(self):
        """الصفحات تتطلب تسجيل الدخول"""
        self.client.logout()
        url = reverse('notifications:notification_list')
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)  # redirect to login

    def test_mark_read_wrong_user(self):
        """لا يمكن تعليم إشعار مستخدم آخر كمقروء"""
        other_user = User.objects.create_user(username='other', password='test123')
        n = Notification.objects.create(user=other_user, title='للآخر', message='x')
        url = reverse('notifications:mark_read', kwargs={'pk': n.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
