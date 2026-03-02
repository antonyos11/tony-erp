"""
اختبارات Sprint 22B — محاسبة التكاليف الصناعية + الميزانيات + أعمار الديون
═══════════════════════════════════════════════════════════════════════════════
"""
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

# Core
from apps.core.models import Branch, Warehouse

# Accounts
from apps.accounts.models import (
    Account, FiscalYear, CostCenter,
    CostAllocation, WIPAccount, Budget, BudgetLine,
)
from apps.accounts.services.manufacturing_cost_engine import ManufacturingCostEngine
from apps.accounts.services.budget_engine import BudgetEngine

# Inventory / Production
from apps.inventory.models import Category, UnitOfMeasure, Product, BillOfMaterials
from apps.production.models import ProductionOrder

User = get_user_model()


# ══════════════════════════════════════════════════════
# Fixture mixin مشترك لكل الاختبارات
# ══════════════════════════════════════════════════════

class BaseSprint22BTest(TestCase):
    """Setup مشترك: يُنشئ كل الـ fixtures اللازمة"""

    @classmethod
    def setUpTestData(cls):
        # مستخدم
        cls.user = User.objects.create_user(
            username='sprint22b_user', password='pass123',
        )

        # فرع
        cls.branch = Branch.objects.create(
            name='فرع Test 22B', branch_type='owned', governorate='القاهرة',
        )

        # مخازن
        cls.wh_raw = Warehouse.objects.create(
            name='مخزن خامات Test', branch=cls.branch, warehouse_type='raw',
        )
        cls.wh_fg = Warehouse.objects.create(
            name='مخزن منتجات Test', branch=cls.branch, warehouse_type='finished',
        )

        # سنة مالية
        cls.fiscal_year = FiscalYear.objects.create(
            name='FY-Test-22B',
            start_date='2026-01-01',
            end_date='2026-12-31',
            is_active=True,
            is_closed=False,
        )

        # الحسابات الأساسية (WIP / خامات / عمالة / overhead / منتجات تامة)
        cls.acc_raw = Account.objects.create(
            code='121', name='مخزون خامات', account_type='asset',
            nature='debit', is_detail=True, is_system=True,
        )
        cls.acc_wip = Account.objects.create(
            code='131', name='إنتاج تحت التشغيل', account_type='asset',
            nature='debit', is_detail=True, is_system=True,
        )
        cls.acc_fg = Account.objects.create(
            code='122', name='مخزون منتجات تامة', account_type='asset',
            nature='debit', is_detail=True, is_system=True,
        )
        cls.acc_labor = Account.objects.create(
            code='212', name='أجور مستحقة', account_type='liability',
            nature='credit', is_detail=True, is_system=True,
        )
        cls.acc_overhead = Account.objects.create(
            code='513', name='تكاليف صناعية غير مباشرة', account_type='expense',
            nature='debit', is_detail=True, is_system=True,
        )
        cls.acc_expense = Account.objects.create(
            code='520', name='مصروفات عامة', account_type='expense',
            nature='debit', is_detail=True, is_system=True,
        )

        # وحدة قياس
        cls.unit = UnitOfMeasure.objects.create(name='قطعة', symbol='قطعة')

        # تصنيف
        cls.category = Category.objects.create(name='تصنيف Test 22B')

        # منتج
        cls.product = Product.objects.create(
            code='PRD-TEST-22B',
            name='منتج تجريبي 22B',
            product_type='finished',
            unit=cls.unit,
            cost_price=Decimal('0'),
        )

        # خامة
        cls.raw_material = Product.objects.create(
            code='RAW-TEST-22B',
            name='خامة تجريبية 22B',
            product_type='raw_material',
            unit=cls.unit,
            cost_price=Decimal('50'),
        )

        # BOM
        cls.bom = BillOfMaterials.objects.create(
            product=cls.product,
            name='BOM Test 22B',
        )

        # أمر إنتاج
        cls.order = ProductionOrder.objects.create(
            order_number='ORD-TEST-22B-001',
            date=date.today(),
            product=cls.product,
            bom=cls.bom,
            quantity=Decimal('100'),
            quantity_produced=Decimal('100'),
            warehouse_raw=cls.wh_raw,
            warehouse_finished=cls.wh_fg,
        )


# ══════════════════════════════════════════════════════
# اختبارات محرك التكاليف الصناعية
# ══════════════════════════════════════════════════════

class ManufacturingCostTest(BaseSprint22BTest):
    """اختبارات ManufacturingCostEngine"""

    def test_allocate_material_creates_allocation_and_entry(self):
        """تحميل خامات ينشئ CostAllocation وقيد محاسبي"""
        materials = [
            {'product': self.raw_material, 'quantity': 10, 'unit_cost': Decimal('50')},
        ]
        total, entry = ManufacturingCostEngine.allocate_material_cost(
            self.order, materials, user=self.user,
        )

        self.assertEqual(total, Decimal('500'))
        self.assertIsNotNone(entry)
        self.assertEqual(CostAllocation.objects.filter(
            production_order=self.order, cost_type='material',
        ).count(), 1)
        alloc = CostAllocation.objects.get(production_order=self.order, cost_type='material')
        self.assertEqual(alloc.amount, Decimal('500'))

    def test_allocate_labor_creates_entry(self):
        """تحميل عمالة ينشئ قيد محاسبي وتخصيص"""
        entry = ManufacturingCostEngine.allocate_labor_cost(
            self.order, amount=Decimal('2000'), user=self.user,
        )
        self.assertIsNotNone(entry)
        self.assertEqual(CostAllocation.objects.filter(
            production_order=self.order, cost_type='labor',
        ).count(), 1)

    def test_allocate_overhead_creates_entry(self):
        """تحميل تكاليف غير مباشرة ينشئ قيد وتخصيص"""
        entry = ManufacturingCostEngine.allocate_overhead(
            self.order, amount=Decimal('1000'), cost_type='overhead', user=self.user,
        )
        self.assertIsNotNone(entry)
        self.assertEqual(CostAllocation.objects.filter(
            production_order=self.order, cost_type='overhead',
        ).count(), 1)

    def test_wip_recalculate(self):
        """WIP يُحسب صحيح بعد التحميلات"""
        materials = [{'product': self.raw_material, 'quantity': 10, 'unit_cost': Decimal('50')}]
        ManufacturingCostEngine.allocate_material_cost(self.order, materials, user=self.user)
        ManufacturingCostEngine.allocate_labor_cost(self.order, Decimal('1000'), user=self.user)
        ManufacturingCostEngine.allocate_overhead(self.order, Decimal('500'), user=self.user)

        wip = WIPAccount.objects.get(production_order=self.order)
        self.assertEqual(wip.material_cost, Decimal('500'))
        self.assertEqual(wip.labor_cost, Decimal('1000'))
        self.assertEqual(wip.overhead_cost, Decimal('500'))
        self.assertEqual(wip.total_cost, Decimal('2000'))

    def test_unit_cost_calculated_correctly(self):
        """تكلفة الوحدة = إجمالي / الكمية"""
        materials = [{'product': self.raw_material, 'quantity': 10, 'unit_cost': Decimal('50')}]
        ManufacturingCostEngine.allocate_material_cost(self.order, materials, user=self.user)
        ManufacturingCostEngine.allocate_labor_cost(self.order, Decimal('1000'), user=self.user)

        wip = WIPAccount.objects.get(production_order=self.order)
        expected_unit_cost = Decimal('1500') / Decimal('100')
        self.assertEqual(wip.unit_cost, expected_unit_cost)

    def test_close_production_transfers_wip(self):
        """إقفال الأمر يُنشئ قيد نقل من WIP إلى منتجات تامة"""
        materials = [{'product': self.raw_material, 'quantity': 10, 'unit_cost': Decimal('50')}]
        ManufacturingCostEngine.allocate_material_cost(self.order, materials, user=self.user)
        ManufacturingCostEngine.allocate_labor_cost(self.order, Decimal('2000'), user=self.user)

        wip, entry = ManufacturingCostEngine.close_production_order(self.order, user=self.user)

        self.assertTrue(wip.is_closed)
        self.assertIsNotNone(wip.closed_at)
        self.assertIsNotNone(entry)

        # تحقق من القيد: دائن WIP + مدين منتجات تامة
        from apps.accounts.models import JournalLine
        lines = entry.lines.all()
        debit_acc = lines.filter(account__code='122').first()
        credit_acc = lines.filter(account__code='131').first()
        self.assertIsNotNone(debit_acc)
        self.assertIsNotNone(credit_acc)
        self.assertEqual(debit_acc.debit, Decimal('2500'))

    def test_cannot_close_already_closed(self):
        """محاولة إقفال أمر مُقفل بالفعل ترفع ValueError"""
        materials = [{'product': self.raw_material, 'quantity': 1, 'unit_cost': Decimal('100')}]
        ManufacturingCostEngine.allocate_material_cost(self.order, materials, user=self.user)
        ManufacturingCostEngine.close_production_order(self.order, user=self.user)

        with self.assertRaises(ValueError):
            ManufacturingCostEngine.close_production_order(self.order, user=self.user)

    def test_wip_summary(self):
        """ملخص WIP يعرض الأوامر المفتوحة"""
        materials = [{'product': self.raw_material, 'quantity': 5, 'unit_cost': Decimal('100')}]
        ManufacturingCostEngine.allocate_material_cost(self.order, materials, user=self.user)

        summary = ManufacturingCostEngine.get_wip_summary()
        self.assertGreaterEqual(summary['count'], 1)
        self.assertGreater(summary['total_wip_value'], 0)

    def test_production_cost_report(self):
        """تقرير التكلفة يُرجع مفاتيح صحيحة"""
        materials = [{'product': self.raw_material, 'quantity': 2, 'unit_cost': Decimal('50')}]
        ManufacturingCostEngine.allocate_material_cost(self.order, materials, user=self.user)

        report = ManufacturingCostEngine.get_production_cost_report(self.order)
        self.assertIn('material_cost', report)
        self.assertIn('unit_cost', report)
        self.assertIn('allocations', report)
        self.assertEqual(report['material_cost'], Decimal('100'))


# ══════════════════════════════════════════════════════
# اختبارات نماذج الميزانية
# ══════════════════════════════════════════════════════

class BudgetModelTest(BaseSprint22BTest):
    """اختبارات نموذج Budget + BudgetLine"""

    def test_create_budget(self):
        """إنشاء ميزانية بنجاح"""
        budget = Budget.objects.create(
            name='ميزانية Test 2026',
            fiscal_year=self.fiscal_year,
            period_type='monthly',
            status='draft',
            created_by=self.user, updated_by=self.user,
        )
        self.assertEqual(budget.name, 'ميزانية Test 2026')
        self.assertEqual(budget.status, 'draft')

    def test_budget_line_annual_total(self):
        """سطر الميزانية يحسب الإجمالي السنوي تلقائياً"""
        budget = Budget.objects.create(
            name='ميزانية تلقائية',
            fiscal_year=self.fiscal_year,
            status='draft',
            created_by=self.user, updated_by=self.user,
        )
        line = BudgetLine.objects.create(
            budget=budget,
            account=self.acc_expense,
            jan=Decimal('1000'), feb=Decimal('1000'), mar=Decimal('1000'),
            apr=Decimal('1000'), may=Decimal('1000'), jun=Decimal('1000'),
            jul=Decimal('1000'), aug=Decimal('1000'), sep=Decimal('1000'),
            oct=Decimal('1000'), nov=Decimal('1000'), dec=Decimal('1000'),
        )
        self.assertEqual(line.annual_total, Decimal('12000'))

    def test_budget_line_get_month_amount(self):
        """get_month_amount يرجع الصحيح"""
        budget = Budget.objects.create(
            name='ميزانية شهرية',
            fiscal_year=self.fiscal_year,
            status='draft',
            created_by=self.user, updated_by=self.user,
        )
        line = BudgetLine.objects.create(
            budget=budget, account=self.acc_expense,
            jan=Decimal('500'), mar=Decimal('750'),
        )
        self.assertEqual(line.get_month_amount(1), Decimal('500'))
        self.assertEqual(line.get_month_amount(2), Decimal('0'))
        self.assertEqual(line.get_month_amount(3), Decimal('750'))


# ══════════════════════════════════════════════════════
# اختبارات BudgetEngine
# ══════════════════════════════════════════════════════

class BudgetEngineTest(BaseSprint22BTest):
    """اختبارات BudgetEngine"""

    def setUp(self):
        # ميزانية معتمدة
        self.budget = Budget.objects.create(
            name='ميزانية معتمدة Test',
            fiscal_year=self.fiscal_year,
            status='approved',
            branch=self.branch,
            created_by=self.user, updated_by=self.user,
        )
        # سطر ميزانية: 5000 لشهر مارس
        self.budget_line = BudgetLine.objects.create(
            budget=self.budget,
            account=self.acc_expense,
            mar=Decimal('5000'),
        )

    def test_budget_check_within_limit(self):
        """فحص ميزانية: المبلغ ضمن الحد → True"""
        is_within, budget_amt, actual, remaining = BudgetEngine.check_budget(
            account_code='520',
            amount=Decimal('1000'),
            branch=self.branch,
            month=3,
        )
        self.assertTrue(is_within)
        self.assertEqual(budget_amt, Decimal('5000'))

    def test_budget_check_over_limit(self):
        """فحص ميزانية: المبلغ يتجاوز الحد → False"""
        is_within, budget_amt, actual, remaining = BudgetEngine.check_budget(
            account_code='520',
            amount=Decimal('6000'),
            branch=self.branch,
            month=3,
        )
        self.assertFalse(is_within)

    def test_budget_vs_actual_report_structure(self):
        """تقرير budget vs actual يُرجع الهيكل الصحيح"""
        report = BudgetEngine.get_budget_vs_actual(self.budget.pk, month=3)
        self.assertIn('budget', report)
        self.assertIn('lines', report)
        self.assertIn('total_budget', report)
        self.assertIn('total_actual', report)
        self.assertIn('total_variance', report)
        self.assertEqual(len(report['lines']), 1)

    def test_budget_vs_actual_variance(self):
        """الفرق = الميزانية - الفعلي"""
        report = BudgetEngine.get_budget_vs_actual(self.budget.pk, month=3)
        line = report['lines'][0]
        self.assertEqual(line['budget'], Decimal('5000'))
        # لا يوجد فعلي → الفرق = 5000
        self.assertEqual(line['variance'], Decimal('5000'))
        self.assertEqual(line['status'], 'normal')

    def test_annual_summary_has_12_months(self):
        """الملخص السنوي يحتوي على 12 شهراً"""
        summary = BudgetEngine.get_annual_summary(self.budget.pk)
        self.assertEqual(len(summary['months']), 12)

    def test_budget_status_classification(self):
        """حالة السطر تُصنَّف صحيح"""
        # إنشاء قيد فعلي يتجاوز 90% من الميزانية
        from apps.accounts.models import JournalEntry, JournalLine
        entry = JournalEntry.objects.create(
            entry_number='TEST-BVA-001',
            date='2026-03-15',
            fiscal_year=self.fiscal_year,
            description='اختبار',
            source='expense',
            status='posted',
            total_debit=Decimal('4800'),
            total_credit=Decimal('4800'),
        )
        # سطر مدين على حساب المصروف
        JournalLine.objects.create(
            entry=entry,
            account=self.acc_expense,
            debit=Decimal('4800'),
            credit=Decimal('0'),
        )
        # سطر دائن موازن
        JournalLine.objects.create(
            entry=entry,
            account=self.acc_overhead,
            debit=Decimal('0'),
            credit=Decimal('4800'),
        )

        report = BudgetEngine.get_budget_vs_actual(self.budget.pk, month=3)
        line = report['lines'][0]
        # 4800/5000 = 96% > 90% → warning
        self.assertEqual(line['status'], 'warning')


# ══════════════════════════════════════════════════════
# اختبارات تقارير أعمار الديون
# ══════════════════════════════════════════════════════

class AgingReportTest(BaseSprint22BTest):
    """اختبارات AgingReport"""

    def _create_customer_and_invoice(self, days_old, amount):
        """helper لإنشاء عميل وفاتورة"""
        from apps.sales.models import SalesInvoice
        from apps.sales.models import Customer

        customer, _ = Customer.objects.get_or_create(
            code=f'AGE-CUST-{days_old}',
            defaults={
                'name': f'عميل Test Aging {days_old}',
                'phone': '01000000000',
                'customer_type': 'retail',
            },
        )
        inv_date = timezone.now() - timedelta(days=days_old)
        priceList = None
        try:
            from apps.sales.models import PriceList
            priceList = PriceList.objects.first()
        except Exception:
            pass

        inv = SalesInvoice.objects.create(
            invoice_number=f'AGE-INV-{days_old}-{amount}',
            date=inv_date,
            customer=customer,
            branch=self.branch,
            warehouse=self.wh_fg,
            status='confirmed',
            total=Decimal(str(amount)),
            remaining_amount=Decimal(str(amount)),
        )
        return customer, inv

    def test_customer_aging_categories(self):
        """الفواتير تُصنَّف بشكل صحيح حسب الأيام"""
        from apps.reports.services.advanced_reports import AgingReport

        self._create_customer_and_invoice(0, 1000)    # حالي
        self._create_customer_and_invoice(15, 500)    # 1-30 يوم
        self._create_customer_and_invoice(45, 750)    # 31-60 يوم
        self._create_customer_and_invoice(75, 300)    # 61-90 يوم
        self._create_customer_and_invoice(120, 200)   # +90 يوم

        result = AgingReport.customer_aging()

        self.assertIn('rows', result)
        self.assertIn('totals', result)
        totals = result['totals']
        self.assertGreater(totals['current'], 0)
        self.assertGreater(totals['days_30'], 0)
        self.assertGreater(totals['days_60'], 0)
        self.assertGreater(totals['days_90'], 0)
        self.assertGreater(totals['over_90'], 0)
        self.assertEqual(
            totals['total'],
            totals['current'] + totals['days_30'] + totals['days_60'] +
            totals['days_90'] + totals['over_90'],
        )

    def test_supplier_aging(self):
        """تقرير أعمار الموردين يُرجع هيكلاً صحيحاً"""
        from apps.reports.services.advanced_reports import AgingReport

        result = AgingReport.supplier_aging()
        self.assertIn('rows', result)
        self.assertIn('totals', result)
        self.assertIn('as_of_date', result)
