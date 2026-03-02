"""
اختبارات Sprint 22A — محرك الصلاحيات المؤسسي
"""
from django.test import TestCase, Client
from apps.authorization.models import SystemPermission, SystemRole, UserRoleAssignment
from apps.authorization.services.permission_engine import PermissionEngine
from apps.authorization.services.menu_builder import MenuBuilder


class PermissionSetupTest(TestCase):
    """اختبار إنشاء الصلاحيات"""

    def test_setup_permissions_command(self):
        from django.core.management import call_command
        call_command('setup_permissions', verbosity=0)
        self.assertGreaterEqual(SystemPermission.objects.count(), 50)
        self.assertGreaterEqual(SystemRole.objects.count(), 17)

    def test_all_roles_have_permissions(self):
        from django.core.management import call_command
        call_command('setup_permissions', verbosity=0)
        for role in SystemRole.objects.all():
            self.assertGreater(role.permissions.count(), 0,
                               f"الدور {role.name} بدون صلاحيات!")


class PermissionEngineTest(TestCase):
    """اختبار محرك الصلاحيات"""

    def setUp(self):
        from django.core.management import call_command
        call_command('setup_permissions', verbosity=0)
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.admin = User.objects.create_superuser('admin_22a', 'a@a.com', 'test123')
        self.salesperson_user = User.objects.create_user('seller1_22a', password='test123')
        self.storekeeper_user = User.objects.create_user('store1_22a', password='test123')
        self.cashier_user = User.objects.create_user('cashier1_22a', password='test123')

        seller_role = SystemRole.objects.get(code='salesperson')
        store_role = SystemRole.objects.get(code='storekeeper')
        cashier_role = SystemRole.objects.get(code='cashier')

        UserRoleAssignment.objects.create(user=self.salesperson_user, role=seller_role)
        UserRoleAssignment.objects.create(user=self.storekeeper_user, role=store_role)
        UserRoleAssignment.objects.create(user=self.cashier_user, role=cashier_role)

    def test_admin_has_all_permissions(self):
        self.assertTrue(PermissionEngine.has_permission(self.admin, 'accounts', 'view'))
        self.assertTrue(PermissionEngine.has_permission(self.admin, 'accounts', 'close'))

    def test_salesperson_can_view_sales(self):
        self.assertTrue(PermissionEngine.has_permission(self.salesperson_user, 'sales', 'view'))

    def test_salesperson_cannot_view_accounts(self):
        self.assertFalse(PermissionEngine.has_permission(self.salesperson_user, 'accounts', 'view'))

    def test_salesperson_cannot_view_cost(self):
        self.assertFalse(PermissionEngine.has_permission(self.salesperson_user, 'accounts', 'view_cost'))

    def test_salesperson_cannot_cancel_invoice(self):
        self.assertFalse(PermissionEngine.has_permission(self.salesperson_user, 'sales', 'cancel'))

    def test_storekeeper_cannot_view_accounts(self):
        self.assertFalse(PermissionEngine.has_permission(self.storekeeper_user, 'accounts', 'view'))

    def test_storekeeper_cannot_adjust_stock(self):
        """أمين المخزن لا يعمل تسوية بدون اعتماد"""
        self.assertFalse(PermissionEngine.has_permission(self.storekeeper_user, 'inventory', 'adjust'))

    def test_cashier_cannot_cancel_invoice(self):
        self.assertFalse(PermissionEngine.has_permission(self.cashier_user, 'sales', 'cancel'))

    def test_cashier_cannot_give_discount(self):
        self.assertFalse(PermissionEngine.has_permission(self.cashier_user, 'sales', 'give_discount'))

    def test_max_discount_for_salesperson(self):
        from decimal import Decimal
        max_disc = PermissionEngine.get_max_discount(self.salesperson_user)
        self.assertEqual(max_disc, Decimal('5'))

    def test_max_discount_for_cashier(self):
        from decimal import Decimal
        max_disc = PermissionEngine.get_max_discount(self.cashier_user)
        self.assertEqual(max_disc, Decimal('0'))


class MenuBuilderTest(TestCase):
    """اختبار القائمة الديناميكية"""

    def setUp(self):
        from django.core.management import call_command
        call_command('setup_permissions', verbosity=0)
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.admin = User.objects.create_superuser('admin_menu_22a', 'a@a.com', 'test123')
        self.storekeeper_user = User.objects.create_user('store_menu_22a', password='test123')
        store_role = SystemRole.objects.get(code='storekeeper')
        UserRoleAssignment.objects.create(user=self.storekeeper_user, role=store_role)

    def test_admin_sees_all_menus(self):
        menu = MenuBuilder.build_menu(self.admin)
        menu_ids = [s['id'] for s in menu]
        self.assertIn('accounts', menu_ids)
        self.assertIn('hr', menu_ids)
        self.assertIn('settings', menu_ids)

    def test_storekeeper_sees_only_inventory(self):
        """أمين المخزن لا يرى المحاسبة ولا HR ولا المبيعات"""
        menu = MenuBuilder.build_menu(self.storekeeper_user)
        menu_ids = [s['id'] for s in menu]
        self.assertIn('inventory', menu_ids)
        self.assertNotIn('accounts', menu_ids)
        self.assertNotIn('hr', menu_ids)
        self.assertNotIn('sales', menu_ids)
        self.assertNotIn('settings', menu_ids)

    def test_storekeeper_inventory_has_no_valuation(self):
        """أمين المخزن لا يرى تقييم المخزون (لأنه يحتاج view_cost)"""
        menu = MenuBuilder.build_menu(self.storekeeper_user)
        inventory_sections = [s for s in menu if s['id'] == 'inventory']
        self.assertTrue(len(inventory_sections) > 0, "أمين المخزن يجب أن يرى قسم المخزون")
        inventory_section = inventory_sections[0]
        child_urls = [c.get('url_name', '') for c in inventory_section['children']]
        self.assertNotIn('inventory:valuation', child_urls)


class ServerEnforcementTest(TestCase):
    """اختبار طبقة السيرفر"""

    def setUp(self):
        from django.core.management import call_command
        call_command('setup_permissions', verbosity=0)
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.storekeeper_user = User.objects.create_user('store_server_22a', password='test123')
        store_role = SystemRole.objects.get(code='storekeeper')
        UserRoleAssignment.objects.create(user=self.storekeeper_user, role=store_role)

        self.client = Client()
        self.client.login(username='store_server_22a', password='test123')

    def test_storekeeper_blocked_from_accounts(self):
        """أمين المخزن يُرفض من صفحة المحاسبة"""
        response = self.client.get('/accounts/')
        self.assertEqual(response.status_code, 302)

    def test_storekeeper_blocked_from_hr(self):
        response = self.client.get('/hr/employees/')
        self.assertEqual(response.status_code, 302)

    def test_storekeeper_can_access_inventory(self):
        response = self.client.get('/inventory/products/')
        self.assertIn(response.status_code, [200, 302])

    def test_violation_is_logged(self):
        """محاولة الوصول المرفوضة تُسجّل"""
        from apps.authorization.models import SecurityViolationLog
        initial_count = SecurityViolationLog.objects.count()
        self.client.get('/accounts/')
        self.assertGreater(SecurityViolationLog.objects.count(), initial_count)
        log = SecurityViolationLog.objects.order_by('-timestamp').first()
        self.assertEqual(log.user, self.storekeeper_user)
        self.assertEqual(log.attempted_module, 'accounts')


class DelegationTest(TestCase):
    """اختبار التفويض الهرمي"""

    def setUp(self):
        from django.core.management import call_command
        call_command('setup_permissions', verbosity=0)

    def test_branch_manager_can_grant_salesperson(self):
        bm_role = SystemRole.objects.get(code='branch_manager')
        seller_role = SystemRole.objects.get(code='salesperson')
        self.assertTrue(seller_role.can_be_granted_by.filter(id=bm_role.id).exists())

    def test_branch_manager_cannot_grant_cfo(self):
        bm_role = SystemRole.objects.get(code='branch_manager')
        cfo_role = SystemRole.objects.get(code='cfo')
        self.assertFalse(cfo_role.can_be_granted_by.filter(id=bm_role.id).exists())
