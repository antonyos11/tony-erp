"""
اختبارات التقارير ولوحة القيادة — RITA ERP
Sprint 7
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import Branch, Warehouse
from apps.inventory.models import Product, UnitOfMeasure, Category, StockLevel, BillOfMaterials, BOMLine
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine, PriceList
from apps.production.models import ProductionOrder, ProductionLine
from apps.accounts.models import FiscalYear

from apps.reports.services.sales_reports import SalesReports
from apps.reports.services.inventory_reports import InventoryReports
from apps.reports.services.cost_reports import CostReports
from apps.reports.services.branch_reports import BranchReports

User = get_user_model()


class BaseReportTestCase(TestCase):
    """بيانات أساسية مشتركة لكل الاختبارات"""

    @classmethod
    def setUpTestData(cls):
        # مستخدم
        cls.user = User.objects.create_user(
            username='testuser', password='testpass123',
            first_name='أحمد', last_name='محمد',
        )

        # فرع
        cls.branch = Branch.objects.create(name='الفرع الرئيسي', branch_type='owned')

        # مخزن
        cls.warehouse = Warehouse.objects.create(
            name='المخزن الرئيسي', warehouse_type='finished', branch=cls.branch,
        )
        cls.raw_warehouse = Warehouse.objects.create(
            name='مخزن الخامات', warehouse_type='raw_materials', branch=cls.branch,
        )

        # وحدة قياس + تصنيف
        cls.unit = UnitOfMeasure.objects.create(name='قطعة', symbol='قطعة')
        cls.category = Category.objects.create(name='أثاث')

        # منتجات
        cls.product = Product.objects.create(
            code='PROD-001', name='كرسي مكتب',
            product_type='finished', unit=cls.unit, category=cls.category,
            cost_price=100, retail_price=200, reorder_level=10,
        )
        cls.product2 = Product.objects.create(
            code='PROD-002', name='مكتب خشب',
            product_type='finished', unit=cls.unit, category=cls.category,
            cost_price=300, retail_price=600, reorder_level=5,
        )
        cls.raw_material = Product.objects.create(
            code='RAW-001', name='خشب زان',
            product_type='raw_material', unit=cls.unit, category=cls.category,
            cost_price=50, retail_price=0,
        )

        # رصيد مخزون
        StockLevel.objects.create(
            product=cls.product, warehouse=cls.warehouse,
            quantity=20, average_cost=100,
        )
        StockLevel.objects.create(
            product=cls.product2, warehouse=cls.warehouse,
            quantity=3, average_cost=300,  # تحت حد إعادة الطلب
        )
        StockLevel.objects.create(
            product=cls.raw_material, warehouse=cls.raw_warehouse,
            quantity=100, average_cost=50,
        )

        # عميل
        cls.customer = Customer.objects.create(
            code='CUST-001', name='شركة ABC', customer_type='wholesale',
            branch=cls.branch,
        )
        cls.customer2 = Customer.objects.create(
            code='CUST-002', name='محل XYZ', customer_type='retail',
            branch=cls.branch,
        )

        # سنة مالية
        cls.fiscal_year = FiscalYear.objects.create(
            name='2026', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        )

        # BOM
        cls.bom = BillOfMaterials.objects.create(
            product=cls.product, name='BOM كرسي', is_default=True,
        )
        BOMLine.objects.create(
            bom=cls.bom, raw_material=cls.raw_material, quantity=2, waste_percentage=5,
        )

        # فواتير مبيعات
        now = timezone.now()
        cls.invoice1 = SalesInvoice.objects.create(
            invoice_number='INV-TEST-001',
            date=now,
            customer=cls.customer,
            branch=cls.branch,
            warehouse=cls.warehouse,
            salesperson=cls.user,
            status='paid',
            payment_method='cash',
            subtotal=1000, discount_amount=50, taxable_amount=950,
            tax_amount=133, total=1083, paid_amount=1083, remaining_amount=0,
        )
        SalesInvoiceLine.objects.create(
            invoice=cls.invoice1, product=cls.product,
            quantity=5, unit_price=200,
            discount_percentage=0, discount_amount=0,
            subtotal=1000, cost_price=100, profit=500,
        )

        cls.invoice2 = SalesInvoice.objects.create(
            invoice_number='INV-TEST-002',
            date=now - timedelta(days=2),
            customer=cls.customer2,
            branch=cls.branch,
            warehouse=cls.warehouse,
            salesperson=cls.user,
            status='confirmed',
            payment_method='installment',
            subtotal=600, discount_amount=0, taxable_amount=600,
            tax_amount=84, total=684, paid_amount=200, remaining_amount=484,
        )
        SalesInvoiceLine.objects.create(
            invoice=cls.invoice2, product=cls.product2,
            quantity=1, unit_price=600,
            discount_percentage=0, discount_amount=0,
            subtotal=600, cost_price=300, profit=300,
        )


# ===== اختبارات تقارير المبيعات =====

class SalesReportsTests(BaseReportTestCase):
    """اختبارات تقارير المبيعات"""

    def test_sales_summary(self):
        start = date.today() - timedelta(days=7)
        end = date.today()
        report = SalesReports.sales_summary(start, end)
        self.assertEqual(report['invoice_count'], 2)
        self.assertGreater(report['total_sales'], 0)
        self.assertGreater(report['gross_profit'], 0)
        self.assertGreater(report['profit_margin'], 0)

    def test_sales_summary_with_branch_filter(self):
        start = date.today() - timedelta(days=7)
        end = date.today()
        report = SalesReports.sales_summary(start, end, branch=self.branch)
        self.assertEqual(report['invoice_count'], 2)

    def test_sales_summary_with_salesperson_filter(self):
        start = date.today() - timedelta(days=7)
        end = date.today()
        report = SalesReports.sales_summary(start, end, salesperson=self.user)
        self.assertEqual(report['invoice_count'], 2)

    def test_sales_by_product(self):
        start = date.today() - timedelta(days=7)
        end = date.today()
        products = SalesReports.sales_by_product(start, end)
        self.assertEqual(len(products), 2)
        # أول منتج هو الأعلى إيراداً
        self.assertIn('profit_margin', products[0])

    def test_sales_by_customer(self):
        start = date.today() - timedelta(days=7)
        end = date.today()
        customers = SalesReports.sales_by_customer(start, end)
        self.assertEqual(len(customers), 2)

    def test_sales_by_salesperson(self):
        start = date.today() - timedelta(days=7)
        end = date.today()
        salespersons = SalesReports.sales_by_salesperson(start, end)
        self.assertEqual(len(salespersons), 1)
        self.assertEqual(salespersons[0]['invoice_count'], 2)

    def test_profitability_report(self):
        start = date.today() - timedelta(days=7)
        end = date.today()
        products = SalesReports.profitability_report(start, end)
        self.assertEqual(len(products), 2)
        self.assertIn('status', products[0])
        self.assertIn('status_color', products[0])

    def test_daily_sales_trend(self):
        trend = SalesReports.daily_sales_trend(days=7)
        self.assertEqual(len(trend), 7)
        self.assertIn('total_sales', trend[0])


# ===== اختبارات تقارير المخزون =====

class InventoryReportsTests(BaseReportTestCase):
    """اختبارات تقارير المخزون"""

    def test_stock_movement_report(self):
        start = date.today() - timedelta(days=30)
        end = date.today()
        report = InventoryReports.stock_movement_report(start, end)
        self.assertIn('items', report)
        self.assertIn('total_in_value', report)

    def test_dead_stock_report(self):
        # كل الأرصدة جديدة فلن يكون هناك راكد
        result = InventoryReports.dead_stock_report(days=1)
        self.assertIsInstance(result, list)

    def test_reorder_report(self):
        result = InventoryReports.reorder_report()
        # product2 تحت الحد (3 < 5)
        self.assertTrue(len(result) >= 1)
        codes = [r['product_code'] for r in result]
        self.assertIn('PROD-002', codes)

    def test_stock_turnover_report(self):
        start = date.today() - timedelta(days=30)
        end = date.today()
        result = InventoryReports.stock_turnover_report(start, end)
        self.assertIsInstance(result, list)


# ===== اختبارات تقارير التكاليف =====

class CostReportsTests(BaseReportTestCase):
    """اختبارات تقارير التكاليف"""

    def test_product_cost_report(self):
        products = CostReports.product_cost_report()
        self.assertTrue(len(products) >= 2)
        # يجب أن يكون لكل منتج حقل status
        for p in products:
            self.assertIn('status', p)
            self.assertIn('margin_pct', p)

    def test_product_cost_report_single_product(self):
        products = CostReports.product_cost_report(product=self.product)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['product_code'], 'PROD-001')

    def test_cost_variance_report(self):
        start = date.today() - timedelta(days=30)
        end = date.today()
        result = CostReports.cost_variance_report(start, end)
        self.assertIsInstance(result, list)

    def test_production_line_profitability(self):
        start = date.today() - timedelta(days=30)
        end = date.today()
        result = CostReports.production_line_profitability(start, end)
        self.assertIsInstance(result, list)


# ===== اختبارات تقارير الفروع =====

class BranchReportsTests(BaseReportTestCase):
    """اختبارات تقارير الفروع"""

    def test_branch_scorecard(self):
        start = date.today() - timedelta(days=30)
        end = date.today()
        result = BranchReports.branch_scorecard(start, end)
        self.assertTrue(len(result) >= 1)
        branch_data = result[0]
        self.assertIn('total_sales', branch_data)
        self.assertIn('score', branch_data)

    def test_abnormal_discounts_report(self):
        start = date.today() - timedelta(days=30)
        end = date.today()
        result = BranchReports.abnormal_discounts_report(start, end)
        self.assertIn('items', result)
        self.assertIn('avg_discount', result)

    def test_aging_report_customer(self):
        result = BranchReports.aging_report(partner_type='customer')
        self.assertIn('items', result)
        self.assertIn('buckets', result)
        self.assertEqual(result['partner_type'], 'عملاء')
        # invoice2 لها رصيد متبقي
        self.assertTrue(result['total_count'] >= 1)

    def test_aging_report_supplier(self):
        result = BranchReports.aging_report(partner_type='supplier')
        self.assertEqual(result['partner_type'], 'موردين')


# ===== اختبارات الصفحات (HTTP 200) =====

class ReportViewsTests(BaseReportTestCase):
    """اختبار أن كل صفحات التقارير ترجع 200"""

    def setUp(self):
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_dashboard(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_sales_summary_page(self):
        response = self.client.get('/reports/sales-summary/')
        self.assertEqual(response.status_code, 200)

    def test_sales_by_product_page(self):
        response = self.client.get('/reports/sales-by-product/')
        self.assertEqual(response.status_code, 200)

    def test_sales_by_customer_page(self):
        response = self.client.get('/reports/sales-by-customer/')
        self.assertEqual(response.status_code, 200)

    def test_sales_by_salesperson_page(self):
        response = self.client.get('/reports/sales-by-salesperson/')
        self.assertEqual(response.status_code, 200)

    def test_profitability_page(self):
        response = self.client.get('/reports/profitability/')
        self.assertEqual(response.status_code, 200)

    def test_stock_movement_page(self):
        response = self.client.get('/reports/stock-movement/')
        self.assertEqual(response.status_code, 200)

    def test_dead_stock_page(self):
        response = self.client.get('/reports/dead-stock/')
        self.assertEqual(response.status_code, 200)

    def test_reorder_page(self):
        response = self.client.get('/reports/reorder/')
        self.assertEqual(response.status_code, 200)

    def test_product_cost_page(self):
        response = self.client.get('/reports/product-cost/')
        self.assertEqual(response.status_code, 200)

    def test_cost_variance_page(self):
        response = self.client.get('/reports/cost-variance/')
        self.assertEqual(response.status_code, 200)

    def test_branch_scorecard_page(self):
        response = self.client.get('/reports/branch-scorecard/')
        self.assertEqual(response.status_code, 200)

    def test_aging_page(self):
        response = self.client.get('/reports/aging/')
        self.assertEqual(response.status_code, 200)

    def test_vat_report_page(self):
        response = self.client.get('/reports/vat/')
        self.assertEqual(response.status_code, 200)

    def test_sales_summary_with_filters(self):
        """اختبار الفلترة بالتاريخ والفرع"""
        response = self.client.get('/reports/sales-summary/', {
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'branch': self.branch.pk,
        })
        self.assertEqual(response.status_code, 200)

    def test_aging_page_supplier(self):
        response = self.client.get('/reports/aging/', {'partner_type': 'supplier'})
        self.assertEqual(response.status_code, 200)

    def test_dead_stock_with_days_param(self):
        response = self.client.get('/reports/dead-stock/', {'days': '60'})
        self.assertEqual(response.status_code, 200)


# ===== اختبارات لوحة القيادة =====

class DashboardTests(BaseReportTestCase):
    """اختبارات لوحة القيادة"""

    def setUp(self):
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_dashboard_context(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        ctx = response.context
        self.assertIn('stats', ctx)
        self.assertIn('chart_labels', ctx)
        self.assertIn('chart_data', ctx)
        self.assertIn('top_products', ctx)
        self.assertIn('alerts', ctx)

    def test_dashboard_stats_not_zero(self):
        """مع وجود بيانات — KPIs لازم تكون > 0"""
        response = self.client.get('/')
        stats = response.context['stats']
        self.assertGreater(stats['sales_month'], 0)
        self.assertGreater(stats['profit_month'], 0)

    def test_dashboard_alerts_present(self):
        """يجب أن تكون هناك تنبيهات"""
        response = self.client.get('/')
        alerts = response.context['alerts']
        self.assertTrue(len(alerts) >= 1)
