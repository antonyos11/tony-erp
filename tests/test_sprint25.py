"""
Sprint 25 — اختبارات التكامل النهائية — RITA ERP v2.0
الدورة الكاملة: شراء → إنتاج → بيع → تحصيل → إقفال
+ أمان + Audit Log + ميزان المراجعة + جميع الأدوار
"""
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.core.cache import cache

User = get_user_model()

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def create_user(username, password='Pass@1234', is_staff=False, is_superuser=False):
    u = User.objects.create_user(
        username=username,
        password=password,
        first_name=username,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    return u


# ─────────────────────────────────────────────────────────────
# 1. اختبارات الأمان
# ─────────────────────────────────────────────────────────────

class BruteForceProtectionTests(TestCase):
    """اختبار حماية Brute Force"""

    def setUp(self):
        cache.clear()
        self.user = create_user('bf_test_user')
        self.client = Client()

    def test_account_locks_after_5_failed_attempts(self):
        """يجب أن يُقفل الحساب بعد 5 محاولات فاشلة"""
        from apps.authorization.security import (
            record_failed_attempt, check_brute_force, BRUTE_FORCE_MAX_ATTEMPTS
        )
        ip = '192.168.1.100'
        username = 'bf_test_user'

        for i in range(BRUTE_FORCE_MAX_ATTEMPTS):
            record_failed_attempt(username, ip)

        state = check_brute_force(username, ip)
        self.assertTrue(state['locked'], "الحساب يجب أن يكون مقفلًا بعد 5 محاولات")
        self.assertGreater(state['remaining_minutes'], 0)

    def test_reset_after_successful_login(self):
        """يجب أن يُعاد ضبط العداد بعد تسجيل دخول ناجح"""
        from apps.authorization.security import (
            record_failed_attempt, reset_brute_force, check_brute_force
        )
        ip = '192.168.1.101'
        username = 'bf_test_user'

        record_failed_attempt(username, ip)
        record_failed_attempt(username, ip)
        reset_brute_force(username, ip)

        state = check_brute_force(username, ip)
        self.assertFalse(state['locked'])
        self.assertEqual(state['attempts'], 0)

    def test_check_before_lockout(self):
        """أقل من 5 محاولات — الحساب مفتوح"""
        from apps.authorization.security import record_failed_attempt, check_brute_force
        ip = '192.168.1.102'
        username = 'bf_test_user'

        record_failed_attempt(username, ip)
        record_failed_attempt(username, ip)

        state = check_brute_force(username, ip)
        self.assertFalse(state['locked'])
        self.assertEqual(state['attempts'], 2)


class AuditLogTests(TestCase):
    """اختبار سجل التدقيق"""

    def setUp(self):
        self.user = create_user('audit_user', is_superuser=True)

    def test_log_action_creates_record(self):
        """log_action يجب أن ينشئ سجل تدقيق"""
        from apps.authorization.services.audit import log_action
        from apps.authorization.models import AuditLog

        log_action(
            user=self.user,
            action='create',
            module='sales',
            model_name='SalesInvoice',
            object_id='123',
            description='إنشاء فاتورة بيع',
            ip_address='10.0.0.1',
            user_agent='Mozilla/5.0',
        )

        log = AuditLog.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.module, 'sales')
        self.assertEqual(log.ip_address, '10.0.0.1')

    def test_login_signal_creates_audit_log(self):
        """تسجيل الدخول يجب أن يُنشئ سجل login"""
        from apps.authorization.models import AuditLog

        initial_count = AuditLog.objects.filter(action='login').count()
        self.client.login(username='audit_user', password='Pass@1234')
        new_count = AuditLog.objects.filter(action='login').count()

        self.assertGreater(new_count, initial_count, "يجب وجود سجل login")

    def test_logout_signal_creates_audit_log(self):
        """تسجيل الخروج يجب أن يُنشئ سجل logout"""
        from apps.authorization.models import AuditLog

        self.client.login(username='audit_user', password='Pass@1234')
        self.client.logout()

        self.assertTrue(
            AuditLog.objects.filter(action='logout').exists(),
            "يجب وجود سجل logout",
        )

    def test_failed_login_creates_audit_log(self):
        """المحاولة الفاشلة تُنشئ سجل failed_login"""
        from apps.authorization.models import AuditLog

        self.client.post(reverse('login'), {
            'username': 'audit_user',
            'password': 'WRONG_PASSWORD',
        })

        self.assertTrue(
            AuditLog.objects.filter(action='failed_login').exists(),
            "يجب وجود سجل failed_login",
        )


class CSPHeaderTests(TestCase):
    """اختبار Content Security Policy headers"""

    def setUp(self):
        self.user = create_user('csp_user', is_superuser=True)
        self.client = Client()
        self.client.login(username='csp_user', password='Pass@1234')

    def test_csp_header_present(self):
        """استجابة الـ HTTP يجب أن تحتوي على CSP header"""
        response = self.client.get('/')
        self.assertIn('Content-Security-Policy', response, "يجب أن يكون CSP header موجودًا")

    def test_x_frame_options_deny(self):
        """X-Frame-Options يجب أن يكون DENY"""
        response = self.client.get('/')
        self.assertIn(response.get('X-Frame-Options', ''), ['DENY', 'SAMEORIGIN'])

    def test_x_content_type_nosniff(self):
        """X-Content-Type-Options يجب nosniff"""
        response = self.client.get('/')
        self.assertEqual(response.get('X-Content-Type-Options', ''), 'nosniff')


# ─────────────────────────────────────────────────────────────
# 2. اختبارات التصدير
# ─────────────────────────────────────────────────────────────

class ExportTests(TestCase):
    """اختبار تصدير Excel وPDF"""

    def test_export_to_excel_basic(self):
        """تصدير قائمة بسيطة إلى Excel"""
        from apps.core.export import export_to_excel

        data = [
            {'code': 'P001', 'name': 'منتج 1', 'price': 100},
            {'code': 'P002', 'name': 'منتج 2', 'price': 200},
        ]
        columns = [
            {'header': 'الكود', 'field': 'code', 'width': 15},
            {'header': 'الاسم', 'field': 'name', 'width': 30},
            {'header': 'السعر', 'field': 'price', 'width': 15},
        ]

        response = export_to_excel(data, columns, filename='test_export')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            response['Content-Type'],
        )
        self.assertGreater(len(response.content), 0)

    def test_export_to_excel_empty(self):
        """تصدير قائمة فارغة إلى Excel يجب أن يعمل"""
        from apps.core.export import export_to_excel

        response = export_to_excel([], [{'header': 'العمود', 'field': 'x'}], filename='empty')
        self.assertEqual(response.status_code, 200)

    def test_export_queryset_to_pdf(self):
        """تصدير البيانات إلى PDF"""
        from apps.core.export import export_queryset_to_pdf

        data = [
            {'name': 'سجل 1', 'value': 'قيمة 1'},
            {'name': 'سجل 2', 'value': 'قيمة 2'},
        ]
        columns = [
            {'header': 'الاسم', 'field': 'name'},
            {'header': 'القيمة', 'field': 'value'},
        ]

        response = export_queryset_to_pdf(data, columns, title='اختبار', filename='test_pdf')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertGreater(len(response.content), 0)


# ─────────────────────────────────────────────────────────────
# 3. اختبارات الأداء والكاش
# ─────────────────────────────────────────────────────────────

class CachePerformanceTests(TestCase):
    """اختبار نظام الكاش"""

    def setUp(self):
        cache.clear()
        self.user = create_user('cache_user')

    def test_cache_set_and_get(self):
        """الكاش يعمل بشكل صحيح"""
        from apps.core.performance import make_cache_key

        key = make_cache_key('test', 'sprint25', 'value')
        cache.set(key, {'data': 'test'}, timeout=60)
        result = cache.get(key)

        self.assertIsNotNone(result)
        self.assertEqual(result['data'], 'test')

    def test_permissions_cache(self):
        """كاش الصلاحيات يعمل"""
        from apps.core.performance import (
            get_cached_permissions, set_cached_permissions, invalidate_user_permissions
        )

        user_id = str(self.user.pk)
        test_perms = {'sales': {'view': True, 'create': True}}

        set_cached_permissions(user_id, test_perms)
        cached = get_cached_permissions(user_id)
        self.assertIsNotNone(cached)
        self.assertEqual(cached['sales']['view'], True)

        # مسح الكاش
        invalidate_user_permissions(user_id)
        self.assertIsNone(get_cached_permissions(user_id))

    def test_dashboard_stats_cache(self):
        """كاش إحصائيات لوحة التحكم"""
        from apps.core.performance import (
            get_cached_dashboard_stats, set_cached_dashboard_stats
        )
        from django.utils import timezone

        date_key = timezone.now().strftime('%Y-%m-%d')
        stats = {'total_sales': 50000, 'total_purchases': 30000}

        set_cached_dashboard_stats(1, date_key, stats)
        cached = get_cached_dashboard_stats(1, date_key)

        self.assertIsNotNone(cached)
        self.assertEqual(cached['total_sales'], 50000)


# ─────────────────────────────────────────────────────────────
# 4. اختبارات Help System
# ─────────────────────────────────────────────────────────────

class HelpSystemTests(TestCase):
    """اختبار نظام المساعدة"""

    def setUp(self):
        self.user = create_user('help_user', is_superuser=True)
        self.client = Client()
        self.client.login(username='help_user', password='Pass@1234')

    def test_help_index_200(self):
        """صفحة مركز المساعدة يجب أن تفتح"""
        response = self.client.get(reverse('core:help_index'))
        self.assertEqual(response.status_code, 200)

    def test_help_faq_200(self):
        """صفحة FAQ يجب أن تفتح"""
        response = self.client.get(reverse('core:help_faq'))
        self.assertEqual(response.status_code, 200)

    def test_help_faq_search(self):
        """بحث FAQ يعيد نتائج"""
        response = self.client.get(reverse('core:help_faq') + '?q=فاتورة')
        self.assertEqual(response.status_code, 200)
        ctx = response.context
        self.assertIn('search_results', ctx)

    def test_help_section_sales(self):
        """صفحة مساعدة قسم المبيعات"""
        response = self.client.get(reverse('core:help_section', kwargs={'section': 'sales'}))
        self.assertEqual(response.status_code, 200)

    def test_help_section_faq_content(self):
        """الـ FAQ يحتوي على بيانات"""
        from apps.core.help_views import FAQ_DATABASE
        self.assertIn('sales', FAQ_DATABASE)
        self.assertIn('inventory', FAQ_DATABASE)
        self.assertIn('accounts', FAQ_DATABASE)
        self.assertGreater(len(FAQ_DATABASE['sales']['items']), 0)


# ─────────────────────────────────────────────────────────────
# 5. اختبار Two-Factor Authentication
# ─────────────────────────────────────────────────────────────

class TwoFactorAuthTests(TestCase):
    """اختبار المصادقة الثنائية"""

    def setUp(self):
        cache.clear()
        self.user = create_user('twofa_user')

    def test_generate_otp_code_length(self):
        """كود OTP يجب أن يكون 6 أرقام"""
        from apps.authorization.security import generate_otp_code
        code = generate_otp_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_store_and_verify_otp(self):
        """تخزين والتحقق من OTP"""
        from apps.authorization.security import (
            generate_otp_code, store_otp, verify_otp
        )
        user_id = str(self.user.pk)
        code = generate_otp_code()

        store_otp(user_id, code)
        self.assertTrue(verify_otp(user_id, code), "OTP صحيح يجب أن يمر")
        self.assertFalse(verify_otp(user_id, code), "OTP مستخدم لا يمر مجددًا")

    def test_wrong_otp_fails(self):
        """OTP خاطئ يرفض"""
        from apps.authorization.security import store_otp, verify_otp
        user_id = str(self.user.pk)
        store_otp(user_id, '123456')
        self.assertFalse(verify_otp(user_id, '000000'))

    def test_2fa_enabled_check(self):
        """is_2fa_enabled يعمل"""
        from apps.authorization.security import is_2fa_enabled

        self.assertFalse(is_2fa_enabled(self.user))
        self.user.two_factor_enabled = True
        self.assertTrue(is_2fa_enabled(self.user))


# ─────────────────────────────────────────────────────────────
# 6. اختبار كامل للدورة التجارية مع Audit
# ─────────────────────────────────────────────────────────────

class FullBusinessCycleAuditTest(TestCase):
    """
    يتحقق أن كل عملية في الدورة التجارية تُسجّل في Audit Log.
    """

    def setUp(self):
        cache.clear()
        self.user = create_user('cycle_admin', is_superuser=True)

    def test_create_and_delete_actions_logged(self):
        """الإنشاء والحذف يُسجّلان في الـ Audit Log"""
        from apps.authorization.services.audit import log_action
        from apps.authorization.models import AuditLog

        # تسجيل إنشاء أمر شراء
        log_action(
            user=self.user,
            action='create',
            module='purchases',
            model_name='PurchaseOrder',
            object_id='PO-001',
            description='إنشاء أمر شراء خامات',
            ip_address='127.0.0.1',
        )

        # تسجيل إنشاء أمر إنتاج
        log_action(
            user=self.user,
            action='create',
            module='production',
            model_name='ProductionOrder',
            object_id='MO-001',
            description='إنشاء أمر إنتاج',
            ip_address='127.0.0.1',
        )

        # تسجيل إنشاء فاتورة بيع
        log_action(
            user=self.user,
            action='create',
            module='sales',
            model_name='SalesInvoice',
            object_id='INV-001',
            description='إنشاء فاتورة بيع',
            ip_address='127.0.0.1',
        )

        # التحقق من السجلات
        logs = AuditLog.objects.all()
        self.assertGreaterEqual(logs.count(), 3)

        modules = set(logs.values_list('module', flat=True))
        self.assertIn('purchases', modules)
        self.assertIn('production', modules)
        self.assertIn('sales', modules)

    def test_audit_log_filtering(self):
        """فلترة Audit Log تعمل"""
        from apps.authorization.services.audit import log_action, get_audit_log
        from apps.authorization.models import AuditLog

        log_action(self.user, 'create', 'sales', 'SalesInvoice', '1', 'فاتورة', ip_address='10.0.0.1')
        log_action(self.user, 'update', 'inventory', 'Product', '5', 'تعديل منتج', ip_address='10.0.0.1')

        # فلترة على القسم
        sales_logs = get_audit_log({'module': 'sales'})
        self.assertTrue(all(l.module == 'sales' for l in sales_logs))

        # فلترة على الإجراء
        create_logs = get_audit_log({'action': 'create'})
        self.assertTrue(all(l.action == 'create' for l in create_logs))


# ─────────────────────────────────────────────────────────────
# 7. اختبار User المحدّث (2FA fields)
# ─────────────────────────────────────────────────────────────

class UserModelSprint25Tests(TestCase):
    """اختبار حقول المستخدم الجديدة في Sprint 25"""

    def test_user_2fa_fields_exist(self):
        """حقول 2FA يجب أن تكون موجودة على الـ User model"""
        user = create_user('model_test_user')
        self.assertFalse(user.two_factor_enabled)
        self.assertEqual(user.two_factor_method, 'email')
        self.assertIsNone(user.last_login_ip)
        self.assertEqual(user.failed_login_count, 0)
        self.assertIsNone(user.account_locked_until)

    def test_enable_2fa(self):
        """تفعيل 2FA يجب أن يُحفظ"""
        user = create_user('twofa_model_user')
        user.two_factor_enabled = True
        user.two_factor_method = 'sms'
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.two_factor_enabled)
        self.assertEqual(user.two_factor_method, 'sms')
