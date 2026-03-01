"""
اختبارات نظام الصلاحيات — RITA ERP (Sprint 6)
"""
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from django.utils import timezone

from apps.authorization.models import (
    Role, Permission, UserRole, AuditLog, Delegation,
)
from apps.authorization.services.permission_engine import PermissionEngine
from apps.authorization.services.audit import log_action, get_audit_log
from apps.core.models import User, Branch


class RoleModelTest(TestCase):
    """اختبار نموذج الأدوار"""

    def test_create_role(self):
        """إنشاء دور جديد"""
        role = Role.objects.create(
            name='محاسب اختبار',
            level='accountant',
            description='دور اختباري',
            max_discount_percentage=Decimal('5.00'),
        )
        self.assertEqual(role.name, 'محاسب اختبار')
        self.assertEqual(role.level, 'accountant')
        self.assertTrue(role.is_active)
        self.assertFalse(role.is_deleted)

    def test_role_str(self):
        """التأكد من __str__"""
        role = Role.objects.create(name='مدير', level='ceo')
        self.assertEqual(str(role), 'مدير')

    def test_role_soft_delete(self):
        """الحذف الناعم"""
        role = Role.objects.create(name='للحذف', level='custom')
        role.is_deleted = True
        role.save()
        self.assertTrue(role.is_deleted)
        # لا يزال موجود في DB
        self.assertTrue(Role.objects.filter(pk=role.pk).exists())


class PermissionModelTest(TestCase):
    """اختبار نموذج الصلاحيات"""

    def setUp(self):
        self.role = Role.objects.create(
            name='بائع اختبار', level='salesperson'
        )

    def test_create_permission(self):
        """إنشاء صلاحية"""
        perm = Permission.objects.create(
            role=self.role,
            module='sales',
            action='view',
            is_allowed=True,
        )
        self.assertTrue(perm.is_allowed)
        self.assertEqual(perm.module, 'sales')

    def test_unique_together(self):
        """لا يمكن تكرار نفس الصلاحية"""
        Permission.objects.create(
            role=self.role, module='sales', action='view', is_allowed=True
        )
        with self.assertRaises(Exception):
            Permission.objects.create(
                role=self.role, module='sales', action='view', is_allowed=False
            )


class PermissionEngineTest(TestCase):
    """اختبار محرك الصلاحيات"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            first_name='أحمد', last_name='تجريبي',
        )
        self.superuser = User.objects.create_superuser(
            username='admin', password='adminpass123',
        )
        self.role = Role.objects.create(
            name='بائع', level='salesperson',
            max_discount_percentage=Decimal('5.00'),
            can_see_cost=False,
            can_see_profit=False,
        )
        Permission.objects.create(
            role=self.role, module='sales', action='view', is_allowed=True
        )
        Permission.objects.create(
            role=self.role, module='sales', action='create', is_allowed=True
        )
        Permission.objects.create(
            role=self.role, module='inventory', action='view', is_allowed=True
        )
        UserRole.objects.create(
            user=self.user, role=self.role, is_primary=True, is_active=True
        )

    def test_has_permission_allowed(self):
        """المستخدم لديه صلاحية مسموحة"""
        self.assertTrue(PermissionEngine.has_permission(self.user, 'sales', 'view'))
        self.assertTrue(PermissionEngine.has_permission(self.user, 'sales', 'create'))

    def test_has_permission_denied(self):
        """المستخدم ليس لديه صلاحية"""
        self.assertFalse(PermissionEngine.has_permission(self.user, 'accounts', 'view'))
        self.assertFalse(PermissionEngine.has_permission(self.user, 'sales', 'delete'))

    def test_superuser_has_all_permissions(self):
        """المشرف لديه كل الصلاحيات"""
        self.assertTrue(PermissionEngine.has_permission(self.superuser, 'accounts', 'view'))
        self.assertTrue(PermissionEngine.has_permission(self.superuser, 'production', 'delete'))

    def test_anonymous_user_no_permissions(self):
        """المستخدم غير المسجل ليس لديه صلاحيات"""
        self.assertFalse(PermissionEngine.has_permission(None, 'sales', 'view'))

    def test_get_user_permissions(self):
        """استرجاع كل صلاحيات المستخدم"""
        perms = PermissionEngine.get_user_permissions(self.user)
        self.assertIn('sales', perms)
        self.assertTrue(perms['sales'].get('view'))
        self.assertTrue(perms['sales'].get('create'))
        self.assertNotIn('accounts', perms)

    def test_can_user_discount_within_limit(self):
        """المستخدم يقدر يعمل خصم ضمن الحد"""
        self.assertTrue(PermissionEngine.can_user_discount(self.user, Decimal('3.00')))
        self.assertTrue(PermissionEngine.can_user_discount(self.user, Decimal('5.00')))

    def test_can_user_discount_exceeds_limit(self):
        """المستخدم ما يقدرش يعمل خصم أعلى من الحد"""
        self.assertFalse(PermissionEngine.can_user_discount(self.user, Decimal('10.00')))

    def test_get_max_discount(self):
        """أقصى نسبة خصم"""
        self.assertEqual(PermissionEngine.get_max_discount(self.user), Decimal('5.00'))

    def test_has_role_level(self):
        """التحقق من مستوى الدور"""
        self.assertTrue(PermissionEngine.has_role_level(self.user, 'salesperson'))
        self.assertFalse(PermissionEngine.has_role_level(self.user, 'ceo'))

    def test_can_see_cost(self):
        """التحقق من صلاحية رؤية التكلفة"""
        self.assertFalse(PermissionEngine.can_see_cost(self.user))
        self.assertTrue(PermissionEngine.can_see_cost(self.superuser))

    def test_can_see_profit(self):
        """التحقق من صلاحية رؤية الأرباح"""
        self.assertFalse(PermissionEngine.can_see_profit(self.user))


class DelegationTest(TestCase):
    """اختبار التفويض المؤقت"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='delegator', password='testpass',
        )
        self.user2 = User.objects.create_user(
            username='delegate', password='testpass',
        )
        self.role = Role.objects.create(
            name='مدير مالي', level='cfo',
            max_discount_percentage=Decimal('50.00'),
            can_see_cost=True,
            can_see_profit=True,
        )
        Permission.objects.create(
            role=self.role, module='accounts', action='view', is_allowed=True
        )
        Permission.objects.create(
            role=self.role, module='accounts', action='create', is_allowed=True
        )
        Permission.objects.create(
            role=self.role, module='accounts', action='approve', is_allowed=True
        )

    def test_active_delegation_grants_permission(self):
        """التفويض النشط يمنح الصلاحية"""
        now = timezone.now()
        Delegation.objects.create(
            delegator=self.user1,
            delegate=self.user2,
            role=self.role,
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(days=7),
            reason='إجازة',
            is_active=True,
        )
        self.assertTrue(PermissionEngine.has_permission(self.user2, 'accounts', 'view'))
        self.assertTrue(PermissionEngine.has_permission(self.user2, 'accounts', 'approve'))

    def test_expired_delegation_no_permission(self):
        """التفويض المنتهي لا يمنح صلاحية"""
        now = timezone.now()
        Delegation.objects.create(
            delegator=self.user1,
            delegate=self.user2,
            role=self.role,
            start_date=now - timedelta(days=10),
            end_date=now - timedelta(days=1),
            reason='إجازة انتهت',
            is_active=True,
        )
        self.assertFalse(PermissionEngine.has_permission(self.user2, 'accounts', 'view'))

    def test_inactive_delegation_no_permission(self):
        """التفويض المعطل لا يمنح صلاحية"""
        now = timezone.now()
        Delegation.objects.create(
            delegator=self.user1,
            delegate=self.user2,
            role=self.role,
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(days=7),
            reason='تم إلغاؤه',
            is_active=False,
        )
        self.assertFalse(PermissionEngine.has_permission(self.user2, 'accounts', 'view'))


class AuditLogTest(TestCase):
    """اختبار سجل التدقيق"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='auditor', password='testpass',
        )

    def test_log_action(self):
        """تسجيل حركة"""
        log = log_action(
            user=self.user,
            action='create',
            module='sales',
            model_name='SalesInvoice',
            object_id='123',
            description='إنشاء فاتورة بيع جديدة',
            ip_address='192.168.1.100',
        )
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.module, 'sales')
        self.assertEqual(log.object_id, '123')
        self.assertIsNotNone(log.timestamp)

    def test_get_audit_log_no_filter(self):
        """استعلام السجل بدون فلتر"""
        log_action(user=self.user, action='create', module='sales', description='test1')
        log_action(user=self.user, action='update', module='sales', description='test2')
        logs = get_audit_log()
        self.assertEqual(logs.count(), 2)

    def test_get_audit_log_with_filter(self):
        """استعلام السجل مع فلتر"""
        log_action(user=self.user, action='create', module='sales', description='test1')
        log_action(user=self.user, action='update', module='inventory', description='test2')
        log_action(user=self.user, action='delete', module='sales', description='test3')

        logs = get_audit_log({'module': 'sales'})
        self.assertEqual(logs.count(), 2)

        logs = get_audit_log({'action': 'update'})
        self.assertEqual(logs.count(), 1)


class ViewPermissionTest(TestCase):
    """اختبار الصفحات مع الصلاحيات"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='viewtester', password='testpass123',
        )
        self.superuser = User.objects.create_superuser(
            username='superadmin', password='superpass123',
        )

    def test_role_list_requires_login(self):
        """صفحة الأدوار تتطلب تسجيل دخول"""
        response = self.client.get(reverse('authorization:role_list'))
        self.assertNotEqual(response.status_code, 200)

    def test_role_list_accessible_to_superuser(self):
        """المشرف يقدر يدخل صفحة الأدوار"""
        self.client.login(username='superadmin', password='superpass123')
        response = self.client.get(reverse('authorization:role_list'))
        self.assertEqual(response.status_code, 200)

    def test_audit_log_accessible_to_superuser(self):
        """المشرف يقدر يدخل سجل التدقيق"""
        self.client.login(username='superadmin', password='superpass123')
        response = self.client.get(reverse('authorization:audit_log'))
        self.assertEqual(response.status_code, 200)

    def test_delegation_list_accessible_to_superuser(self):
        """المشرف يقدر يدخل التفويضات"""
        self.client.login(username='superadmin', password='superpass123')
        response = self.client.get(reverse('authorization:delegation_list'))
        self.assertEqual(response.status_code, 200)

    def test_role_create_page(self):
        """صفحة إنشاء دور"""
        self.client.login(username='superadmin', password='superpass123')
        response = self.client.get(reverse('authorization:role_create'))
        self.assertEqual(response.status_code, 200)

    def test_assign_role_page(self):
        """صفحة تعيين الأدوار"""
        self.client.login(username='superadmin', password='superpass123')
        response = self.client.get(reverse('authorization:assign_role'))
        self.assertEqual(response.status_code, 200)

    def test_user_without_permission_denied(self):
        """المستخدم بدون صلاحية يُرفض"""
        self.client.login(username='viewtester', password='testpass123')
        response = self.client.get(reverse('authorization:role_list'))
        self.assertEqual(response.status_code, 403)

    def test_user_with_permission_access(self):
        """المستخدم مع صلاحية يقدر يدخل"""
        role = Role.objects.create(
            name='أدمن', level='owner',
        )
        Permission.objects.create(
            role=role, module='settings', action='view', is_allowed=True
        )
        UserRole.objects.create(
            user=self.user, role=role, is_primary=True, is_active=True
        )
        self.client.login(username='viewtester', password='testpass123')
        response = self.client.get(reverse('authorization:role_list'))
        self.assertEqual(response.status_code, 200)

    def test_creating_role_with_permissions(self):
        """إنشاء دور مع صلاحيات عبر POST"""
        self.client.login(username='superadmin', password='superpass123')
        response = self.client.post(reverse('authorization:role_create'), {
            'name': 'دور تجريبي',
            'level': 'custom',
            'description': 'دور للاختبار',
            'max_discount_percentage': '10.00',
            'is_active': 'on',
            'perm_sales_view': 'on',
            'perm_sales_create': 'on',
        })
        self.assertEqual(response.status_code, 302)  # redirect
        self.assertTrue(Role.objects.filter(name='دور تجريبي').exists())
        role = Role.objects.get(name='دور تجريبي')
        self.assertTrue(
            Permission.objects.filter(
                role=role, module='sales', action='view', is_allowed=True
            ).exists()
        )
        self.assertTrue(
            Permission.objects.filter(
                role=role, module='sales', action='create', is_allowed=True
            ).exists()
        )
        # الصلاحيات غير المحددة يجب أن تكون False
        self.assertTrue(
            Permission.objects.filter(
                role=role, module='accounts', action='view', is_allowed=False
            ).exists()
        )

    def test_assign_role_to_user(self):
        """تعيين دور لمستخدم"""
        self.client.login(username='superadmin', password='superpass123')
        role = Role.objects.create(name='كاشير', level='cashier')
        response = self.client.post(reverse('authorization:assign_role'), {
            'user': str(self.user.pk),
            'role': str(role.pk),
            'is_primary': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            UserRole.objects.filter(user=self.user, role=role, is_active=True).exists()
        )


class SetupRolesCommandTest(TestCase):
    """اختبار أمر إعداد الأدوار"""

    def test_setup_roles_command(self):
        """تشغيل setup_roles ينشئ الأدوار"""
        from django.core.management import call_command
        call_command('setup_roles')
        self.assertTrue(Role.objects.filter(level='owner').exists())
        self.assertTrue(Role.objects.filter(level='ceo').exists())
        self.assertTrue(Role.objects.filter(level='salesperson').exists())
        self.assertTrue(Role.objects.filter(level='cashier').exists())
        self.assertEqual(Role.objects.count(), 11)

    def test_setup_roles_idempotent(self):
        """تشغيل setup_roles مرتين لا يكرر البيانات"""
        from django.core.management import call_command
        call_command('setup_roles')
        count1 = Role.objects.count()
        call_command('setup_roles')
        count2 = Role.objects.count()
        self.assertEqual(count1, count2)

    def test_owner_has_all_permissions(self):
        """دور الإدارة العليا لديه كل الصلاحيات"""
        from django.core.management import call_command
        call_command('setup_roles')
        owner = Role.objects.get(level='owner')
        # يجب أن يكون لديه صلاحية على كل الأقسام
        for mod_code, _ in Permission.MODULES:
            for act_code, _ in Permission.ACTIONS:
                self.assertTrue(
                    Permission.objects.filter(
                        role=owner, module=mod_code, action=act_code, is_allowed=True
                    ).exists(),
                    f'المالك يجب أن يكون لديه {mod_code}.{act_code}'
                )

    def test_salesperson_limited_permissions(self):
        """البائع لديه صلاحيات محدودة"""
        from django.core.management import call_command
        call_command('setup_roles')
        salesperson = Role.objects.get(level='salesperson')
        # يقدر يشوف وينشئ مبيعات
        self.assertTrue(
            Permission.objects.filter(
                role=salesperson, module='sales', action='view', is_allowed=True
            ).exists()
        )
        self.assertTrue(
            Permission.objects.filter(
                role=salesperson, module='sales', action='create', is_allowed=True
            ).exists()
        )
        # ما يقدرش يحذف
        self.assertFalse(
            Permission.objects.filter(
                role=salesperson, module='sales', action='delete', is_allowed=True
            ).exists()
        )
        # ما يقدرش يدخل المحاسبة
        self.assertFalse(
            Permission.objects.filter(
                role=salesperson, module='accounts', action='view', is_allowed=True
            ).exists()
        )
        # الخصم 5%
        self.assertEqual(salesperson.max_discount_percentage, Decimal('5'))
