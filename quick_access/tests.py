"""
Quick Access Tests
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from quick_access.models import QuickAction, UserPreference, BulkActionHistory
from inventory.models import Product


class QuickAccessTests(TestCase):
    """اختبارات نظام الوصول السريع"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_quick_dashboard_loads(self):
        """اختبار تحميل لوحة الوصول السريع"""
        response = self.client.get(reverse('quick_access:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'لوحة الوصول السريع')
    
    def test_global_search(self):
        """اختبار البحث الشامل"""
        # إنشاء منتج للبحث عنه
        Product.objects.create(
            name='منتج اختبار',
            sku='TEST001',
            price=100
        )
        
        response = self.client.get(
            reverse('quick_access:global_search'),
            {'q': 'منتج'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data['results']), 0)
    
    def test_shortcuts_guide(self):
        """اختبار دليل الاختصارات"""
        response = self.client.get(reverse('quick_access:shortcuts_guide'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'دليل اختصارات لوحة المفاتيح')
    
    def test_bulk_actions_interface(self):
        """اختبار واجهة العمليات الجماعية"""
        response = self.client.get(reverse('quick_access:bulk_actions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'العمليات الجماعية')
    
    def test_user_preferences_creation(self):
        """اختبار إنشاء تفضيلات المستخدم"""
        prefs, created = UserPreference.objects.get_or_create(user=self.user)
        self.assertTrue(created or prefs.pk is not None)
        self.assertEqual(prefs.default_view, 'grid')
    
    def test_quick_action_tracking(self):
        """اختبار تتبع استخدام الإجراءات"""
        action = QuickAction.objects.create(
            name='اختبار',
            name_en='Test',
            icon='bi-test',
            url='/test/',
            category='other'
        )
        
        initial_count = action.usage_count
        action.increment_usage()
        
        self.assertEqual(action.usage_count, initial_count + 1)
    
    def test_bulk_action_history(self):
        """اختبار سجل العمليات الجماعية"""
        history = BulkActionHistory.objects.create(
            user=self.user,
            action_type='test_action',
            model_name='Product',
            affected_count=10,
            success_count=8,
            error_count=2,
            duration_seconds=1.5
        )
        
        self.assertEqual(history.affected_count, 10)
        self.assertEqual(history.success_count, 8)


class SmartNotificationsTests(TestCase):
    """اختبارات نظام الإشعارات الذكي"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_smart_notification_creation(self):
        """اختبار إنشاء إشعار ذكي"""
        from quick_access.smart_notifications import SmartNotificationManager
        
        notification = SmartNotificationManager.create_smart_notification(
            user=self.user,
            title='اختبار',
            message='رسالة اختبار',
            notification_type='info',
            priority='normal'
        )
        
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, 'اختبار')
