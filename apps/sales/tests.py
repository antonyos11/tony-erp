"""
اختبارات تطبيق المبيعات — RITA ERP
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from apps.accounts.models import Account, FiscalYear
from apps.core.models import Branch, Warehouse
from apps.inventory.models import Category, UnitOfMeasure, Product, StockLevel
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine, SalesReturn
from apps.sales.services.sales_engine import SalesEngine

User = get_user_model()


def _create_accounts():
    """إنشاء الحسابات الضرورية للاختبارات"""
    data = [
        ('1111', 'الخزينة',        'asset',     'debit'),
        ('1121', 'ذمم العملاء',    'asset',     'debit'),
        ('1141', 'المخزون',        'asset',     'debit'),
        ('1143', 'مخزون إنتاج',    'asset',     'debit'),
        ('115',  'مردودات مبيعات', 'asset',     'debit'),
        ('213',  'ضريبة مبيعات',   'liability', 'credit'),
        ('411',  'مبيعات قطاعي',   'revenue',   'credit'),
        ('51',   'تكلفة المبيعات', 'expense',   'debit'),
        ('43',   'مردودات مشتريات','expense',   'debit'),
    ]
    for code, name, atype, nature in data:
        Account.objects.get_or_create(
            code=code,
            defaults=dict(name=name, account_type=atype, nature=nature,
                          is_detail=True, is_system=True),
        )


class SalesEngineTest(TestCase):
    """اختبار SalesEngine"""

    def setUp(self):
        self.user = User.objects.create_user(username='sales_tester', password='test123')

        self.branch = Branch.objects.create(
            name='فرع تجريبي', branch_type='owned', governorate='القاهرة',
        )
        self.warehouse = Warehouse.objects.create(
            name='مخزن تجريبي', warehouse_type='factory', branch=self.branch,
        )

        FiscalYear.objects.create(
            name='2026', start_date='2026-01-01', end_date='2026-12-31',
            is_active=True, is_closed=False,
        )
        _create_accounts()

        uom = UnitOfMeasure.objects.create(name='قطعة', symbol='pcs')
        cat = Category.objects.create(name='أثاث')
        self.product = Product.objects.create(
            code='P001', name='كنبة', unit=uom, category=cat,
            cost_price=Decimal('100.00'), retail_price=Decimal('200.00'),
        )
        # رصيد مخزني أولي
        StockLevel.objects.create(
            product=self.product, warehouse=self.warehouse,
            quantity=Decimal('50'),
        )

        self.customer = Customer.objects.create(
            code='C001', name='عميل تجريبي', customer_type='retail',
        )

        self.engine = SalesEngine()

    # ------------------------------------------------------------------ #
    def test_create_invoice(self):
        """إنشاء فاتورة مسودة"""
        lines = [{'product': self.product, 'quantity': Decimal('2'),
                  'unit_price': Decimal('200'), 'discount_percentage': Decimal('0')}]
        inv = self.engine.create_invoice(
            customer=self.customer, branch=self.branch, warehouse=self.warehouse,
            payment_method='cash', items=lines,
            salesperson=self.user, is_taxable=True, user=self.user,
        )
        self.assertEqual(inv.status, 'draft')
        self.assertEqual(inv.lines.count(), 1)
        self.assertGreater(inv.total, 0)

    def test_confirm_invoice_cash(self):
        """تأكيد فاتورة نقدية — تصبح مدفوعة ويُخصم المخزون"""
        lines = [{'product': self.product, 'quantity': Decimal('3'),
                  'unit_price': Decimal('200'), 'discount_percentage': Decimal('0')}]
        inv = self.engine.create_invoice(
            customer=self.customer, branch=self.branch, warehouse=self.warehouse,
            payment_method='cash', items=lines,
            salesperson=self.user, is_taxable=False, user=self.user,
        )
        confirmed = self.engine.confirm_invoice(inv, self.user)
        self.assertEqual(confirmed.status, 'paid')
        stock = StockLevel.objects.get(product=self.product, warehouse=self.warehouse)
        self.assertEqual(stock.quantity, Decimal('47'))

    def test_confirm_invoice_credit(self):
        """تأكيد فاتورة آجلة — تصبح مؤكدة"""
        lines = [{'product': self.product, 'quantity': Decimal('1'),
                  'unit_price': Decimal('200'), 'discount_percentage': Decimal('0')}]
        inv = self.engine.create_invoice(
            customer=self.customer, branch=self.branch, warehouse=self.warehouse,
            payment_method='installment', items=lines,
            salesperson=self.user, is_taxable=False, user=self.user,
        )
        confirmed = self.engine.confirm_invoice(inv, self.user)
        self.assertEqual(confirmed.status, 'confirmed')

    def test_record_payment(self):
        """تسجيل دفعة جزئية"""
        lines = [{'product': self.product, 'quantity': Decimal('1'),
                  'unit_price': Decimal('200'), 'discount_percentage': Decimal('0')}]
        inv = self.engine.create_invoice(
            customer=self.customer, branch=self.branch, warehouse=self.warehouse,
            payment_method='installment', items=lines,
            salesperson=self.user, is_taxable=False, user=self.user,
        )
        self.engine.confirm_invoice(inv, self.user)
        inv.refresh_from_db()
        updated = self.engine.record_payment(
            invoice=inv, amount=Decimal('100'), payment_method='cash',
            user=self.user,
        )
        self.assertEqual(updated.paid_amount, Decimal('100'))
        self.assertEqual(updated.remaining_amount, inv.total - Decimal('100'))

    def test_create_and_approve_return(self):
        """إنشاء مرتجع والموافقة عليه"""
        lines = [{'product': self.product, 'quantity': Decimal('5'),
                  'unit_price': Decimal('200'), 'discount_percentage': Decimal('0')}]
        inv = self.engine.create_invoice(
            customer=self.customer, branch=self.branch, warehouse=self.warehouse,
            payment_method='cash', items=lines,
            salesperson=self.user, is_taxable=False, user=self.user,
        )
        self.engine.confirm_invoice(inv, self.user)
        inv.refresh_from_db()

        return_lines = [{'product': self.product, 'quantity': Decimal('2')}]
        ret = self.engine.create_return(
            original_invoice=inv, reason='عيب', items=return_lines, user=self.user,
        )
        self.assertEqual(ret.status, 'draft')

        approved = self.engine.approve_return(ret, self.user)
        self.assertEqual(approved.status, 'completed')
        # approve_return يُعيد جميع أسطر الفاتورة الأصلية (5 وحدات) للمخزون
        # 50 - 5 (تأكيد) + 5 (مرتجع) = 50
        stock = StockLevel.objects.get(product=self.product, warehouse=self.warehouse)
        self.assertEqual(stock.quantity, Decimal('50'))


# ------------------------------------------------------------------ #
class SalesViewsTest(TestCase):
    """اختبار صفحات تطبيق المبيعات"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(username='view_tester', password='pass123')
        self.client.login(username='view_tester', password='pass123')

        self.branch = Branch.objects.create(
            name='فرع', branch_type='owned', governorate='القاهرة',
        )
        self.warehouse = Warehouse.objects.create(
            name='مخزن', warehouse_type='factory', branch=self.branch,
        )
        FiscalYear.objects.create(
            name='2026', start_date='2026-01-01', end_date='2026-12-31',
            is_active=True, is_closed=False,
        )
        _create_accounts()

        self.customer = Customer.objects.create(
            code='C002', name='عميل عرض', customer_type='retail',
        )

    def test_customer_list_page(self):
        resp = self.client.get('/sales/customers/')
        self.assertEqual(resp.status_code, 200)

    def test_invoice_list_page(self):
        resp = self.client.get('/sales/invoices/')
        self.assertEqual(resp.status_code, 200)

    def test_return_list_page(self):
        resp = self.client.get('/sales/returns/')
        self.assertEqual(resp.status_code, 200)

    def test_price_list_page(self):
        resp = self.client.get('/sales/price-lists/')
        self.assertEqual(resp.status_code, 200)

    def test_customer_detail_page(self):
        resp = self.client.get(f'/sales/customers/{self.customer.pk}/')
        self.assertEqual(resp.status_code, 200)

    def test_redirect_when_not_logged_in(self):
        self.client.logout()
        resp = self.client.get('/sales/invoices/')
        self.assertEqual(resp.status_code, 302)
