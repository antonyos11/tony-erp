"""
اختبارات تطبيق المشتريات — RITA ERP
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Account, FiscalYear
from apps.core.models import Branch, Warehouse
from apps.inventory.models import Category, UnitOfMeasure, Product, StockLevel
from apps.partners.models import Supplier
from apps.purchases.models import PurchaseOrder, PurchaseOrderLine
from apps.purchases.services.purchase_engine import PurchaseEngine

User = get_user_model()


def _create_accounts():
    """إنشاء الحسابات الضرورية للاختبارات"""
    data = [
        ('1141', 'المخزون',        'asset',     'debit'),
        ('115',  'ضريبة مدخلات',   'asset',     'debit'),
        ('2111', 'ذمم الموردون',   'liability', 'credit'),
        ('1111', 'الخزينة',        'asset',     'debit'),
        ('1121', 'ذمم العملاء',    'asset',     'debit'),
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


class PurchaseEngineTest(TestCase):
    """اختبار PurchaseEngine"""

    def setUp(self):
        self.user = User.objects.create_user(username='pur_tester', password='test123')

        self.branch = Branch.objects.create(
            name='فرع مشتريات', branch_type='owned', governorate='القاهرة',
        )
        self.warehouse = Warehouse.objects.create(
            name='مخزن مشتريات', warehouse_type='factory', branch=self.branch,
        )

        FiscalYear.objects.create(
            name='2026', start_date='2026-01-01', end_date='2026-12-31',
            is_active=True, is_closed=False,
        )
        _create_accounts()

        uom = UnitOfMeasure.objects.create(name='قطعة', symbol='pcs')
        cat = Category.objects.create(name='خامات')
        self.product = Product.objects.create(
            code='X001', name='قماش', unit=uom, category=cat,
            cost_price=Decimal('50.00'), retail_price=Decimal('100.00'),
        )
        StockLevel.objects.create(
            product=self.product, warehouse=self.warehouse,
            quantity=Decimal('0'),
        )

        self.supplier = Supplier.objects.create(
            code='S001', name='مورد تجريبي', supplier_type='local',
        )

    # ------------------------------------------------------------------ #
    def test_create_purchase_order(self):
        """إنشاء أمر شراء — التحقق من المجاميع"""
        items = [
            {'product': self.product, 'quantity': Decimal('10'), 'unit_cost': Decimal('50')},
        ]
        order = PurchaseEngine.create_purchase_order(
            supplier=self.supplier, branch=self.branch, warehouse=self.warehouse,
            items=items, is_taxable=True, user=self.user,
        )
        self.assertEqual(order.status, 'draft')
        self.assertEqual(order.lines.count(), 1)
        self.assertEqual(order.subtotal, Decimal('500.00'))
        self.assertGreater(order.tax_amount, 0)
        self.assertEqual(order.total, order.subtotal + order.tax_amount)

    def test_create_purchase_order_no_tax(self):
        """أمر شراء بدون ضريبة"""
        items = [
            {'product': self.product, 'quantity': Decimal('4'), 'unit_cost': Decimal('100')},
        ]
        order = PurchaseEngine.create_purchase_order(
            supplier=self.supplier, branch=self.branch, warehouse=self.warehouse,
            items=items, is_taxable=False, user=self.user,
        )
        self.assertEqual(order.tax_amount, Decimal('0'))
        self.assertEqual(order.total, Decimal('400.00'))

    def test_receive_purchase(self):
        """استلام أمر الشراء — المخزون يزيد والحالة تتغير"""
        items = [
            {'product': self.product, 'quantity': Decimal('20'), 'unit_cost': Decimal('50')},
        ]
        order = PurchaseEngine.create_purchase_order(
            supplier=self.supplier, branch=self.branch, warehouse=self.warehouse,
            items=items, is_taxable=False, user=self.user,
        )
        received = PurchaseEngine.receive_purchase(order, self.user)
        self.assertEqual(received.status, 'received')
        self.assertIsNotNone(received.journal_entry)
        stock = StockLevel.objects.get(product=self.product, warehouse=self.warehouse)
        self.assertEqual(stock.quantity, Decimal('20'))

    def test_cannot_receive_twice(self):
        """لا يمكن استلام أمر مستلم مسبقاً"""
        items = [{'product': self.product, 'quantity': Decimal('5'), 'unit_cost': Decimal('50')}]
        order = PurchaseEngine.create_purchase_order(
            supplier=self.supplier, branch=self.branch, warehouse=self.warehouse,
            items=items, is_taxable=False, user=self.user,
        )
        PurchaseEngine.receive_purchase(order, self.user)
        order.refresh_from_db()
        with self.assertRaises(ValueError):
            PurchaseEngine.receive_purchase(order, self.user)


# ------------------------------------------------------------------ #
class PurchasesViewsTest(TestCase):
    """اختبار صفحات تطبيق المشتريات"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(username='pur_viewer', password='pass123')
        self.client.login(username='pur_viewer', password='pass123')

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

        self.supplier = Supplier.objects.create(
            code='S002', name='مورد عرض', supplier_type='local',
        )

        uom = UnitOfMeasure.objects.create(name='قطعة', symbol='pcs')
        cat = Category.objects.create(name='خامات')
        product = Product.objects.create(
            code='X002', name='قطن', unit=uom, category=cat,
            cost_price=Decimal('30.00'), retail_price=Decimal('60.00'),
        )
        StockLevel.objects.create(
            product=product, warehouse=self.warehouse,
            quantity=Decimal('0'),
        )

        self.order = PurchaseEngine.create_purchase_order(
            supplier=self.supplier, branch=self.branch, warehouse=self.warehouse,
            items=[{'product': product, 'quantity': Decimal('10'), 'unit_cost': Decimal('30')}],
            is_taxable=False, user=self.user,
        )

    def test_supplier_list_page(self):
        resp = self.client.get('/purchases/suppliers/')
        self.assertEqual(resp.status_code, 200)

    def test_order_list_page(self):
        resp = self.client.get('/purchases/orders/')
        self.assertEqual(resp.status_code, 200)

    def test_order_detail_page(self):
        resp = self.client.get(f'/purchases/orders/{self.order.pk}/')
        self.assertEqual(resp.status_code, 200)

    def test_supplier_detail_page(self):
        resp = self.client.get(f'/purchases/suppliers/{self.supplier.pk}/')
        self.assertEqual(resp.status_code, 200)

    def test_redirect_when_not_logged_in(self):
        self.client.logout()
        resp = self.client.get('/purchases/orders/')
        self.assertEqual(resp.status_code, 302)
