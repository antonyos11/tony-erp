"""
واجهات عرض نظام التحليلات المتقدم للعملاء
CRM Analytics Views
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import csv
import json

from partners.models import Customer
from sales.models import Invoice, FieldVisit
from hr.models import Employee
from sales.services.crm_analytics import (
	CustomerAnalyticsService,
	SalesPipelineAnalyzer,
	CommissionCalculator,
	LeadConversionTracker
)


@login_required
def crm_analytics_dashboard(request):
	"""لوحة تحكم التحليلات المتقدمة للعملاء"""
	
	# الفترة الافتراضية: آخر 3 أشهر
	period_end = timezone.now().date()
	period_start = period_end - timedelta(days=90)
	
	# معلمات الفترة من الطلب
	if request.GET.get('period_start'):
		period_start = date.fromisoformat(request.GET.get('period_start'))
	if request.GET.get('period_end'):
		period_end = date.fromisoformat(request.GET.get('period_end'))
	
	# تصنيف العملاء
	segmentation = CustomerAnalyticsService.get_customer_segmentation(
		period_start, period_end
	)
	
	# نظرة عامة على المبيعات
	pipeline = SalesPipelineAnalyzer.get_pipeline_overview(
		period_start, period_end
	)
	
	# مؤشرات التحويل
	conversion = LeadConversionTracker.get_conversion_metrics(
		period_start, period_end
	)
	
	# إحصائيات سريعة
	total_customers = Customer.objects.count()
	active_customers = Invoice.objects.filter(
		date__range=[period_start, period_end],
		is_deleted=False
	).values('customer').distinct().count()
	
	total_revenue = Invoice.objects.filter(
		date__range=[period_start, period_end],
		is_deleted=False
	).aggregate(total=Sum('cached_total'))['total'] or Decimal('0')
	
	avg_order_value = Invoice.objects.filter(
		date__range=[period_start, period_end],
		is_deleted=False
	).aggregate(avg=Avg('cached_total'))['avg'] or Decimal('0')
	
	context = {
		'period_start': period_start,
		'period_end': period_end,
		'segmentation': segmentation,
		'pipeline': pipeline,
		'conversion': conversion,
		'total_customers': total_customers,
		'active_customers': active_customers,
		'total_revenue': total_revenue,
		'avg_order_value': avg_order_value,
	}
	
	return render(request, 'sales/crm_analytics/dashboard.html', context)


@login_required
def customer_lifetime_value_report(request, customer_id=None):
	"""تقرير قيمة العميل مدى الحياة"""
	
	if customer_id:
		# عميل محدد
		customer = get_object_or_404(Customer, id=customer_id)
		clv_data = CustomerAnalyticsService.get_customer_lifetime_value(customer)
		rfm_data = CustomerAnalyticsService.get_rfm_analysis(customer)
		journey = LeadConversionTracker.track_lead_journey(customer)
		
		context = {
			'customer': customer,
			'clv_data': clv_data,
			'rfm_data': rfm_data,
			'journey': journey
		}
		
		return render(request, 'sales/crm_analytics/customer_clv.html', context)
	
	else:
		# جميع العملاء
		from datetime import datetime, timedelta
		from decimal import Decimal
		
		period_start = datetime.now() - timedelta(days=365)
		period_end = datetime.now()
		
		customers = Customer.objects.all()
		clv_list = []
		
		for customer in customers:
			clv = CustomerAnalyticsService.get_customer_lifetime_value(customer)
			if clv['total_revenue'] > 0:  # فقط العملاء الذين لديهم مبيعات
				clv_list.append({
					'name': customer.name,
					'total_orders': clv['total_orders'],
					'total_sales': clv['total_revenue'],
					'average_order_value': clv['average_order_value'],
					'clv': clv['lifetime_value'],
				})
		
		# ترتيب حسب القيمة مدى الحياة
		clv_list.sort(key=lambda x: x['clv'], reverse=True)
		
		# حساب الإحصائيات
		total_customers = len(clv_list)
		total_orders = sum(c['total_orders'] for c in clv_list)
		total_revenue = sum(c['total_sales'] for c in clv_list)
		average_clv = total_revenue / total_customers if total_customers > 0 else Decimal('0')
		
		# تصنيف العملاء
		threshold_medium = average_clv / 2
		
		for customer in clv_list:
			if customer['clv'] > average_clv:
				customer['clv_class'] = 'clv-high'
				customer['badge_class'] = 'bg-success'
				customer['category_label'] = 'عميل مميز'
			elif customer['clv'] > threshold_medium:
				customer['clv_class'] = 'clv-medium'
				customer['badge_class'] = 'bg-warning'
				customer['category_label'] = 'عميل جيد'
			else:
				customer['clv_class'] = 'clv-low'
				customer['badge_class'] = 'bg-secondary'
				customer['category_label'] = 'عميل عادي'
		
		context = {
			'clv_data': clv_list[:50],  # أفضل 50 عميل
			'period_start': period_start,
			'period_end': period_end,
			'total_customers': total_customers,
			'total_orders': total_orders,
			'total_revenue': total_revenue,
			'average_clv': average_clv,
		}
		
		return render(request, 'sales/crm_analytics/clv_report.html', context)


@login_required
def customer_segmentation_view(request):
	"""عرض تصنيف العملاء RFM"""
	
	period_end = timezone.now().date()
	period_start = period_end - timedelta(days=365)
	
	segmentation = CustomerAnalyticsService.get_customer_segmentation(
		period_start, period_end
	)
	
	# تفاصيل كل تصنيف
	segment_filter = request.GET.get('segment', 'all')
	
	if segment_filter != 'all':
		filtered_customers = segmentation['segment_details'].get(segment_filter, [])
	else:
		filtered_customers = []
		for segment_customers in segmentation['segment_details'].values():
			filtered_customers.extend(segment_customers)
	
	context = {
		'segmentation': segmentation,
		'segment_filter': segment_filter,
		'filtered_customers': filtered_customers
	}
	
	return render(request, 'sales/crm_analytics/segmentation.html', context)


@login_required
def sales_pipeline_view(request):
	"""عرض مسار المبيعات"""
	
	period_end = timezone.now().date()
	period_start = period_end - timedelta(days=90)
	
	if request.GET.get('period_start'):
		period_start = date.fromisoformat(request.GET.get('period_start'))
	if request.GET.get('period_end'):
		period_end = date.fromisoformat(request.GET.get('period_end'))
	
	pipeline = SalesPipelineAnalyzer.get_pipeline_overview(
		period_start, period_end
	)
	
	funnel = SalesPipelineAnalyzer.get_sales_funnel_stages(
		period_start, period_end
	)
	
	context = {
		'period_start': period_start,
		'period_end': period_end,
		'pipeline': pipeline,
		'funnel': funnel
	}
	
	return render(request, 'sales/crm_analytics/pipeline.html', context)


@login_required
def employee_commission_report(request, employee_id=None):
	"""تقرير عمولات الموظفين"""
	
	period_end = timezone.now().date()
	period_start = date(period_end.year, period_end.month, 1)  # بداية الشهر
	
	if request.GET.get('period_start'):
		period_start = date.fromisoformat(request.GET.get('period_start'))
	if request.GET.get('period_end'):
		period_end = date.fromisoformat(request.GET.get('period_end'))
	
	if employee_id:
		# موظف محدد
		employee = get_object_or_404(Employee, id=employee_id)
		commission = CommissionCalculator.calculate_sales_commission(
			employee, period_start, period_end
		)
		
		context = {
			'employee': employee,
			'commission': commission,
			'period_start': period_start,
			'period_end': period_end
		}
		
		return render(request, 'sales/crm_analytics/employee_commission.html', context)
	
	else:
		# جميع الموظفين
		employees = Employee.objects.filter(
			status='active',
			position__title__icontains='مبيعات'
		) | Employee.objects.filter(
			status='active',
			position__title__icontains='مندوب'
		)
		
		commission_list = []
		
		for employee in employees.distinct():
			commission = CommissionCalculator.calculate_sales_commission(
				employee, period_start, period_end
			)
			# عرض جميع الموظفين حتى لو لم تكن لديهم مبيعات
			commission_list.append(commission)
		
		# ترتيب حسب إجمالي العمولة
		commission_list.sort(key=lambda x: x['total_commission'], reverse=True)
		
		context = {
			'commission_list': commission_list,
			'period_start': period_start,
			'period_end': period_end,
			'total_employees': len(commission_list),
			'total_sales': sum(c['total_sales'] for c in commission_list),
			'total_commissions': sum(c['total_commission'] for c in commission_list),
		}
		
		return render(request, 'sales/crm_analytics/commission_report.html', context)


@login_required
def lead_conversion_report(request):
	"""تقرير تحويل العملاء المحتملين"""
	
	period_end = timezone.now().date()
	period_start = period_end - timedelta(days=90)
	
	if request.GET.get('period_start'):
		period_start = date.fromisoformat(request.GET.get('period_start'))
	if request.GET.get('period_end'):
		period_end = date.fromisoformat(request.GET.get('period_end'))
	
	conversion_metrics = LeadConversionTracker.get_conversion_metrics(
		period_start, period_end
	)
	
	# رحلات العملاء التفصيلية
	visited_customers = FieldVisit.objects.filter(
		visit_date__range=[period_start, period_end]
	).values_list('customer_id', flat=True).distinct()
	
	customer_journeys = []
	for customer_id in visited_customers[:50]:  # أول 50
		try:
			customer = Customer.objects.get(id=customer_id)
			journey = LeadConversionTracker.track_lead_journey(customer)
			customer_journeys.append({
				'customer': customer,
				'journey': journey
			})
		except Customer.DoesNotExist:
			continue
	
	context = {
		'period_start': period_start,
		'period_end': period_end,
		'conversion_metrics': conversion_metrics,
		'customer_journeys': customer_journeys
	}
	
	return render(request, 'sales/crm_analytics/lead_conversion.html', context)


@login_required
def export_customers_csv(request):
	"""تصدير بيانات العملاء إلى CSV"""
	
	response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
	response['Content-Disposition'] = 'attachment; filename="customers_analytics.csv"'
	
	# BOM for Excel UTF-8
	response.write('\ufeff')
	
	writer = csv.writer(response)
	writer.writerow([
		'اسم العميل',
		'إجمالي الإيرادات',
		'عدد الطلبات',
		'متوسط قيمة الطلب',
		'قيمة العميل مدى الحياة',
		'درجة الربحية',
		'تصنيف RFM',
		'آخر شراء'
	])
	
	customers = Customer.objects.all()
	
	for customer in customers:
		clv = CustomerAnalyticsService.get_customer_lifetime_value(customer)
		rfm = CustomerAnalyticsService.get_rfm_analysis(customer)
		
		if clv['total_revenue'] > 0:
			writer.writerow([
				customer.name,
				float(clv['total_revenue']),
				clv['total_orders'],
				float(clv['average_order_value']),
				float(clv['lifetime_value']),
				clv['profitability_score'],
				rfm['rfm_segment'],
				clv['last_purchase_date'].strftime('%Y-%m-%d') if clv['last_purchase_date'] else ''
			])
	
	return response


@login_required
def ajax_customer_analytics(request, customer_id):
	"""AJAX: تحليلات عميل محدد"""
	
	try:
		customer = Customer.objects.get(id=customer_id)
		
		clv = CustomerAnalyticsService.get_customer_lifetime_value(customer)
		rfm = CustomerAnalyticsService.get_rfm_analysis(customer)
		journey = LeadConversionTracker.track_lead_journey(customer)
		
		# تحويل التواريخ إلى نصوص
		if clv['first_purchase_date']:
			clv['first_purchase_date'] = clv['first_purchase_date'].isoformat()
		if clv['last_purchase_date']:
			clv['last_purchase_date'] = clv['last_purchase_date'].isoformat()
		if journey['first_contact']:
			journey['first_contact'] = journey['first_contact'].isoformat()
		if journey['conversion_date']:
			journey['conversion_date'] = journey['conversion_date'].isoformat()
		
		# تحويل Decimal إلى float
		for key in ['total_revenue', 'average_order_value', 'lifetime_value']:
			if key in clv:
				clv[key] = float(clv[key])
		
		if 'monetary_total' in rfm:
			rfm['monetary_total'] = float(rfm['monetary_total'])
		
		return JsonResponse({
			'success': True,
			'customer_name': customer.name,
			'clv': clv,
			'rfm': rfm,
			'journey': journey
		})
	
	except Customer.DoesNotExist:
		return JsonResponse({'success': False, 'error': 'العميل غير موجود'}, status=404)
	except Exception as e:
		return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def ajax_update_visit_outcome(request):
	"""AJAX: تحديث نتيجة زيارة"""
	
	if request.method == 'POST':
		try:
			data = json.loads(request.body)
			visit_id = data.get('visit_id')
			outcome = data.get('outcome')
			
			visit = FieldVisit.objects.get(id=visit_id)
			visit.outcome = outcome
			visit.save()
			
			return JsonResponse({'success': True})
		
		except FieldVisit.DoesNotExist:
			return JsonResponse({'success': False, 'error': 'الزيارة غير موجودة'}, status=404)
		except Exception as e:
			return JsonResponse({'success': False, 'error': str(e)}, status=500)
	
	return JsonResponse({'success': False, 'error': 'طلب غير صالح'}, status=400)


@login_required
def top_customers_widget(request):
	"""ويدجت أفضل العملاء (للوحات التحكم)"""
	
	period_end = timezone.now().date()
	period_start = period_end - timedelta(days=365)
	
	segmentation = CustomerAnalyticsService.get_customer_segmentation(
		period_start, period_end
	)
	
	top_customers = segmentation['top_customers'][:10]
	
	return render(request, 'sales/crm_analytics/widgets/top_customers.html', {
		'top_customers': top_customers
	})


@login_required
def sales_performance_widget(request):
	"""ويدجت أداء المبيعات"""
	
	period_end = timezone.now().date()
	period_start = period_end - timedelta(days=30)
	
	pipeline = SalesPipelineAnalyzer.get_pipeline_overview(
		period_start, period_end
	)
	
	return render(request, 'sales/crm_analytics/widgets/sales_performance.html', {
		'pipeline': pipeline
	})
