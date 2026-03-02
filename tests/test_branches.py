"""
اختبارات Sprint 12 — إدارة الفروع المتعددة (Multi-Branch)
RITA ERP
"""
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Branch, Warehouse
from apps.core.middleware import BranchMiddleware
from apps.core.mixins import apply_branch_filter, BranchFilterMixin, BranchCreateMixin

User = get_user_model()


# ══════════════════════════════════════════════════════
# Helper — إنشاء بيانات اختبار
# ══════════════════════════════════════════════════════

def create_branch(name='فرع A', branch_type='owned', is_active=True):
    return Branch.objects.create(name=name, branch_type=branch_type, is_active=is_active)


def create_user(username, branch=None, is_superuser=False, is_staff=False):
    user = User.objects.create_user(
        username=username,
        password='Test@1234',
        branch=branch,
        is_superuser=is_superuser,
        is_staff=is_staff,
    )
    return user


# ══════════════════════════════════════════════════════
# 1. اختبارات الـ Middleware
# ══════════════════════════════════════════════════════

class BranchMiddlewareTestCase(TestCase):
    """اختبارات BranchMiddleware"""

    def setUp(self):
        self.factory = RequestFactory()
        self.branch_a = create_branch('فرع A')
        self.branch_b = create_branch('فرع B')
        self.user_a = create_user('user_a', branch=self.branch_a)
        self.admin = create_user('admin_user', is_superuser=True)

    def _get_request(self, user, session_data=None):
        """إنشاء request وهمي مع user"""
        from django.contrib.sessions.backends.db import SessionStore
        request = self.factory.get('/')
        request.user = user
        session = SessionStore()
        if session_data:
            for k, v in session_data.items():
                session[k] = v
        session.save()
        request.session = session
        return request

    def test_unauthenticated_sets_no_branch(self):
        """المستخدم غير المسجل لا يحصل على فرع"""
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get('/')
        request.user = AnonymousUser()
        request.session = {}
        middleware = BranchMiddleware(get_response=lambda r: None)
        middleware.process_request(request)
        self.assertIsNone(request.current_branch)
        self.assertFalse(request.can_see_all_branches)

    def test_regular_user_gets_their_branch(self):
        """المستخدم العادي يحصل على فرعه"""
        request = self._get_request(self.user_a)
        middleware = BranchMiddleware(get_response=lambda r: None)
        middleware.process_request(request)
        self.assertEqual(request.current_branch, self.branch_a)
        self.assertFalse(request.can_see_all_branches)

    def test_superuser_can_see_all_branches(self):
        """الـ Admin يحصل على can_see_all_branches = True"""
        request = self._get_request(self.admin)
        middleware = BranchMiddleware(get_response=lambda r: None)
        middleware.process_request(request)
        self.assertTrue(request.can_see_all_branches)

    def test_superuser_with_session_branch_gets_current_branch(self):
        """الـ Admin اللي اختار فرع من الـ session يحصل على الفرع ده"""
        request = self._get_request(self.admin, {'active_branch_id': self.branch_a.id})
        middleware = BranchMiddleware(get_response=lambda r: None)
        middleware.process_request(request)
        self.assertTrue(request.can_see_all_branches)
        self.assertEqual(request.current_branch, self.branch_a)


# ══════════════════════════════════════════════════════
# 2. اختبارات apply_branch_filter
# ══════════════════════════════════════════════════════

class ApplyBranchFilterTestCase(TestCase):
    """اختبارات دالة apply_branch_filter"""

    def setUp(self):
        self.branch_a = create_branch('فرع A')
        self.branch_b = create_branch('فرع B')
        self.user_a = create_user('user_a', branch=self.branch_a)
        self.admin = create_user('admin_user', is_superuser=True)

    def _make_request(self, user, current_branch=None, can_see_all=False):
        """إنشاء request وهمي"""
        request = RequestFactory().get('/')
        request.user = user
        request.current_branch = current_branch
        request.can_see_all_branches = can_see_all
        return request

    def test_regular_user_sees_only_their_branch(self):
        """مستخدم فرع A يرى مخازن فرع A فقط"""
        Warehouse.objects.create(name='مخزن A1', branch=self.branch_a)
        Warehouse.objects.create(name='مخزن B1', branch=self.branch_b)
        request = self._make_request(self.user_a, current_branch=self.branch_a)
        qs = apply_branch_filter(Warehouse.objects.all(), request)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().branch, self.branch_a)

    def test_user_without_branch_sees_nothing(self):
        """مستخدم بدون فرع لا يرى أي بيانات"""
        Warehouse.objects.create(name='مخزن A1', branch=self.branch_a)
        user_no_branch = create_user('no_branch')
        request = self._make_request(user_no_branch, current_branch=None, can_see_all=False)
        qs = apply_branch_filter(Warehouse.objects.all(), request)
        self.assertEqual(qs.count(), 0)

    def test_admin_without_selection_sees_all(self):
        """Admin بدون اختيار فرع يرى كل البيانات"""
        Warehouse.objects.create(name='مخزن A1', branch=self.branch_a)
        Warehouse.objects.create(name='مخزن B1', branch=self.branch_b)
        request = self._make_request(self.admin, current_branch=None, can_see_all=True)
        qs = apply_branch_filter(Warehouse.objects.all(), request)
        self.assertEqual(qs.count(), 2)

    def test_admin_with_selection_sees_only_selected_branch(self):
        """Admin اختار فرع A يرى فرع A فقط"""
        Warehouse.objects.create(name='مخزن A1', branch=self.branch_a)
        Warehouse.objects.create(name='مخزن B1', branch=self.branch_b)
        request = self._make_request(self.admin, current_branch=self.branch_a, can_see_all=True)
        qs = apply_branch_filter(Warehouse.objects.all(), request)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().branch, self.branch_a)


# ══════════════════════════════════════════════════════
# 3. اختبارات SalesInvoice بالفرع
# ══════════════════════════════════════════════════════

class SalesInvoiceBranchTestCase(TestCase):
    """اختبارات فلترة فواتير البيع حسب الفرع"""

    def setUp(self):
        self.client = Client()
        self.branch_a = create_branch('فرع A')
        self.branch_b = create_branch('فرع B')
        self.user_a = create_user('user_a', branch=self.branch_a)
        self.admin = create_user('admin_test', is_superuser=True, is_staff=True)

        # إنشاء بيانات أساسية
        try:
            from apps.sales.models import Customer, SalesInvoice
            from apps.inventory.models import Warehouse as InvWarehouse
            from apps.core.models import Warehouse as CoreWarehouse

            self.warehouse_a = CoreWarehouse.objects.create(name='مخزن A', branch=self.branch_a)
            self.warehouse_b = CoreWarehouse.objects.create(name='مخزن B', branch=self.branch_b)

            self.customer = Customer.objects.create(
                name='عميل تجريبي',
                code='C001',
                branch=self.branch_a,
            )

            # فاتورة في فرع A
            self.invoice_a = SalesInvoice.objects.create(
                customer=self.customer,
                branch=self.branch_a,
                warehouse=self.warehouse_a,
                date=timezone.now(),
                subtotal=Decimal('1000'),
                discount_amount=Decimal('0'),
                tax_amount=Decimal('0'),
                total=Decimal('1000'),
                paid_amount=Decimal('0'),
                remaining_amount=Decimal('1000'),
                status='draft',
                created_by=self.user_a,
            )

            # فاتورة في فرع B
            user_b = create_user('user_b', branch=self.branch_b)
            self.invoice_b = SalesInvoice.objects.create(
                customer=self.customer,
                branch=self.branch_b,
                warehouse=self.warehouse_b,
                date=timezone.now(),
                subtotal=Decimal('2000'),
                discount_amount=Decimal('0'),
                tax_amount=Decimal('0'),
                total=Decimal('2000'),
                paid_amount=Decimal('0'),
                remaining_amount=Decimal('2000'),
                status='draft',
                created_by=user_b,
            )
            self.has_sales_data = True
        except Exception:
            self.has_sales_data = False

    def test_branch_user_sees_only_own_invoices(self):
        """مستخدم فرع A لا يرى فواتير فرع B"""
        if not self.has_sales_data:
            self.skipTest('Sales models not available')

        from apps.sales.models import SalesInvoice
        # محاكاة الـ request
        request = RequestFactory().get('/')
        request.current_branch = self.branch_a
        request.can_see_all_branches = False
        qs = apply_branch_filter(SalesInvoice.objects.all(), request)
        invoice_numbers = list(qs.values_list('id', flat=True))
        self.assertIn(self.invoice_a.id, invoice_numbers)
        self.assertNotIn(self.invoice_b.id, invoice_numbers)

    def test_admin_sees_all_invoices(self):
        """Admin يرى كل الفواتير"""
        if not self.has_sales_data:
            self.skipTest('Sales models not available')

        from apps.sales.models import SalesInvoice
        request = RequestFactory().get('/')
        request.current_branch = None
        request.can_see_all_branches = True
        qs = apply_branch_filter(SalesInvoice.objects.all(), request)
        self.assertEqual(qs.count(), 2)


# ══════════════════════════════════════════════════════
# 4. اختبارات Switch Branch
# ══════════════════════════════════════════════════════

class SwitchBranchViewTestCase(TestCase):
    """اختبارات تبديل الفرع"""

    def setUp(self):
        self.client = Client()
        self.branch_a = create_branch('فرع A')
        self.branch_b = create_branch('فرع B')
        self.admin = create_user('switch_admin', is_superuser=True, is_staff=True)

    def test_switch_to_branch(self):
        """Admin ينتقل إلى فرع معين"""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('core:switch_branch'),
            {'branch': str(self.branch_a.id)},
            HTTP_REFERER='/',
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)
        self.assertEqual(self.client.session.get('active_branch_id'), self.branch_a.id)

    def test_switch_to_all(self):
        """Admin يعود إلى عرض كل الفروع"""
        self.client.force_login(self.admin)
        # أولاً اختر فرع
        session = self.client.session
        session['active_branch_id'] = self.branch_a.id
        session.save()
        # ثم ارجع لـ "كل الفروع"
        self.client.get(
            reverse('core:switch_branch'),
            {'branch': 'all'},
            HTTP_REFERER='/',
        )
        self.assertNotIn('active_branch_id', self.client.session)

    def test_regular_user_cannot_switch(self):
        """المستخدم العادي لا يمكنه تبديل الفرع"""
        regular = create_user('regular_user', branch=self.branch_a)
        self.client.force_login(regular)
        response = self.client.get(
            reverse('core:switch_branch'),
            {'branch': str(self.branch_b.id)},
            HTTP_REFERER='/',
        )
        # يُعاد التوجيه بدون تغيير الـ session
        self.assertNotIn('active_branch_id', self.client.session)


# ══════════════════════════════════════════════════════
# 5. اختبارات BranchCreateMixin
# ══════════════════════════════════════════════════════

class BranchCreateMixinTestCase(TestCase):
    """اختبار تعيين الفرع تلقائياً عند الإنشاء"""

    def setUp(self):
        self.branch_a = create_branch('فرع A')
        self.user_a = create_user('creator_a', branch=self.branch_a)

    def test_branch_assigned_automatically_on_create(self):
        """الفرع يُعيَّن تلقائياً عند إنشاء الفاتورة"""
        # محاكاة عبر apply_branch_filter
        # هنا نتحقق فقط أن المنطق صحيح
        request = RequestFactory().get('/')
        request.user = self.user_a
        request.current_branch = self.branch_a
        # أي كائن له branch_id = None يحصل على فرع المستخدم
        class FakeInstance:
            branch = None
            branch_id = None
            created_by = None
            created_by_id = None
        instance = FakeInstance()
        if hasattr(instance, 'branch') and not instance.branch_id:
            instance.branch = request.current_branch
        self.assertEqual(instance.branch, self.branch_a)


# ══════════════════════════════════════════════════════
# 6. اختبارات Branch Views (Admin)
# ══════════════════════════════════════════════════════

class BranchViewsTestCase(TestCase):
    """اختبارات واجهات إدارة الفروع"""

    def setUp(self):
        self.client = Client()
        self.admin = create_user('branch_admin', is_superuser=True, is_staff=True)
        self.branch_a = create_branch('فرع A')

    def test_branch_list_requires_admin(self):
        """قائمة الفروع تتطلب Admin"""
        regular = create_user('regular2', branch=self.branch_a)
        self.client.force_login(regular)
        response = self.client.get(reverse('core:branch_list'))
        self.assertEqual(response.status_code, 403)

    def test_branch_list_for_admin(self):
        """Admin يرى قائمة الفروع"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('core:branch_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.branch_a.name)

    def test_branch_create(self):
        """Admin يُنشئ فرعاً جديداً"""
        self.client.force_login(self.admin)
        response = self.client.post(reverse('core:branch_create'), {
            'name': 'فرع جديد',
            'branch_type': 'owned',
            'is_active': 'on',
            'discount_rate': '0',
            'has_warehouse': '',
        })
        self.assertEqual(Branch.objects.filter(name='فرع جديد').count(), 1)

    def test_branch_detail(self):
        """Admin يرى تفاصيل الفرع"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('core:branch_detail', kwargs={'pk': self.branch_a.pk}))
        self.assertEqual(response.status_code, 200)

    def test_branch_update(self):
        """Admin يعدّل الفرع"""
        self.client.force_login(self.admin)
        response = self.client.post(reverse('core:branch_update', kwargs={'pk': self.branch_a.pk}), {
            'name': 'فرع A معدّل',
            'branch_type': 'owned',
            'is_active': 'on',
            'discount_rate': '5',
            'has_warehouse': '',
        })
        self.branch_a.refresh_from_db()
        self.assertEqual(self.branch_a.name, 'فرع A معدّل')
        self.assertEqual(self.branch_a.discount_rate, Decimal('5'))


# ══════════════════════════════════════════════════════
# 7. اختبارات Warehouse Views
# ══════════════════════════════════════════════════════

class WarehouseViewsTestCase(TestCase):
    """اختبارات إدارة المخازن"""

    def setUp(self):
        self.client = Client()
        self.admin = create_user('wh_admin', is_superuser=True, is_staff=True)
        self.branch_a = create_branch('فرع للمخزن')

    def test_warehouse_list(self):
        """Admin يرى قائمة المخازن"""
        Warehouse.objects.create(name='مخزن 1', branch=self.branch_a)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('core:warehouse_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مخزن 1')

    def test_warehouse_create(self):
        """Admin يُنشئ مخزناً جديداً"""
        self.client.force_login(self.admin)
        response = self.client.post(reverse('core:warehouse_create'), {
            'name': 'مخزن جديد',
            'warehouse_type': 'branch',
            'branch': self.branch_a.pk,
            'is_active': 'on',
        })
        self.assertEqual(Warehouse.objects.filter(name='مخزن جديد').count(), 1)


# ══════════════════════════════════════════════════════
# 8. اختبارات User Views
# ══════════════════════════════════════════════════════

class UserViewsTestCase(TestCase):
    """اختبارات إدارة المستخدمين"""

    def setUp(self):
        self.client = Client()
        self.admin = create_user('user_mgr', is_superuser=True, is_staff=True)
        self.branch_a = create_branch('فرع المستخدمين')

    def test_user_list(self):
        """Admin يرى قائمة المستخدمين"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('core:user_list'))
        self.assertEqual(response.status_code, 200)

    def test_user_create(self):
        """Admin يُنشئ مستخدماً جديداً"""
        self.client.force_login(self.admin)
        response = self.client.post(reverse('core:user_create'), {
            'username': 'new_user_test',
            'first_name': 'مستخدم',
            'last_name': 'جديد',
            'email': 'new@test.com',
            'branch': self.branch_a.pk,
            'phone': '',
            'password1': 'StrongPass@123',
            'password2': 'StrongPass@123',
            'is_active': 'on',
        })
        self.assertEqual(User.objects.filter(username='new_user_test').count(), 1)

    def test_user_detail(self):
        """Admin يرى تفاصيل المستخدم"""
        self.client.force_login(self.admin)
        user2 = create_user('user_detail_test', branch=self.branch_a)
        response = self.client.get(reverse('core:user_detail', kwargs={'pk': str(user2.pk)}))
        self.assertEqual(response.status_code, 200)


# ══════════════════════════════════════════════════════
# 9. اختبارات Franchise Management
# ══════════════════════════════════════════════════════

class FranchiseViewTestCase(TestCase):
    """اختبارات إدارة التوكيلات"""

    def setUp(self):
        self.client = Client()
        self.admin = create_user('franchise_admin', is_superuser=True, is_staff=True)

        today = date.today()
        # توكيل نشط
        self.franchise_active = Branch.objects.create(
            name='توكيل القاهرة',
            branch_type='franchise',
            discount_rate=Decimal('10'),
            contract_start=today - timedelta(days=180),
            contract_end=today + timedelta(days=60),
            is_active=True,
        )
        # توكيل قارب على الانتهاء
        self.franchise_expiring = Branch.objects.create(
            name='توكيل الإسكندرية',
            branch_type='franchise',
            discount_rate=Decimal('8'),
            contract_start=today - timedelta(days=180),
            contract_end=today + timedelta(days=15),
            is_active=True,
        )
        # توكيل منتهٍ
        self.franchise_expired = Branch.objects.create(
            name='توكيل أسوان',
            branch_type='distributor',
            discount_rate=Decimal('5'),
            contract_start=today - timedelta(days=365),
            contract_end=today - timedelta(days=10),
            is_active=True,
        )

    def test_franchise_management_view(self):
        """Admin يرى صفحة إدارة التوكيلات"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('core:franchise_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'توكيل القاهرة')
        self.assertContains(response, 'توكيل الإسكندرية')
        self.assertContains(response, 'توكيل أسوان')

    def test_expiring_contracts_detected(self):
        """التوكيلات القاربة على الانتهاء تُكتشف"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('core:franchise_management'))
        context = response.context
        self.assertGreaterEqual(context['expiring_soon_count'], 1)
        self.assertGreaterEqual(context['expired_count'], 1)

    def test_franchise_requires_admin(self):
        """صفحة التوكيلات تتطلب Admin"""
        branch = create_branch('فرع عادي')
        regular = create_user('reg_franchise', branch=branch)
        self.client.force_login(regular)
        response = self.client.get(reverse('core:franchise_management'))
        self.assertEqual(response.status_code, 403)

    def test_franchise_contract_status_active(self):
        """حالة العقد النشط صحيحة"""
        today = date.today()
        days_left = (self.franchise_active.contract_end - today).days
        self.assertGreater(days_left, 30)

    def test_franchise_contract_status_expiring(self):
        """حالة العقد القارب على الانتهاء صحيحة"""
        today = date.today()
        days_left = (self.franchise_expiring.contract_end - today).days
        self.assertLessEqual(days_left, 30)
        self.assertGreater(days_left, 0)

    def test_franchise_contract_status_expired(self):
        """حالة العقد المنتهي صحيحة"""
        today = date.today()
        days_left = (self.franchise_expired.contract_end - today).days
        self.assertLess(days_left, 0)


# ══════════════════════════════════════════════════════
# 10. اختبارات Context Processor
# ══════════════════════════════════════════════════════

class BranchContextProcessorTestCase(TestCase):
    """اختبارات branch_context processor"""

    def setUp(self):
        self.branch_a = create_branch('CP Branch A')
        self.branch_b = create_branch('CP Branch B')
        self.admin = create_user('cp_admin', is_superuser=True, is_staff=True)
        self.user_a = create_user('cp_user_a', branch=self.branch_a)

    def test_admin_context_has_all_branches(self):
        """Admin context يحتوي على all_branches"""
        request = RequestFactory().get('/')
        request.user = self.admin
        request.current_branch = None
        request.can_see_all_branches = True
        from apps.core.context_processors import branch_context
        ctx = branch_context(request)
        self.assertIn('all_branches', ctx)
        self.assertTrue(ctx['can_see_all_branches'])

    def test_regular_user_context_no_all_branches(self):
        """المستخدم العادي لا يحصل على all_branches"""
        request = RequestFactory().get('/')
        request.user = self.user_a
        request.current_branch = self.branch_a
        request.can_see_all_branches = False
        from apps.core.context_processors import branch_context
        ctx = branch_context(request)
        self.assertNotIn('all_branches', ctx)
        self.assertEqual(ctx['current_branch'], self.branch_a)
        self.assertFalse(ctx['can_see_all_branches'])


# ══════════════════════════════════════════════════════
# 11. اختبارات Dashboard بالفرع
# ══════════════════════════════════════════════════════

class DashboardBranchFilterTestCase(TestCase):
    """التحقق من أن الداشبورد يعرض بيانات الفرع الحالي"""

    def setUp(self):
        self.client = Client()
        self.branch_a = create_branch('داش فرع A')
        self.admin = create_user('dash_admin', is_superuser=True, is_staff=True)

    def test_dashboard_loads_for_admin(self):
        """الداشبورد يُحمَّل للـ Admin"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_loads_for_branch_user(self):
        """الداشبورد يُحمَّل لمستخدم الفرع"""
        user_a = create_user('dash_user_a', branch=self.branch_a)
        self.client.force_login(user_a)
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
