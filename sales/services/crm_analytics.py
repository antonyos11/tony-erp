"""
نظام التحليلات المتقدم للعملاء - CRM Analytics
Advanced Customer Relationship Management Analytics System

يوفر:
- تحليلات شاملة للعملاء
- تتبع مسار المبيعات (Sales Pipeline)
- حساب العمولات للموظفين
- قيمة العميل مدى الحياة (Customer Lifetime Value - CLV)
- تحليل تحويل العملاء المحتملين (Lead Conversion)
- تصنيف العملاء (RFM Analysis)
"""

from django.db.models import Sum, Count, Avg, Q, F, Max, Min
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from partners.models import Customer
from sales.models import Invoice, FieldVisit
from hr.models import Employee


class CustomerAnalyticsService:
	"""خدمة تحليلات العملاء الشاملة"""
	
	@staticmethod
	def get_customer_lifetime_value(customer: Customer) -> Dict[str, Any]:
		"""
		حساب قيمة العميل مدى الحياة (CLV)
		
		CLV = (متوسط قيمة الطلب × تكرار الشراء × مدة العلاقة)
		
		Args:
			customer: العميل المراد حساب قيمته
			
		Returns:
			Dict يحتوي على:
			- total_revenue: إجمالي الإيرادات
			- average_order_value: متوسط قيمة الطلب
			- order_frequency: تكرار الطلبات (طلبات/شهر)
			- customer_age_months: عمر العلاقة بالشهور
			- lifetime_value: القيمة المقدرة مدى الحياة
			- profitability_score: درجة الربحية (0-100)
		"""
		
		# جميع الفواتير للعميل (غير المحذوفة)
		invoices = Invoice.objects.filter(
			customer=customer,
			is_deleted=False
		).order_by('date')
		
		if not invoices.exists():
			return {
				'total_revenue': Decimal('0'),
				'average_order_value': Decimal('0'),
				'order_frequency': 0,
				'customer_age_months': 0,
				'lifetime_value': Decimal('0'),
				'profitability_score': 0,
				'first_purchase_date': None,
				'last_purchase_date': None,
				'total_orders': 0
			}
		
		# حساب الإيرادات
		total_revenue = sum(inv.total for inv in invoices)
		total_orders = invoices.count()
		average_order_value = total_revenue / total_orders if total_orders > 0 else Decimal('0')
		
		# حساب عمر العميل
		first_purchase = invoices.first().date
		last_purchase = invoices.last().date
		customer_age_days = (last_purchase - first_purchase).days
		customer_age_months = max(customer_age_days / 30.0, 1)  # على الأقل شهر واحد
		
		# تكرار الطلبات (طلبات/شهر)
		order_frequency = total_orders / customer_age_months
		
		# CLV = متوسط قيمة الطلب × تكرار الشراء السنوي × متوسط عمر العميل المتوقع
		# نفترض عمر متوقع 3 سنوات (36 شهر)
		expected_lifetime_months = 36
		annual_frequency = order_frequency * 12
		lifetime_value = Decimal(str(float(average_order_value) * annual_frequency * (expected_lifetime_months / 12)))
		
		# درجة الربحية (0-100)
		# معايير: القيمة الكلية، التكرار، حداثة الشراء
		recency_days = (timezone.now().date() - last_purchase).days
		recency_score = max(0, 100 - (recency_days / 3.65))  # تناقص بمعدل 1% كل 3.65 يوم
		frequency_score = min(100, order_frequency * 20)  # كل 5 طلبات/شهر = 100%
		monetary_score = min(100, float(total_revenue) / 10000)  # كل 10,000 ج.م = 100%
		
		profitability_score = int(
			(recency_score * 0.3) +
			(frequency_score * 0.3) +
			(monetary_score * 0.4)
		)
		
		return {
			'total_revenue': total_revenue,
			'average_order_value': average_order_value,
			'order_frequency': round(order_frequency, 2),
			'customer_age_months': round(customer_age_months, 1),
			'lifetime_value': lifetime_value,
			'profitability_score': profitability_score,
			'first_purchase_date': first_purchase,
			'last_purchase_date': last_purchase,
			'total_orders': total_orders
		}
	
	@staticmethod
	def get_rfm_analysis(customer: Customer) -> Dict[str, Any]:
		"""
		تحليل RFM (Recency, Frequency, Monetary)
		
		تصنيف العملاء حسب:
		- R: حداثة آخر شراء
		- F: تكرار الشراء
		- M: القيمة النقدية
		
		Returns:
			Dict يحتوي على:
			- recency_score: درجة الحداثة (1-5)
			- frequency_score: درجة التكرار (1-5)
			- monetary_score: درجة القيمة (1-5)
			- rfm_segment: التصنيف (champions, loyal, potential, at_risk, lost)
		"""
		
		invoices = Invoice.objects.filter(
			customer=customer,
			is_deleted=False
		).order_by('-date')
		
		if not invoices.exists():
			return {
				'recency_score': 0,
				'frequency_score': 0,
				'monetary_score': 0,
				'rfm_segment': 'inactive',
				'recency_days': 9999,
				'frequency_count': 0,
				'monetary_total': Decimal('0')
			}
		
		# Recency: عدد الأيام منذ آخر شراء
		last_purchase = invoices.first().date
		recency_days = (timezone.now().date() - last_purchase).days
		
		# تسجيل الحداثة (1-5، 5 = أحدث)
		if recency_days <= 30:
			recency_score = 5
		elif recency_days <= 60:
			recency_score = 4
		elif recency_days <= 90:
			recency_score = 3
		elif recency_days <= 180:
			recency_score = 2
		else:
			recency_score = 1
		
		# Frequency: عدد الطلبات في آخر 12 شهر
		one_year_ago = timezone.now().date() - timedelta(days=365)
		frequency_count = invoices.filter(date__gte=one_year_ago).count()
		
		# تسجيل التكرار (1-5، 5 = أكثر تكراراً)
		if frequency_count >= 12:
			frequency_score = 5
		elif frequency_count >= 8:
			frequency_score = 4
		elif frequency_count >= 5:
			frequency_score = 3
		elif frequency_count >= 2:
			frequency_score = 2
		else:
			frequency_score = 1
		
		# Monetary: إجمالي القيمة في آخر 12 شهر
		monetary_total = sum(
			inv.total for inv in invoices.filter(date__gte=one_year_ago)
		)
		
		# تسجيل القيمة (1-5، 5 = أعلى قيمة)
		if monetary_total >= 100000:
			monetary_score = 5
		elif monetary_total >= 50000:
			monetary_score = 4
		elif monetary_total >= 20000:
			monetary_score = 3
		elif monetary_total >= 5000:
			monetary_score = 2
		else:
			monetary_score = 1
		
		# تحديد التصنيف
		avg_score = (recency_score + frequency_score + monetary_score) / 3
		
		if avg_score >= 4.5:
			segment = 'champions'  # أبطال: أفضل العملاء
		elif avg_score >= 4.0:
			segment = 'loyal'  # مخلصون: عملاء دائمون
		elif avg_score >= 3.0:
			segment = 'potential'  # محتملون: يحتاجون اهتمام
		elif avg_score >= 2.0:
			segment = 'at_risk'  # معرضون للفقد: يحتاجون إعادة تنشيط
		else:
			segment = 'lost'  # مفقودون: شبه متوقفون
		
		return {
			'recency_score': recency_score,
			'frequency_score': frequency_score,
			'monetary_score': monetary_score,
			'rfm_segment': segment,
			'recency_days': recency_days,
			'frequency_count': frequency_count,
			'monetary_total': monetary_total
		}
	
	@staticmethod
	def get_customer_segmentation(
		period_start: Optional[date] = None,
		period_end: Optional[date] = None
	) -> Dict[str, Any]:
		"""
		تصنيف جميع العملاء حسب RFM
		
		Returns:
			Dict يحتوي على:
			- segments: عدد العملاء في كل تصنيف
			- top_customers: أفضل 20 عميل
			- at_risk_customers: العملاء المعرضون للفقد
		"""
		
		if not period_end:
			period_end = timezone.now().date()
		if not period_start:
			period_start = period_end - timedelta(days=365)
		
		all_customers = Customer.objects.all()
		
		segments = {
			'champions': [],
			'loyal': [],
			'potential': [],
			'at_risk': [],
			'lost': [],
			'inactive': []
		}
		
		for customer in all_customers:
			rfm = CustomerAnalyticsService.get_rfm_analysis(customer)
			segments[rfm['rfm_segment']].append({
				'customer': customer,
				'rfm_data': rfm
			})
		
		# ترتيب أفضل العملاء حسب القيمة
		all_active = segments['champions'] + segments['loyal'] + segments['potential']
		top_customers = sorted(
			all_active,
			key=lambda x: x['rfm_data']['monetary_total'],
			reverse=True
		)[:20]
		
		return {
			'segments': {
				seg: len(customers) for seg, customers in segments.items()
			},
			'segment_details': segments,
			'top_customers': top_customers,
			'at_risk_customers': segments['at_risk'][:10]
		}


class SalesPipelineAnalyzer:
	"""محلل مسار المبيعات (Sales Pipeline)"""
	
	@staticmethod
	def get_pipeline_overview(
		period_start: Optional[date] = None,
		period_end: Optional[date] = None
	) -> Dict[str, Any]:
		"""
		نظرة عامة على مسار المبيعات
		
		Returns:
			Dict يحتوي على:
			- total_visits: إجمالي الزيارات
			- conversion_rate: معدل التحويل
			- won_visits: الزيارات الناجحة
			- lost_visits: الزيارات الفاشلة
			- follow_up_visits: زيارات تحتاج متابعة
		"""
		
		if not period_end:
			period_end = timezone.now().date()
		if not period_start:
			period_start = period_end - timedelta(days=90)  # آخر 3 أشهر
		
		visits = FieldVisit.objects.filter(
			visit_date__range=[period_start, period_end]
		)
		
		total_visits = visits.count()
		won_visits = visits.filter(outcome='won').count()
		lost_visits = visits.filter(outcome='lost').count()
		follow_up_visits = visits.filter(outcome='follow_up').count()
		demo_visits = visits.filter(outcome='demo').count()
		
		conversion_rate = (won_visits / total_visits * 100) if total_visits > 0 else 0
		
		# تحليل حسب المندوب
		by_employee: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
			'total': 0,
			'won': 0,
			'lost': 0,
			'conversion_rate': 0.0
		})
		
		for visit in visits.select_related('employee'):
			if visit.employee:
				emp_id = visit.employee.id
				by_employee[emp_id]['total'] += 1
				if visit.outcome == 'won':
					by_employee[emp_id]['won'] += 1
				elif visit.outcome == 'lost':
					by_employee[emp_id]['lost'] += 1
				by_employee[emp_id]['employee'] = visit.employee
		
		# حساب معدل التحويل لكل موظف
		for emp_id, data in by_employee.items():
			if data['total'] > 0:
				data['conversion_rate'] = (data['won'] / data['total']) * 100
		
		# ترتيب حسب معدل التحويل
		top_performers = sorted(
			by_employee.values(),
			key=lambda x: x['conversion_rate'],
			reverse=True
		)[:10]
		
		return {
			'total_visits': total_visits,
			'won_visits': won_visits,
			'lost_visits': lost_visits,
			'follow_up_visits': follow_up_visits,
			'demo_visits': demo_visits,
			'conversion_rate': round(conversion_rate, 2),
			'by_employee': dict(by_employee),
			'top_performers': top_performers
		}
	
	@staticmethod
	def get_sales_funnel_stages(
		period_start: Optional[date] = None,
		period_end: Optional[date] = None
	) -> Dict[str, Any]:
		"""
		مراحل قمع المبيعات (Sales Funnel)
		
		Returns:
			مراحل القمع من البداية للنهاية
		"""
		
		if not period_end:
			period_end = timezone.now().date()
		if not period_start:
			period_start = period_end - timedelta(days=90)
		
		visits = FieldVisit.objects.filter(
			visit_date__range=[period_start, period_end]
		)
		
		# عدد العملاء الفريدين في كل مرحلة
		total_prospects = visits.values('customer').distinct().count()
		demo_customers = visits.filter(outcome='demo').values('customer').distinct().count()
		follow_up_customers = visits.filter(outcome='follow_up').values('customer').distinct().count()
		won_customers = visits.filter(outcome='won').values('customer').distinct().count()
		
		return {
			'stages': [
				{
					'name': 'عملاء محتملون',
					'count': total_prospects,
					'percentage': 100
				},
				{
					'name': 'عروض توضيحية',
					'count': demo_customers,
					'percentage': (demo_customers / total_prospects * 100) if total_prospects > 0 else 0
				},
				{
					'name': 'متابعة',
					'count': follow_up_customers,
					'percentage': (follow_up_customers / total_prospects * 100) if total_prospects > 0 else 0
				},
				{
					'name': 'إغلاق ناجح',
					'count': won_customers,
					'percentage': (won_customers / total_prospects * 100) if total_prospects > 0 else 0
				}
			]
		}


class CommissionCalculator:
	"""حاسب العمولات للموظفين"""
	
	@staticmethod
	def calculate_sales_commission(
		employee: Employee,
		period_start: date,
		period_end: date,
		commission_structure: Optional[Dict[str, Any]] = None
	) -> Dict[str, Any]:
		"""
		حساب عمولة المبيعات للموظف
		
		Args:
			employee: الموظف
			period_start: بداية الفترة
			period_end: نهاية الفترة
			commission_structure: هيكل العمولة:
				{
					'base_rate': 0.05,  # 5% عمولة أساسية
					'tier_bonuses': [  # مكافآت حسب الشرائح
						{'min': 0, 'max': 50000, 'rate': 0.05},
						{'min': 50000, 'max': 100000, 'rate': 0.07},
						{'min': 100000, 'rate': 0.10}
					],
					'customer_type_multipliers': {
						'key_account': 1.5  # عملاء رئيسيون × 1.5
					}
				}
		
		Returns:
			Dict يحتوي على:
			- total_sales: إجمالي المبيعات
			- base_commission: العمولة الأساسية
			- tier_bonus: مكافأة الشريحة
			- total_commission: إجمالي العمولة
		"""
		
		if commission_structure is None:
			commission_structure = {
				'base_rate': Decimal('0.05'),  # 5% افتراضي
				'tier_bonuses': [
					{'min': 0, 'max': 50000, 'rate': Decimal('0.05')},
					{'min': 50000, 'max': 100000, 'rate': Decimal('0.07')},
					{'min': 100000, 'rate': Decimal('0.10')}
				],
				'customer_type_multipliers': {
					'key_account': Decimal('1.5')
				}
			}
		
		# الزيارات الناجحة للموظف
		won_visits = FieldVisit.objects.filter(
			employee=employee,
			outcome='won',
			visit_date__range=[period_start, period_end]
		).select_related('customer')
		
		# جمع المبيعات المرتبطة بهذه الزيارات
		# نفترض أن الفاتورة في نفس يوم الزيارة أو بعدها بأسبوع
		total_sales = Decimal('0')
		sales_breakdown = []
		
		for visit in won_visits:
			if visit.customer:
				# فواتير العميل خلال أسبوع من الزيارة
				invoices = Invoice.objects.filter(
					customer=visit.customer,
					date__range=[
						visit.visit_date,
						visit.visit_date + timedelta(days=7)
					],
					is_deleted=False
				)
				
				for invoice in invoices:
					amount = invoice.total
					
					# مضاعف نوع العميل
					multiplier = Decimal('1.0')
					if visit.customer.is_key_account:
						multiplier = commission_structure['customer_type_multipliers'].get(
							'key_account',
							Decimal('1.0')
						)
					
					total_sales += amount
					sales_breakdown.append({
						'invoice': invoice,
						'customer': visit.customer,
						'amount': amount,
						'multiplier': multiplier
					})
		
		# حساب العمولة حسب الشرائح
		base_rate = commission_structure['base_rate']
		base_commission = total_sales * base_rate
		
		# مكافأة الشريحة
		tier_bonus = Decimal('0')
		for tier in commission_structure['tier_bonuses']:
			tier_min = tier['min']
			tier_max = tier.get('max', float('inf'))
			tier_rate = tier['rate']
			
			if total_sales >= tier_min:
				# المبلغ في هذه الشريحة
				tier_amount = min(total_sales, tier_max) - tier_min
				if tier_amount > 0:
					tier_bonus += tier_amount * (tier_rate - base_rate)
		
		total_commission = base_commission + tier_bonus
		
		return {
			'employee': employee,
			'period_start': period_start,
			'period_end': period_end,
			'total_sales': total_sales,
			'base_commission': base_commission,
			'tier_bonus': tier_bonus,
			'total_commission': total_commission,
			'sales_breakdown': sales_breakdown,
			'won_visits_count': won_visits.count()
		}


class LeadConversionTracker:
	"""متتبع تحويل العملاء المحتملين"""
	
	@staticmethod
	def track_lead_journey(customer: Customer) -> Dict[str, Any]:
		"""
		تتبع رحلة العميل من أول زيارة إلى الإغلاق
		
		Returns:
			Dict يحتوي على:
			- first_contact: تاريخ أول اتصال
			- conversion_date: تاريخ التحويل (أول فاتورة)
			- days_to_conversion: عدد الأيام للتحويل
			- visits_count: عدد الزيارات قبل التحويل
			- conversion_status: حالة التحويل (converted, in_progress, lost)
		"""
		
		# أول زيارة
		first_visit = FieldVisit.objects.filter(
			customer=customer
		).order_by('visit_date').first()
		
		# أول فاتورة
		first_invoice = Invoice.objects.filter(
			customer=customer,
			is_deleted=False
		).order_by('date').first()
		
		if not first_visit:
			return {
				'first_contact': None,
				'conversion_date': None,
				'days_to_conversion': None,
				'visits_count': 0,
				'conversion_status': 'no_contact'
			}
		
		first_contact = first_visit.visit_date
		visits_count = FieldVisit.objects.filter(customer=customer).count()
		
		if first_invoice:
			conversion_date = first_invoice.date
			days_to_conversion = (conversion_date - first_contact).days
			conversion_status = 'converted'
		else:
			# تحقق من آخر نتيجة زيارة
			last_visit = FieldVisit.objects.filter(
				customer=customer
			).order_by('-visit_date').first()
			
			if last_visit.outcome == 'lost':
				conversion_status = 'lost'
			else:
				conversion_status = 'in_progress'
			
			conversion_date = None
			days_to_conversion = None
		
		return {
			'first_contact': first_contact,
			'conversion_date': conversion_date,
			'days_to_conversion': days_to_conversion,
			'visits_count': visits_count,
			'conversion_status': conversion_status,
			'last_visit_outcome': FieldVisit.objects.filter(
				customer=customer
			).order_by('-visit_date').first().outcome if visits_count > 0 else None
		}
	
	@staticmethod
	def get_conversion_metrics(
		period_start: Optional[date] = None,
		period_end: Optional[date] = None
	) -> Dict[str, Any]:
		"""
		مؤشرات التحويل الإجمالية
		
		Returns:
			معدلات التحويل والأداء
		"""
		
		if not period_end:
			period_end = timezone.now().date()
		if not period_start:
			period_start = period_end - timedelta(days=90)
		
		# جميع العملاء الذين تمت زيارتهم في الفترة
		visited_customers = FieldVisit.objects.filter(
			visit_date__range=[period_start, period_end]
		).values_list('customer_id', flat=True).distinct()
		
		total_leads = len(visited_customers)
		converted = 0
		lost = 0
		in_progress = 0
		
		total_days_to_conversion = []
		
		for customer_id in visited_customers:
			try:
				customer = Customer.objects.get(id=customer_id)
				journey = LeadConversionTracker.track_lead_journey(customer)
				
				if journey['conversion_status'] == 'converted':
					converted += 1
					if journey['days_to_conversion']:
						total_days_to_conversion.append(journey['days_to_conversion'])
				elif journey['conversion_status'] == 'lost':
					lost += 1
				else:
					in_progress += 1
			except Customer.DoesNotExist:
				continue
		
		avg_days_to_conversion = (
			sum(total_days_to_conversion) / len(total_days_to_conversion)
			if total_days_to_conversion else 0
		)
		
		conversion_rate = (converted / total_leads * 100) if total_leads > 0 else 0
		
		return {
			'total_leads': total_leads,
			'converted': converted,
			'lost': lost,
			'in_progress': in_progress,
			'conversion_rate': round(conversion_rate, 2),
			'avg_days_to_conversion': round(avg_days_to_conversion, 1)
		}
