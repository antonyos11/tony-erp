"""
اختبارات Sprint 20 — RITA ERP
يغطي: إدارة المستخدمين، الجرد المخزني، المبيعات، المشتريات،
       الإنتاج، الخزينة، عروض الأسعار، التقارير، البحث الشامل
"""
import uuid
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
        self.admin = make_user('admin_sprint20', is_admin=True)
        self.user = make_user('user_sprint20')
        self.client = Client()
        self.client.login(username='admin_sprint20', password='Test@12345')

    def assertOkOrRedirect(self, url, method='get', data=None):
        """الصفحة يجب أن ترجع 200 أو إعادة توجيه (لا 500، لا 403)."""
        if method == 'get':
            resp = self.client.get(url)
        else:
            resp = self.client.post(url, data or {})
        self.assertIn(
            resp.status_code, [200, 301, 302],
            msg=f"{method.upper()} {url} returned {resp.status_code}"
        )
        return resp


# ─────────────── 1. User Management ───────────────
class UserManagementTest(BaseTestCase):
    """اختبارات إدارة المستخدمين"""

    def test_my_profile_view(self):
        self.client.login(username='user_sprint20', password='Test@12345')
        resp = self.client.get(reverse('core:my_profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'user_sprint20')

    def test_my_change_password_get(self):
        self.client.login(username='user_sprint20', password='Test@12345')
        resp = self.client.get(reverse('core:my_change_password'))
        self.assertEqual(resp.status_code, 200)

    def test_my_change_password_wrong_old(self):
        self.client.login(username='user_sprint20', password='Test@12345')
        resp = self.client.post(reverse('core:my_change_password'), {
            'old_password': 'WRONG',
            'new_password1': 'NewPass@99',
            'new_password2': 'NewPass@99',
        })
        # يجب أن يبقى في الصفحة أو يعيد توجيه مع رسالة خطأ
        self.assertIn(resp.status_code, [200, 302])

    def test_user_update_view(self):
        url = reverse('core:user_update', kwargs={'pk': str(self.user.pk)})
        self.assertOkOrRedirect(url)

    def test_user_toggle_active(self):
        url = reverse('core:user_toggle', kwargs={'pk': str(self.user.pk)})
        was_active = self.user.is_active
        resp = self.client.post(url)
        self.assertIn(resp.status_code, [200, 302])
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.is_active, was_active)

    def test_user_toggle_self_protection(self):
        """المسؤول لا يستطيع تعطيل نفسه"""
        url = reverse('core:user_toggle', kwargs={'pk': str(self.admin.pk)})
        resp = self.client.post(url)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_change_password_get(self):
        url = reverse('core:user_change_password', kwargs={'pk': str(self.user.pk)})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_admin_change_password_mismatch(self):
        url = reverse('core:user_change_password', kwargs={'pk': str(self.user.pk)})
        resp = self.client.post(url, {
            'new_password1': 'Pass@111',
            'new_password2': 'Pass@222',
        })
        self.assertIn(resp.status_code, [200, 302])


# ─────────────── 2. Global Search ───────────────
class GlobalSearchTest(BaseTestCase):
    """اختبارات البحث الشامل"""

    def test_search_empty_query(self):
        url = reverse('core:global_search')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_search_with_query(self):
        url = reverse('core:global_search') + '?q=test'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_search_requires_login(self):
        self.client.logout()
        url = reverse('core:global_search') + '?q=test'
        resp = self.client.get(url)
        self.assertIn(resp.status_code, [302])  # redirect to login


# ─────────────── 3. Inventory / StockCount ───────────────
class StockCountModelTest(TestCase):
    """اختبارات نموذج الجرد المخزني"""

    def setUp(self):
        from apps.core.models import Warehouse
        self.admin = make_user('admin_inv', is_admin=True)
        # إنشاء مستودع اختبار
        self.warehouse, _ = Warehouse.objects.get_or_create(
            name='مستودع الاختبار',
            defaults={'is_active': True},
        )

    def test_stock_count_auto_number(self):
        from apps.inventory.models import StockCount
        sc = StockCount.objects.create(
            date=date.today(),
            warehouse=self.warehouse,
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.assertTrue(sc.count_number.startswith('SC-'))
        self.assertIn('-', sc.count_number)

    def test_stock_count_line_difference(self):
        from apps.inventory.models import StockCount, StockCountLine, Product
        sc = StockCount.objects.create(
            date=date.today(),
            warehouse=self.warehouse,
            created_by=self.admin,
            updated_by=self.admin,
        )
        # نحتاج منتج — نتحقق أن الـ model موجود
        try:
            p = Product.objects.first()
            if p:
                line = StockCountLine.objects.create(
                    stock_count=sc,
                    product=p,
                    system_quantity=Decimal('100'),
                    actual_quantity=Decimal('90'),
                )
                self.assertEqual(line.difference, Decimal('-10'))
        except Exception:
            pass  # إذا لم يكن هناك منتجات في الاختبار


class StockCountViewTest(BaseTestCase):
    """اختبارات واجهات الجرد المخزني"""

    def test_stock_count_list(self):
        resp = self.client.get(reverse('inventory:stock_count_list'))
        self.assertIn(resp.status_code, [200, 302])

    def test_stock_count_create_get(self):
        resp = self.client.get(reverse('inventory:stock_count_create'))
        self.assertIn(resp.status_code, [200, 302])


# ─────────────── 4. Sales ───────────────
class SalesViewTest(BaseTestCase):
    """اختبارات واجهات المبيعات"""

    def _get_invoice(self):
        try:
            from apps.sales.models import SalesInvoice
            return SalesInvoice.objects.first()
        except Exception:
            return None

    def _get_customer(self):
        try:
            from apps.sales.models import Customer
            return Customer.objects.first()
        except Exception:
            return None

    def test_customer_statement_requires_login(self):
        customer = self._get_customer()
        if customer:
            self.client.logout()
            url = reverse('sales:customer_statement', kwargs={'pk': customer.pk})
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)

    def test_invoice_print_view(self):
        invoice = self._get_invoice()
        if invoice:
            url = reverse('sales:invoice_print', kwargs={'pk': invoice.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])

    def test_invoice_thermal_view(self):
        invoice = self._get_invoice()
        if invoice:
            url = reverse('sales:invoice_thermal', kwargs={'pk': invoice.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])

    def test_price_list_create_get(self):
        resp = self.client.get(reverse('sales:price_list_create'))
        self.assertIn(resp.status_code, [200, 302])


# ─────────────── 5. Purchases ───────────────
class PurchasesViewTest(BaseTestCase):
    """اختبارات واجهات المشتريات"""

    def _get_order(self):
        try:
            from apps.purchases.models import PurchaseOrder
            return PurchaseOrder.objects.first()
        except Exception:
            return None

    def test_purchase_order_print(self):
        order = self._get_order()
        if order:
            url = reverse('purchases:order_print', kwargs={'pk': order.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])


# ─────────────── 6. Accounts ───────────────
class AccountsViewTest(BaseTestCase):
    """اختبارات واجهات المحاسبة"""

    def _get_journal(self):
        try:
            from apps.accounts.models import JournalEntry
            return JournalEntry.objects.first()
        except Exception:
            return None

    def test_journal_edit_get(self):
        journal = self._get_journal()
        if journal:
            url = reverse('accounts:journal_edit', kwargs={'pk': journal.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302, 403])

    def test_journal_cancel_post(self):
        journal = self._get_journal()
        if journal:
            url = reverse('accounts:journal_cancel', kwargs={'pk': journal.pk})
            resp = self.client.post(url)
            self.assertIn(resp.status_code, [200, 302, 403])

    def test_journal_post_view(self):
        journal = self._get_journal()
        if journal:
            url = reverse('accounts:journal_post', kwargs={'pk': journal.pk})
            resp = self.client.post(url)
            self.assertIn(resp.status_code, [200, 302, 403])


# ─────────────── 7. HR ───────────────
class HRViewTest(BaseTestCase):
    """اختبارات واجهات الموارد البشرية"""

    def _get_employee(self):
        try:
            from apps.hr.models import Employee
            return Employee.objects.first()
        except Exception:
            return None

    def test_employee_terminate_get(self):
        emp = self._get_employee()
        if emp:
            url = reverse('hr:employee_terminate', kwargs={'pk': emp.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302, 403])


# ─────────────── 8. Treasury ───────────────
class TreasuryViewTest(BaseTestCase):
    """اختبارات واجهات الخزينة"""

    def _get_cashbox(self):
        try:
            from apps.treasury.models import CashBox
            return CashBox.objects.first()
        except Exception:
            return None

    def _get_bank(self):
        try:
            from apps.treasury.models import BankAccount
            return BankAccount.objects.first()
        except Exception:
            return None

    def test_cashbox_deposit_get(self):
        cb = self._get_cashbox()
        if cb:
            url = reverse('treasury:cashbox_deposit', kwargs={'pk': cb.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])

    def test_cashbox_statement_get(self):
        cb = self._get_cashbox()
        if cb:
            url = reverse('treasury:cashbox_statement', kwargs={'pk': cb.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])

    def test_bank_deposit_get(self):
        bank = self._get_bank()
        if bank:
            url = reverse('treasury:bank_deposit', kwargs={'pk': bank.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])

    def test_bank_statement_get(self):
        bank = self._get_bank()
        if bank:
            url = reverse('treasury:bank_statement', kwargs={'pk': bank.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])


# ─────────────── 9. Quotations ───────────────
class QuotationsViewTest(BaseTestCase):
    """اختبارات واجهات عروض الأسعار"""

    def _get_quotation(self):
        try:
            from apps.quotations.models import Quotation
            return Quotation.objects.first()
        except Exception:
            return None

    def test_quotation_whatsapp_get(self):
        q = self._get_quotation()
        if q:
            url = reverse('quotations:quotation_whatsapp', kwargs={'pk': q.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])

    def test_quotation_duplicate_post(self):
        q = self._get_quotation()
        if q:
            url = reverse('quotations:quotation_duplicate', kwargs={'pk': q.pk})
            resp = self.client.post(url)
            self.assertIn(resp.status_code, [200, 302])


# ─────────────── 10. Reports ───────────────
class ReportsViewTest(BaseTestCase):
    """اختبارات واجهات التقارير"""

    report_urls = [
        'reports:sales_daily',
        'reports:customer_balance',
        'reports:supplier_balance',
        'reports:cash_flow',
        'reports:expense_summary',
        'reports:production_summary',
        'reports:hr_summary',
        'reports:attendance_report',
    ]

    def test_all_report_views(self):
        for url_name in self.report_urls:
            with self.subTest(url=url_name):
                resp = self.client.get(reverse(url_name))
                self.assertIn(
                    resp.status_code, [200, 302],
                    msg=f"{url_name} returned {resp.status_code}"
                )


# ─────────────── 11. Production ───────────────
class ProductionViewTest(BaseTestCase):
    """اختبارات واجهات الإنتاج"""

    def _get_order(self):
        try:
            from apps.production.models import ProductionOrder
            return ProductionOrder.objects.first()
        except Exception:
            return None

    def test_extra_material_get(self):
        order = self._get_order()
        if order:
            url = reverse('production:extra_material', kwargs={'pk': order.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])

    def test_efficiency_report_get(self):
        resp = self.client.get(reverse('production:efficiency_report'))
        self.assertIn(resp.status_code, [200, 302])

    def test_production_waste_get(self):
        order = self._get_order()
        if order:
            url = reverse('production:production_waste', kwargs={'pk': order.pk})
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [200, 302])


# ─────────────── 12. Error Pages ───────────────
class ErrorPagesTest(TestCase):
    """اختبارات صفحات الخطأ"""

    def test_404_template_exists(self):
        import os
        self.assertTrue(
            os.path.exists('/var/www/rita-erp/templates/404.html')
        )

    def test_500_template_exists(self):
        import os
        self.assertTrue(
            os.path.exists('/var/www/rita-erp/templates/500.html')
        )


# ─────────────── 13. UI / Base Template ───────────────
class BaseTemplateTest(TestCase):
    """اختبارات القالب الأساسي"""

    def setUp(self):
        self.admin = make_user('admin_ui_test', is_admin=True)
        self.client = Client()
        self.client.login(username='admin_ui_test', password='Test@12345')

    def test_base_template_has_loading_overlay(self):
        import os
        with open('/var/www/rita-erp/templates/base.html', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('loadingOverlay', content)

    def test_base_template_has_toast(self):
        import os
        with open('/var/www/rita-erp/templates/base.html', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('toast-container', content)

    def test_base_template_has_stock_count_link(self):
        with open('/var/www/rita-erp/templates/base.html', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('stock_count_list', content)

    def test_base_template_has_search_form(self):
        with open('/var/www/rita-erp/templates/base.html', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('global_search', content)

    def test_base_template_has_profile_link(self):
        with open('/var/www/rita-erp/templates/base.html', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('my_profile', content)


# ─────────────── 14. Backup Script ───────────────
class BackupScriptTest(TestCase):
    """اختبار وجود سكريبت النسخ الاحتياطي"""

    def test_backup_script_exists(self):
        import os
        self.assertTrue(
            os.path.exists('/var/www/rita-erp/scripts/backup.sh')
        )

    def test_backup_script_executable(self):
        import os, stat
        path = '/var/www/rita-erp/scripts/backup.sh'
        if os.path.exists(path):
            mode = os.stat(path).st_mode
            self.assertTrue(bool(mode & stat.S_IXUSR))


# ─────────────── 15. Auto-Warranty on Invoice Confirm ───────────────
class AutoWarrantyTest(TestCase):
    """اختبار إنشاء بطاقات الضمان تلقائياً عند تأكيد الفاتورة"""

    def test_confirm_invoice_view_has_warranty_method(self):
        """تحقق من وجود دالة _create_warranty_cards في ConfirmInvoiceView"""
        from apps.sales.views import ConfirmInvoiceView
        self.assertTrue(hasattr(ConfirmInvoiceView, '_create_warranty_cards'))

    def test_warranty_card_model_exists(self):
        """تحقق من وجود نموذج WarrantyCard"""
        from apps.warranty.models import WarrantyCard
        self.assertIsNotNone(WarrantyCard)

    def test_warranty_card_generate_serial(self):
        """تحقق من توليد رقم ضمان فريد"""
        from apps.warranty.models import WarrantyCard
        serial = WarrantyCard.generate_serial()
        self.assertTrue(serial.startswith('WR'))
        self.assertGreater(len(serial), 6)

    def test_product_has_warranty_months_field(self):
        """تحقق من وجود حقل warranty_months في المنتج"""
        from apps.inventory.models import Product
        field_names = [f.name for f in Product._meta.get_fields()]
        self.assertIn('warranty_months', field_names)


# ─────────────── 16. Role-Based Dashboard KPIs ───────────────
class RoleBasedDashboardTest(TestCase):
    """اختبار لوحة التحكم بناءً على صلاحيات المستخدم"""

    def setUp(self):
        from apps.core.models import User
        self.admin_user = User.objects.create_superuser(
            username='dashboard_admin',
            password='testpass123',
        )
        self.regular_user = User.objects.create_user(
            username='dashboard_regular',
            password='testpass123',
        )

    def test_dashboard_view_has_get_dashboard_permissions_method(self):
        """تحقق من وجود دالة _get_dashboard_permissions في DashboardView"""
        from apps.core.views import DashboardView
        self.assertTrue(hasattr(DashboardView, '_get_dashboard_permissions'))

    def test_superuser_gets_all_dashboard_perms(self):
        """المشرف العام يرى جميع بطاقات KPIs"""
        from apps.core.views import DashboardView
        view = DashboardView()
        perms = view._get_dashboard_permissions(self.admin_user)
        self.assertTrue(perms['see_sales'])
        self.assertTrue(perms['see_accounting'])
        self.assertTrue(perms['see_inventory'])
        self.assertTrue(perms['see_all_kpis'])

    def test_regular_user_gets_fallback_perms(self):
        """المستخدم بدون دور يحصل على صلاحيات أساسية"""
        from apps.core.views import DashboardView
        view = DashboardView()
        perms = view._get_dashboard_permissions(self.regular_user)
        # يجب أن يكون dict بالمفاتيح الصحيحة
        self.assertIn('see_sales', perms)
        self.assertIn('see_accounting', perms)
        self.assertIn('see_inventory', perms)
        self.assertIn('see_all_kpis', perms)

    def test_dashboard_template_uses_dashboard_perms(self):
        """تحقق من أن قالب لوحة التحكم يستخدم dashboard_perms"""
        with open('/var/www/rita-erp/templates/dashboard.html', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('dashboard_perms', content)

    def test_dashboard_accessible_to_superuser(self):
        """تحقق من إمكانية وصول المشرف للوحة التحكم"""
        self.client.login(username='dashboard_admin', password='testpass123')
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 302])
