"""
نظام تكامل الأجور مع الإنتاج
Wage-Production Integration System

يوفر:
- حساب الأجور بالقطعة (Piece Rate)
- مكافآت الإنتاجية (Productivity Bonuses)
- تتبع الإنتاج الفردي
- تكاليف العمالة الفعلية
"""

from django.db.models import Sum, F, Q, Count, Avg, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
import logging

from hr.models import Employee, Payroll, AttendanceRecord
from production.models import ProductionOrder, ProductionOrderStage, ProductionStage

logger = logging.getLogger(__name__)


class ProductionWageCalculator:
	"""حاسب الأجور بالقطعة والإنتاجية"""
	
	@staticmethod
	def calculate_piece_rate_wage(
		employee: Employee,
		production_records: List[Dict],
		piece_rate_settings: Optional[Dict] = None
	) -> Dict[str, Any]:
		"""
		حساب الأجر بناءً على الإنتاج الفعلي
		
		الصيغة:
		Wage = Σ (Quantity Produced × Rate per Piece)
		
		Args:
			employee: الموظف
			production_records: سجلات الإنتاج
				[
					{
						'product': Product,
						'quantity': int,
						'stage': ProductionStage,
						'date': date
					}
				]
			piece_rate_settings: إعدادات الأجر بالقطعة
				{
					'default_rate': Decimal,  # السعر الافتراضي للقطعة
					'product_rates': {product_id: rate},  # أسعار محددة للمنتجات
					'stage_multipliers': {stage_id: multiplier}  # معاملات المراحل
				}
		
		Returns:
			{
				'total_wage': Decimal,
				'total_pieces': int,
				'breakdown': [
					{
						'product': Product,
						'quantity': int,
						'rate': Decimal,
						'wage': Decimal
					}
				],
				'daily_summary': {...}
			}
		"""
		
		if piece_rate_settings is None:
			piece_rate_settings = {
				'default_rate': Decimal('1.00'),
				'product_rates': {},
				'stage_multipliers': {}
			}
		
		breakdown = []
		total_wage = Decimal('0')
		total_pieces = 0
		daily_totals = {}
		
		for record in production_records:
			product = record['product']
			quantity = record['quantity']
			stage = record.get('stage')
			record_date = record['date']
			
			# الحصول على السعر
			rate = piece_rate_settings['product_rates'].get(
				product.id,
				piece_rate_settings['default_rate']
			)
			
			# معامل المرحلة (صعوبة المرحلة)
			if stage:
				multiplier = piece_rate_settings['stage_multipliers'].get(stage.id, Decimal('1.0'))
				rate = rate * multiplier
			
			# حساب الأجر
			wage = quantity * rate
			total_wage += wage
			total_pieces += quantity
			
			breakdown.append({
				'product': product,
				'quantity': quantity,
				'rate': rate,
				'wage': wage,
				'stage': stage,
				'date': record_date
			})
			
			# التجميع اليومي
			date_key = record_date.isoformat()
			if date_key not in daily_totals:
				daily_totals[date_key] = {
					'pieces': 0,
					'wage': Decimal('0'),
					'date': record_date
				}
			daily_totals[date_key]['pieces'] += quantity
			daily_totals[date_key]['wage'] += wage
		
		return {
			'employee': employee,
			'total_wage': total_wage,
			'total_pieces': total_pieces,
			'average_rate': total_wage / total_pieces if total_pieces > 0 else Decimal('0'),
			'breakdown': breakdown,
			'daily_summary': list(daily_totals.values())
		}
	
	@staticmethod
	def calculate_productivity_bonus(
		employee: Employee,
		period_start: date,
		period_end: date,
		target_units: int,
		bonus_structure: Optional[Dict] = None
	) -> Dict[str, Any]:
		"""
		حساب مكافأة الإنتاجية
		
		المعايير:
		1. الكمية المنتجة مقابل الهدف
		2. جودة الإنتاج (نسبة التالف)
		3. الالتزام بالمواعيد
		
		Args:
			employee: الموظف
			period_start: بداية الفترة
			period_end: نهاية الفترة
			target_units: الهدف بالقطع
			bonus_structure: هيكل المكافآت
				{
					'quantity_thresholds': [
						{'min': 100, 'max': 120, 'bonus_pct': 5},
						{'min': 120, 'max': 150, 'bonus_pct': 10},
						{'min': 150, 'bonus_pct': 15}
					],
					'quality_bonus': {
						'scrap_rate_max': 0.02,  # أقل من 2% تالف
						'bonus_amount': Decimal('500')
					},
					'timeliness_bonus': {
						'on_time_pct_min': 0.95,  # 95% في الموعد
						'bonus_amount': Decimal('300')
					}
				}
		"""
		
		if bonus_structure is None:
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
		
		# الحصول على سجلات الإنتاج من ProductionOrderStage
		# افتراضياً نحتاج نموذج جديد لتتبع الإنتاج الفردي
		# هنا نستخدم منطق مبسط
		
		from production.models import ProductionOrder
		
		# الأوامر التي عمل عليها الموظف
		orders = ProductionOrder.objects.filter(
			supervisor=employee,
			actual_start_date__gte=period_start,
			actual_end_date__lte=period_end,
			status='completed'
		)
		
		total_produced = orders.aggregate(
			total=Sum('produced_quantity')
		)['total'] or 0
		
		total_scrap = orders.aggregate(
			total=Sum('scrap_quantity')
		)['total'] or 0
		
		# 1. مكافأة الكمية
		achievement_pct = (total_produced / target_units * 100) if target_units > 0 else 0
		quantity_bonus = Decimal('0')
		
		for threshold in bonus_structure['quantity_thresholds']:
			min_pct = threshold.get('min', 0)
			max_pct = threshold.get('max', float('inf'))
			
			if min_pct <= achievement_pct < max_pct:
				bonus_pct = Decimal(str(threshold['bonus_pct']))
				quantity_bonus = employee.basic_salary * (bonus_pct / 100)
				break
		
		# 2. مكافأة الجودة
		scrap_rate = (total_scrap / (total_produced + total_scrap)) if (total_produced + total_scrap) > 0 else 0
		quality_bonus = Decimal('0')
		
		quality_settings = bonus_structure.get('quality_bonus', {})
		if scrap_rate <= quality_settings.get('scrap_rate_max', 0.02):
			quality_bonus = quality_settings.get('bonus_amount', Decimal('0'))
		
		# 3. مكافأة الالتزام بالمواعيد
		on_time_count = orders.filter(
			actual_end_date__lte=F('planned_end_date')
		).count()
		
		total_count = orders.count()
		on_time_pct = (on_time_count / total_count) if total_count > 0 else 0
		timeliness_bonus = Decimal('0')
		
		timeliness_settings = bonus_structure.get('timeliness_bonus', {})
		if on_time_pct >= timeliness_settings.get('on_time_pct_min', 0.95):
			timeliness_bonus = timeliness_settings.get('bonus_amount', Decimal('0'))
		
		# الإجمالي
		total_bonus = quantity_bonus + quality_bonus + timeliness_bonus
		
		return {
			'employee': employee,
			'period': {
				'start': period_start,
				'end': period_end
			},
			'production_stats': {
				'target': target_units,
				'produced': int(total_produced),
				'scrap': int(total_scrap),
				'achievement_pct': achievement_pct,
				'scrap_rate': scrap_rate * 100,
				'on_time_pct': on_time_pct * 100
			},
			'bonuses': {
				'quantity': quantity_bonus,
				'quality': quality_bonus,
				'timeliness': timeliness_bonus,
				'total': total_bonus
			}
		}


class ProductionLaborCostTracker:
	"""متتبع تكاليف العمالة في الإنتاج"""
	
	@staticmethod
	def calculate_actual_labor_cost(
		production_order: ProductionOrder,
		labor_records: Optional[List[Dict]] = None
	) -> Dict[str, Any]:
		"""
		حساب تكلفة العمالة الفعلية لأمر إنتاج
		
		الطرق:
		1. Labor Hours × Hourly Rate
		2. Direct Assignment (مباشر)
		3. Overhead Allocation (تخصيص)
		
		Args:
			production_order: أمر الإنتاج
			labor_records: سجلات العمالة
				[
					{
						'employee': Employee,
						'hours': Decimal,
						'hourly_rate': Decimal,
						'date': date
					}
				]
		
		Returns:
			{
				'direct_labor_cost': Decimal,
				'indirect_labor_cost': Decimal,
				'total_labor_cost': Decimal,
				'labor_hours': Decimal,
				'employees_involved': int,
				'breakdown': [...]
			}
		"""
		
		if labor_records is None:
			# محاولة الحصول من سجلات الحضور
			labor_records = []
			
			# افتراضياً نستخدم ساعات العمل من الحضور
			if production_order.actual_start_date and production_order.actual_end_date:
				# الموظفين في القسم الإنتاجي
				from hr.models import Employee, AttendanceRecord
				
				employees = Employee.objects.filter(
					department__name__icontains='إنتاج',
					status='active'
				)
				
				for emp in employees:
					# حساب ساعات العمل في الفترة
					attendance = AttendanceRecord.objects.filter(
						employee=emp,
						date__gte=production_order.actual_start_date,
						date__lte=production_order.actual_end_date
					)
					
					# حساب مبسط: 8 ساعات/يوم
					days_worked = attendance.values('date').distinct().count()
					hours = Decimal(str(days_worked * 8))
					
					# معدل الساعة
					monthly_hours = Decimal('160')  # 20 يوم × 8 ساعات
					hourly_rate = emp.total_salary / monthly_hours
					
					if hours > 0:
						labor_records.append({
							'employee': emp,
							'hours': hours,
							'hourly_rate': hourly_rate,
							'date': production_order.actual_start_date
						})
		
		direct_labor_cost = Decimal('0')
		total_hours = Decimal('0')
		breakdown = []
		employees_set = set()
		
		for record in labor_records:
			employee = record['employee']
			hours = record['hours']
			rate = record['hourly_rate']
			
			cost = hours * rate
			direct_labor_cost += cost
			total_hours += hours
			employees_set.add(employee.id)
			
			breakdown.append({
				'employee': employee,
				'hours': hours,
				'rate': rate,
				'cost': cost,
				'date': record.get('date')
			})
		
		# التكاليف غير المباشرة (overhead)
		# افتراضياً 30% من التكاليف المباشرة
		overhead_rate = Decimal('0.30')
		indirect_labor_cost = direct_labor_cost * overhead_rate
		
		total_cost = direct_labor_cost + indirect_labor_cost
		
		return {
			'production_order': production_order,
			'direct_labor_cost': direct_labor_cost,
			'indirect_labor_cost': indirect_labor_cost,
			'total_labor_cost': total_cost,
			'labor_hours': total_hours,
			'employees_involved': len(employees_set),
			'average_hourly_cost': total_cost / total_hours if total_hours > 0 else Decimal('0'),
			'breakdown': breakdown
		}
	
	@staticmethod
	def allocate_labor_cost_by_stage(
		production_order: ProductionOrder
	) -> Dict[str, Any]:
		"""
		توزيع تكاليف العمالة على المراحل
		
		الطريقة:
		- توزيع بناءً على ساعات العمل في كل مرحلة
		- أو بناءً على نسبة الإنجاز
		"""
		
		stages = production_order.order_stages.all()
		
		# الحصول على إجمالي التكلفة
		total_labor_cost = production_order.actual_labor_cost
		
		if total_labor_cost == 0:
			# حساب من جديد
			cost_data = ProductionLaborCostTracker.calculate_actual_labor_cost(production_order)
			total_labor_cost = cost_data['total_labor_cost']
		
		# التوزيع بناءً على الوقت الفعلي
		stage_allocations = []
		total_duration = Decimal('0')
		
		for stage in stages:
			if stage.actual_start_date and stage.actual_end_date:
				duration = (stage.actual_end_date - stage.actual_start_date).total_seconds() / 3600
				duration = Decimal(str(duration))
			else:
				duration = Decimal('0')
			
			total_duration += duration
			
			stage_allocations.append({
				'stage': stage,
				'duration_hours': duration,
				'allocated_cost': Decimal('0')  # سيتم حسابه لاحقاً
			})
		
		# حساب التكلفة لكل مرحلة
		if total_duration > 0:
			for allocation in stage_allocations:
				allocation['allocated_cost'] = (
					allocation['duration_hours'] / total_duration
				) * total_labor_cost
		
		return {
			'production_order': production_order,
			'total_labor_cost': total_labor_cost,
			'total_duration_hours': total_duration,
			'stage_allocations': stage_allocations
		}


class EmployeeProductivityAnalyzer:
	"""محلل إنتاجية الموظفين"""
	
	@staticmethod
	def calculate_employee_productivity(
		employee: Employee,
		period_start: date,
		period_end: date
	) -> Dict[str, Any]:
		"""
		حساب مؤشرات إنتاجية الموظف
		
		المؤشرات:
		1. Units per Hour (قطع/ساعة)
		2. Quality Rate (نسبة الجودة)
		3. Efficiency Score (درجة الكفاءة)
		4. Cost per Unit (تكلفة/قطعة)
		
		Returns:
			{
				'units_per_hour': float,
				'quality_rate': float,
				'efficiency_score': float,
				'cost_per_unit': Decimal,
				'total_units': int,
				'total_hours': Decimal,
				'classification': str  # 'excellent', 'good', 'average', 'poor'
			}
		"""
		
		# الحصول على أوامر الإنتاج
		orders = ProductionOrder.objects.filter(
			supervisor=employee,
			actual_start_date__gte=period_start,
			actual_end_date__lte=period_end
		)
		
		total_produced = orders.aggregate(
			total=Sum('produced_quantity')
		)['total'] or 0
		
		total_scrap = orders.aggregate(
			total=Sum('scrap_quantity')
		)['total'] or 0
		
		# ساعات العمل
		attendance = AttendanceRecord.objects.filter(
			employee=employee,
			date__gte=period_start,
			date__lte=period_end,
			record_type='check_in'
		)
		
		days_worked = attendance.values('date').distinct().count()
		total_hours = Decimal(str(days_worked * 8))  # مبسط
		
		# المؤشرات
		units_per_hour = float(total_produced / total_hours) if total_hours > 0 else 0.0
		
		quality_rate = (
			total_produced / (total_produced + total_scrap) * 100
		) if (total_produced + total_scrap) > 0 else 100.0
		
		# درجة الكفاءة (0-100)
		# معيار: 10 قطع/ساعة = 100%
		standard_rate = 10.0
		efficiency_score = min(100, (units_per_hour / standard_rate) * 100)
		
		# تكلفة الوحدة
		labor_cost = employee.total_salary / Decimal('160') * total_hours  # راتب الفترة
		cost_per_unit = labor_cost / Decimal(str(total_produced)) if total_produced > 0 else Decimal('0')
		
		# التصنيف
		if efficiency_score >= 90 and quality_rate >= 98:
			classification = 'excellent'
		elif efficiency_score >= 75 and quality_rate >= 95:
			classification = 'good'
		elif efficiency_score >= 60 and quality_rate >= 90:
			classification = 'average'
		else:
			classification = 'poor'
		
		return {
			'employee': employee,
			'period': {'start': period_start, 'end': period_end},
			'units_per_hour': round(units_per_hour, 2),
			'quality_rate': round(quality_rate, 2),
			'efficiency_score': round(efficiency_score, 2),
			'cost_per_unit': cost_per_unit,
			'total_units': int(total_produced),
			'total_hours': total_hours,
			'total_scrap': int(total_scrap),
			'classification': classification
		}
	
	@staticmethod
	def get_productivity_ranking(
		department_id: Optional[int] = None,
		period_days: int = 30
	) -> List[Dict]:
		"""
		ترتيب الموظفين حسب الإنتاجية
		
		Args:
			department_id: قسم محدد (اختياري)
			period_days: فترة التحليل
		
		Returns:
			قائمة الموظفين مرتبة حسب الإنتاجية
		"""
		
		from hr.models import Employee
		
		end_date = date.today()
		start_date = end_date - timedelta(days=period_days)
		
		employees = Employee.objects.filter(status='active')
		
		if department_id:
			employees = employees.filter(department_id=department_id)
		
		rankings = []
		
		for emp in employees:
			productivity = EmployeeProductivityAnalyzer.calculate_employee_productivity(
				emp, start_date, end_date
			)
			
			if productivity['total_units'] > 0:  # فقط من لديه إنتاج
				rankings.append(productivity)
		
		# الترتيب حسب درجة الكفاءة
		rankings.sort(key=lambda x: x['efficiency_score'], reverse=True)
		
		# إضافة الترتيب
		for i, item in enumerate(rankings, 1):
			item['rank'] = i
		
		return rankings


class WagePayrollIntegrator:
	"""مُدمِج الأجور مع نظام الرواتب"""
	
	@staticmethod
	def generate_payroll_from_production(
		employee: Employee,
		period_start: date,
		period_end: date,
		wage_type: str = 'mixed'  # 'salary', 'piece_rate', 'mixed'
	) -> Dict[str, Any]:
		"""
		إنشاء كشف راتب بناءً على الإنتاج
		
		الأنواع:
		- salary: راتب ثابت فقط
		- piece_rate: أجر بالقطعة فقط
		- mixed: راتب أساسي + أجر بالقطعة
		
		Args:
			employee: الموظف
			period_start: بداية الفترة
			period_end: نهاية الفترة
			wage_type: نوع الأجر
		
		Returns:
			{
				'basic_salary': Decimal,
				'piece_rate_wage': Decimal,
				'productivity_bonus': Decimal,
				'total_earnings': Decimal,
				'deductions': Decimal,
				'net_salary': Decimal
			}
		"""
		
		# الراتب الأساسي
		days_in_month = 30
		period_days = (period_end - period_start).days + 1
		
		if wage_type in ['salary', 'mixed']:
			basic_salary = employee.total_salary * (Decimal(str(period_days)) / Decimal(str(days_in_month)))
		else:
			basic_salary = Decimal('0')
		
		# أجر القطعة
		piece_rate_wage = Decimal('0')
		if wage_type in ['piece_rate', 'mixed']:
			# الحصول على سجلات الإنتاج
			# افتراضياً نحتاج جدول EmployeeProductionRecord
			# هنا نستخدم تقدير مبسط
			productivity = EmployeeProductivityAnalyzer.calculate_employee_productivity(
				employee, period_start, period_end
			)
			
			# افتراض: 2 ج.م/قطعة
			piece_rate = Decimal('2.00')
			piece_rate_wage = Decimal(str(productivity['total_units'])) * piece_rate
		
		# مكافأة الإنتاجية
		bonus_data = ProductionWageCalculator.calculate_productivity_bonus(
			employee,
			period_start,
			period_end,
			target_units=1000  # هدف افتراضي
		)
		productivity_bonus = bonus_data['bonuses']['total']
		
		# الإجمالي
		total_earnings = basic_salary + piece_rate_wage + productivity_bonus
		
		# الخصومات (تأمينات اجتماعية، غياب، إلخ)
		# مبسط: 10%
		deductions = total_earnings * Decimal('0.10')
		
		# الصافي
		net_salary = total_earnings - deductions
		
		return {
			'employee': employee,
			'period': {'start': period_start, 'end': period_end},
			'wage_type': wage_type,
			'basic_salary': basic_salary,
			'piece_rate_wage': piece_rate_wage,
			'productivity_bonus': productivity_bonus,
			'total_earnings': total_earnings,
			'deductions': deductions,
			'net_salary': net_salary,
			'breakdown': {
				'basic': float(basic_salary),
				'piece_rate': float(piece_rate_wage),
				'bonus': float(productivity_bonus)
			}
		}
	
	@staticmethod
	def create_payroll_entry(
		employee: Employee,
		wage_data: Dict
	) -> 'Payroll':
		"""
		إنشاء سجل في جدول Payroll
		
		Args:
			employee: الموظف
			wage_data: بيانات الأجر من generate_payroll_from_production
		
		Returns:
			كائن Payroll
		"""
		
		from hr.models import Payroll
		from datetime import datetime
		
		payroll = Payroll.objects.create(
			employee=employee,
			month=wage_data['period']['end'].month,
			year=wage_data['period']['end'].year,
			basic_salary=wage_data['basic_salary'],
			allowances=wage_data['piece_rate_wage'] + wage_data['productivity_bonus'],
			deductions=wage_data['deductions'],
			net_salary=wage_data['net_salary'],
			status='calculated',
			notes=f"نوع الأجر: {wage_data['wage_type']}\n"
			      f"أجر القطعة: {wage_data['piece_rate_wage']}\n"
			      f"مكافأة الإنتاجية: {wage_data['productivity_bonus']}"
		)
		
		return payroll
