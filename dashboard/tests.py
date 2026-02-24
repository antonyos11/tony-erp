"""
Dashboard KPI Unit Tests
اختبارات وحدة لحسابات مؤشرات الأداء
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

User = get_user_model()


class EnhancedKPICalculatorTest(TestCase):
    """اختبارات حاسبة KPI المحسّنة"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='test_kpi_user',
            password='testpass123',
            is_active=True,
        )

    def _get_calculator(self, date_range=None):
        from dashboard.enhanced_kpis import EnhancedKPICalculator
        return EnhancedKPICalculator(user=self.user, date_range=date_range)

    # ---------- get_all_kpis ----------
    def test_get_all_kpis_returns_expected_categories(self):
        calc = self._get_calculator()
        kpis = calc.get_all_kpis()
        self.assertIn('sales', kpis)
        self.assertIn('inventory', kpis)
        self.assertIn('financial', kpis)
        self.assertIn('customer', kpis)
        self.assertIn('operational', kpis)

    # ---------- get_sales_kpis ----------
    def test_sales_kpis_returns_expected_keys(self):
        calc = self._get_calculator()
        data = calc.get_sales_kpis()
        expected_keys = {
            'total_sales', 'previous_sales', 'growth_rate',
            'invoice_count', 'avg_invoice_value', 'daily_avg',
        }
        self.assertEqual(set(data.keys()), expected_keys)

    def test_sales_kpis_zero_when_no_invoices(self):
        calc = self._get_calculator()
        data = calc.get_sales_kpis()
        self.assertEqual(data['total_sales'], 0.0)
        self.assertEqual(data['invoice_count'], 0)

    # ---------- get_inventory_kpis ----------
    def test_inventory_kpis_returns_expected_keys(self):
        calc = self._get_calculator()
        data = calc.get_inventory_kpis()
        expected_keys = {
            'inventory_value', 'turnover_ratio', 'low_stock_count',
            'out_of_stock_count', 'total_products', 'avg_product_value',
        }
        self.assertEqual(set(data.keys()), expected_keys)

    def test_inventory_kpis_no_error_on_empty_db(self):
        """لا يجب أن يرمي خطأ حتى لو لم يكن هناك منتجات"""
        calc = self._get_calculator()
        data = calc.get_inventory_kpis()
        self.assertIsInstance(data['inventory_value'], float)
        self.assertIsInstance(data['total_products'], int)

    # ---------- get_financial_kpis ----------
    def test_financial_kpis_returns_expected_keys(self):
        calc = self._get_calculator()
        data = calc.get_financial_kpis()
        expected_keys = {
            'revenue', 'costs', 'gross_profit', 'profit_margin',
            'receivables', 'payables', 'net_position',
        }
        self.assertEqual(set(data.keys()), expected_keys)

    def test_financial_kpis_profit_margin_zero_when_no_revenue(self):
        calc = self._get_calculator()
        data = calc.get_financial_kpis()
        self.assertEqual(data['profit_margin'], 0)

    # ---------- get_customer_kpis ----------
    def test_customer_kpis_returns_expected_keys(self):
        calc = self._get_calculator()
        data = calc.get_customer_kpis()
        expected_keys = {
            'total_customers', 'active_customers', 'new_customers',
            'repeat_customers', 'repeat_rate', 'avg_customer_value',
        }
        self.assertEqual(set(data.keys()), expected_keys)

    # ---------- get_operational_kpis ----------
    def test_operational_kpis_returns_expected_keys(self):
        calc = self._get_calculator()
        data = calc.get_operational_kpis()
        expected_keys = {
            'avg_processing_hours', 'rejection_rate',
            'employee_productivity', 'active_employees',
        }
        self.assertEqual(set(data.keys()), expected_keys)

    def test_operational_kpis_employee_count_includes_test_user(self):
        calc = self._get_calculator()
        data = calc.get_operational_kpis()
        self.assertGreaterEqual(data['active_employees'], 1)

    # ---------- date range ----------
    def test_custom_date_range(self):
        today = timezone.now().date()
        calc = self._get_calculator(date_range={
            'start': today - timedelta(days=7),
            'end': today,
        })
        data = calc.get_sales_kpis()
        self.assertEqual(data['total_sales'], 0.0)

    # ---------- get_comparison_data ----------
    def test_comparison_data_returns_categories(self):
        calc = self._get_calculator()
        comparison = calc.get_comparison_data()
        self.assertIn('sales', comparison)
        self.assertIn('inventory', comparison)


class CacheOptimizerTest(TestCase):
    """اختبارات محسّن الكاش"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='test_cache_user',
            password='testpass123',
            is_active=True,
            is_staff=True,
        )

    def test_sales_chart_data_no_error(self):
        from dashboard.cache_optimizer import DashboardDataOptimizer
        try:
            data = DashboardDataOptimizer.get_sales_chart_data(self.user, days=30)
            self.assertIn('labels', data)
            self.assertIn('sales', data)
        except Exception as e:
            self.fail(f"get_sales_chart_data raised {type(e).__name__}: {e}")

    def test_kpi_data_no_error(self):
        from dashboard.cache_optimizer import DashboardDataOptimizer
        try:
            data = DashboardDataOptimizer.get_kpi_data(self.user)
            self.assertIn('today_sales', data)
            self.assertIn('month_sales', data)
        except Exception as e:
            self.fail(f"get_kpi_data raised {type(e).__name__}: {e}")

    def test_inventory_chart_data_no_error(self):
        from dashboard.cache_optimizer import DashboardDataOptimizer
        try:
            data = DashboardDataOptimizer.get_inventory_chart_data(self.user)
            self.assertIn('by_category', data)
            self.assertIn('stock_status', data)
        except Exception as e:
            self.fail(f"get_inventory_chart_data raised {type(e).__name__}: {e}")


class DashboardAPITest(TestCase):
    """اختبارات API لوحة المعلومات"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='test_dash_api',
            password='testpass123',
            is_active=True,
            is_staff=True,
        )

    def _get_token(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken.for_user(self.user)
        return str(token.access_token)

    def test_kpis_endpoint_returns_200(self):
        token = self._get_token()
        response = self.client.get(
            '/dashboard-api/api/kpis/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)

    def test_data_endpoint_returns_200(self):
        token = self._get_token()
        response = self.client.get(
            '/dashboard-api/api/data/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)

    def test_daily_profit_endpoint_returns_200(self):
        token = self._get_token()
        response = self.client.get(
            '/core/api/dashboard/daily-profit/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)

    def test_kpis_unauthenticated_returns_401(self):
        response = self.client.get('/dashboard-api/api/kpis/')
        self.assertIn(response.status_code, [401, 403])
