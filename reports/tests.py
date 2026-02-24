from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, ContentType
from datetime import date, timedelta
from .services import get_overview_report, get_sales_report, get_inventory_report, get_purchases_report, parse_date


class ReportServicesTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.user = User.objects.create_user('svc', password='p')
		ct, _ = ContentType.objects.get_or_create(app_label='reports', model='reportsmeta')
		Permission.objects.get_or_create(codename='view_reports', name='Can view aggregated reports', content_type=ct)
		Permission.objects.get_or_create(codename='export_reports', name='Can export report data', content_type=ct)

	def test_overview_structure(self):
		data = get_overview_report()
		self.assertIn('stats', data)
		self.assertIn('charts', data)

	def test_sales_empty_range(self):
		d1 = date.today() - timedelta(days=1)
		d2 = date.today()
		data = get_sales_report(d1, d2)
		self.assertIn('sales_summary', data)
		self.assertIn('charts', data)

	def test_inventory_basic(self):
		data = get_inventory_report()
		self.assertIn('stock_analysis', data)

	def test_purchases_empty(self):
		d1 = date.today() - timedelta(days=7)
		d2 = date.today()
		data = get_purchases_report(d1, d2)
		self.assertIn('purchases_summary', data)

	def test_parse_date(self):
		default = date.today()
		self.assertEqual(parse_date('', default), default)
		self.assertEqual(parse_date('2030-01-01', default).year, 2030)
