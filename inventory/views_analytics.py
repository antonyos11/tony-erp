"""
واجهات عرض تحليلات المخزون المتقدم
Advanced Inventory Analytics Views
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, F, Q
from django.utils.translation import gettext as _
from datetime import date, timedelta
from decimal import Decimal
import csv

from inventory.models import Product, Location, Stock
from inventory.services.inventory_analytics import (
	StockAgingAnalyzer,
	ABCAnalyzer,
	ReorderPointOptimizer,
	InventoryTurnoverAnalyzer,
	DeadStockIdentifier
)


@login_required
def inventory_analytics_dashboard(request):
	"""لوحة تحكم تحليلات المخزون الشاملة"""
	
	# إحصائيات سريعة
	total_products = Product.objects.count()
	total_stock_value = Stock.objects.aggregate(
		total=Sum(F('quantity') * F('product__cost'))
	)['total'] or Decimal('0')
	
	# عدد المنتجات منخفضة المخزون
	low_stock_count = Product.objects.filter(
		stocks__quantity__lte=F('min_stock')
	).distinct().count()
	
	# المخزون الراكد (أكثر من 180 يوم)
	dead_stock_data = DeadStockIdentifier.identify_dead_stock(no_sales_days=180)
	dead_stock_value = dead_stock_data['summary']['total_value']
	dead_stock_count = len(dead_stock_data['dead_stock'])
	
	# تحليل ABC (مبسط)
	abc_data = ABCAnalyzer.perform_abc_analysis(period_days=365)
	
	# معدل دوران إجمالي
	turnover_data = InventoryTurnoverAnalyzer.calculate_turnover_ratio(period_days=365)
	
	context = {
		'total_products': total_products,
		'total_stock_value': total_stock_value,
		'low_stock_count': low_stock_count,
		'dead_stock_count': dead_stock_count,
		'dead_stock_value': dead_stock_value,
		'abc_summary': abc_data['summary'],
		'turnover_ratio': turnover_data['turnover_ratio'],
		'turnover_classification': turnover_data['classification'],
		'days_in_inventory': turnover_data['days_in_inventory']
	}
	
	return render(request, 'inventory/analytics/dashboard.html', context)


@login_required
def stock_aging_report(request):
	"""تقرير أعمار المخزون"""
	
	location_id = request.GET.get('location')
	product_id = request.GET.get('product')
	
	location = None
	product = None
	
	if location_id:
		location = get_object_or_404(Location, id=location_id)
	if product_id:
		product = get_object_or_404(Product, id=product_id)
	
	# تقرير الأعمار
	aging_data = StockAgingAnalyzer.get_stock_aging_report(
		location=location,
		product=product
	)
	
	# البيانات للرسم البياني
	age_distribution = aging_data['summary']['age_distribution']
	
	context = {
		'aging_data': aging_data['aging_data'],
		'summary': aging_data['summary'],
		'age_distribution': age_distribution,
		'locations': Location.objects.filter(is_active=True),
		'selected_location': location,
		'selected_product': product
	}
	
	return render(request, 'inventory/analytics/stock_aging.html', context)


@login_required
def abc_analysis_report(request):
	"""تقرير تحليل ABC"""
	
	period_days = int(request.GET.get('period', 365))
	location_id = request.GET.get('location')
	
	location = None
	if location_id:
		location = get_object_or_404(Location, id=location_id)
	
	# تحليل ABC
	abc_data = ABCAnalyzer.perform_abc_analysis(
		period_days=period_days,
		location=location
	)
	
	# تقسيم المنتجات حسب الفئة
	products_a = [p for p in abc_data['products'] if p['abc_category'] == 'A']
	products_b = [p for p in abc_data['products'] if p['abc_category'] == 'B']
	products_c = [p for p in abc_data['products'] if p['abc_category'] == 'C']
	
	context = {
		'summary': abc_data['summary'],
		'total_value': abc_data['total_value'],
		'total_products': abc_data['total_products'],
		'products_a': products_a[:20],  # أول 20
		'products_b': products_b[:20],
		'products_c': products_c[:20],
		'period_days': period_days,
		'locations': Location.objects.filter(is_active=True),
		'selected_location': location
	}
	
	return render(request, 'inventory/analytics/abc_analysis.html', context)


@login_required
def reorder_point_analysis(request):
	"""تحليل نقاط إعادة الطلب"""
	
	location_id = request.GET.get('location')
	only_critical = request.GET.get('critical') == '1'
	
	location = None
	if location_id:
		location = get_object_or_404(Location, id=location_id)
	
	# الحصول على توصيات إعادة الطلب
	suggestions = ReorderPointOptimizer.get_reorder_suggestions(
		location=location,
		only_critical=only_critical
	)
	
	# الإحصائيات
	critical_count = sum(1 for s in suggestions if s['status'] == 'critical')
	warning_count = sum(1 for s in suggestions if s['status'] == 'warning')
	total_order_value = sum(
		s['recommended_order_qty'] * s['product'].cost 
		for s in suggestions
	)
	
	context = {
		'suggestions': suggestions,
		'critical_count': critical_count,
		'warning_count': warning_count,
		'total_suggestions': len(suggestions),
		'total_order_value': total_order_value,
		'locations': Location.objects.filter(is_active=True),
		'selected_location': location,
		'only_critical': only_critical
	}
	
	return render(request, 'inventory/analytics/reorder_point.html', context)


@login_required
def inventory_turnover_report(request):
	"""تقرير معدل دوران المخزون"""
	
	period_days = int(request.GET.get('period', 365))
	location_id = request.GET.get('location')
	
	location = None
	if location_id:
		location = get_object_or_404(Location, id=location_id)
	
	# معدل الدوران الإجمالي
	overall_turnover = InventoryTurnoverAnalyzer.calculate_turnover_ratio(
		location=location,
		period_days=period_days
	)
	
	# معدل الدوران لكل منتج
	products_turnover = InventoryTurnoverAnalyzer.get_turnover_by_category()
	
	# تصنيف المنتجات
	excellent = [p for p in products_turnover if p['classification'] == 'excellent']
	good = [p for p in products_turnover if p['classification'] == 'good']
	fair = [p for p in products_turnover if p['classification'] == 'fair']
	poor = [p for p in products_turnover if p['classification'] == 'poor']
	
	context = {
		'overall_turnover': overall_turnover,
		'excellent_products': excellent[:10],
		'good_products': good[:10],
		'fair_products': fair[:10],
		'poor_products': poor[:20],  # التركيز على الضعيفة
		'period_days': period_days,
		'locations': Location.objects.filter(is_active=True),
		'selected_location': location
	}
	
	return render(request, 'inventory/analytics/turnover_report.html', context)


@login_required
def dead_stock_report(request):
	"""تقرير المخزون الراكد"""
	
	no_sales_days = int(request.GET.get('days', 180))
	location_id = request.GET.get('location')
	
	location = None
	if location_id:
		location = get_object_or_404(Location, id=location_id)
	
	# كشف المخزون الراكد
	dead_stock_data = DeadStockIdentifier.identify_dead_stock(
		no_sales_days=no_sales_days,
		location=location
	)
	
	# المنتجات بطيئة الحركة
	slow_movers = DeadStockIdentifier.get_slow_moving_products(
		turnover_threshold=2.0,
		period_days=365
	)
	
	context = {
		'dead_stock': dead_stock_data['dead_stock'],
		'summary': dead_stock_data['summary'],
		'slow_movers': slow_movers[:20],
		'no_sales_days': no_sales_days,
		'locations': Location.objects.filter(is_active=True),
		'selected_location': location
	}
	
	return render(request, 'inventory/analytics/dead_stock.html', context)


@login_required
def product_analytics_detail(request, product_id):
	"""تحليلات تفصيلية لمنتج محدد"""
	
	product = get_object_or_404(Product, id=product_id)
	
	# نقطة إعادة الطلب
	reorder_info = ReorderPointOptimizer.calculate_reorder_point(product)
	
	# معدل الدوران
	turnover_info = InventoryTurnoverAnalyzer.calculate_turnover_ratio(product=product)
	
	# أعمار المخزون
	aging_info = StockAgingAnalyzer.get_stock_aging_report(product=product)
	
	# تحليل ABC
	abc_full = ABCAnalyzer.perform_abc_analysis()
	product_abc = next(
		(p for p in abc_full['products'] if p['product'].id == product_id),
		None
	)
	
	context = {
		'product': product,
		'reorder_info': reorder_info,
		'turnover_info': turnover_info,
		'aging_info': aging_info,
		'product_abc': product_abc
	}
	
	return render(request, 'inventory/analytics/product_detail.html', context)


@login_required
def export_abc_analysis_csv(request):
	"""تصدير تحليل ABC كملف CSV"""
	
	period_days = int(request.GET.get('period', 365))
	abc_data = ABCAnalyzer.perform_abc_analysis(period_days=period_days)
	
	response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
	response['Content-Disposition'] = f'attachment; filename="abc_analysis_{date.today()}.csv"'
	
	# إضافة BOM لدعم العربية في Excel
	response.write('\ufeff')
	
	writer = csv.writer(response)
	writer.writerow([
		'SKU', 'اسم المنتج', 'الفئة ABC', 'كمية المبيعات', 
		'قيمة المبيعات', 'المخزون الحالي', 'قيمة المخزون',
		'نسبة القيمة %', 'النسبة التراكمية %'
	])
	
	for item in abc_data['products']:
		writer.writerow([
			item['product'].sku,
			item['product'].name,
			item['abc_category'],
			item['total_sales_qty'],
			f"{item['total_sales_value']:.2f}",
			item['current_stock_qty'],
			f"{item['current_stock_value']:.2f}",
			f"{item['value_percentage']:.2f}",
			f"{item['cumulative_percentage']:.2f}"
		])
	
	return response


@login_required
def export_dead_stock_csv(request):
	"""تصدير المخزون الراكد كملف CSV"""
	
	no_sales_days = int(request.GET.get('days', 180))
	dead_stock_data = DeadStockIdentifier.identify_dead_stock(no_sales_days=no_sales_days)
	
	response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
	response['Content-Disposition'] = f'attachment; filename="dead_stock_{date.today()}.csv"'
	
	response.write('\ufeff')
	
	writer = csv.writer(response)
	writer.writerow([
		'SKU', 'اسم المنتج', 'الموقع', 'الكمية', 'القيمة',
		'آخر بيع', 'أيام بدون مبيعات', 'التصنيف'
	])
	
	for item in dead_stock_data['dead_stock']:
		writer.writerow([
			item['product'].sku,
			item['product'].name,
			item['location'].name,
			item['quantity'],
			f"{item['value']:.2f}",
			item['last_sale_date'] or 'لا يوجد',
			item['days_since_last_sale'],
			item['age_category']
		])
	
	return response


@login_required
def reorder_point_ajax(request, product_id):
	"""حساب نقطة إعادة الطلب عبر AJAX"""
	
	if request.method != 'GET':
		return JsonResponse({'error': 'Method not allowed'}, status=405)
	
	product = get_object_or_404(Product, id=product_id)
	
	lead_time = int(request.GET.get('lead_time', 7))
	service_level = float(request.GET.get('service_level', 0.95))
	
	reorder_info = ReorderPointOptimizer.calculate_reorder_point(
		product=product,
		lead_time_days=lead_time,
		service_level=service_level
	)
	
	return JsonResponse({
		'success': True,
		'data': {
			'reorder_point': reorder_info['reorder_point'],
			'safety_stock': reorder_info['safety_stock'],
			'avg_daily_consumption': round(reorder_info['avg_daily_consumption'], 2),
			'current_stock': reorder_info['current_stock'],
			'status': reorder_info['status'],
			'days_until_stockout': reorder_info['days_until_stockout'],
			'recommended_order_qty': reorder_info['recommended_order_qty']
		}
	})


@login_required
def stock_valuation_report(request):
	"""تقرير تقييم المخزون (FIFO/LIFO)"""
	
	# ملاحظة: حسابات FIFO/LIFO المتقدمة تعتمد على سجل حركات المخزون
	# الحساب الحالي يستخدم متوسط تكلفة الوحدة، يمكن تطويره لاحقاً
	# لدعم FIFO/LIFO الحقيقي بناءً على StockMovement
	
	location_id = request.GET.get('location')
	method = request.GET.get('method', 'fifo')  # fifo or lifo
	
	location = None
	if location_id:
		location = get_object_or_404(Location, id=location_id)
	
	# الحصول على جميع المنتجات بمخزون
	products_with_stock = Product.objects.filter(stocks__quantity__gt=0).distinct()
	
	valuation_data = []
	total_fifo = Decimal('0')
	total_lifo = Decimal('0')
	
	for product in products_with_stock:
		stock_qty = product.current_stock
		
		# تقييم FIFO - استخدام متوسط تكلفة الوحدة (يمكن تطويره لاحقاً)
		fifo_value = product.unit_cost * stock_qty if hasattr(product, 'unit_cost') else Decimal('0')
		
		# تقييم LIFO - استخدام متوسط تكلفة الوحدة (يمكن تطويره لاحقاً)
		lifo_value = product.unit_cost * stock_qty if hasattr(product, 'unit_cost') else Decimal('0')
		
		difference = fifo_value - lifo_value
		
		valuation_data.append({
			'product': product,
			'quantity': stock_qty,
			'fifo_value': fifo_value,
			'lifo_value': lifo_value,
			'difference': difference,
			'difference_pct': (difference / fifo_value * 100) if fifo_value > 0 else 0
		})
		
		total_fifo += fifo_value
		total_lifo += lifo_value
	
	context = {
		'valuation_data': valuation_data,
		'total_fifo': total_fifo,
		'total_lifo': total_lifo,
		'total_difference': total_fifo - total_lifo,
		'selected_method': method,
		'locations': Location.objects.filter(is_active=True),
		'selected_location': location
	}
	
	return render(request, 'inventory/analytics/stock_valuation.html', context)
