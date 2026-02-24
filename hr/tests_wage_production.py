"""
اختبارات نظام تكامل الأجور مع الإنتاج
Wage-Production Integration Tests
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, timedelta, datetime
from decimal import Decimal
from django.utils import timezone

from hr.models import Employee, Department, JobPosition, Payroll
from production.models import Product, ProductionOrder, BillOfMaterials, ProductionStage
from inventory.models import Location
from hr.services.wage_production_integration import (
	ProductionWageCalculator,
	ProductionLaborCostTracker,
	EmployeeProductivityAnalyzer,
	WagePayrollIntegrator
)


class ProductionWageCalculatorTests(TestCase):
	"""اختبارات حاسب الأجور بالقطعة"""
	
	def setUp(self):
		self.user = User.objects.create_user(
			username='testuser',
			password='testpass'
		)
		
		self.department = Department.objects.create(
			name="قسم الإنتاج",
			code="PROD"
		)
		
		self.position = JobPosition.objects.create(
			title="عامل إنتاج",
			department=self.department
		)
		
		self.employee = Employee.objects.create(
			user=self.user,
			employee_id="EMP-001",
			first_name="أحمد",
			last_name="محمد",
			arabic_name="أحمد محمد",
			national_id="1234567890",
			gender='M',
			birth_date=date(1990, 1, 1),
			marital_status='single',
			phone="0500000000",
			email="ahmed@test.com",
			address="الرياض",
			emergency_contact_name="محمد",
			emergency_contact_phone="0511111111",
			department=self.department,
			position=self.position,
			hire_date=date(2020, 1, 1),
			basic_salary=Decimal('5000'),
			housing_allowance=Decimal('1000'),
			transportation_allowance=Decimal('500')
		)
		
		from inventory.models import Product
		self.product = Product.objects.create(
			sku="PROD-001",
			name="Test Product",
			cost=Decimal('10'),
			price=Decimal('20')
		)
	
	def test_calculate_piece_rate_wage_basic(self):
		"""اختبار أساسي لحساب أجر القطعة"""
		
		production_records = [
			{
				'product': self.product,
				'quantity': 100,
				'date': date.today()
			},
			{
				'product': self.product,
				'quantity': 50,
				'date': date.today()
			}
		]
		
		piece_rate_settings = {
			'default_rate': Decimal('2.00'),
			'product_rates': {},
			'stage_multipliers': {}
		}
		
		result = ProductionWageCalculator.calculate_piece_rate_wage(
			self.employee,
			production_records,
			piece_rate_settings
		)
		
		self.assertEqual(result['total_pieces'], 150)
		self.assertEqual(result['total_wage'], Decimal('300.00'))  # 150 × 2
		self.assertEqual(len(result['breakdown']), 2)
	
	def test_piece_rate_with_custom_product_rate(self):
		"""اختبار بأسعار مخصصة للمنتجات"""
		
		production_records = [
			{
				'product': self.product,
				'quantity': 100,
				'date': date.today()
			}
		]
		
		piece_rate_settings = {
			'default_rate': Decimal('2.00'),
			'product_rates': {
				self.product.id: Decimal('3.00')  # سعر مخصص
			},
			'stage_multipliers': {}
		}
		
		result = ProductionWageCalculator.calculate_piece_rate_wage(
			self.employee,
			production_records,
			piece_rate_settings
		)
		
		self.assertEqual(result['total_wage'], Decimal('300.00'))  # 100 × 3


class ProductivityBonusTests(TestCase):
	"""اختبارات مكافأة الإنتاجية"""
	
	def setUp(self):
		self.user = User.objects.create_user(
			username='testuser',
			password='testpass'
		)
		
		self.department = Department.objects.create(
			name="قسم الإنتاج",
			code="PROD"
		)
		
		self.position = JobPosition.objects.create(
			title="عامل إنتاج",
			department=self.department
		)
		
		self.employee = Employee.objects.create(
			user=self.user,
			employee_id="EMP-001",
			first_name="أحمد",
			last_name="محمد",
			arabic_name="أحمد محمد",
			national_id="1234567890",
			gender='M',
			birth_date=date(1990, 1, 1),
			marital_status='single',
			phone="0500000000",
			email="ahmed@test.com",
			address="الرياض",
			emergency_contact_name="محمد",
			emergency_contact_phone="0511111111",
			department=self.department,
			position=self.position,
			hire_date=date(2020, 1, 1),
			basic_salary=Decimal('5000')
		)
	
	def test_productivity_bonus_structure(self):
		"""اختبار هيكل مكافأة الإنتاجية"""
		
		bonus_structure = {
			'quantity_thresholds': [
				{'min': 100, 'max': 120, 'bonus_pct': 5},
				{'min': 120, 'bonus_pct': 10}
			],
			'quality_bonus': {
				'scrap_rate_max': 0.02,
				'bonus_amount': Decimal('500')
			},
			'timeliness_bonus': {
				'on_time_pct_min': 0.95,
				'bonus_amount': Decimal('300')
			}
		}
		
		period_start = date.today() - timedelta(days=30)
		period_end = date.today()
		
		result = ProductionWageCalculator.calculate_productivity_bonus(
			self.employee,
			period_start,
			period_end,
			target_units=100,
			bonus_structure=bonus_structure
		)
		
		self.assertIn('bonuses', result)
		self.assertIn('production_stats', result)


class EmployeeProductivityAnalyzerTests(TestCase):
	"""اختبارات محلل الإنتاجية"""
	
	def setUp(self):
		self.user = User.objects.create_user(
			username='testuser',
			password='testpass'
		)
		
		self.department = Department.objects.create(
			name="قسم الإنتاج",
			code="PROD"
		)
		
		self.position = JobPosition.objects.create(
			title="عامل إنتاج",
			department=self.department
		)
		
		self.employee = Employee.objects.create(
			user=self.user,
			employee_id="EMP-001",
			first_name="أحمد",
			last_name="محمد",
			arabic_name="أحمد محمد",
			national_id="1234567890",
			gender='M',
			birth_date=date(1990, 1, 1),
			marital_status='single',
			phone="0500000000",
			email="ahmed@test.com",
			address="الرياض",
			emergency_contact_name="محمد",
			emergency_contact_phone="0511111111",
			department=self.department,
			position=self.position,
			hire_date=date(2020, 1, 1),
			basic_salary=Decimal('5000')
		)
	
	def test_calculate_productivity_basic(self):
		"""اختبار أساسي لحساب الإنتاجية"""
		
		period_start = date.today() - timedelta(days=30)
		period_end = date.today()
		
		result = EmployeeProductivityAnalyzer.calculate_employee_productivity(
			self.employee,
			period_start,
			period_end
		)
		
		self.assertIn('units_per_hour', result)
		self.assertIn('quality_rate', result)
		self.assertIn('efficiency_score', result)
		self.assertIn('classification', result)
		self.assertIn(result['classification'], ['excellent', 'good', 'average', 'poor'])


class WagePayrollIntegratorTests(TestCase):
	"""اختبارات مدمج الأجور مع الرواتب"""
	
	def setUp(self):
		self.user = User.objects.create_user(
			username='testuser',
			password='testpass'
		)
		
		self.department = Department.objects.create(
			name="قسم الإنتاج",
			code="PROD"
		)
		
		self.position = JobPosition.objects.create(
			title="عامل إنتاج",
			department=self.department
		)
		
		self.employee = Employee.objects.create(
			user=self.user,
			employee_id="EMP-001",
			first_name="أحمد",
			last_name="محمد",
			arabic_name="أحمد محمد",
			national_id="1234567890",
			gender='M',
			birth_date=date(1990, 1, 1),
			marital_status='single',
			phone="0500000000",
			email="ahmed@test.com",
			address="الرياض",
			emergency_contact_name="محمد",
			emergency_contact_phone="0511111111",
			department=self.department,
			position=self.position,
			hire_date=date(2020, 1, 1),
			basic_salary=Decimal('5000'),
			housing_allowance=Decimal('1000'),
			transportation_allowance=Decimal('500')
		)
	
	def test_generate_payroll_salary_type(self):
		"""اختبار إنشاء كشف راتب - نوع راتب ثابت"""
		
		period_start = date(2025, 1, 1)
		period_end = date(2025, 1, 31)
		
		result = WagePayrollIntegrator.generate_payroll_from_production(
			self.employee,
			period_start,
			period_end,
			wage_type='salary'
		)
		
		self.assertGreater(result['basic_salary'], Decimal('0'))
		self.assertEqual(result['piece_rate_wage'], Decimal('0'))
		self.assertIn('net_salary', result)
	
	def test_generate_payroll_mixed_type(self):
		"""اختبار إنشاء كشف راتب - نوع مختلط"""
		
		period_start = date(2025, 1, 1)
		period_end = date(2025, 1, 31)
		
		result = WagePayrollIntegrator.generate_payroll_from_production(
			self.employee,
			period_start,
			period_end,
			wage_type='mixed'
		)
		
		self.assertGreater(result['basic_salary'], Decimal('0'))
		self.assertIn('piece_rate_wage', result)
		self.assertIn('productivity_bonus', result)


class WageProductionViewsTests(TestCase):
	"""اختبارات واجهات العرض"""
	
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_superuser(
			username='testuser',
			password='testpass',
			email='test@example.com'
		)
		
		self.department = Department.objects.create(
			name="قسم الإنتاج",
			code="PROD"
		)
		
		self.position = JobPosition.objects.create(
			title="عامل إنتاج",
			department=self.department
		)
		
		self.employee = Employee.objects.create(
			user=self.user,
			employee_id="EMP-001",
			first_name="أحمد",
			last_name="محمد",
			arabic_name="أحمد محمد",
			national_id="1234567890",
			gender='M',
			birth_date=date(1990, 1, 1),
			marital_status='single',
			phone="0500000000",
			email="ahmed@test.com",
			address="الرياض",
			emergency_contact_name="محمد",
			emergency_contact_phone="0511111111",
			department=self.department,
			position=self.position,
			hire_date=date(2020, 1, 1),
			basic_salary=Decimal('5000')
		)
	
	def test_dashboard_view(self):
		"""اختبار لوحة التحكم"""
		
		self.client.login(username='testuser', password='testpass')
		response = self.client.get(reverse('hr:wage_production_dashboard'))
		
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'تكامل الأجور')
	
	def test_productivity_ranking_view(self):
		"""اختبار ترتيب الإنتاجية"""
		
		self.client.login(username='testuser', password='testpass')
		response = self.client.get(reverse('hr:productivity_ranking'))
		
		self.assertEqual(response.status_code, 200)
	
	def test_export_productivity_csv(self):
		"""اختبار تصدير CSV"""
		
		self.client.login(username='testuser', password='testpass')
		response = self.client.get(reverse('hr:export_productivity_csv'))
		
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8-sig')


class IntegrationTests(TestCase):
	"""اختبارات التكامل الشاملة"""
	
	def setUp(self):
		self.user = User.objects.create_user(
			username='admin',
			password='adminpass'
		)
		
		self.department = Department.objects.create(
			name="قسم الإنتاج",
			code="PROD"
		)
		
		self.position = JobPosition.objects.create(
			title="مشرف إنتاج",
			department=self.department
		)
		
		self.employee = Employee.objects.create(
			user=self.user,
			employee_id="SUP-001",
			first_name="محمد",
			last_name="أحمد",
			arabic_name="محمد أحمد",
			national_id="9876543210",
			gender='M',
			birth_date=date(1985, 1, 1),
			marital_status='married',
			phone="0500000000",
			email="mohammed@test.com",
			address="جدة",
			emergency_contact_name="أحمد",
			emergency_contact_phone="0511111111",
			department=self.department,
			position=self.position,
			hire_date=date(2018, 1, 1),
			basic_salary=Decimal('8000'),
			housing_allowance=Decimal('2000')
		)
	
	def test_full_wage_calculation_workflow(self):
		"""اختبار تدفق حساب الأجور الكامل"""
		
		# 1. حساب الإنتاجية
		period_start = date.today() - timedelta(days=30)
		period_end = date.today()
		
		productivity = EmployeeProductivityAnalyzer.calculate_employee_productivity(
			self.employee,
			period_start,
			period_end
		)
		
		self.assertIsInstance(productivity, dict)
		
		# 2. حساب المكافآت
		bonus = ProductionWageCalculator.calculate_productivity_bonus(
			self.employee,
			period_start,
			period_end,
			target_units=500
		)
		
		self.assertIn('bonuses', bonus)
		
		# 3. إنشاء كشف راتب
		payroll_data = WagePayrollIntegrator.generate_payroll_from_production(
			self.employee,
			period_start,
			period_end,
			wage_type='mixed'
		)
		
		self.assertGreater(payroll_data['net_salary'], Decimal('0'))
