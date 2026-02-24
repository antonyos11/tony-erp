"""
نظام تحليلات المخزون المتقدم
Advanced Inventory Analytics System

يوفر:
- Stock Aging Report (تقرير أعمار المخزون)
- ABC Analysis (تحليل ABC)
- Reorder Point Optimization (تحسين نقطة إعادة الطلب)
- Inventory Turnover (معدل دوران المخزون)
- Dead Stock Identification (كشف المخزون الراكد)
"""

from django.db.models import Sum, F, Q, Count, Avg, Max, Min, DecimalField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
import logging

from inventory.models import Product, Stock, StockBatch, Location
from sales.models import Invoice, InvoiceItem
try:  # توفر SaleOrderItem كـ proxy في بيئات الاختبار
	from sales.models import SaleOrderItem
except Exception:  # pragma: no cover - يحمي التشغيل في حال غياب النموذج
	SaleOrderItem = None

logger = logging.getLogger(__name__)


def _sales_queryset():
	"""إرجاع QuerySet لبيانات المبيعات مستخدماً SaleOrderItem إن وجدت وإلا InvoiceItem."""
	if SaleOrderItem is not None:
		qs = SaleOrderItem.objects.select_related('invoice', 'product')
		if qs.exists():
			return qs
	return InvoiceItem.objects.select_related('invoice', 'product')


class StockAgingAnalyzer:
	"""محلل أعمار المخزون - تحليل عمر البضاعة في المخزن"""
	
	@staticmethod
	def get_stock_aging_report(
		location: Optional[Location] = None,
		product: Optional[Product] = None,
		aging_brackets: Optional[List[int]] = None
	) -> Dict[str, Any]:
		"""
		تقرير تفصيلي لأعمار المخزون
		
		Args:
			location: موقع محدد (اختياري)
			product: منتج محدد (اختياري)
			aging_brackets: فترات العمر بالأيام [30, 60, 90, 180, 365]
		
		Returns:
			{
				'aging_data': [
					{
						'product': Product,
						'location': Location,
						'batches': [
							{
								'lot_number': str,
								'quantity': int,
								'unit_cost': Decimal,
								'total_value': Decimal,
								'age_days': int,
								'age_category': str,
								'received_at': datetime
							}
						],
						'total_quantity': int,
						'total_value': Decimal,
						'avg_age_days': float
					}
				],
				'summary': {
					'total_items': int,
					'total_value': Decimal,
					'age_distribution': {
						'0-30': {'count': int, 'value': Decimal},
						'31-60': {...},
						...
					}
				}
			}
		"""
		
		if aging_brackets is None:
			aging_brackets = [30, 60, 90, 180, 365]
		
		# الحصول على الدفعات
		batches = StockBatch.objects.filter(quantity__gt=0).select_related('product', 'location')
		
		if location:
			batches = batches.filter(location=location)
		if product:
			batches = batches.filter(product=product)
		
		today = timezone.now()
		aging_data = []
		age_distribution = {f"{aging_brackets[i-1] + 1 if i > 0 else 0}-{b}": {'count': 0, 'value': Decimal('0')} 
		                    for i, b in enumerate(aging_brackets)}
		age_distribution['365+'] = {'count': 0, 'value': Decimal('0')}
		
		# تجميع حسب المنتج والموقع
		from itertools import groupby
		
		batches_list = list(batches.order_by('product', 'location'))
		
		for (prod_id, loc_id), group in groupby(batches_list, key=lambda b: (b.product_id, b.location_id)):
			batch_list = list(group)
			product_obj = batch_list[0].product
			location_obj = batch_list[0].location
			
			batch_details = []
			total_qty = 0
			total_val = Decimal('0')
			total_age_weighted = 0
			
			for batch in batch_list:
				age_days = (today - batch.received_at).days
				age_category = StockAgingAnalyzer._categorize_age(age_days, aging_brackets)
				batch_value = batch.quantity * batch.unit_cost
				
				batch_details.append({
					'lot_number': batch.lot_number or f"Batch-{batch.id}",
					'quantity': batch.quantity,
					'unit_cost': batch.unit_cost,
					'total_value': batch_value,
					'age_days': age_days,
					'age_category': age_category,
					'received_at': batch.received_at,
					'expiry_date': batch.expiry_date
				})
				
				total_qty += batch.quantity
				total_val += batch_value
				total_age_weighted += age_days * batch.quantity
				
				# توزيع الأعمار
				age_distribution[age_category]['count'] += batch.quantity
				age_distribution[age_category]['value'] += batch_value
			
			avg_age = total_age_weighted / total_qty if total_qty > 0 else 0
			
			aging_data.append({
				'product': product_obj,
				'location': location_obj,
				'batches': batch_details,
				'total_quantity': total_qty,
				'total_value': total_val,
				'avg_age_days': avg_age
			})
		
		# الإحصائيات الإجمالية
		total_items = sum(item['total_quantity'] for item in aging_data)
		total_value = sum(item['total_value'] for item in aging_data)
		
		return {
			'aging_data': aging_data,
			'summary': {
				'total_items': total_items,
				'total_value': total_value,
				'age_distribution': age_distribution
			}
		}
	
	@staticmethod
	def _categorize_age(age_days: int, brackets: List[int]) -> str:
		"""تصنيف العمر حسب الفئات المحددة"""
		for i, bracket in enumerate(brackets):
			if age_days <= bracket:
				start = brackets[i-1] + 1 if i > 0 else 0
				return f"{start}-{bracket}"
		return "365+"


class ABCAnalyzer:
	"""محلل ABC - تصنيف المخزون حسب القيمة والأهمية"""
	
	@staticmethod
	def perform_abc_analysis(
		period_days: int = 365,
		location: Optional[Location] = None
	) -> Dict[str, Any]:
		"""
		تحليل ABC للمخزون
		
		المعايير:
		- A: 80% من القيمة (عادة 20% من الأصناف)
		- B: 15% من القيمة (عادة 30% من الأصناف)
		- C: 5% من القيمة (عادة 50% من الأصناف)
		
		Args:
			period_days: فترة التحليل (افتراضي سنة)
			location: موقع محدد (اختياري)
		
		Returns:
			{
				'products': [
					{
						'product': Product,
						'total_sales_qty': int,
						'total_sales_value': Decimal,
						'current_stock_qty': int,
						'current_stock_value': Decimal,
						'abc_category': str,  # A, B, or C
						'value_percentage': float,
						'cumulative_percentage': float
					}
				],
				'summary': {
					'A': {'count': int, 'percentage': float, 'value': Decimal},
					'B': {...},
					'C': {...}
				}
			}
		"""
		
		# الحصول على المبيعات خلال الفترة
		start_date = date.today() - timedelta(days=period_days)
		
		# مبيعات كل منتج
		sales_qs = _sales_queryset().filter(
			invoice__date__gte=start_date,
		)
		# عند استخدام InvoiceItem احتفظ بفلتر المحذوفين
		if not (SaleOrderItem is not None and issubclass(sales_qs.model, SaleOrderItem)):
			sales_qs = sales_qs.filter(invoice__is_deleted=False)
        
		sales_data = sales_qs.values('product').annotate(
			total_qty=Sum('quantity'),
			total_value=Sum(F('quantity') * F('price'), output_field=DecimalField())
		).order_by('-total_value')
		
		# تحويل لقاموس للوصول السريع
		sales_dict = {item['product']: item for item in sales_data}
		
		# الحصول على المخزون الحالي
		stock_query = Stock.objects.select_related('product', 'location')
		if location:
			stock_query = stock_query.filter(location=location)
		
		stock_data = stock_query.values('product').annotate(
			total_stock=Sum('quantity')
		)
		
		stock_dict = {item['product']: item['total_stock'] for item in stock_data}
		
		# تجميع البيانات
		products_data = []
		total_value = Decimal('0')
		
		# جميع المنتجات (من المبيعات أو المخزون)
		all_product_ids = set(sales_dict.keys()) | set(stock_dict.keys())
		
		for product_id in all_product_ids:
			try:
				product = Product.objects.get(id=product_id)
			except Product.DoesNotExist:
				continue
			
			sales_info = sales_dict.get(product_id, {})
			sales_value = sales_info.get('total_value', Decimal('0'))
			sales_qty = sales_info.get('total_qty', 0)
			
			stock_qty = stock_dict.get(product_id, 0)
			stock_value = stock_qty * product.cost
			
			# القيمة الإجمالية (مبيعات + مخزون)
			item_value = sales_value + stock_value
			total_value += item_value
			
			products_data.append({
				'product': product,
				'total_sales_qty': sales_qty,
				'total_sales_value': sales_value,
				'current_stock_qty': stock_qty,
				'current_stock_value': stock_value,
				'total_value': item_value
			})
		
		# الترتيب حسب القيمة (تنازلي)
		products_data.sort(key=lambda x: x['total_value'], reverse=True)
		
		# حساب النسب المئوية والتصنيف
		cumulative_value = Decimal('0')
		
		for item in products_data:
			item['value_percentage'] = float((item['total_value'] / total_value * 100) if total_value > 0 else 0)
			cumulative_value += item['total_value']
			cumulative_pct = float((cumulative_value / total_value * 100) if total_value > 0 else 0)
			item['cumulative_percentage'] = cumulative_pct
			
			# تصنيف ABC
			if cumulative_pct <= 80:
				item['abc_category'] = 'A'
			elif cumulative_pct <= 95:
				item['abc_category'] = 'B'
			else:
				item['abc_category'] = 'C'
		
		# الإحصائيات الإجمالية
		summary = {
			'A': {'count': 0, 'percentage': 0.0, 'value': Decimal('0')},
			'B': {'count': 0, 'percentage': 0.0, 'value': Decimal('0')},
			'C': {'count': 0, 'percentage': 0.0, 'value': Decimal('0')}
		}
		
		for item in products_data:
			cat = item['abc_category']
			summary[cat]['count'] += 1
			summary[cat]['value'] += item['total_value']
		
		total_count = len(products_data)
		for cat in ['A', 'B', 'C']:
			summary[cat]['percentage'] = (summary[cat]['count'] / total_count * 100) if total_count > 0 else 0
		
		return {
			'products': products_data,
			'summary': summary,
			'total_value': total_value,
			'total_products': total_count
		}


class ReorderPointOptimizer:
	"""محسن نقطة إعادة الطلب - حساب نقاط الطلب المثالية"""
	
	@staticmethod
	def calculate_reorder_point(
		product: Product,
		location: Optional[Location] = None,
		lead_time_days: int = 7,
		service_level: float = 0.95,
		analysis_period_days: int = 90
	) -> Dict[str, Any]:
		"""
		حساب نقطة إعادة الطلب المثالية
		
		الصيغة:
		ROP = (متوسط الاستهلاك اليومي × Lead Time) + Safety Stock
		Safety Stock = Z-Score × StdDev × √Lead Time
		
		Args:
			product: المنتج
			location: الموقع (اختياري)
			lead_time_days: فترة التوريد بالأيام
			service_level: مستوى الخدمة (0.95 = 95%)
			analysis_period_days: فترة التحليل
		
		Returns:
			{
				'reorder_point': int,
				'safety_stock': int,
				'avg_daily_consumption': float,
				'std_dev': float,
				'current_stock': int,
				'status': str,  # 'ok', 'warning', 'critical'
				'days_until_stockout': int,
				'recommended_order_qty': int
			}
		"""
		
		# الحصول على المبيعات خلال فترة التحليل
		start_date = date.today() - timedelta(days=analysis_period_days)

		sales_query = _sales_queryset().filter(
			product=product,
			invoice__date__gte=start_date,
		)
		if not (SaleOrderItem is not None and issubclass(sales_query.model, SaleOrderItem)):
			sales_query = sales_query.filter(invoice__is_deleted=False)
		
		if location:
			# TODO: ربط المبيعات بالموقع (يحتاج حقل location في Invoice)
			pass
		
		# حساب الاستهلاك اليومي
		daily_sales = sales_query.values('invoice__date').annotate(
			total_qty=Sum('quantity')
		).order_by('invoice__date')
		
		daily_consumption = [item['total_qty'] for item in daily_sales]
		
		if not daily_consumption:
			# لا توجد بيانات مبيعات
			logger.warning(f"No sales data for product {product.sku}")
			return {
				'reorder_point': product.min_stock or 0,
				'safety_stock': 0,
				'avg_daily_consumption': 0.0,
				'std_dev': 0.0,
				'current_stock': product.current_stock,
				'status': 'no_data',
				'days_until_stockout': 999,
				'recommended_order_qty': 0
			}
		
		# الإحصائيات
		import statistics
		avg_daily = statistics.mean(daily_consumption)
		std_dev = statistics.stdev(daily_consumption) if len(daily_consumption) > 1 else 0
		
		# Z-Score حسب مستوى الخدمة
		# 0.95 = 1.65, 0.99 = 2.33
		z_scores = {0.90: 1.28, 0.95: 1.65, 0.98: 1.96, 0.99: 2.33}
		z_score = z_scores.get(service_level, 1.65)
		
		# حساب Safety Stock
		import math
		safety_stock = z_score * std_dev * math.sqrt(lead_time_days)
		
		# نقطة إعادة الطلب
		reorder_point = int((avg_daily * lead_time_days) + safety_stock)
		
		# المخزون الحالي
		current_stock = product.current_stock
		
		# حالة المخزون
		if current_stock <= reorder_point:
			status = 'critical'
		elif current_stock <= reorder_point * 1.2:
			status = 'warning'
		else:
			status = 'ok'
		
		# الأيام حتى نفاد المخزون
		days_until_stockout = int(current_stock / avg_daily) if avg_daily > 0 else 999
		
		# الكمية الموصى بطلبها (EOQ مبسط)
		# EOQ = sqrt((2 × Annual Demand × Order Cost) / Holding Cost)
		# مبسط: طلب شهر واحد
		recommended_qty = int(avg_daily * 30)
		
		return {
			'reorder_point': reorder_point,
			'safety_stock': int(safety_stock),
			'avg_daily_consumption': avg_daily,
			'std_dev': std_dev,
			'current_stock': current_stock,
			'status': status,
			'days_until_stockout': days_until_stockout,
			'recommended_order_qty': recommended_qty,
			'lead_time_days': lead_time_days,
			'service_level': service_level
		}
	
	@staticmethod
	def get_reorder_suggestions(
		location: Optional[Location] = None,
		only_critical: bool = False
	) -> List[Dict]:
		"""
		الحصول على قائمة المنتجات التي تحتاج إعادة طلب
		
		Args:
			location: موقع محدد
			only_critical: فقط الحالات الحرجة
		
		Returns:
			قائمة المنتجات مع معلومات إعادة الطلب
		"""
		
		products = Product.objects.filter(min_stock__gt=0)
		suggestions = []
		
		for product in products:
			reorder_info = ReorderPointOptimizer.calculate_reorder_point(product, location)
			
			if only_critical and reorder_info['status'] != 'critical':
				continue
			
			if reorder_info['status'] in ['critical', 'warning']:
				suggestions.append({
					'product': product,
					**reorder_info
				})
		
		# الترتيب حسب الأولوية
		suggestions.sort(key=lambda x: (
			0 if x['status'] == 'critical' else 1,
			x['days_until_stockout']
		))
		
		return suggestions


class InventoryTurnoverAnalyzer:
	"""محلل معدل دوران المخزون"""
	
	@staticmethod
	def calculate_turnover_ratio(
		product: Optional[Product] = None,
		location: Optional[Location] = None,
		period_days: int = 365
	) -> Dict[str, Any]:
		"""
		حساب معدل دوران المخزون
		
		الصيغة:
		Inventory Turnover = Cost of Goods Sold / Average Inventory
		Days in Inventory = 365 / Inventory Turnover
		
		Args:
			product: منتج محدد (اختياري)
			location: موقع محدد (اختياري)
			period_days: فترة التحليل
		
		Returns:
			{
				'turnover_ratio': float,
				'days_in_inventory': float,
				'cogs': Decimal,  # تكلفة البضاعة المباعة
				'avg_inventory_value': Decimal,
				'classification': str,  # 'excellent', 'good', 'fair', 'poor'
			}
		"""
		
		start_date = date.today() - timedelta(days=period_days)

		# تكلفة البضاعة المباعة (COGS)
		sales_query = _sales_queryset().filter(
			invoice__date__gte=start_date,
		)
		if not (SaleOrderItem is not None and issubclass(sales_query.model, SaleOrderItem)):
			sales_query = sales_query.filter(invoice__is_deleted=False)
		
		if product:
			sales_query = sales_query.filter(product=product)
		
		# COGS = Quantity × Cost
		cogs = sales_query.aggregate(
			total=Sum(F('quantity') * F('product__cost'), output_field=DecimalField())
		)['total'] or Decimal('0')
		
		# متوسط قيمة المخزون
		# مبسط: المخزون الحالي (يمكن تحسينه بحساب متوسط شهري)
		stock_query = Stock.objects.select_related('product')
		
		if location:
			stock_query = stock_query.filter(location=location)
		if product:
			stock_query = stock_query.filter(product=product)
		
		avg_inventory = stock_query.aggregate(
			total_value=Sum(F('quantity') * F('product__cost'), output_field=DecimalField())
		)['total_value'] or Decimal('0')
		
		# حساب معدل الدوران
		if avg_inventory > 0:
			turnover_ratio = float(cogs / avg_inventory)
		else:
			turnover_ratio = 0.0
		
		# الأيام في المخزون
		days_in_inventory = (period_days / turnover_ratio) if turnover_ratio > 0 else 999
		
		# التصنيف
		if turnover_ratio >= 12:  # دوران شهري
			classification = 'excellent'
		elif turnover_ratio >= 6:  # دوران كل شهرين
			classification = 'good'
		elif turnover_ratio >= 4:  # دوران ربع سنوي
			classification = 'fair'
		else:
			classification = 'poor'
		
		return {
			'turnover_ratio': round(turnover_ratio, 2),
			'days_in_inventory': round(days_in_inventory, 1),
			'cogs': cogs,
			'avg_inventory_value': avg_inventory,
			'classification': classification,
			'period_days': period_days
		}
	
	@staticmethod
	def get_turnover_by_category() -> List[Dict]:
		"""معدل الدوران لكل فئة/منتج"""
		
		products = Product.objects.all()
		results = []
		
		for product in products:
			turnover = InventoryTurnoverAnalyzer.calculate_turnover_ratio(product=product)
			results.append({
				'product': product,
				**turnover
			})
		
		# الترتيب حسب معدل الدوران (الأقل أولاً)
		results.sort(key=lambda x: x['turnover_ratio'])
		
		return results


class DeadStockIdentifier:
	"""كاشف المخزون الراكد/الميت"""
	
	@staticmethod
	def identify_dead_stock(
		no_sales_days: int = 180,
		location: Optional[Location] = None
	) -> Dict[str, Any]:
		"""
		كشف المخزون الراكد
		
		المعايير:
		- لا مبيعات خلال الفترة المحددة
		- قيمة مخزون موجب
		
		Args:
			no_sales_days: عدد الأيام بدون مبيعات
			location: موقع محدد
		
		Returns:
			{
				'dead_stock': [
					{
						'product': Product,
						'quantity': int,
						'value': Decimal,
						'last_sale_date': date,
						'days_since_last_sale': int,
						'age_category': str  # 'slow', 'dead', 'obsolete'
					}
				],
				'summary': {
					'total_items': int,
					'total_value': Decimal,
					'categories': {
						'slow': {...},
						'dead': {...},
						'obsolete': {...}
					}
				}
			}
		"""
		
		cutoff_date = date.today() - timedelta(days=no_sales_days)
		
		# الحصول على المخزون الحالي
		stock_query = Stock.objects.filter(quantity__gt=0).select_related('product', 'location')
		
		if location:
			stock_query = stock_query.filter(location=location)
		
		dead_stock = []
		summary = {
			'total_items': 0,
			'total_value': Decimal('0'),
			'categories': {
				'slow': {'count': 0, 'value': Decimal('0')},      # 90-180 يوم
				'dead': {'count': 0, 'value': Decimal('0')},      # 180-365 يوم
				'obsolete': {'count': 0, 'value': Decimal('0')}   # أكثر من سنة
			}
		}
		
		for stock in stock_query:
			# آخر عملية بيع
			sales_qs = _sales_queryset().filter(product=stock.product)
			if not (SaleOrderItem is not None and issubclass(sales_qs.model, SaleOrderItem)):
				sales_qs = sales_qs.filter(invoice__is_deleted=False)
			last_sale = sales_qs.order_by('-invoice__date').first()
			
			if last_sale:
				last_sale_date = last_sale.invoice.date
				days_since = (date.today() - last_sale_date).days
			else:
				# لا توجد مبيعات أبداً
				last_sale_date = None
				days_since = 999
			
			# هل راكد؟
			if last_sale_date is None or days_since >= no_sales_days:
				stock_value = stock.quantity * stock.product.cost
				
				# التصنيف
				if 90 <= days_since < 180:
					age_category = 'slow'
				elif 180 <= days_since < 365:
					age_category = 'dead'
				else:
					age_category = 'obsolete'
				
				dead_stock.append({
					'product': stock.product,
					'location': stock.location,
					'quantity': stock.quantity,
					'value': stock_value,
					'last_sale_date': last_sale_date,
					'days_since_last_sale': days_since,
					'age_category': age_category
				})
				
				# الإحصائيات
				summary['total_items'] += stock.quantity
				summary['total_value'] += stock_value
				summary['categories'][age_category]['count'] += stock.quantity
				summary['categories'][age_category]['value'] += stock_value
		
		# الترتيب حسب القيمة (الأعلى أولاً)
		dead_stock.sort(key=lambda x: x['value'], reverse=True)
		
		return {
			'dead_stock': dead_stock,
			'summary': summary,
			'criteria': {
				'no_sales_days': no_sales_days,
				'cutoff_date': cutoff_date
			}
		}
	
	@staticmethod
	def get_slow_moving_products(
		turnover_threshold: float = 2.0,
		period_days: int = 365
	) -> List[Dict]:
		"""
		كشف المنتجات بطيئة الحركة (معدل دوران منخفض)
		
		Args:
			turnover_threshold: الحد الأدنى لمعدل الدوران
			period_days: فترة التحليل
		"""
		
		slow_movers = []
		products = Product.objects.filter(stocks__quantity__gt=0).distinct()
		
		for product in products:
			turnover = InventoryTurnoverAnalyzer.calculate_turnover_ratio(
				product=product,
				period_days=period_days
			)
			
			if turnover['turnover_ratio'] < turnover_threshold:
				slow_movers.append({
					'product': product,
					'turnover_ratio': turnover['turnover_ratio'],
					'days_in_inventory': turnover['days_in_inventory'],
					'current_stock': product.current_stock,
					'stock_value': product.current_stock * product.cost
				})
		
		# الترتيب حسب معدل الدوران (الأقل أولاً)
		slow_movers.sort(key=lambda x: x['turnover_ratio'])
		
		return slow_movers
