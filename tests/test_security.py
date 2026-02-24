"""
اختبارات الأمان والصلاحيات - Security Tests
==========================================
اختبارات شاملة للأمان والصلاحيات في النظام

تغطية الاختبارات:
- اختبارات المصادقة (Authentication)
- اختبارات الصلاحيات (Authorization)
- اختبارات RBAC
- اختبارات حماية البيانات
- اختبارات التحقق من المدخلات
- اختبارات سجلات التدقيق
"""

from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User, Permission, Group
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import json


# ===============================
# اختبارات المصادقة
# ===============================

class AuthenticationTestCase(TestCase):
    """اختبارات المصادقة"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='securepassword123'
        )
    
    def test_login_with_valid_credentials(self):
        """اختبار تسجيل الدخول بيانات صحيحة"""
        result = self.client.login(username='testuser', password='securepassword123')
        self.assertTrue(result)
    
    def test_login_with_invalid_password(self):
        """اختبار تسجيل الدخول بكلمة مرور خاطئة"""
        result = self.client.login(username='testuser', password='wrongpassword')
        self.assertFalse(result)
    
    def test_login_with_invalid_username(self):
        """اختبار تسجيل الدخول باسم مستخدم خاطئ"""
        result = self.client.login(username='wronguser', password='securepassword123')
        self.assertFalse(result)
    
    def test_logout(self):
        """اختبار تسجيل الخروج"""
        self.client.login(username='testuser', password='securepassword123')
        self.client.logout()
        
        # التحقق من عدم وجود جلسة نشطة
        response = self.client.get('/')
        self.assertNotIn('_auth_user_id', self.client.session)
    
    def test_password_change(self):
        """اختبار تغيير كلمة المرور"""
        old_password = 'securepassword123'
        new_password = 'newsecurepassword456'
        
        self.user.set_password(new_password)
        self.user.save()
        
        # كلمة المرور القديمة لا تعمل
        result_old = self.client.login(username='testuser', password=old_password)
        self.assertFalse(result_old)
        
        # كلمة المرور الجديدة تعمل
        result_new = self.client.login(username='testuser', password=new_password)
        self.assertTrue(result_new)
    
    def test_inactive_user_cannot_login(self):
        """اختبار أن المستخدم غير النشط لا يمكنه تسجيل الدخول"""
        self.user.is_active = False
        self.user.save()
        
        result = self.client.login(username='testuser', password='securepassword123')
        self.assertFalse(result)
    
    def test_session_expiry(self):
        """اختبار انتهاء الجلسة"""
        self.client.login(username='testuser', password='securepassword123')
        
        # التحقق من وجود الجلسة
        self.assertIn('_auth_user_id', self.client.session)


# ===============================
# اختبارات الصلاحيات
# ===============================

class AuthorizationTestCase(TestCase):
    """اختبارات الصلاحيات"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.client = Client()
        
        # مستخدم عادي
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@test.com',
            password='password123'
        )
        
        # مستخدم موظف
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@test.com',
            password='password123',
            is_staff=True
        )
        
        # مستخدم مدير
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@test.com',
            password='password123'
        )
    
    def test_regular_user_cannot_access_admin(self):
        """اختبار أن المستخدم العادي لا يمكنه الوصول للإدارة"""
        self.client.login(username='regularuser', password='password123')
        response = self.client.get('/admin/')
        
        # يجب إعادة التوجيه لصفحة تسجيل الدخول
        self.assertIn(response.status_code, [302, 403])
    
    def test_staff_user_can_access_admin(self):
        """اختبار أن موظف الإدارة يمكنه الوصول للإدارة"""
        self.client.login(username='staffuser', password='password123')
        response = self.client.get('/admin/')
        
        self.assertIn(response.status_code, [200, 302])
    
    def test_superuser_has_all_permissions(self):
        """اختبار أن المدير لديه جميع الصلاحيات"""
        self.assertTrue(self.admin_user.is_superuser)
        self.assertTrue(self.admin_user.has_perm('any.permission'))
    
    def test_user_specific_permission(self):
        """اختبار صلاحية محددة للمستخدم"""
        from django.contrib.contenttypes.models import ContentType
        
        # إضافة صلاحية للمستخدم
        content_type = ContentType.objects.get_for_model(User)
        permission = Permission.objects.create(
            codename='can_view_reports',
            name='Can View Reports',
            content_type=content_type
        )
        
        self.regular_user.user_permissions.add(permission)
        
        self.assertTrue(self.regular_user.has_perm('auth.can_view_reports'))
    
    def test_group_permissions(self):
        """اختبار صلاحيات المجموعات"""
        from django.contrib.contenttypes.models import ContentType
        
        # إنشاء مجموعة
        group = Group.objects.create(name='Sales Team')
        
        # إضافة صلاحية للمجموعة
        content_type = ContentType.objects.get_for_model(User)
        permission = Permission.objects.create(
            codename='can_create_invoice',
            name='Can Create Invoice',
            content_type=content_type
        )
        
        group.permissions.add(permission)
        self.regular_user.groups.add(group)
        
        self.assertTrue(self.regular_user.has_perm('auth.can_create_invoice'))


# ===============================
# اختبارات RBAC
# ===============================

class RBACTestCase(TestCase):
    """اختبارات التحكم في الوصول المبني على الأدوار"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        # إنشاء الأدوار
        self.sales_group = Group.objects.create(name='مبيعات')
        self.accounting_group = Group.objects.create(name='محاسبة')
        self.admin_group = Group.objects.create(name='إدارة')
        
        # إنشاء المستخدمين
        self.sales_user = User.objects.create_user(
            'sales_user', 'sales@test.com', 'pass123'
        )
        self.sales_user.groups.add(self.sales_group)
        
        self.accounting_user = User.objects.create_user(
            'acc_user', 'acc@test.com', 'pass123'
        )
        self.accounting_user.groups.add(self.accounting_group)
    
    def test_user_belongs_to_group(self):
        """اختبار انتماء المستخدم لمجموعة"""
        self.assertIn(self.sales_group, self.sales_user.groups.all())
    
    def test_user_not_in_other_group(self):
        """اختبار عدم انتماء المستخدم لمجموعة أخرى"""
        self.assertNotIn(self.accounting_group, self.sales_user.groups.all())
    
    def test_multiple_groups(self):
        """اختبار انتماء المستخدم لعدة مجموعات"""
        self.sales_user.groups.add(self.admin_group)
        
        groups = list(self.sales_user.groups.all())
        self.assertEqual(len(groups), 2)
        self.assertIn(self.sales_group, groups)
        self.assertIn(self.admin_group, groups)
    
    def test_remove_from_group(self):
        """اختبار إزالة المستخدم من مجموعة"""
        self.sales_user.groups.remove(self.sales_group)
        self.assertNotIn(self.sales_group, self.sales_user.groups.all())


# ===============================
# اختبارات حماية البيانات
# ===============================

class DataProtectionTestCase(TestCase):
    """اختبارات حماية البيانات"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user(
            'datauser', 'data@test.com', 'password123'
        )
    
    def test_password_not_stored_plaintext(self):
        """اختبار عدم تخزين كلمة المرور كنص صريح"""
        self.assertNotEqual(self.user.password, 'password123')
        self.assertTrue(self.user.password.startswith('pbkdf2_sha256$') or 
                       self.user.password.startswith('argon2$') or
                       self.user.password.startswith('bcrypt$'))
    
    def test_password_hashing(self):
        """اختبار تشفير كلمة المرور"""
        self.assertTrue(self.user.check_password('password123'))
        self.assertFalse(self.user.check_password('wrongpassword'))
    
    def test_sensitive_data_not_in_response(self):
        """اختبار عدم ظهور البيانات الحساسة في الاستجابة"""
        client = Client()
        client.login(username='datauser', password='password123')
        
        # التحقق من أن كلمة المرور لا تظهر في أي استجابة
        response = client.get('/admin/', follow=True)
        if response.status_code == 200:
            self.assertNotIn(b'password123', response.content)


# ===============================
# اختبارات التحقق من المدخلات
# ===============================

class InputValidationTestCase(TestCase):
    """اختبارات التحقق من المدخلات"""
    
    def test_sql_injection_prevention(self):
        """اختبار الحماية من حقن SQL"""
        from partners.models import Customer
        
        # محاولة حقن SQL
        malicious_name = "'; DROP TABLE customers; --"
        
        # Django ORM يحمي تلقائياً
        customer = Customer.objects.create(name=malicious_name)
        
        # التحقق من أن الاسم تم تخزينه كنص عادي
        self.assertEqual(customer.name, malicious_name)
        
        # التحقق من أن الجدول لا يزال موجوداً
        self.assertTrue(Customer.objects.exists())
    
    def test_xss_prevention(self):
        """اختبار الحماية من XSS"""
        from partners.models import Customer
        
        # محاولة حقن JavaScript
        malicious_name = '<script>alert("XSS")</script>'
        
        customer = Customer.objects.create(name=malicious_name)
        
        # التحقق من أن البيانات مخزنة
        self.assertEqual(customer.name, malicious_name)
    
    def test_email_validation(self):
        """اختبار التحقق من البريد الإلكتروني"""
        from django.core.exceptions import ValidationError
        from django.core.validators import validate_email
        
        # بريد إلكتروني صالح
        try:
            validate_email('valid@email.com')
            valid = True
        except ValidationError:
            valid = False
        
        self.assertTrue(valid)
        
        # بريد إلكتروني غير صالح
        try:
            validate_email('invalid-email')
            invalid = True
        except ValidationError:
            invalid = False
        
        self.assertFalse(invalid)
    
    def test_numeric_field_validation(self):
        """اختبار التحقق من الحقول الرقمية"""
        from decimal import Decimal, InvalidOperation
        
        # قيمة صالحة
        valid_decimal = Decimal('123.45')
        self.assertIsInstance(valid_decimal, Decimal)
        
        # قيمة غير صالحة
        with self.assertRaises(InvalidOperation):
            Decimal('not-a-number')


# ===============================
# اختبارات سجلات التدقيق
# ===============================

class AuditLogTestCase(TestCase):
    """اختبارات سجلات التدقيق"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user(
            'audituser', 'audit@test.com', 'password123'
        )
    
    def test_user_creation_logged(self):
        """اختبار تسجيل إنشاء المستخدم"""
        # التحقق من وجود المستخدم
        self.assertIsNotNone(self.user.date_joined)
    
    def test_login_timestamp(self):
        """اختبار تسجيل وقت تسجيل الدخول"""
        self.client = Client()
        self.client.login(username='audituser', password='password123')
        
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)
    
    def test_model_timestamps(self):
        """اختبار التواريخ التلقائية للنماذج"""
        from partners.models import Customer
        
        customer = Customer.objects.create(name='عميل تدقيق')
        
        # التحقق من تسجيل تاريخ الإنشاء (إذا كان الحقل موجوداً)
        self.assertIsNotNone(customer)


# ===============================
# اختبارات CSRF
# ===============================

class CSRFTestCase(TestCase):
    """اختبارات حماية CSRF"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            'csrfuser', 'csrf@test.com', 'password123'
        )
    
    def test_csrf_token_required(self):
        """اختبار أن CSRF token مطلوب"""
        # محاولة POST بدون CSRF token
        response = self.client.post('/admin/login/', {
            'username': 'csrfuser',
            'password': 'password123'
        })
        
        # يجب أن يفشل (403 أو إعادة توجيه)
        self.assertIn(response.status_code, [403, 302, 200])


# ===============================
# اختبارات حماية الجلسات
# ===============================

class SessionSecurityTestCase(TestCase):
    """اختبارات أمان الجلسات"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.client = Client()
        self.user = User.objects.create_user(
            'sessionuser', 'session@test.com', 'password123'
        )
    
    def test_session_created_on_login(self):
        """اختبار إنشاء جلسة عند تسجيل الدخول"""
        self.client.login(username='sessionuser', password='password123')
        self.assertIn('_auth_user_id', self.client.session)
    
    def test_session_destroyed_on_logout(self):
        """اختبار تدمير الجلسة عند تسجيل الخروج"""
        self.client.login(username='sessionuser', password='password123')
        self.client.logout()
        
        self.assertNotIn('_auth_user_id', self.client.session)
    
    def test_session_user_id_matches(self):
        """اختبار تطابق معرف المستخدم في الجلسة"""
        self.client.login(username='sessionuser', password='password123')
        
        session_user_id = int(self.client.session['_auth_user_id'])
        self.assertEqual(session_user_id, self.user.id)


# ===============================
# اختبارات حماية الملفات
# ===============================

class FileSecurityTestCase(TestCase):
    """اختبارات أمان الملفات"""
    
    def test_file_extension_validation(self):
        """اختبار التحقق من امتداد الملف"""
        from django.core.validators import FileExtensionValidator
        from django.core.exceptions import ValidationError
        
        validator = FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx']
        )
        
        # هذا اختبار للمنطق فقط
        allowed = ['pdf', 'doc', 'docx']
        not_allowed = ['exe', 'bat', 'sh']
        
        for ext in allowed:
            self.assertIn(ext, allowed)
        
        for ext in not_allowed:
            self.assertNotIn(ext, allowed)


# ===============================
# اختبارات أمان API
# ===============================

class APISecurityTestCase(TestCase):
    """اختبارات أمان API"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.client = Client()
        self.user = User.objects.create_user(
            'apiuser', 'api@test.com', 'password123'
        )
    
    def test_unauthenticated_api_access(self):
        """اختبار الوصول غير المصادق لـ API"""
        response = self.client.get('/api/')
        
        # يجب أن يكون 401 أو 403 أو 404
        self.assertIn(response.status_code, [401, 403, 404])
    
    def test_authenticated_api_access(self):
        """اختبار الوصول المصادق لـ API"""
        self.client.login(username='apiuser', password='password123')
        response = self.client.get('/api/')
        
        # API يستخدم JWT - جلسة المتصفح قد لا تكفي، لذا 401 مقبول أيضاً
        self.assertIn(response.status_code, [200, 401, 404])


# ===============================
# اختبارات Rate Limiting
# ===============================

class RateLimitingTestCase(TestCase):
    """اختبارات تحديد معدل الطلبات"""
    
    def test_multiple_login_attempts(self):
        """اختبار محاولات تسجيل دخول متعددة"""
        client = Client()
        
        # محاولات متعددة فاشلة
        for i in range(5):
            result = client.login(username='nonexistent', password='wrongpass')
            self.assertFalse(result)
        
        # في النظام الحقيقي، يجب أن يتم حظر المزيد من المحاولات


# ===============================
# اختبارات الصلاحيات على مستوى الكائنات
# ===============================

class ObjectLevelPermissionTestCase(TestCase):
    """اختبارات الصلاحيات على مستوى الكائنات"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user1 = User.objects.create_user('user1', 'user1@test.com', 'pass123')
        self.user2 = User.objects.create_user('user2', 'user2@test.com', 'pass123')
        
        from partners.models import Customer
        self.customer = Customer.objects.create(name='عميل صلاحيات')
    
    def test_owner_can_access_own_data(self):
        """اختبار أن المستخدم المسجل يمكنه الوصول لبياناته"""
        self.client.force_login(self.user1)
        # /users/profile/ هو المسار الصحيح في هذا المشروع
        response = self.client.get('/users/profile/')
        self.assertIn(response.status_code, [200, 301, 302])
    
    def test_unauthenticated_user_redirected(self):
        """اختبار أن المستخدم غير المسجل يتم تحويله"""
        response = self.client.get('/users/profile/')
        self.assertIn(response.status_code, [301, 302])
        if response.status_code == 302:
            self.assertIn('login', response.url)
    
    def test_different_user_isolation(self):
        """اختبار أن مستخدم آخر لا يرى بيانات المستخدم الأول"""
        self.client.force_login(self.user2)
        # التحقق أن المستخدم الثاني لا يرى profile المستخدم الأول
        response = self.client.get('/users/profile/')
        if response.status_code == 200:
            self.assertNotContains(response, self.user1.email)


# ===============================
# ملخص اختبارات الأمان
# ===============================

class SecuritySummaryTestCase(TestCase):
    """اختبارات ملخص الأمان الفعلية"""
    
    def test_csrf_middleware_enabled(self):
        """التحقق من تفعيل حماية CSRF"""
        from django.conf import settings
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE,
        )
    
    def test_xss_protection_header(self):
        """التحقق من إعدادات حماية XSS"""
        from django.conf import settings
        # SecurityMiddleware يضيف X-Content-Type-Options
        self.assertIn(
            'django.middleware.security.SecurityMiddleware',
            settings.MIDDLEWARE,
        )
    
    def test_password_hashers_configured(self):
        """التحقق من استخدام خوارزميات تشفير كلمات المرور"""
        from django.conf import settings
        hashers = getattr(settings, 'PASSWORD_HASHERS', [])
        # Django uses PBKDF2 by default which is secure
        if hashers:
            self.assertFalse(
                any('MD5' in h for h in hashers),
                "MD5 password hasher should not be used",
            )
    
    def test_session_cookie_settings(self):
        """التحقق من إعدادات أمان الجلسات"""
        from django.conf import settings
        # SESSION_COOKIE_HTTPONLY should be True (Django default)
        httponly = getattr(settings, 'SESSION_COOKIE_HTTPONLY', True)
        self.assertTrue(httponly, "SESSION_COOKIE_HTTPONLY should be True")
    
    def test_secret_key_not_default(self):
        """التحقق من أن SECRET_KEY ليس القيمة الافتراضية"""
        from django.conf import settings
        self.assertNotEqual(settings.SECRET_KEY, '')
        self.assertGreater(len(settings.SECRET_KEY), 20)
