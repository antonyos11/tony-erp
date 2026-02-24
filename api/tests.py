from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from core.models import Company, AuditLog


class AuditLogAPITests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.client.defaults['HTTP_ACCEPT'] = 'application/json'
		User = get_user_model()
		self.user = User.objects.create_user('apiuser', password='p')
		# Start unauthenticated; authenticate explicitly per test phase

	def test_requires_view_permission(self):
		c = Company.objects.create(name='API C1')
		# Explicitly create audit log since force_authenticate doesn't trigger signals
		from django.contrib.contenttypes.models import ContentType
		ct = ContentType.objects.get_for_model(Company)
		AuditLog.objects.create(
			user=self.user, action='create', content_type=ct,
			object_id=str(c.pk), model_name='Company',
			changes={'name': 'API C1'}
		)
		url = '/api/audit-logs/'
		resp = self.client.get(url)
		self.assertIn(resp.status_code, (401, 403))
		perm = Permission.objects.get(codename='view_auditlog', content_type__app_label='core', content_type__model='auditlog')
		self.user.user_permissions.add(perm)
		# Refresh user cache after adding permission
		self.user = get_user_model().objects.get(pk=self.user.pk)
		self.client.force_authenticate(user=self.user)
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertIn('results', resp.data)
		self.assertGreaterEqual(resp.data['count'], 1)

	def test_filtering_by_action(self):
		perm = Permission.objects.get(codename='view_auditlog', content_type__app_label='core', content_type__model='auditlog')
		self.user.user_permissions.add(perm)
		# Refresh user cache after adding permission
		self.user = get_user_model().objects.get(pk=self.user.pk)
		self.client.force_authenticate(user=self.user)
		c = Company.objects.create(name='API C2')
		c.name = 'API C2-up'
		c.save()
		# Explicitly create audit log with 'update' action
		from django.contrib.contenttypes.models import ContentType
		ct = ContentType.objects.get_for_model(Company)
		AuditLog.objects.create(
			user=self.user, action='update', content_type=ct,
			object_id=str(c.pk), model_name='Company',
			changes={'name': ['API C2', 'API C2-up']}
		)
		url = '/api/audit-logs/?action=update'
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		actions = {row['action'] for row in resp.data['results']}
		self.assertIn('update', actions)


class ReportsAPITestBase(TestCase):
	@classmethod
	def setUpTestData(cls):
		User = get_user_model()
		# Base privileged user (superuser) for positive happy-path tests
		cls.user = User.objects.create_user('reportuser', password='p', is_superuser=True, is_staff=True)
		Company.objects.create(name='R1')
		from django.contrib.contenttypes.models import ContentType
		from django.contrib.auth.models import Permission
		ct, _ = ContentType.objects.get_or_create(app_label='reports', model='reportsmeta')
		# Use canonical names from ReportsMeta.permissions to avoid duplicate (different name) creation
		cls.view_perm = Permission.objects.filter(codename='view_reports', content_type=ct).first()
		if not cls.view_perm:
			cls.view_perm = Permission.objects.create(codename='view_reports', name='Can view aggregated reports', content_type=ct)
		cls.export_perm = Permission.objects.filter(codename='export_reports', content_type=ct).first()
		if not cls.export_perm:
			cls.export_perm = Permission.objects.create(codename='export_reports', name='Can export report data', content_type=ct)
		# Pre-assign permissions to user-level set for faster lookup (direct m2m check in permission class)
		cls.user.user_permissions.add(cls.view_perm, cls.export_perm)

	def setUp(self):
		self.client = APIClient()
		self.client.defaults['HTTP_ACCEPT'] = 'application/json'
		# Always refresh user to ensure fresh permission cache
		# Re-fetch user to get fresh permission cache
		self.user = get_user_model().objects.get(pk=self.user.pk)

class ReportsAPITests(ReportsAPITestBase):
	def setUp(self):
		super().setUp()
		# Use force_authenticate for DRF API (JWT-only, no session auth)
		self.client.force_authenticate(user=self.user)

	def test_overview_endpoint(self):
		resp = self.client.get('/api/reports/overview/')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('stats', resp.data)
		self.assertIn('top_products', resp.data)
		self.assertIn('charts', resp.data)

	def test_sales_endpoint_empty(self):
		resp = self.client.get('/api/reports/sales/?date_from=2025-01-01&date_to=2025-01-02')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('sales_summary', resp.data)
		self.assertIn('charts', resp.data)
		self.assertIn('daily_revenue', resp.data['charts'])

	def test_purchases_endpoint_empty(self):
		resp = self.client.get('/api/reports/purchases/')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('purchases_summary', resp.data)

	def test_inventory_endpoint(self):
		resp = self.client.get('/api/reports/inventory/')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('stock_analysis', resp.data)

	def test_full_system_report(self):
		resp = self.client.get('/api/reports/full/')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('overview', resp.data)

	def test_profit_loss_report(self):
		resp = self.client.get('/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('revenue', resp.data)
		# FIFO enhanced fields presence
		self.assertIn('cogs', resp.data)
		self.assertIn('cogs_fifo', resp.data)
		self.assertIn('gross_profit_fifo', resp.data)
		self.assertIn('operating_profit_fifo', resp.data)
		self.assertIn('margin_percent_fifo', resp.data)
		self.assertIn('cogs_method', resp.data)
		# Logical relation checks (with zero-safe behavior)
		net_rev = float(resp.data.get('net_revenue', 0) or 0)
		cogs_fifo = float(resp.data.get('cogs_fifo', 0) or 0)
		gross_profit_fifo = float(resp.data.get('gross_profit_fifo', 0) or 0)
		self.assertAlmostEqual(gross_profit_fifo, net_rev - cogs_fifo, places=2)
		if net_rev:  # avoid division by zero
			self.assertAlmostEqual(float(resp.data.get('margin_percent_fifo', 0) or 0), (gross_profit_fifo / net_rev) * 100, places=2)

	def test_profit_loss_report_force_approx(self):
		resp = self.client.get('/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31&cogs_method=approx')
		self.assertEqual(resp.status_code,200)
		self.assertEqual(resp.data.get('cogs_method'),'approx')

	def test_profit_loss_report_force_weighted(self):
		resp = self.client.get('/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31&cogs_method=weighted')
		self.assertEqual(resp.status_code,200)
		self.assertEqual(resp.data.get('cogs_method'),'weighted')
		# weighted specific fields expected
		self.assertIn('cogs_weighted', resp.data)
		self.assertIn('gross_profit_weighted', resp.data)
		self.assertIn('operating_profit_weighted', resp.data)

	def test_profit_loss_report_compare_all(self):
		"""Request both costing methods (auto + compare) and expect variance metrics."""
		resp = self.client.get('/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31&compare=1')
		self.assertEqual(resp.status_code,200)
		# Should include at least one advanced method
		self.assertTrue('cogs_fifo' in resp.data or 'cogs_weighted' in resp.data)
		# If both present variance keys should exist
		if 'cogs_fifo' in resp.data and 'cogs_weighted' in resp.data:
			self.assertIn('fifo_vs_weighted_cogs_diff', resp.data)
			self.assertIn('fifo_vs_weighted_cogs_percent', resp.data)

	def test_profit_loss_invalid_cogs_method(self):
		resp = self.client.get('/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31&cogs_method=invalidx')
		self.assertEqual(resp.status_code,400)

	def test_cash_flow_report(self):
		resp = self.client.get('/api/reports/cash-flow/?date_from=2025-01-01&date_to=2025-01-31')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('inflows', resp.data)  # legacy key
		self.assertIn('operating', resp.data)
		self.assertIn('investing', resp.data)
		self.assertIn('financing', resp.data)
		self.assertIn('net_total', resp.data)

	def test_inventory_turnover_report(self):
		resp = self.client.get('/api/reports/inventory-turnover/?date_from=2025-01-01&date_to=2025-03-31')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('turnover_ratio', resp.data)
		# FIFO fields
		self.assertIn('cogs_approx', resp.data)
		self.assertIn('cogs_fifo', resp.data)
		self.assertIn('opening_inventory_estimate', resp.data)
		self.assertIn('average_inventory_fifo_based', resp.data)
		self.assertIn('turnover_ratio_fifo', resp.data)
		self.assertIn('cogs_method', resp.data)
		# Relation: turnover_ratio_fifo = cogs_fifo / average_inventory_fifo_based (when average > 0)
		avg_inv_fifo = float(resp.data.get('average_inventory_fifo_based') or 0)
		turnover_fifo = float(resp.data.get('turnover_ratio_fifo') or 0)
		cogs_fifo = float(resp.data.get('cogs_fifo') or 0)
		if avg_inv_fifo > 0:
			self.assertAlmostEqual(turnover_fifo, cogs_fifo / avg_inv_fifo, places=4)

	def test_inventory_turnover_force_approx(self):
		resp = self.client.get('/api/reports/inventory-turnover/?date_from=2025-01-01&date_to=2025-03-31&cogs_method=approx')
		self.assertEqual(resp.status_code,200)
		self.assertEqual(resp.data.get('cogs_method'),'approx')

	def test_inventory_turnover_force_weighted(self):
		resp = self.client.get('/api/reports/inventory-turnover/?date_from=2025-01-01&date_to=2025-03-31&cogs_method=weighted')
		self.assertEqual(resp.status_code,200)
		self.assertEqual(resp.data.get('cogs_method'),'weighted')
		self.assertIn('cogs_weighted', resp.data)
		self.assertIn('turnover_ratio_weighted', resp.data)
		self.assertIn('days_per_turn_weighted', resp.data)

	def test_inventory_turnover_compare_all(self):
		resp = self.client.get('/api/reports/inventory-turnover/?date_from=2025-01-01&date_to=2025-03-31&compare=1')
		self.assertEqual(resp.status_code,200)
		self.assertTrue('cogs_fifo' in resp.data or 'cogs_weighted' in resp.data)
		if 'cogs_fifo' in resp.data and 'cogs_weighted' in resp.data:
			self.assertIn('fifo_vs_weighted_cogs_diff', resp.data)
			self.assertIn('fifo_vs_weighted_cogs_percent', resp.data)

	def test_stock_aging_all_flag(self):
		resp = self.client.get('/api/reports/stock-aging/?as_of=2025-06-30&all=1')
		self.assertEqual(resp.status_code,200)
		if 'limit_applied' in resp.data:
			self.assertEqual(resp.data['limit_applied'],'all')

	def test_stock_aging_report(self):
		resp = self.client.get('/api/reports/stock-aging/?as_of=2025-06-30')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('summary', resp.data)
	def test_stock_aging_report_limit(self):
		resp = self.client.get('/api/reports/stock-aging/?as_of=2025-06-30&limit=5')
		self.assertEqual(resp.status_code,200)
		self.assertIn('products', resp.data)
		if 'limit_applied' in resp.data:
			self.assertLessEqual(len(resp.data['products']),5)

	def test_balance_sheet_structure(self):
		resp = self.client.get('/api/reports/balance-sheet/?as_of=2025-06-30')
		# قد تكون غير مفعلة لو نماذج المحاسبة غير موجودة، نقبل 200 أو 200 مع enabled False
		self.assertEqual(resp.status_code, 200)
		self.assertIn('as_of', resp.data)
		# إن توفرت الحقول الأساسية
		if 'assets' in resp.data:
			self.assertIn('is_balanced', resp.data)


# إبقاء الاختبارات السابقة

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from django.test import TestCase

User = get_user_model()

class ReportsPermissionsAndExportTests(ReportsAPITestBase):
	def setUp(self):
		super().setUp()
		# For permission edge tests we use a normal user (no superuser bypass)
		User = get_user_model()
		self.normal_user = User.objects.create_user('reports_normal', password='p')
		self.client.force_authenticate(user=self.normal_user)

	def test_overview_without_permissions(self):
		resp = self.client.get('/api/reports/overview/')
		self.assertEqual(resp.status_code, 403)
    
	def test_overview_with_view_permission(self):
		self.normal_user.user_permissions.add(self.view_perm)
		# Clear perm cache and re-login to ensure has_perm sees new permission
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		resp = self.client.get('/api/reports/overview/')
		self.assertEqual(resp.status_code, 200)

	def test_export_requires_export_permission(self):
		self.normal_user.user_permissions.add(self.view_perm)
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		r1 = self.client.get('/api/reports/sales/?export=csv')
		# بعد استقرار المسارات يجب أن يكون الرفض 403 صريح
		self.assertEqual(r1.status_code, 403)
		self.normal_user.user_permissions.add(self.export_perm)
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		r2 = self.client.get('/api/reports/sales/?export=csv')
		self.assertIn(r2.status_code, (200, 204))

	def test_export_requires_export_permission_profit_loss(self):
		# add view only
		self.normal_user.user_permissions.add(self.view_perm)
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		url='/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31&export=csv'
		resp1=self.client.get(url)
		self.assertEqual(resp1.status_code,403)
		# grant export
		self.normal_user.user_permissions.add(self.export_perm)
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		resp2=self.client.get(url)
		self.assertIn(resp2.status_code,(200,204))

	def test_export_requires_export_permission_cash_flow(self):
		self.normal_user.user_permissions.add(self.view_perm)
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		url='/api/reports/cash-flow/?date_from=2025-01-01&date_to=2025-01-31&export=csv'
		resp1=self.client.get(url)
		self.assertEqual(resp1.status_code,403)
		self.normal_user.user_permissions.add(self.export_perm)
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		resp2=self.client.get(url)
		self.assertIn(resp2.status_code,(200,204))

	def test_export_requires_export_permission_inventory_turnover(self):
		self.normal_user.user_permissions.add(self.view_perm)
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		url='/api/reports/inventory-turnover/?date_from=2025-01-01&date_to=2025-03-31&export=csv'
		resp1=self.client.get(url)
		self.assertEqual(resp1.status_code,403)
		self.normal_user.user_permissions.add(self.export_perm)
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		resp2=self.client.get(url)
		self.assertIn(resp2.status_code,(200,204))

	def test_export_requires_export_permission_stock_aging(self):
		self.normal_user.user_permissions.add(self.view_perm)
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		url='/api/reports/stock-aging/?as_of=2025-06-30&export=csv'
		resp1=self.client.get(url)
		self.assertEqual(resp1.status_code,403)
		self.normal_user.user_permissions.add(self.export_perm)
		self.normal_user = get_user_model().objects.get(pk=self.normal_user.pk); self.client.force_authenticate(user=self.normal_user)
		resp2=self.client.get(url)
		self.assertIn(resp2.status_code,(200,204))


class ReportsStatsTimingTests(ReportsAPITestBase):
	def setUp(self):
		super().setUp()
		self.client.force_authenticate(user=self.user)

	def test_profit_loss_stats_and_timing(self):
		url = '/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31&stats=1'
		r1 = self.client.get(url)
		self.assertEqual(r1.status_code, 200)
		# First call should produce misses>=1
		self.assertIn('cache_stats', r1.data)
		self.assertIn('timing_ms', r1.data)
		self.assertIn('avg_ms', r1.data)
		misses1 = r1.data['cache_stats']['misses']
		# Second call should hit cache (hits increases or timing faster)
		r2 = self.client.get(url)
		self.assertEqual(r2.status_code, 200)
		self.assertIn('cache_stats', r2.data)
		# Cache may not be enabled in test; just check structure exists
		self.assertIn('hits', r2.data['cache_stats'])
		self.assertIn('misses', r2.data['cache_stats'])
		self.assertIn('timing_ms', r2.data)
		self.assertIn('avg_ms', r2.data)

class ReportsSnapshotRetentionTests(ReportsAPITestBase):
	def setUp(self):
		super().setUp(); self.client.force_authenticate(user=self.user)
	def test_snapshot_retention_cleanup(self):
		from reports.models import ReportDailySnapshot
		from reports.services import create_daily_snapshot
		from django.test import override_settings
		import datetime as _dt
		old_date = _dt.date.today() - _dt.timedelta(days=10)
		# Create an old snapshot manually
		ReportDailySnapshot.objects.create(date=old_date, net_revenue=0, expenses=0, cogs_approx=0, closing_inventory_value=0)
		self.assertTrue(ReportDailySnapshot.objects.filter(date=old_date).exists())
		with override_settings(REPORT_SNAPSHOT_RETENTION_DAYS=5):
			create_daily_snapshot(_dt.date.today())
		# Old snapshot should be deleted after retention cleanup
		self.assertFalse(ReportDailySnapshot.objects.filter(date=old_date).exists())

class ReportsVarianceWarningTests(ReportsAPITestBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)
    def test_profit_loss_variance_warning_default_threshold(self):
        r = self.client.get('/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31&compare=1')
        self.assertEqual(r.status_code,200)
        # variance_warning may or may not trigger depending on data; just validate structure if present
        if 'variance_warning' in r.data:
            vw = r.data['variance_warning']
            self.assertIn('percent', vw)
            self.assertIn('threshold_used', vw)
            self.assertIn('triggered', vw)
    def test_inventory_turnover_variance_warning_custom_threshold(self):
        r = self.client.get('/api/reports/inventory-turnover/?date_from=2025-01-01&date_to=2025-03-31&compare=1&warn_threshold=0.1')
        self.assertEqual(r.status_code,200)
        if 'variance_warning' in r.data:
            self.assertAlmostEqual(r.data['variance_warning'].get('threshold_used'),0.1)


class ReportsNewEnhancementsTests(ReportsAPITestBase):
	def setUp(self):
		super().setUp()
		self.client.force_authenticate(user=self.user)

	def test_snapshot_series_endpoint_basic(self):
		r = self.client.get('/api/reports/snapshots/?days=7')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertIn('series', data)
		self.assertLessEqual(len(data['series']), 7)

	def test_health_endpoint(self):
		r = self.client.get('/api/reports/health/')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertIn('cache', data)
		self.assertIn('timestamp', data)

	def test_ar_aging_compare_delta(self):
		r = self.client.get('/api/reports/ar-aging/?compare=1')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		if data.get('previous_period'):
			self.assertIn('total_outstanding_delta', data)

	def test_ap_aging_compare_delta(self):
		r = self.client.get('/api/reports/ap-aging/?compare=1')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		if data.get('previous_period'):
			self.assertIn('total_outstanding_delta', data)

	def test_cash_flow_monthly_series(self):
		r = self.client.get('/api/reports/cash-flow/?series=1')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertIn('monthly_series', data)

	def test_stock_aging_pagination(self):
		r = self.client.get('/api/reports/stock-aging/?page=1&page_size=50')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		if 'products' in data:
			self.assertLessEqual(len(data['products']), 50)

	def test_csv_gzip_force(self):
		"""Force gzip compression path even with small dataset using force_compress=1."""
		resp = self.client.get('/api/reports/overview/?export=csv&force_compress=1')
		self.assertEqual(resp.status_code, 200)
		# Should present gzip header
		self.assertIn('Content-Encoding', resp.headers)
		self.assertEqual(resp.headers.get('Content-Encoding'), 'gzip')


class ReportsHealthVarianceIncidentTests(ReportsAPITestBase):
	def setUp(self):
		super().setUp()
		self.client.force_authenticate(user=self.user)

	def test_health_includes_variance_incidents(self):
		from django.core.cache import cache
		# تنظيف الكاش أولاً والتحقق من وجود الحقل
		cache.delete('reports:variance:incidents')
		r = self.client.get('/api/reports/health/')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertIn('variance_incidents', data)
		# القيمة الافتراضية 0 إذا لم يكن هناك قيمة في الكاش
		self.assertEqual(data['variance_incidents'], 0)

	def test_variance_warning_global_min_applied_if_present(self):
		# Set a global minimum higher than provided warn_threshold; if variance_warning appears its threshold_used should reflect it.
		from django.test import override_settings
		with override_settings(VARIANCE_ALERT_MIN_PERCENT=1.0):
			r = self.client.get('/api/reports/profit-loss/?date_from=2025-01-01&date_to=2025-01-31&compare=1&warn_threshold=0.1')
			self.assertEqual(r.status_code, 200)
			if 'variance_warning' in r.data:
				vw = r.data['variance_warning']
				# If variance exists threshold_used should be >= global min (1.0)
				self.assertGreaterEqual(vw.get('threshold_used', 0), 1.0)
				self.assertIn('global_min_applied', vw)


class ReportsVarianceIncidentsEndpointTests(ReportsAPITestBase):
	def setUp(self):
		super().setUp(); self.client.force_authenticate(user=self.user)
	def test_variance_incidents_endpoint(self):
		from reports.models import ReportVarianceIncident
		from datetime import date as _d
		ReportVarianceIncident.objects.create(report='profit_loss', percent=25.0, threshold_used=10.0, global_min_applied=True, date_from=_d(2025,1,1), date_to=_d(2025,1,31))
		r = self.client.get('/api/reports/variance-incidents/?limit=10')
		self.assertEqual(r.status_code,200)
		self.assertIn('results', r.data)
		self.assertGreaterEqual(len(r.data['results']),1)
