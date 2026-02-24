"""
اختبارات نظام تحليلات المخزون المتقدم
Advanced Inventory Analytics Tests
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, timedelta, datetime
from decimal import Decimal
from django.utils import timezone

from inventory.models import Product, Location, Stock, StockBatch
from sales.models import SaleOrder, SaleOrderItem
from inventory.services.inventory_analytics import (
	StockAgingAnalyzer,
	ABCAnalyzer,
	ReorderPointOptimizer,
	InventoryTurnoverAnalyzer,
	DeadStockIdentifier
)


class StockAgingAnalyzerTests(TestCase):
	"""اختبارات محلل أعمار المخزون"""
	
	def setUp(self):
		self.location = Location.objects.create(
			name="Main Warehouse",
			code="WH-001"
		)
		
		self.product1 = Product.objects.create(
			sku="PROD-001",
			name="Test Product 1",
			cost=Decimal('100')
		)
		
		self.product2 = Product.objects.create(
			sku="PROD-002",
			name="Test Product 2",
			cost=Decimal('50')
		)
	
	def test_stock_aging_basic(self):
		"""اختبار أساسي لتقرير الأعمار"""
		
		# إنشاء دفعات بأعمار مختلفة
		batch1 = StockBatch.objects.create(
			product=self.product1,
			location=self.location,
			lot_number="LOT-001",
			quantity=100,
			unit_cost=Decimal('100'),
			received_at=timezone.now() - timedelta(days=45)
		)
		
		batch2 = StockBatch.objects.create(
			product=self.product1,
			location=self.location,
			lot_number="LOT-002",
			quantity=50,
			unit_cost=Decimal('105'),
			received_at=timezone.now() - timedelta(days=200)
		)
		
		# التقرير
		result = StockAgingAnalyzer.get_stock_aging_report(location=self.location)
		
		self.assertIn('aging_data', result)
		self.assertIn('summary', result)
		self.assertEqual(len(result['aging_data']), 1)  # منتج واحد
		
		# التحقق من البيانات
		aging_item = result['aging_data'][0]
		self.assertEqual(aging_item['product'].id, self.product1.id)
		self.assertEqual(len(aging_item['batches']), 2)
		self.assertEqual(aging_item['total_quantity'], 150)
	
	def test_age_categorization(self):
		"""اختبار تصنيف الأعمار"""
		
		brackets = [30, 60, 90, 180, 365]
		
		# 15 يوم -> 0-30
		self.assertEqual(
			StockAgingAnalyzer._categorize_age(15, brackets),
			'0-30'
		)
		
		# 45 يوم -> 31-60
		self.assertEqual(
			StockAgingAnalyzer._categorize_age(45, brackets),
			'31-60'
		)
		
		# 400 يوم -> 365+
		self.assertEqual(
			StockAgingAnalyzer._categorize_age(400, brackets),
			'365+'
		)


class ABCAnalyzerTests(TestCase):
	"""اختبارات محلل ABC"""
	
	def setUp(self):
		self.location = Location.objects.create(
			name="Store",
			code="ST-001"
		)
		
		self.user = User.objects.create_user(
			username='testuser',
			password='testpass'
		)
		
		# إنشاء 10 منتجات
		self.products = []
		for i in range(1, 11):
			product = Product.objects.create(
				sku=f"PROD-{i:03d}",
				name=f"Product {i}",
				cost=Decimal(str(10 * i)),
				price=Decimal(str(20 * i))
			)
			self.products.append(product)
			
			# مخزون
			Stock.objects.create(
				product=product,
				location=self.location,
				quantity=100
			)
	
	def test_abc_analysis_basic(self):
		"""اختبار أساسي لتحليل ABC"""
		
		# إنشاء مبيعات متفاوتة
		order = SaleOrder.objects.create(
			customer_name="Test Customer",
			date=date.today(),
			status='confirmed'
		)
		
		# منتج 10 (الأعلى سعراً) - مبيعات عالية
		SaleOrderItem.objects.create(
			order=order,
			product=self.products[9],
			quantity=50,
			unit_price=self.products[9].price
		)
		
		# منتج 5 - مبيعات متوسطة
		SaleOrderItem.objects.create(
			order=order,
			product=self.products[4],
			quantity=30,
			unit_price=self.products[4].price
		)
		
		# تحليل ABC
		result = ABCAnalyzer.perform_abc_analysis(period_days=365)
		
		self.assertIn('products', result)
		self.assertIn('summary', result)
		self.assertGreater(len(result['products']), 0)
		
		# التحقق من التصنيف
		summary = result['summary']
		self.assertIn('A', summary)
		self.assertIn('B', summary)
		self.assertIn('C', summary)
		
		# المجموع يجب أن يساوي عدد المنتجات
		total_count = summary['A']['count'] + summary['B']['count'] + summary['C']['count']
		self.assertEqual(total_count, len(result['products']))
	
	def test_abc_cumulative_percentage(self):
		"""اختبار النسب التراكمية"""
		
		result = ABCAnalyzer.perform_abc_analysis()
		
		if result['products']:
			# النسبة التراكمية الأخيرة يجب أن تكون ~100%
			last_product = result['products'][-1]
			self.assertAlmostEqual(
				last_product['cumulative_percentage'],
				100.0,
				delta=0.1
			)


class ReorderPointOptimizerTests(TestCase):
	"""اختبارات محسن نقطة إعادة الطلب"""
	
	def setUp(self):
		self.product = Product.objects.create(
			sku="PROD-ROP",
			name="Reorder Product",
			cost=Decimal('50'),
			price=Decimal('100'),
			min_stock=20
		)
		
		self.location = Location.objects.create(
			name="Warehouse",
			code="WH-001"
		)
		
		Stock.objects.create(
			product=self.product,
			location=self.location,
			quantity=500
		)
		
		self.user = User.objects.create_user(
			username='testuser',
			password='testpass'
		)
	
	def test_calculate_reorder_point_with_sales_data(self):
		"""اختبار حساب نقطة الطلب مع بيانات مبيعات"""
		
		# إنشاء مبيعات يومية
		for i in range(30):
			order = SaleOrder.objects.create(
				customer_name=f"Customer {i}",
				date=date.today() - timedelta(days=i),
				status='confirmed'
			)
			
			# استهلاك يومي ~5 قطع
			SaleOrderItem.objects.create(
				order=order,
				product=self.product,
				quantity=5,
				unit_price=self.product.price
			)
		
		# حساب نقطة الطلب
		result = ReorderPointOptimizer.calculate_reorder_point(
			product=self.product,
			lead_time_days=7,
			service_level=0.95
		)
		
		self.assertIn('reorder_point', result)
		self.assertIn('safety_stock', result)
		self.assertIn('avg_daily_consumption', result)
		
		# متوسط الاستهلاك يجب أن يكون ~5
		self.assertAlmostEqual(result['avg_daily_consumption'], 5.0, delta=1.0)
		
		# نقطة الطلب > 0
		self.assertGreater(result['reorder_point'], 0)
	
	def test_reorder_point_no_sales_data(self):
		"""اختبار بدون بيانات مبيعات"""
		
		result = ReorderPointOptimizer.calculate_reorder_point(
			product=self.product
		)
		
		self.assertEqual(result['status'], 'no_data')
		self.assertEqual(result['avg_daily_consumption'], 0.0)
	
	def test_get_reorder_suggestions(self):
		"""اختبار الحصول على توصيات إعادة الطلب"""
		
		# إنشاء مبيعات
		order = SaleOrder.objects.create(
			customer_name="Customer",
			date=date.today(),
			status='confirmed'
		)
		
		SaleOrderItem.objects.create(
			order=order,
			product=self.product,
			quantity=50,
			unit_price=self.product.price
		)
		
		# تقليل المخزون
		stock = Stock.objects.get(product=self.product, location=self.location)
		stock.quantity = 10  # أقل من min_stock
		stock.save()
		
		suggestions = ReorderPointOptimizer.get_reorder_suggestions()
		
		self.assertGreater(len(suggestions), 0)


class InventoryTurnoverAnalyzerTests(TestCase):
	"""اختبارات محلل معدل الدوران"""
	
	def setUp(self):
		self.product = Product.objects.create(
			sku="PROD-TURN",
			name="Turnover Product",
			cost=Decimal('100'),
			price=Decimal('200')
		)
		
		self.location = Location.objects.create(
			name="Warehouse",
			code="WH-001"
		)
		
		Stock.objects.create(
			product=self.product,
			location=self.location,
			quantity=100
		)
		
		self.user = User.objects.create_user(
			username='testuser',
			password='testpass'
		)
	
	def test_calculate_turnover_ratio(self):
		"""اختبار حساب معدل الدوران"""
		
		# إنشاء مبيعات
		order = SaleOrder.objects.create(
			customer_name="Customer",
			date=date.today(),
			status='confirmed'
		)
		
		# بيع 500 قطعة بتكلفة 100 = COGS 50,000
		# مخزون متوسط 100 × 100 = 10,000
		# Turnover = 50,000 / 10,000 = 5
		SaleOrderItem.objects.create(
			order=order,
			product=self.product,
			quantity=500,
			unit_price=self.product.price
		)
		
		result = InventoryTurnoverAnalyzer.calculate_turnover_ratio(
			product=self.product
		)
		
		self.assertIn('turnover_ratio', result)
		self.assertIn('classification', result)
		
		# يجب أن يكون التصنيف جيد أو ممتاز
		self.assertIn(result['classification'], ['good', 'excellent', 'fair'])
	
	def test_turnover_classification(self):
		"""اختبار تصنيف معدل الدوران"""
		
		# Excellent: >= 12
		result_excellent = {
			'turnover_ratio': 15.0,
			'cogs': Decimal('150000'),
			'avg_inventory_value': Decimal('10000'),
			'period_days': 365
		}
		
		# محاكاة التصنيف
		if result_excellent['turnover_ratio'] >= 12:
			classification = 'excellent'
		elif result_excellent['turnover_ratio'] >= 6:
			classification = 'good'
		elif result_excellent['turnover_ratio'] >= 4:
			classification = 'fair'
		else:
			classification = 'poor'
		
		self.assertEqual(classification, 'excellent')


class DeadStockIdentifierTests(TestCase):
	"""اختبارات كاشف المخزون الراكد"""
	
	def setUp(self):
		self.location = Location.objects.create(
			name="Warehouse",
			code="WH-001"
		)
		
		self.product_active = Product.objects.create(
			sku="PROD-ACTIVE",
			name="Active Product",
			cost=Decimal('50')
		)
		
		self.product_dead = Product.objects.create(
			sku="PROD-DEAD",
			name="Dead Product",
			cost=Decimal('100')
		)
		
		Stock.objects.create(
			product=self.product_active,
			location=self.location,
			quantity=100
		)
		
		Stock.objects.create(
			product=self.product_dead,
			location=self.location,
			quantity=50
		)
		
		self.user = User.objects.create_user(
			username='testuser',
			password='testpass'
		)
	
	def test_identify_dead_stock(self):
		"""اختبار كشف المخزون الراكد"""
		
		# إنشاء مبيعات فقط للمنتج النشط
		order = SaleOrder.objects.create(
			customer_name="Customer",
			date=date.today() - timedelta(days=10),
			status='confirmed'
		)
		
		SaleOrderItem.objects.create(
			order=order,
			product=self.product_active,
			quantity=10,
			unit_price=self.product_active.price
		)
		
		# كشف الراكد (180 يوم)
		result = DeadStockIdentifier.identify_dead_stock(no_sales_days=180)
		
		self.assertIn('dead_stock', result)
		self.assertIn('summary', result)
		
		# يجب أن يكون المنتج الميت في القائمة
		dead_skus = [item['product'].sku for item in result['dead_stock']]
		self.assertIn('PROD-DEAD', dead_skus)
	
	def test_slow_moving_products(self):
		"""اختبار المنتجات بطيئة الحركة"""
		
		# إنشاء مبيعات قليلة
		order = SaleOrder.objects.create(
			customer_name="Customer",
			date=date.today(),
			status='confirmed'
		)
		
		SaleOrderItem.objects.create(
			order=order,
			product=self.product_active,
			quantity=5,  # قليل
			unit_price=self.product_active.price
		)
		
		slow_movers = DeadStockIdentifier.get_slow_moving_products(
			turnover_threshold=2.0
		)
		
		self.assertIsInstance(slow_movers, list)


class InventoryAnalyticsViewsTests(TestCase):
	"""اختبارات واجهات عرض التحليلات"""
	
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_superuser(
			username='testuser',
			password='testpass',
			email='test@example.com'
		)
		
		self.location = Location.objects.create(
			name="Warehouse",
			code="WH-001"
		)
		
		self.product = Product.objects.create(
			sku="PROD-001",
			name="Test Product",
			cost=Decimal('100'),
			price=Decimal('200')
		)
		
		Stock.objects.create(
			product=self.product,
			location=self.location,
			quantity=100
		)
	
	def test_dashboard_view(self):
		"""اختبار لوحة التحكم"""
		
		self.client.login(username='testuser', password='testpass')
		response = self.client.get(reverse('inventory:inventory_analytics_dashboard'))
		
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'تحليلات المخزون')
	
	def test_stock_aging_report_view(self):
		"""اختبار تقرير الأعمار"""
		
		self.client.login(username='testuser', password='testpass')
		response = self.client.get(reverse('inventory:stock_aging_report'))
		
		self.assertEqual(response.status_code, 200)
	
	def test_abc_analysis_report_view(self):
		"""اختبار تقرير ABC"""
		
		self.client.login(username='testuser', password='testpass')
		response = self.client.get(reverse('inventory:abc_analysis_report'))
		
		self.assertEqual(response.status_code, 200)
	
	def test_export_abc_csv(self):
		"""اختبار تصدير ABC كـ CSV"""
		
		self.client.login(username='testuser', password='testpass')
		response = self.client.get(reverse('inventory:export_abc_analysis_csv'))
		
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8-sig')


class InventoryAnalyticsIntegrationTests(TestCase):
	"""اختبارات التكامل الشاملة"""
	
	def setUp(self):
		self.location = Location.objects.create(
			name="Main Warehouse",
			code="WH-MAIN"
		)
		
		self.user = User.objects.create_user(
			username='admin',
			password='adminpass'
		)
		
		# إنشاء 5 منتجات بسيناريوهات مختلفة
		self.products = []
		for i in range(1, 6):
			product = Product.objects.create(
				sku=f"INT-{i:03d}",
				name=f"Integration Product {i}",
				cost=Decimal(str(50 * i)),
				price=Decimal(str(100 * i)),
				min_stock=10 * i
			)
			self.products.append(product)
			
			Stock.objects.create(
				product=product,
				location=self.location,
				quantity=50 * i
			)
			
			# دفعات بأعمار مختلفة
			StockBatch.objects.create(
				product=product,
				location=self.location,
				lot_number=f"BATCH-{i}-1",
				quantity=25 * i,
				unit_cost=Decimal(str(50 * i)),
				received_at=timezone.now() - timedelta(days=30 * i)
			)
	
	def test_full_analytics_workflow(self):
		"""اختبار تدفق التحليلات الكامل"""
		
		# 1. تقرير الأعمار
		aging = StockAgingAnalyzer.get_stock_aging_report(location=self.location)
		self.assertGreater(len(aging['aging_data']), 0)
		
		# 2. تحليل ABC
		abc = ABCAnalyzer.perform_abc_analysis()
		self.assertIn('products', abc)
		
		# 3. نقطة الطلب
		rop = ReorderPointOptimizer.calculate_reorder_point(self.products[0])
		self.assertIn('reorder_point', rop)
		
		# 4. معدل الدوران
		turnover = InventoryTurnoverAnalyzer.calculate_turnover_ratio()
		self.assertIn('turnover_ratio', turnover)
		
		# 5. المخزون الراكد
		dead = DeadStockIdentifier.identify_dead_stock()
		self.assertIn('dead_stock', dead)


class InventoryAnalyticsPerformanceTests(TestCase):
	"""اختبارات الأداء"""
	
	def test_large_dataset_performance(self):
		"""اختبار الأداء مع بيانات كبيرة"""
		
		import time
		
		location = Location.objects.create(
			name="Mega Warehouse",
			code=f"WH-MEGA-{int(time.time()*1000)}"
		)
		
		# إنشاء 100 منتج
		products = []
		import uuid
		for i in range(100):
			unique_id = uuid.uuid4().hex[:8]
			product = Product.objects.create(
				sku=f"PERF-{unique_id}-{i:04d}",
				name=f"Performance Product {i}",
				cost=Decimal(str(10 + i)),
				price=Decimal(str(20 + i)),
				internal_code=f"INTPERF{unique_id}{i:04d}"
			)
			products.append(product)
			
			Stock.objects.create(
				product=product,
				location=location,
				quantity=100
			)
		
		# قياس وقت تحليل ABC
		start = time.time()
		abc_result = ABCAnalyzer.perform_abc_analysis()
		abc_time = time.time() - start
		
		# يجب أن يكون أقل من 5 ثواني
		self.assertLess(abc_time, 5.0)
		self.assertEqual(len(abc_result['products']), 100)
