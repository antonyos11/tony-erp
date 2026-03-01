"""
اختبارات التكامل الشاملة — RITA ERP
دورة كاملة: مورد → شراء خامات → BOM → إنتاج → بيع → تحقق محاسبي
"""
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Account, FiscalYear, JournalEntry, JournalLine
from apps.core.models import Branch, Warehouse
from apps.inventory.models import (
    Category, UnitOfMeasure, Product,
    BillOfMaterials, BOMLine, StockLevel,
)
from apps.partners.models import Supplier
from apps.purchases.models import PurchaseOrder
from apps.purchases.services.purchase_engine import PurchaseEngine
from apps.production.models import ProductionOrder
from apps.production.services.production_engine import ProductionEngine
from apps.sales.models import Customer, SalesInvoice
from apps.sales.services.sales_engine import SalesEngine
from apps.inventory.services.stock_engine import StockEngine
from apps.accounts.services.financial_reports import FinancialReports

User = get_user_model()

# ══════════════════════════════════════════════════════════════════
# مساعدات الإعداد
# ══════════════════════════════════════════════════════════════════

def _make_account(code, name, atype, nature, is_detail=True, parent_code=None):
    parent = None
    if parent_code:
        parent, _ = Account.objects.get_or_create(
            code=parent_code,
            defaults=dict(name=f'حساب {parent_code}', account_type=atype,
                          nature=nature, is_detail=False, is_system=True),
        )
    acc, _ = Account.objects.get_or_create(
        code=code,
        defaults=dict(
            name=name, account_type=atype, nature=nature,
            is_detail=is_detail, is_system=True,
            parent=parent, is_active=True,
        ),
    )
    return acc


def _setup_chart_of_accounts():
    """إنشاء دليل الحسابات الضروري لتشغيل محرك القيود"""
    # الأصول
    assets     = _make_account('1',    'الأصول',               'asset',     'debit',  False)
    curr_assets= _make_account('11',   'الأصول المتداولة',     'asset',     'debit',  False)
    cash_grp   = _make_account('111',  'النقدية والبنوك',       'asset',     'debit',  False)
    cash       = _make_account('1111', 'الخزينة الرئيسية',      'asset',     'debit')
    cust_grp   = _make_account('112',  'العملاء',               'asset',     'debit',  False)
    cust_ret   = _make_account('1121', 'عملاء قطاعي',           'asset',     'debit')
    cust_whl   = _make_account('1122', 'عملاء جملة',            'asset',     'debit')
    cust_fra   = _make_account('1123', 'عملاء توكيلات',         'asset',     'debit')
    cust_dis   = _make_account('1124', 'عملاء موزعين',          'asset',     'debit')
    cust_onl   = _make_account('1125', 'عملاء أونلاين',         'asset',     'debit')
    inv_grp    = _make_account('114',  'المخزون',               'asset',     'debit',  False)
    inv_raw    = _make_account('1141', 'مخزون خامات',           'asset',     'debit')
    inv_wip    = _make_account('1142', 'مخزون تحت التشغيل',     'asset',     'debit')
    inv_fin    = _make_account('1143', 'مخزون منتجات تامة',     'asset',     'debit')
    vat_in     = _make_account('115',  'ضريبة مشتريات',         'asset',     'debit')
    # الخصوم
    liab       = _make_account('2',    'الخصوم',                'liability', 'credit', False)
    curr_liab  = _make_account('21',   'الخصوم المتداولة',      'liability', 'credit', False)
    sup_grp    = _make_account('211',  'الموردون',              'liability', 'credit', False)
    sup_acc    = _make_account('2111', 'موردون عامون',           'liability', 'credit')
    vat_out    = _make_account('213',  'ضريبة مبيعات',          'liability', 'credit')
    # حقوق الملكية
    equity     = _make_account('3',    'حقوق الملكية',          'equity',    'credit', False)
    # الإيرادات
    rev        = _make_account('4',    'الإيرادات',             'revenue',   'credit', False)
    sales_grp  = _make_account('41',   'المبيعات',              'revenue',   'credit', False)
    sales_ret  = _make_account('411',  'مبيعات قطاعي',          'revenue',   'credit')
    sales_whl  = _make_account('412',  'مبيعات جملة',           'revenue',   'credit')
    sales_fra  = _make_account('413',  'مبيعات توكيلات',        'revenue',   'credit')
    sales_dis  = _make_account('414',  'مبيعات موزعين',         'revenue',   'credit')
    sales_onl  = _make_account('415',  'مبيعات أونلاين',        'revenue',   'credit')
    # المصروفات
    exp        = _make_account('5',    'المصروفات',             'expense',   'debit',  False)
    cogs_grp   = _make_account('51',   'تكلفة البضاعة المباعة', 'expense',   'debit')
    return cash


def _make_fiscal_year():
    fy, _ = FiscalYear.objects.get_or_create(
        name='FY-INTEGRATION',
        defaults=dict(
            start_date=date(2025, 1, 1),
            end_date=date(2026, 12, 31),
            is_active=True,
            is_closed=False,
        ),
    )
    return fy


def _make_base():
    """إعداد البنية الأساسية: فرع، مخازن، سنة مالية، دليل حسابات، مستخدم"""
    branch = Branch.objects.create(name='فرع التكامل', branch_type='owned')
    warehouse_raw = Warehouse.objects.create(
        name='مخزن الخامات - تكامل',
        warehouse_type='raw_materials',
        branch=branch,
    )
    warehouse_fin = Warehouse.objects.create(
        name='مخزن المنتجات التامة - تكامل',
        warehouse_type='finished',
        branch=branch,
    )
    fy   = _make_fiscal_year()
    cash = _setup_chart_of_accounts()
    user = User.objects.create_user(username='integration_user', password='Pass1!')
    return branch, warehouse_raw, warehouse_fin, fy, user


def _make_uom():
    uom, _ = UnitOfMeasure.objects.get_or_create(
        name='قطعة',
        defaults=dict(symbol='قط'),
    )
    return uom


def _make_supplier():
    supplier_acc = _make_account('2111', 'موردون عامون', 'liability', 'credit')
    sup, _ = Supplier.objects.get_or_create(
        code='SUP-INTG-001',
        defaults=dict(
            name='مورد التكامل',
            supplier_type='local',
            account=supplier_acc,
        ),
    )
    return sup


# ══════════════════════════════════════════════════════════════════
# Test: الدورة الكاملة
# ══════════════════════════════════════════════════════════════════

class FullCycleIntegrationTest(TestCase):
    """
    اختبار الدورة الكاملة للنظام:
    مورد → شراء خامات → BOM → أمر إنتاج → بدء الإنتاج → إكمال الإنتاج
    → عميل → فاتورة بيع → تأكيد → ميزان مراجعة → قائمة الدخل
    """

    @classmethod
    def setUpTestData(cls):
        cls.branch, cls.wh_raw, cls.wh_fin, cls.fy, cls.user = _make_base()
        cls.uom   = _make_uom()
        cls.supplier = _make_supplier()

    # ── الخطوة 1: إنشاء مورد ──────────────────────────────────────
    def test_01_supplier_created(self):
        """التحقق من إنشاء المورد"""
        self.assertIsNotNone(self.supplier.pk)
        self.assertEqual(self.supplier.code, 'SUP-INTG-001')

    # ── الخطوة 2: شراء خامات ──────────────────────────────────────
    def test_02_purchase_raw_materials(self):
        """إنشاء أمر شراء واستلام الخامات"""
        raw = Product.objects.create(
            code='RAW-STEEL-01',
            name='حديد خام',
            product_type='raw_material',
            unit=self.uom,
            cost_price=Decimal('50.00'),
        )

        order = PurchaseEngine.create_purchase_order(
            supplier=self.supplier,
            branch=self.branch,
            warehouse=self.wh_raw,
            items=[{'product': raw, 'quantity': 100, 'unit_cost': 50}],
            is_taxable=False,
            user=self.user,
        )

        self.assertEqual(order.status, 'draft')
        self.assertEqual(order.subtotal, Decimal('5000.00'))

        # استلام البضاعة
        PurchaseEngine.receive_purchase(order, user=self.user)
        order.refresh_from_db()
        self.assertEqual(order.status, 'received')

        # التحقق من رصيد المخزون
        level = StockEngine.get_stock_level(raw, self.wh_raw)
        self.assertEqual(level, Decimal('100'))

    # ── الخطوة 3: إنشاء BOM ────────────────────────────────────────
    def test_03_create_bom(self):
        """إنشاء BOM مع خامة واحدة"""
        raw = Product.objects.create(
            code='RAW-WOOD-01', name='خشب طبيعي',
            product_type='raw_material', unit=self.uom,
            cost_price=Decimal('30.00'),
        )
        finished = Product.objects.create(
            code='FIN-CHAIR-01', name='كرسي خشبي',
            product_type='finished', unit=self.uom,
            cost_price=Decimal('0.00'), retail_price=Decimal('500.00'),
        )

        bom = BillOfMaterials.objects.create(
            product=finished, name='BOM الكرسي الخشبي', is_default=True,
        )
        BOMLine.objects.create(bom=bom, raw_material=raw, quantity=Decimal('3'))

        self.assertEqual(bom.lines.count(), 1)
        self.assertEqual(bom.lines.first().quantity, Decimal('3'))

    # ── الخطوات 4-6: دورة الإنتاج الكاملة ─────────────────────────
    def test_04_05_06_full_production_cycle(self):
        """إنشاء أمر إنتاج → بدء → إكمال"""
        # إعداد المواد
        raw = Product.objects.create(
            code='RAW-FABRIC-01', name='قماش',
            product_type='raw_material', unit=self.uom,
            cost_price=Decimal('20.00'),
        )
        finished = Product.objects.create(
            code='FIN-SOFA-01', name='أريكة',
            product_type='finished', unit=self.uom,
            cost_price=Decimal('0.00'), retail_price=Decimal('800.00'),
        )

        bom = BillOfMaterials.objects.create(
            product=finished, name='BOM الأريكة', is_default=True,
        )
        BOMLine.objects.create(bom=bom, raw_material=raw, quantity=Decimal('5'))

        # إضافة مخزون خامات مبدئي
        StockEngine.receive_stock(
            product=raw,
            warehouse=self.wh_raw,
            quantity=Decimal('50'),
            unit_cost=Decimal('20.00'),
            source_type='initial',
            source_id='INIT-01',
            user=self.user,
        )

        # الخطوة 4: إنشاء أمر إنتاج
        order = ProductionEngine.create_production_order(
            product=finished,
            bom=bom,
            quantity=Decimal('5'),
            production_line=None,
            warehouse_raw=self.wh_raw,
            warehouse_finished=self.wh_fin,
            expected_date=date.today() + timedelta(days=7),
            user=self.user,
        )
        self.assertEqual(order.status, 'draft')

        # تأكيد الأمر
        ProductionEngine.confirm_order(order, user=self.user)
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

        # الخطوة 5: بدء الإنتاج (صرف خامات)
        ProductionEngine.start_production(order, user=self.user)
        order.refresh_from_db()
        self.assertEqual(order.status, 'in_progress')

        # التحقق من خصم الخامات
        raw_level = StockEngine.get_stock_level(raw, self.wh_raw)
        self.assertLess(raw_level, Decimal('50'))

        # الخطوة 6: إكمال الإنتاج (استلام منتج)
        ProductionEngine.complete_production(
            order,
            quantity_produced=Decimal('5'),
            quantity_wasted=Decimal('0'),
            user=self.user,
        )
        order.refresh_from_db()
        self.assertEqual(order.status, 'completed')

        # التحقق من مخزون المنتج التام
        fin_level = StockEngine.get_stock_level(finished, self.wh_fin)
        self.assertEqual(fin_level, Decimal('5'))

    # ── الخطوة 7: إنشاء عميل ──────────────────────────────────────
    def test_07_customer_created(self):
        """إنشاء عميل"""
        customer = Customer.objects.create(
            code='CUST-INTG-001',
            name='عميل التكامل',
            customer_type='retail',
        )
        self.assertIsNotNone(customer.pk)
        self.assertEqual(customer.code, 'CUST-INTG-001')

    # ── الخطوات 8-9: دورة البيع الكاملة ───────────────────────────
    def test_08_09_full_sales_cycle(self):
        """إنشاء فاتورة بيع وتأكيدها"""
        # إعداد منتج تام مع مخزون
        finished = Product.objects.create(
            code='FIN-TABLE-01', name='طاولة',
            product_type='finished', unit=self.uom,
            cost_price=Decimal('100.00'), retail_price=Decimal('300.00'),
        )
        StockEngine.receive_stock(
            product=finished,
            warehouse=self.wh_fin,
            quantity=Decimal('10'),
            unit_cost=Decimal('100.00'),
            source_type='initial',
            source_id='INIT-TABLE',
            user=self.user,
        )

        customer = Customer.objects.create(
            code='CUST-SALE-001',
            name='عميل البيع',
            customer_type='retail',
        )

        # الخطوة 8: إنشاء فاتورة بيع
        invoice = SalesEngine.create_invoice(
            customer=customer,
            branch=self.branch,
            warehouse=self.wh_fin,
            salesperson=self.user,
            items=[{
                'product': finished,
                'quantity': 3,
                'unit_price': Decimal('300.00'),
                'discount_percentage': 0,
            }],
            payment_method='cash',
            is_taxable=False,
            user=self.user,
        )

        self.assertEqual(invoice.status, 'draft')
        self.assertEqual(invoice.subtotal, Decimal('900.00'))
        self.assertEqual(invoice.total, Decimal('900.00'))

        # الخطوة 9: تأكيد الفاتورة (خصم مخزون + قيد)
        SalesEngine.confirm_invoice(invoice, user=self.user)
        invoice.refresh_from_db()

        self.assertIn(invoice.status, ('paid', 'confirmed'))
        self.assertIsNotNone(invoice.journal_entry)

        # التحقق من خصم المخزون
        fin_level = StockEngine.get_stock_level(finished, self.wh_fin)
        self.assertEqual(fin_level, Decimal('7'))

    # ── الخطوة 10: ميزان المراجعة متوازن ─────────────────────────
    def test_10_trial_balance_balanced(self):
        """التحقق من أن ميزان المراجعة متوازن (مدين = دائن)"""
        finished = Product.objects.create(
            code='FIN-LAMP-01', name='مصباح',
            product_type='finished', unit=self.uom,
            cost_price=Decimal('50.00'), retail_price=Decimal('150.00'),
        )
        StockEngine.receive_stock(
            product=finished, warehouse=self.wh_fin,
            quantity=Decimal('5'), unit_cost=Decimal('50.00'),
            source_type='initial', source_id='INIT-LAMP',
            user=self.user,
        )

        customer = Customer.objects.create(
            code='CUST-BALANCE-001', name='عميل الميزان', customer_type='retail')

        invoice = SalesEngine.create_invoice(
            customer=customer, branch=self.branch, warehouse=self.wh_fin,
            salesperson=self.user,
            items=[{'product': finished, 'quantity': 2,
                    'unit_price': Decimal('150.00'), 'discount_percentage': 0}],
            payment_method='cash', is_taxable=False, user=self.user,
        )
        SalesEngine.confirm_invoice(invoice, user=self.user)

        # مجموع المدين = مجموع الدائن في كل القيود المرحّلة
        from django.db.models import Sum
        result = JournalLine.objects.filter(
            entry__status='posted',
        ).aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
        )

        total_debit  = result['total_debit']  or Decimal('0')
        total_credit = result['total_credit'] or Decimal('0')

        self.assertAlmostEqual(
            float(total_debit), float(total_credit), places=2,
            msg=f"ميزان المراجعة غير متوازن: مدين={total_debit}, دائن={total_credit}"
        )

    # ── الخطوة 11: قائمة الدخل تظهر ربحاً ────────────────────────
    def test_11_income_statement_shows_profit(self):
        """التحقق من أن قائمة الدخل تظهر ربحاً صحيحاً"""
        finished = Product.objects.create(
            code='FIN-MUG-01', name='كوب',
            product_type='finished', unit=self.uom,
            cost_price=Decimal('10.00'), retail_price=Decimal('50.00'),
        )
        StockEngine.receive_stock(
            product=finished, warehouse=self.wh_fin,
            quantity=Decimal('10'), unit_cost=Decimal('10.00'),
            source_type='initial', source_id='INIT-MUG',
            user=self.user,
        )

        customer = Customer.objects.create(
            code='CUST-PROFIT-001', name='عميل الربح', customer_type='retail')

        # بيع بسعر أعلى من التكلفة → ربح
        invoice = SalesEngine.create_invoice(
            customer=customer, branch=self.branch, warehouse=self.wh_fin,
            salesperson=self.user,
            items=[{'product': finished, 'quantity': 4,
                    'unit_price': Decimal('50.00'), 'discount_percentage': 0}],
            payment_method='cash', is_taxable=False, user=self.user,
        )
        SalesEngine.confirm_invoice(invoice, user=self.user)

        # إيرادات: 4 × 50 = 200
        # تكلفة:   4 × 10 = 40
        # ربح متوقع: 160
        revenue_accounts = Account.objects.filter(
            account_type='revenue', is_detail=True, is_active=True,
        )
        expense_accounts = Account.objects.filter(
            account_type='expense', is_detail=True, is_active=True,
        )

        from django.db.models import Sum
        revenue = JournalLine.objects.filter(
            entry__status='posted',
            account__in=revenue_accounts,
        ).aggregate(total=Sum('credit'))['total'] or Decimal('0')

        expenses = JournalLine.objects.filter(
            entry__status='posted',
            account__in=expense_accounts,
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0')

        net_profit = revenue - expenses
        self.assertGreater(
            net_profit, Decimal('0'),
            msg=f"لا يوجد ربح! الإيرادات={revenue} التكاليف={expenses}"
        )


# ══════════════════════════════════════════════════════════════════
# Test: التحقق من منطق الخدمات (unit tests للخدمات)
# ══════════════════════════════════════════════════════════════════

class StockEngineTest(TestCase):
    """اختبارات محرك المخزون"""

    def setUp(self):
        self.branch, self.wh_raw, self.wh_fin, self.fy, self.user = _make_base()
        self.uom = _make_uom()

    def test_receive_and_issue_stock(self):
        """استلام وصرف مخزون"""
        product = Product.objects.create(
            code='TEST-STOCK-01', name='منتج تجريبي',
            product_type='finished', unit=self.uom,
            cost_price=Decimal('25.00'),
        )

        StockEngine.receive_stock(
            product=product, warehouse=self.wh_fin,
            quantity=Decimal('20'), unit_cost=Decimal('25'),
            source_type='test', source_id='T-01', user=self.user,
        )

        level = StockEngine.get_stock_level(product, self.wh_fin)
        self.assertEqual(level, Decimal('20'))

        StockEngine.issue_stock(
            product=product, warehouse=self.wh_fin,
            quantity=Decimal('5'),
            source_type='test', source_id='T-02', user=self.user,
        )

        level = StockEngine.get_stock_level(product, self.wh_fin)
        self.assertEqual(level, Decimal('15'))

    def test_stock_transfer(self):
        """تحويل المخزون بين مخزنين"""
        product = Product.objects.create(
            code='TEST-TRANSFER-01', name='منتج تحويل',
            product_type='finished', unit=self.uom,
            cost_price=Decimal('30.00'),
        )

        StockEngine.receive_stock(
            product=product, warehouse=self.wh_raw,
            quantity=Decimal('10'), unit_cost=Decimal('30'),
            source_type='test', source_id='T-03', user=self.user,
        )

        StockEngine.transfer_stock(
            product=product,
            from_warehouse=self.wh_raw,
            to_warehouse=self.wh_fin,
            quantity=Decimal('4'),
            user=self.user,
        )

        self.assertEqual(StockEngine.get_stock_level(product, self.wh_raw), Decimal('6'))
        self.assertEqual(StockEngine.get_stock_level(product, self.wh_fin), Decimal('4'))

    def test_cannot_overdraw_stock(self):
        """لا يمكن صرف أكثر من الرصيد"""
        product = Product.objects.create(
            code='TEST-OVER-01', name='منتج سحب',
            product_type='finished', unit=self.uom,
            cost_price=Decimal('10.00'),
        )

        with self.assertRaises(Exception):
            StockEngine.issue_stock(
                product=product, warehouse=self.wh_fin,
                quantity=Decimal('100'),
                source_type='test', source_id='T-04', user=self.user,
            )


class PurchaseEngineTest(TestCase):
    """اختبارات محرك المشتريات"""

    def setUp(self):
        self.branch, self.wh_raw, self.wh_fin, self.fy, self.user = _make_base()
        self.uom      = _make_uom()
        self.supplier = _make_supplier()

    def test_purchase_order_totals(self):
        """التحقق من حسابات أمر الشراء"""
        raw = Product.objects.create(
            code='RAW-TEST-PO-01', name='خامة شراء',
            product_type='raw_material', unit=self.uom,
            cost_price=Decimal('10.00'),
        )

        order = PurchaseEngine.create_purchase_order(
            supplier=self.supplier,
            branch=self.branch,
            warehouse=self.wh_raw,
            items=[
                {'product': raw, 'quantity': 50, 'unit_cost': Decimal('10')},
                {'product': raw, 'quantity': 30, 'unit_cost': Decimal('15')},
            ],
            is_taxable=False,
            user=self.user,
        )

        # 50×10 + 30×15 = 500 + 450 = 950
        self.assertEqual(order.subtotal, Decimal('950.00'))
        self.assertEqual(order.total, Decimal('950.00'))
        self.assertEqual(order.lines.count(), 2)

    def test_receive_updates_stock(self):
        """استلام أمر الشراء يحدّث المخزون"""
        raw = Product.objects.create(
            code='RAW-TEST-RECV-01', name='خامة استلام',
            product_type='raw_material', unit=self.uom,
            cost_price=Decimal('8.00'),
        )

        order = PurchaseEngine.create_purchase_order(
            supplier=self.supplier,
            branch=self.branch,
            warehouse=self.wh_raw,
            items=[{'product': raw, 'quantity': 25, 'unit_cost': 8}],
            is_taxable=False,
            user=self.user,
        )
        PurchaseEngine.receive_purchase(order, user=self.user)

        level = StockEngine.get_stock_level(raw, self.wh_raw)
        self.assertEqual(level, Decimal('25'))


class ProductionEngineTest(TestCase):
    """اختبارات محرك الإنتاج"""

    def setUp(self):
        self.branch, self.wh_raw, self.wh_fin, self.fy, self.user = _make_base()
        self.uom = _make_uom()

        self.raw = Product.objects.create(
            code='RAW-PROD-TEST-01', name='خامة إنتاج',
            product_type='raw_material', unit=self.uom,
            cost_price=Decimal('15.00'),
        )
        self.finished = Product.objects.create(
            code='FIN-PROD-TEST-01', name='منتج إنتاج',
            product_type='finished', unit=self.uom,
            cost_price=Decimal('0.00'), retail_price=Decimal('200.00'),
        )
        self.bom = BillOfMaterials.objects.create(
            product=self.finished, name='BOM اختبار', is_default=True,
        )
        BOMLine.objects.create(
            bom=self.bom, raw_material=self.raw, quantity=Decimal('2'),
        )
        # تعبئة المخزون
        StockEngine.receive_stock(
            product=self.raw, warehouse=self.wh_raw,
            quantity=Decimal('100'), unit_cost=Decimal('15'),
            source_type='initial', source_id='INIT-PROD', user=self.user,
        )

    def test_cannot_create_order_for_raw_material(self):
        """لا يمكن إنشاء أمر إنتاج لخامة"""
        with self.assertRaises(ValueError):
            ProductionEngine.create_production_order(
                product=self.raw, bom=self.bom, quantity=Decimal('1'),
                production_line=None,
                warehouse_raw=self.wh_raw, warehouse_finished=self.wh_fin,
                user=self.user,
            )

    def test_production_lifecycle(self):
        """دورة حياة أمر الإنتاج: مسودة → مؤكد → قيد التنفيذ → مكتمل"""
        order = ProductionEngine.create_production_order(
            product=self.finished, bom=self.bom, quantity=Decimal('10'),
            production_line=None,
            warehouse_raw=self.wh_raw, warehouse_finished=self.wh_fin,
            user=self.user,
        )
        self.assertEqual(order.status, 'draft')

        ProductionEngine.confirm_order(order, user=self.user)
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

        ProductionEngine.start_production(order, user=self.user)
        order.refresh_from_db()
        self.assertEqual(order.status, 'in_progress')

        # التحقق من صرف الخامات (2 لكل وحدة × 10 = 20)
        raw_level = StockEngine.get_stock_level(self.raw, self.wh_raw)
        self.assertEqual(raw_level, Decimal('80'))

        ProductionEngine.complete_production(
            order, quantity_produced=Decimal('10'),
            quantity_wasted=Decimal('0'), user=self.user,
        )
        order.refresh_from_db()
        self.assertEqual(order.status, 'completed')
        self.assertEqual(order.quantity_produced, Decimal('10'))

        fin_level = StockEngine.get_stock_level(self.finished, self.wh_fin)
        self.assertEqual(fin_level, Decimal('10'))

    def test_shortage_raises_error(self):
        """نقص الخامات يرفع خطأ عند إنشاء الأمر"""
        # استهلاك كل المخزون
        StockEngine.issue_stock(
            product=self.raw, warehouse=self.wh_raw,
            quantity=Decimal('100'),
            source_type='test', source_id='DRAIN',
        )

        with self.assertRaises(ValueError):
            ProductionEngine.create_production_order(
                product=self.finished, bom=self.bom, quantity=Decimal('10'),
                production_line=None,
                warehouse_raw=self.wh_raw, warehouse_finished=self.wh_fin,
                user=self.user,
            )


class SalesEngineTest(TestCase):
    """اختبارات محرك المبيعات"""

    def setUp(self):
        self.branch, self.wh_raw, self.wh_fin, self.fy, self.user = _make_base()
        self.uom = _make_uom()

        self.product = Product.objects.create(
            code='FIN-SALES-TEST-01', name='منتج بيع',
            product_type='finished', unit=self.uom,
            cost_price=Decimal('80.00'), retail_price=Decimal('200.00'),
        )
        StockEngine.receive_stock(
            product=self.product, warehouse=self.wh_fin,
            quantity=Decimal('50'), unit_cost=Decimal('80'),
            source_type='initial', source_id='INIT-SALES', user=self.user,
        )
        self.customer = Customer.objects.create(
            code='CUST-SALES-TEST-01', name='عميل اختبار', customer_type='retail',
        )

    def test_invoice_created_as_draft(self):
        """الفاتورة تُنشأ كمسودة"""
        invoice = SalesEngine.create_invoice(
            customer=self.customer, branch=self.branch, warehouse=self.wh_fin,
            salesperson=self.user,
            items=[{'product': self.product, 'quantity': 2,
                    'unit_price': Decimal('200.00'), 'discount_percentage': 0}],
            payment_method='cash', is_taxable=False, user=self.user,
        )
        self.assertEqual(invoice.status, 'draft')
        self.assertEqual(invoice.total, Decimal('400.00'))

    def test_confirm_invoice_deducts_stock(self):
        """تأكيد الفاتورة يخصم من المخزون"""
        invoice = SalesEngine.create_invoice(
            customer=self.customer, branch=self.branch, warehouse=self.wh_fin,
            salesperson=self.user,
            items=[{'product': self.product, 'quantity': 5,
                    'unit_price': Decimal('200.00'), 'discount_percentage': 0}],
            payment_method='cash', is_taxable=False, user=self.user,
        )
        SalesEngine.confirm_invoice(invoice, user=self.user)

        level = StockEngine.get_stock_level(self.product, self.wh_fin)
        self.assertEqual(level, Decimal('45'))  # 50 - 5

    def test_confirm_invoice_creates_journal_entry(self):
        """تأكيد الفاتورة يُنشئ قيداً محاسبياً"""
        invoice = SalesEngine.create_invoice(
            customer=self.customer, branch=self.branch, warehouse=self.wh_fin,
            salesperson=self.user,
            items=[{'product': self.product, 'quantity': 1,
                    'unit_price': Decimal('200.00'), 'discount_percentage': 0}],
            payment_method='cash', is_taxable=False, user=self.user,
        )
        SalesEngine.confirm_invoice(invoice, user=self.user)
        invoice.refresh_from_db()

        self.assertIsNotNone(invoice.journal_entry)
        self.assertEqual(invoice.journal_entry.status, 'posted')

    def test_journal_entry_is_balanced(self):
        """القيد المحاسبي للفاتورة متوازن (مدين = دائن)"""
        invoice = SalesEngine.create_invoice(
            customer=self.customer, branch=self.branch, warehouse=self.wh_fin,
            salesperson=self.user,
            items=[{'product': self.product, 'quantity': 3,
                    'unit_price': Decimal('200.00'), 'discount_percentage': 0}],
            payment_method='cash', is_taxable=False, user=self.user,
        )
        SalesEngine.confirm_invoice(invoice, user=self.user)
        invoice.refresh_from_db()

        entry = invoice.journal_entry
        self.assertAlmostEqual(
            float(entry.total_debit), float(entry.total_credit), places=2,
            msg="القيد المحاسبي غير متوازن!"
        )
