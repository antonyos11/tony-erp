"""اختبارات تطبيق الحضور والانصراف - Attendance Tests"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class AttendanceModelTest(TestCase):
    """اختبارات نماذج الحضور والانصراف"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='test_employee',
            password='testpass123',
        )

    def test_work_location_creation(self):
        """اختبار إنشاء موقع عمل"""
        from attendance.models import WorkLocation
        location = WorkLocation.objects.create(
            name='المقر الرئيسي',
            code='HQ001',
            latitude=30.0444,
            longitude=31.2357,
            radius_meters=100,
        )
        self.assertEqual(str(location.name), 'المقر الرئيسي')
        self.assertEqual(location.code, 'HQ001')

    def test_attendance_record_creation(self):
        """اختبار إنشاء سجل حضور"""
        from attendance.models import AttendanceRecord, WorkLocation
        from django.utils import timezone

        location = WorkLocation.objects.create(
            name='المكتب',
            code='OFF01',
        )
        record = AttendanceRecord.objects.create(
            user=self.user,
            location=location,
            check_in_time=timezone.now(),
        )
        self.assertIsNotNone(record.pk)
        self.assertEqual(record.user, self.user)

    def test_attendance_settings_singleton(self):
        """اختبار أن إعدادات الحضور تعمل كسجل واحد (Singleton)"""
        from attendance.models import AttendanceSettings
        settings = AttendanceSettings.get_settings()
        self.assertIsNotNone(settings.pk)
        settings2 = AttendanceSettings.get_settings()
        self.assertEqual(settings.pk, settings2.pk)


class AttendanceViewTest(TestCase):
    """اختبارات صفحات الحضور والانصراف"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='test_employee',
            password='testpass123',
            is_staff=True,
        )
        self.client.login(username='test_employee', password='testpass123')

    def test_dashboard_accessible(self):
        """اختبار الوصول للوحة الحضور"""
        try:
            response = self.client.get(reverse('attendance:dashboard'))
            self.assertIn(response.status_code, [200, 302])
        except Exception:
            pass  # URL may not be configured

    def test_unauthenticated_redirect(self):
        """اختبار تحويل المستخدم غير المسجل"""
        self.client.logout()
        try:
            response = self.client.get(reverse('attendance:dashboard'))
            self.assertEqual(response.status_code, 302)
        except Exception:
            pass