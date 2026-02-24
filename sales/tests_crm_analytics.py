"""
اختبارات نظام التحليلات المتقدم للعملاء
CRM Analytics Tests
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone

from partners.models import Customer, Partner
from sales.models import Invoice, InvoiceItem, FieldVisit
from inventory.models import Product, Location
from hr.models import Employee, Department, JobPosition
from sales.services.crm_analytics import (
	CustomerAnalyticsService,
	SalesPipelineAnalyzer,
	CommissionCalculator,
	LeadConversionTracker
)


class CustomerAnalyticsServiceTests(TestCase):
	"""اختبارات خدمة تحليلات العملاء"""
	
	def setUp(self):
		# إنشاء عميل
		self.partner = Partner.objects.create(
			name="شركة الاختبار",
			email="test@test.com",
			partner_type='customer'
		)
		self.customer = Customer.objects.create(
			partner=self.partner,
			name="شركة الاختبار",
			email="test@test.com"
		)
		
		# إنشاء منتج
		self.product = Product.objects.create(
			sku="TEST-001",
			name="منتج اختبار",
			cost=Decimal('50'),
			price=Decimal('100')
		)
		
		# إنشاء موقع
		self.location = Location.objects.create(
			name="المستودع الرئيسي",
			code="MAIN"
		)
	
	def test_customer_lifetime_value_calculation(self):
		"""اختبار حساب قيمة العميل مدى الحياة"""
		
		# إنشاء فواتير للعميل
		for i in range(5):
			invoice = Invoice.objects.create(
				number=f"INV-{i+1:04d}",
				customer=self.customer,
				date=date.today() - timedelta(days=i*30),
				cached_total=Decimal('1000')
			)
		
		# حساب CLV
		clv = CustomerAnalyticsService.get_customer_lifetime_value(self.customer)
		
		self.assertEqual(clv['total_orders'], 5)
		self.assertEqual(clv['total_revenue'], Decimal('5000'))
		self.assertEqual(clv['average_order_value'], Decimal('1000'))
		self.assertGreater(clv['lifetime_value'], Decimal('0'))
		self.assertGreater(clv['profitability_score'], 0)
	
	def test_rfm_analysis(self):
		"""اختبار تحليل RFM"""
		
		# إنشاء فواتير
		for i in range(3):
			Invoice.objects.create(
				number=f"INV-RFM-{i+1:04d}",
				customer=self.customer,
				date=date.today() - timedelta(days=i*30),
				cached_total=Decimal('5000')
			)
		
		rfm = CustomerAnalyticsService.get_rfm_analysis(self.customer)
		
		self.assertIn('recency_score', rfm)
		self.assertIn('frequency_score', rfm)
		self.assertIn('monetary_score', rfm)
		self.assertIn('rfm_segment', rfm)
		self.assertIn(rfm['rfm_segment'], [
			'champions', 'loyal', 'potential', 'at_risk', 'lost', 'inactive'
		])


class SalesPipelineAnalyzerTests(TestCase):
	"""اختبارات محلل مسار المبيعات"""
	
	def setUp(self):
		# إنشاء قسم ومنصب
		self.department = Department.objects.create(
			name="المبيعات",
			code="SALES"
		)
		self.position = JobPosition.objects.create(
			title="مندوب مبيعات",
			department=self.department
		)
		
		# إنشاء مستخدم وموظف
		self.user = User.objects.create_user(
			username='salesman',
			password='test123'
		)
		self.employee = Employee.objects.create(
			user=self.user,
			employee_id="SALES-001",
			first_name="أحمد",
			last_name="محمد",
			arabic_name="أحمد محمد",
			national_id="1234567890",
			gender='M',
			birth_date=date(1990, 1, 1),
			marital_status='single',
			phone="0500000000",
			email="sales@test.com",
			address="الرياض",
			emergency_contact_name="محمد",
			emergency_contact_phone="0511111111",
			department=self.department,
			position=self.position,
			hire_date=date(2020, 1, 1),
			basic_salary=Decimal('5000')
		)
		
		# إنشاء عميل
		self.customer = Customer.objects.create(
			name="عميل اختبار",
			email="customer@test.com"
		)
	
	def test_pipeline_overview(self):
		"""اختبار نظرة عامة على المسار"""
		
		# إنشاء زيارات
		FieldVisit.objects.create(
			employee=self.employee,
			customer=self.customer,
			visit_date=date.today(),
			outcome='won',
			subject="زيارة ناجحة"
		)
		
		FieldVisit.objects.create(
			employee=self.employee,
			customer=self.customer,
			visit_date=date.today() - timedelta(days=5),
			outcome='lost',
			subject="زيارة فاشلة"
		)
		
		FieldVisit.objects.create(
			employee=self.employee,
			customer=self.customer,
			visit_date=date.today() - timedelta(days=10),
			outcome='follow_up',
			subject="متابعة"
		)
		
		pipeline = SalesPipelineAnalyzer.get_pipeline_overview()
		
		self.assertEqual(pipeline['total_visits'], 3)
		self.assertEqual(pipeline['won_visits'], 1)
		self.assertEqual(pipeline['lost_visits'], 1)
		self.assertEqual(pipeline['follow_up_visits'], 1)
		self.assertGreater(pipeline['conversion_rate'], 0)


class CommissionCalculatorTests(TestCase):
	"""اختبارات حاسب العمولات"""
	
	def setUp(self):
		# إنشاء موظف
		department = Department.objects.create(name="المبيعات", code="SALES")
		position = JobPosition.objects.create(title="مندوب", department=department)
		user = User.objects.create_user(username='emp', password='test')
		
		self.employee = Employee.objects.create(
			user=user,
			employee_id="EMP-001",
			first_name="محمد",
			last_name="أحمد",
			arabic_name="محمد أحمد",
			national_id="9876543210",
			gender='M',
			birth_date=date(1990, 1, 1),
			marital_status='single',
			phone="0500000000",
			email="emp@test.com",
			address="الرياض",
			emergency_contact_name="أحمد",
			emergency_contact_phone="0511111111",
			department=department,
			position=position,
			hire_date=date(2020, 1, 1),
			basic_salary=Decimal('6000')
		)
		
		# إنشاء عميل
		self.customer = Customer.objects.create(
			name="عميل",
			is_key_account=True
		)
		
		# إنشاء منتج وموقع
		self.product = Product.objects.create(
			sku="PROD-001",
			name="منتج",
			cost=Decimal('100'),
			price=Decimal('200')
		)
		self.location = Location.objects.create(name="مستودع", code="WH")
	
	def test_commission_calculation(self):
		"""اختبار حساب العمولة"""
		
		# إنشاء زيارة ناجحة
		visit = FieldVisit.objects.create(
			employee=self.employee,
			customer=self.customer,
			visit_date=date.today(),
			outcome='won'
		)
		
		# إنشاء فاتورة
		invoice = Invoice.objects.create(
			number="INV-COMM-001",
			customer=self.customer,
			date=date.today(),
			cached_total=Decimal('10000')
		)
		
		# حساب العمولة
		period_start = date.today() - timedelta(days=7)
		period_end = date.today()
		
		commission = CommissionCalculator.calculate_sales_commission(
			self.employee,
			period_start,
			period_end
		)
		
		self.assertGreater(commission['total_sales'], Decimal('0'))
		self.assertGreater(commission['total_commission'], Decimal('0'))


class CRMAnalyticsViewsTests(TestCase):
	"""اختبارات واجهات العرض"""
	
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(
			username='admin',
			password='TestPass!999'
		)
		# Disable forced password change so tests can access views without redirect
		try:
			profile = self.user.userprofile
			profile.must_change_password = False
			profile.save(update_fields=['must_change_password'])
		except Exception:
			pass
		self.client.login(username='admin', password='TestPass!999')
		
		self.customer = Customer.objects.create(
			name="عميل اختبار",
			email="test@test.com"
		)
	
	def test_dashboard_view(self):
		"""اختبار لوحة التحكم"""
		
		response = self.client.get(reverse('sales:crm_analytics_dashboard'))
		self.assertEqual(response.status_code, 200)
	
	def test_customer_segmentation_view(self):
		"""اختبار عرض التصنيف"""
		
		response = self.client.get(reverse('sales:customer_segmentation'))
		self.assertEqual(response.status_code, 200)
	
	def test_export_csv(self):
		"""اختبار التصدير"""
		
		response = self.client.get(reverse('sales:export_customers_csv'))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8-sig')


class IntegrationTests(TestCase):
	"""اختبارات التكامل"""
	
	def setUp(self):
		# إعداد كامل
		self.customer = Customer.objects.create(
			name="عميل متكامل",
			email="integration@test.com"
		)
		
		self.product = Product.objects.create(
			sku="INT-001",
			name="منتج",
			cost=Decimal('50'),
			price=Decimal('100')
		)
		
		self.location = Location.objects.create(
			name="مستودع",
			code="WH"
		)
		
		dept = Department.objects.create(name="مبيعات", code="S")
		pos = JobPosition.objects.create(title="مندوب", department=dept)
		user = User.objects.create_user(username='sales', password='test')
		
		self.employee = Employee.objects.create(
			user=user,
			employee_id="INT-001",
			first_name="علي",
			last_name="محمد",
			arabic_name="علي محمد",
			national_id="1111111111",
			gender='M',
			birth_date=date(1990, 1, 1),
			marital_status='single',
			phone="0500000000",
			email="ali@test.com",
			address="جدة",
			emergency_contact_name="محمد",
			emergency_contact_phone="0511111111",
			department=dept,
			position=pos,
			hire_date=date(2020, 1, 1),
			basic_salary=Decimal('5000')
		)
	
	def test_full_sales_cycle(self):
		"""اختبار دورة مبيعات كاملة"""
		
		# 1. زيارة ميدانية
		visit = FieldVisit.objects.create(
			employee=self.employee,
			customer=self.customer,
			visit_date=date.today() - timedelta(days=5),
			outcome='follow_up',
			subject="زيارة أولية"
		)
		
		# 2. متابعة ناجحة
		visit2 = FieldVisit.objects.create(
			employee=self.employee,
			customer=self.customer,
			visit_date=date.today() - timedelta(days=2),
			outcome='won',
			subject="إغلاق ناجح"
		)
		
		# 3. فاتورة
		invoice = Invoice.objects.create(
			number="INT-INV-001",
			customer=self.customer,
			date=date.today(),
			cached_total=Decimal('5000')
		)
		
		# تحليلات
		clv = CustomerAnalyticsService.get_customer_lifetime_value(self.customer)
		rfm = CustomerAnalyticsService.get_rfm_analysis(self.customer)
		journey = LeadConversionTracker.track_lead_journey(self.customer)
		
		# التحققات
		self.assertEqual(clv['total_orders'], 1)
		self.assertEqual(journey['conversion_status'], 'converted')
		self.assertEqual(journey['visits_count'], 2)
		self.assertIsNotNone(journey['days_to_conversion'])
