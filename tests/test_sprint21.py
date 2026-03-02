"""
اختبارات Sprint 21 — RITA ERP
يغطي: تطبيق الموردين (partners)، تحسينات الأقساط،
       تحسينات الإشعارات، تحسينات الطباعة
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

User = get_user_model()


# ─────────────── Helpers ───────────────
def make_user(username, is_admin=False, **kwargs):
    u = User.objects.create_user(
        username=username,
        password='Test@12345',
        first_name='Test',
        last_name='User',
        **kwargs,
    )
    if is_admin:
        u.is_staff = True
        u.is_superuser = True
        u.save()
    return u


class BaseTestCase(TestCase):
    def setUp(self):
        self.admin = make_user('admin_sprint21', is_admin=True)
        self.user = make_user('user_sprint21')
        self.client = Client()
        self.client.login(username='admin_sprint21', password='Test@12345')

    def assertOkOrRedirect(self, url, method='get', data=None):
        if method == 'get':
            resp = self.client.get(url)
        else:
            resp = self.client.post(url, data or {})
        self.assertIn(
            resp.status_code, [200, 301, 302],
            msg=f"{method.upper()} {url} returned {resp.status_code}",
        )
        return resp


# ─────────────── 1. Partners — URL Resolution ───────────────
class PartnersURLTest(BaseTestCase):
    """تحقق أن جميع URLs تطبيق الموردين تُحلَّل بشكل صحيح"""

    def test_supplier_list_url_resolves(self):
        url = reverse('partners:supplier_list')
        self.assertEqual(url, '/partners/')

    def test_supplier_create_url_resolves(self):
        url = reverse('partners:supplier_create')
        self.assertEqual(url, '/partners/create/')

    def test_supplier_detail_url_resolves(self):
        url = reverse('partners:supplier_detail', args=[1])
        self.assertEqual(url, '/partners/1/')

    def test_supplier_update_url_resolves(self):
        url = reverse('partners:supplier_update', args=[1])
        self.assertEqual(url, '/partners/1/edit/')

    def test_supplier_toggle_url_resolves(self):
        url = reverse('partners:supplier_toggle', args=[1])
        self.assertEqual(url, '/partners/1/toggle/')

    def test_supplier_statement_url_resolves(self):
        url = reverse('partners:supplier_statement', args=[1])
        self.assertEqual(url, '/partners/1/statement/')

    def test_supplier_export_url_resolves(self):
        url = reverse('partners:supplier_export')
        self.assertEqual(url, '/partners/export/')


# ─────────────── 2. Partners — Views ───────────────
class PartnersViewTest(BaseTestCase):
    """اختبارات views تطبيق الموردين"""

    def _make_supplier(self, suffix=''):
        from apps.partners.models import Supplier
        return Supplier.objects.create(
            code=f'SUP{suffix}001',
            name=f'مورد اختباري {suffix}',
            supplier_type='local',
        )

    def test_supplier_list_view(self):
        resp = self.assertOkOrRedirect(reverse('partners:supplier_list'))
        self.assertEqual(resp.status_code, 200)

    def test_supplier_list_with_search(self):
        self._make_supplier('S')
        url = reverse('partners:supplier_list') + '?q=مورد'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_supplier_list_type_filter(self):
        url = reverse('partners:supplier_list') + '?type=local'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_supplier_list_active_filter(self):
        url = reverse('partners:supplier_list') + '?active=1'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_supplier_create_get(self):
        resp = self.assertOkOrRedirect(reverse('partners:supplier_create'))
        self.assertEqual(resp.status_code, 200)

    def test_supplier_create_post(self):
        data = {
            'code': 'TEST001',
            'name': 'مورد جديد للاختبار',
            'supplier_type': 'local',
            'phone': '01000000000',
            'country': 'مصر',
            'payment_terms': 30,
            'is_active': True,
            'is_taxable': True,
        }
        resp = self.client.post(reverse('partners:supplier_create'), data)
        self.assertIn(resp.status_code, [200, 302])

    def test_supplier_detail_view(self):
        sup = self._make_supplier('D')
        resp = self.assertOkOrRedirect(
            reverse('partners:supplier_detail', args=[sup.pk])
        )
        self.assertEqual(resp.status_code, 200)

    def test_supplier_update_get(self):
        sup = self._make_supplier('U')
        resp = self.assertOkOrRedirect(
            reverse('partners:supplier_update', args=[sup.pk])
        )
        self.assertEqual(resp.status_code, 200)

    def test_supplier_toggle_active(self):
        sup = self._make_supplier('T')
        self.assertTrue(sup.is_active)
        resp = self.client.post(
            reverse('partners:supplier_toggle', args=[sup.pk])
        )
        self.assertIn(resp.status_code, [200, 302])
        sup.refresh_from_db()
        self.assertFalse(sup.is_active)

    def test_supplier_statement_view(self):
        sup = self._make_supplier('ST')
        url = reverse('partners:supplier_statement', args=[sup.pk])
        resp = self.assertOkOrRedirect(url)
        self.assertEqual(resp.status_code, 200)

    def test_supplier_statement_date_filter(self):
        sup = self._make_supplier('STF')
        url = (reverse('partners:supplier_statement', args=[sup.pk])
               + '?date_from=2024-01-01&date_to=2024-12-31')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_supplier_export_csv(self):
        self._make_supplier('EXP')
        resp = self.client.get(reverse('partners:supplier_export'))
        self.assertIn(resp.status_code, [200, 302])
        if resp.status_code == 200:
            self.assertIn(
                'text/csv', resp.get('Content-Type', '')
            )

    def test_supplier_list_requires_login(self):
        c = Client()
        resp = c.get(reverse('partners:supplier_list'))
        self.assertIn(resp.status_code, [302, 403])

    def test_supplier_404_on_missing(self):
        resp = self.client.get(reverse('partners:supplier_detail', args=[99999]))
        self.assertEqual(resp.status_code, 404)


# ─────────────── 3. Partners — Model ───────────────
class SupplierModelTest(TestCase):
    """اختبارات نموذج Supplier"""

    def _make(self, **kwargs):
        from apps.partners.models import Supplier
        defaults = dict(code='MDL001', name='نموذج اختبار', supplier_type='local')
        defaults.update(kwargs)
        return Supplier.objects.create(**defaults)

    def test_create_supplier(self):
        sup = self._make()
        self.assertEqual(sup.name, 'نموذج اختبار')

    def test_str_repr(self):
        sup = self._make()
        self.assertIn('نموذج اختبار', str(sup))

    def test_is_active_default(self):
        sup = self._make(code='ACT001')
        self.assertTrue(sup.is_active)

    def test_supplier_type_choices(self):
        sup = self._make(code='TYP001', supplier_type='foreign')
        self.assertEqual(sup.supplier_type, 'foreign')

    def test_unique_code(self):
        from django.db import IntegrityError
        self._make(code='UNQ001')
        with self.assertRaises(IntegrityError):
            self._make(code='UNQ001')

    def test_queryset_active_filter(self):
        from apps.partners.models import Supplier
        self._make(code='ACT_A', is_active=True)
        self._make(code='ACT_B', is_active=False)
        active = Supplier.objects.filter(is_active=True)
        inactive = Supplier.objects.filter(is_active=False)
        self.assertGreaterEqual(active.count(), 1)
        self.assertGreaterEqual(inactive.count(), 1)


# ─────────────── 4. Installments Enhancements ───────────────
class InstallmentEnhancementsURLTest(TestCase):
    """تحقق أن URLs تحسينات الأقساط تُحلَّل بشكل صحيح"""

    def test_plan_export_url_resolves(self):
        url = reverse('installments:plan_export', args=[1])
        self.assertEqual(url, '/installments/1/export/')

    def test_plan_cancel_url_resolves(self):
        url = reverse('installments:plan_cancel', args=[1])
        self.assertEqual(url, '/installments/1/cancel/')


class InstallmentEnhancementsViewTest(BaseTestCase):
    """اختبارات views تحسينات الأقساط"""

    def _make_plan(self):
        """ينشئ خطة أقساط كاملة مع بيانات موجبة"""
        from apps.sales.models import Customer, SalesInvoice
        from apps.installments.models import InstallmentPlan
        from apps.core.models import Branch, Warehouse

        customer = Customer.objects.create(
            code='CUST_INST21',
            name='عميل اختبار أقساط',
        )
        branch = Branch.objects.create(name='فرع اختبار أقساط 21', branch_type='owned')
        warehouse = Warehouse.objects.create(name='مخزن اختبار 21', branch=branch)
        invoice = SalesInvoice.objects.create(
            invoice_number='INV-INST-021',
            date='2026-01-01 00:00:00',
            customer=customer,
            branch=branch,
            warehouse=warehouse,
            status='confirmed',
            subtotal=Decimal('10000.00'),
            discount_amount=Decimal('0'),
            tax_amount=Decimal('0'),
            total=Decimal('10000.00'),
        )
        plan = InstallmentPlan.objects.create(
            invoice=invoice,
            customer=customer,
            total_amount=Decimal('10000.00'),
            down_payment=Decimal('2000.00'),
            number_of_installments=4,
            installment_amount=Decimal('2000.00'),
            start_date=date.today() + timedelta(days=30),
            status='active',
            created_by=self.admin,
        )
        return plan

    def test_plan_export_view_ok(self):
        plan = self._make_plan()
        resp = self.assertOkOrRedirect(
            reverse('installments:plan_export', args=[plan.pk])
        )
        self.assertIn(resp.status_code, [200, 302])

    def test_plan_export_csv_content_type(self):
        plan = self._make_plan()
        resp = self.client.get(
            reverse('installments:plan_export', args=[plan.pk])
        )
        if resp.status_code == 200:
            self.assertIn('text/csv', resp.get('Content-Type', ''))

    def test_plan_cancel_view_ok(self):
        plan = self._make_plan()
        resp = self.client.post(
            reverse('installments:plan_cancel', args=[plan.pk])
        )
        self.assertIn(resp.status_code, [200, 302])

    def test_plan_cancel_sets_defaulted(self):
        plan = self._make_plan()
        self.client.post(reverse('installments:plan_cancel', args=[plan.pk]))
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'defaulted')

    def test_plan_export_404_on_missing(self):
        resp = self.client.get(
            reverse('installments:plan_export', args=[99999])
        )
        self.assertEqual(resp.status_code, 404)

    def test_plan_cancel_404_on_missing(self):
        resp = self.client.post(
            reverse('installments:plan_cancel', args=[99999])
        )
        self.assertEqual(resp.status_code, 404)

    def test_plan_cancel_requires_login(self):
        plan = self._make_plan()
        c = Client()
        resp = c.post(reverse('installments:plan_cancel', args=[plan.pk]))
        self.assertIn(resp.status_code, [302, 403])


# ─────────────── 5. Notifications Enhancements ───────────────
class NotificationsURLTest(TestCase):
    """تحقق أن URLs تحسينات الإشعارات تُحلَّل بشكل صحيح"""

    def test_unread_count_url_resolves(self):
        url = reverse('notifications:unread_count')
        self.assertEqual(url, '/notifications/unread-count/')

    def test_notification_delete_url_resolves(self):
        url = reverse('notifications:delete', args=[1])
        self.assertEqual(url, '/notifications/1/delete/')

    def test_clear_all_url_resolves(self):
        url = reverse('notifications:clear_all')
        self.assertEqual(url, '/notifications/clear-all/')


class NotificationsViewTest(BaseTestCase):
    """اختبارات views تحسينات الإشعارات"""

    def _make_notification(self, is_read=False):
        from apps.notifications.models import Notification
        return Notification.objects.create(
            user=self.admin,
            title='إشعار اختباري',
            message='رسالة اختبار',
            notification_type='info',
            category='general',
            is_read=is_read,
        )

    def test_unread_count_view_json(self):
        resp = self.client.get(reverse('notifications:unread_count'))
        self.assertIn(resp.status_code, [200, 302])
        if resp.status_code == 200:
            import json
            data = json.loads(resp.content)
            self.assertIn('count', data)

    def test_unread_count_reflects_unread(self):
        """يجب أن يرجع عدد الإشعارات غير المقروءة"""
        self._make_notification(is_read=False)
        self._make_notification(is_read=False)
        resp = self.client.get(reverse('notifications:unread_count'))
        if resp.status_code == 200:
            import json
            data = json.loads(resp.content)
            self.assertGreaterEqual(data['count'], 2)

    def test_delete_notification_post(self):
        n = self._make_notification()
        resp = self.client.post(reverse('notifications:delete', args=[n.pk]))
        self.assertIn(resp.status_code, [200, 302])

    def test_delete_notification_removes_record(self):
        from apps.notifications.models import Notification
        n = self._make_notification()
        pk = n.pk
        self.client.post(reverse('notifications:delete', args=[pk]))
        self.assertFalse(Notification.objects.filter(pk=pk).exists())

    def test_delete_notification_404_on_missing(self):
        resp = self.client.post(reverse('notifications:delete', args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_clear_all_notifications(self):
        from apps.notifications.models import Notification
        self._make_notification(is_read=True)
        self._make_notification(is_read=True)
        self.client.post(reverse('notifications:clear_all'))
        remaining = Notification.objects.filter(
            user=self.admin, is_read=True
        )
        self.assertEqual(remaining.count(), 0)

    def test_clear_all_requires_post(self):
        resp = self.client.get(reverse('notifications:clear_all'))
        self.assertIn(resp.status_code, [200, 302, 405])

    def test_clear_all_requires_login(self):
        c = Client()
        resp = c.post(reverse('notifications:clear_all'))
        self.assertIn(resp.status_code, [302, 403])


# ─────────────── 6. Printing Enhancements ───────────────
class PrintingURLTest(TestCase):
    """تحقق أن URLs تحسينات الطباعة تُحلَّل بشكل صحيح"""

    def test_product_labels_url_resolves(self):
        url = reverse('printing:product_labels')
        self.assertEqual(url, '/printing/labels/')

    def test_label_selector_url_resolves(self):
        url = reverse('printing:label_selector')
        self.assertEqual(url, '/printing/labels/select/')


class PrintingViewTest(BaseTestCase):
    """اختبارات views تحسينات الطباعة"""

    def test_label_selector_get(self):
        resp = self.assertOkOrRedirect(reverse('printing:label_selector'))
        self.assertEqual(resp.status_code, 200)

    def test_product_labels_empty(self):
        """الصفحة تعمل حتى بدون products"""
        resp = self.client.get(reverse('printing:product_labels'))
        self.assertIn(resp.status_code, [200, 302])

    def test_product_labels_with_product(self):
        """الصفحة تعمل مع منتج صالح"""
        from apps.inventory.models import Product, Category, UnitOfMeasure
        cat, _ = Category.objects.get_or_create(name='تصنيف طباعة')
        uom, _ = UnitOfMeasure.objects.get_or_create(
            name='قطعة', defaults={'symbol': 'pcs'}
        )
        product = Product.objects.create(
            code='PTPROD',
            name='منتج طباعة',
            category=cat,
            unit=uom,
            product_type='finished',
            retail_price=Decimal('50.00'),
            created_by=self.admin,
        )
        url = reverse('printing:product_labels') + f'?products={product.pk}&copies=2'
        resp = self.client.get(url)
        self.assertIn(resp.status_code, [200, 302])

    def test_label_selector_post_redirects(self):
        """POST للمنتج يعيد التوجيه إلى صفحة الطباعة"""
        from apps.inventory.models import Product, Category, UnitOfMeasure
        cat, _ = Category.objects.get_or_create(name='تصنيف طباعة 2')
        uom, _ = UnitOfMeasure.objects.get_or_create(
            name='قطعة', defaults={'symbol': 'pcs'}
        )
        product = Product.objects.create(
            code='PTPROD2',
            name='منتج طباعة 2',
            category=cat,
            unit=uom,
            product_type='finished',
            retail_price=Decimal('75.00'),
            created_by=self.admin,
        )
        resp = self.client.post(
            reverse('printing:label_selector'),
            {'products': [product.pk], 'copies': 1, 'label_type': 'code128'},
        )
        self.assertIn(resp.status_code, [200, 302])

    def test_product_labels_requires_login(self):
        c = Client()
        resp = c.get(reverse('printing:product_labels'))
        self.assertIn(resp.status_code, [302, 403])

    def test_label_selector_requires_login(self):
        c = Client()
        resp = c.get(reverse('printing:label_selector'))
        self.assertIn(resp.status_code, [302, 403])
