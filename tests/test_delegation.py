"""
Sprint 22A Part 2 — اختبارات التفويض الهرمي
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.authorization.models import SystemRole, UserRoleAssignment
from apps.authorization.services.delegation_engine import DelegationEngine

User = get_user_model()


class DelegationEngineTest(TestCase):

    def setUp(self):
        from django.core.management import call_command
        call_command('setup_permissions', verbosity=0)

        # إنشاء المستخدمين
        self.admin = User.objects.create_superuser('admin', 'a@a.com', 'test123')

        # مدير فرع القاهرة
        self.branch_mgr = User.objects.create_user('cairo_mgr', password='test123')
        bm_role = SystemRole.objects.get(code='branch_manager')
        from apps.core.models import Branch
        self.cairo = Branch.objects.create(name='القاهرة', is_active=True)
        self.alex = Branch.objects.create(name='الإسكندرية', is_active=True)
        UserRoleAssignment.objects.create(
            user=self.branch_mgr, role=bm_role, branch=self.cairo, assigned_by=self.admin,
        )

        # مدير إنتاج
        self.prod_mgr = User.objects.create_user('prod_mgr', password='test123')
        pm_role = SystemRole.objects.get(code='production_manager')
        UserRoleAssignment.objects.create(
            user=self.prod_mgr, role=pm_role, assigned_by=self.admin,
        )

        # بائع
        self.seller = User.objects.create_user('seller1', password='test123')
        seller_role = SystemRole.objects.get(code='salesperson')
        UserRoleAssignment.objects.create(
            user=self.seller, role=seller_role, branch=self.cairo, assigned_by=self.branch_mgr,
        )

    # ═══ اختبار الأدوار المسموحة ═══

    def test_branch_manager_can_grant_salesperson(self):
        roles = DelegationEngine.get_grantable_roles(self.branch_mgr)
        codes = list(roles.values_list('code', flat=True))
        self.assertIn('salesperson', codes)
        self.assertIn('cashier', codes)
        self.assertIn('storekeeper', codes)

    def test_branch_manager_cannot_grant_accountant(self):
        roles = DelegationEngine.get_grantable_roles(self.branch_mgr)
        codes = list(roles.values_list('code', flat=True))
        self.assertNotIn('accountant_manager', codes)
        self.assertNotIn('cfo', codes)
        self.assertNotIn('production_manager', codes)

    def test_production_manager_can_grant_supervisor(self):
        roles = DelegationEngine.get_grantable_roles(self.prod_mgr)
        codes = list(roles.values_list('code', flat=True))
        self.assertIn('production_supervisor', codes)
        self.assertIn('qc_inspector', codes)

    def test_production_manager_cannot_grant_salesperson(self):
        roles = DelegationEngine.get_grantable_roles(self.prod_mgr)
        codes = list(roles.values_list('code', flat=True))
        self.assertNotIn('salesperson', codes)
        self.assertNotIn('cashier', codes)

    def test_salesperson_cannot_grant_anyone(self):
        roles = DelegationEngine.get_grantable_roles(self.seller)
        self.assertEqual(roles.count(), 0)

    def test_admin_can_grant_all(self):
        roles = DelegationEngine.get_grantable_roles(self.admin)
        self.assertGreaterEqual(roles.count(), 10)

    # ═══ اختبار النطاق ═══

    def test_branch_manager_sees_own_branch_only(self):
        branches = DelegationEngine.get_grantable_branches(self.branch_mgr)
        branch_ids = list(branches.values_list('id', flat=True))
        self.assertIn(self.cairo.id, branch_ids)
        self.assertNotIn(self.alex.id, branch_ids)

    def test_admin_sees_all_branches(self):
        branches = DelegationEngine.get_grantable_branches(self.admin)
        self.assertGreaterEqual(branches.count(), 2)

    # ═══ اختبار التحقق الشامل ═══

    def test_branch_manager_valid_assignment(self):
        seller_role = SystemRole.objects.get(code='salesperson')
        is_valid, error = DelegationEngine.validate_assignment(
            self.branch_mgr, seller_role, self.cairo
        )
        self.assertTrue(is_valid, msg=error)

    def test_branch_manager_cannot_assign_to_other_branch(self):
        seller_role = SystemRole.objects.get(code='salesperson')
        is_valid, error = DelegationEngine.validate_assignment(
            self.branch_mgr, seller_role, self.alex
        )
        self.assertFalse(is_valid)
        self.assertIn('صلاحية', error)

    def test_branch_manager_cannot_assign_accountant(self):
        acc_role = SystemRole.objects.get(code='accountant_manager')
        is_valid, error = DelegationEngine.validate_assignment(
            self.branch_mgr, acc_role, self.cairo
        )
        self.assertFalse(is_valid)

    def test_role_without_branch_rejected(self):
        """دور scope=branch بدون تحديد فرع = خطأ"""
        seller_role = SystemRole.objects.get(code='salesperson')
        is_valid, error = DelegationEngine.validate_assignment(
            self.admin, seller_role, branch=None
        )
        self.assertFalse(is_valid)
        self.assertIn('فرع', error)


class DelegatedUserCreateTest(TestCase):
    """اختبار شاشة إضافة المستخدم"""

    def setUp(self):
        from django.core.management import call_command
        call_command('setup_permissions', verbosity=0)

        self.admin = User.objects.create_superuser('admin_create', 'a2@a.com', 'test123')

        from apps.core.models import Branch
        self.cairo = Branch.objects.create(name='القاهرة_2', is_active=True)

        self.branch_mgr = User.objects.create_user('cairo_mgr2', password='test123')
        bm_role = SystemRole.objects.get(code='branch_manager')
        UserRoleAssignment.objects.create(
            user=self.branch_mgr, role=bm_role, branch=self.cairo, assigned_by=self.admin,
        )

        self.seller = User.objects.create_user('seller2', password='test123')
        seller_role = SystemRole.objects.get(code='salesperson')
        UserRoleAssignment.objects.create(
            user=self.seller, role=seller_role, branch=self.cairo, assigned_by=self.branch_mgr,
        )

    def test_create_page_shows_only_allowed_roles(self):
        """مدير الفرع يرى فقط الأدوار المسموحة"""
        client = Client()
        client.login(username='cairo_mgr2', password='test123')
        response = client.get('/users/create/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'بائع')
        self.assertContains(response, 'كاشير')
        self.assertNotContains(response, 'مدير مالي')
        self.assertNotContains(response, 'مدير إنتاج')

    def test_seller_cannot_access_create_page(self):
        """البائع لا يقدر يضيف مستخدمين"""
        client = Client()
        client.login(username='seller2', password='test123')
        response = client.get('/users/create/')
        # يتحول للقائمة مع رسالة خطأ
        self.assertEqual(response.status_code, 302)

    def test_branch_manager_creates_seller_in_his_branch(self):
        """مدير الفرع ينشئ بائع في فرعه"""
        client = Client()
        client.login(username='cairo_mgr2', password='test123')

        seller_role = SystemRole.objects.get(code='salesperson')

        response = client.post('/users/create/', {
            'username': 'new_seller',
            'password': 'testpass123',
            'confirm_password': 'testpass123',
            'first_name': 'أحمد',
            'last_name': 'محمد',
            'role': seller_role.id,
            'branch': self.cairo.id,
        })

        # تأكد إن المستخدم اتعمل
        self.assertTrue(User.objects.filter(username='new_seller').exists())

        # تأكد إن الدور اتعيّن
        new_user = User.objects.get(username='new_seller')
        assignment = UserRoleAssignment.objects.get(user=new_user, is_active=True)
        self.assertEqual(assignment.role.code, 'salesperson')
        self.assertEqual(assignment.branch, self.cairo)
        self.assertEqual(assignment.assigned_by, self.branch_mgr)

    def test_branch_manager_cannot_create_in_other_branch(self):
        """مدير فرع القاهرة لا ينشئ في الإسكندرية"""
        client = Client()
        client.login(username='cairo_mgr2', password='test123')

        from apps.core.models import Branch
        alex = Branch.objects.create(name='الإسكندرية', is_active=True)
        seller_role = SystemRole.objects.get(code='salesperson')

        response = client.post('/users/create/', {
            'username': 'alex_seller',
            'password': 'testpass123',
            'confirm_password': 'testpass123',
            'first_name': 'علي',
            'role': seller_role.id,
            'branch': alex.id,
        })

        # لا يتم الإنشاء
        self.assertFalse(User.objects.filter(username='alex_seller').exists())

    def test_audit_log_created_on_user_creation(self):
        """كل إنشاء مستخدم يُسجل في Audit Log"""
        client = Client()
        client.login(username='cairo_mgr2', password='test123')

        seller_role = SystemRole.objects.get(code='salesperson')
        client.post('/users/create/', {
            'username': 'audit_test',
            'password': 'testpass123',
            'confirm_password': 'testpass123',
            'first_name': 'تجربة',
            'role': seller_role.id,
            'branch': self.cairo.id,
        })

        from apps.authorization.models import AuditLog
        log = AuditLog.objects.filter(
            action='create', model_name='User',
        ).last()
        self.assertIsNotNone(log)
        self.assertIn('audit_test', log.description)
        self.assertIn('بائع', log.description)
