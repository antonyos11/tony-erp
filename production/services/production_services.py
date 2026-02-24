"""
Production Services - Enhanced Costing and Planning
خدمات الإنتاج - التكلفة والتخطيط المحسّن

Phase 1: Core production costing documentation and stabilization
Phase 2: Production planning and capacity management
"""

from django.db.models import Sum, F, Q, Count, Avg, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from production.models import (
    ProductionOrder, ProductionOrderStage, ProductionWorkCenter,
    ProductionTimeLog, MaterialConsumption, BillOfMaterials, BOMItem,
    ProductionQualityCheck, ProductionCostAnalysis
)
from inventory.models import Product, Stock
from accounting.models import CostCenter, JournalEntryItem


class ProductionCostingService:
    """
    خدمة حساب تكاليف الإنتاج
    
    يحسب:
    - تكلفة المواد المباشرة
    - تكلفة العمالة المباشرة
    - التكاليف الإضافية (Overhead)
    - التكلفة الإجمالية للوحدة
    """
    
    @staticmethod
    def calculate_production_order_cost(order_id: int) -> Dict[str, Decimal]:
        """
        حساب تكلفة أمر إنتاج محدد
        
        Returns:
            dict: {
                'material_cost': Decimal,
                'labor_cost': Decimal,
                'overhead_cost': Decimal,
                'total_cost': Decimal,
                'unit_cost': Decimal,
                'quantity': Decimal
            }
        """
        try:
            order = ProductionOrder.objects.get(id=order_id)
        except ProductionOrder.DoesNotExist:
            return {
                'material_cost': Decimal('0'),
                'labor_cost': Decimal('0'),
                'overhead_cost': Decimal('0'),
                'total_cost': Decimal('0'),
                'unit_cost': Decimal('0'),
                'quantity': Decimal('0')
            }
        
        # 1. تكلفة المواد المباشرة (من MaterialConsumption)
        material_cost = MaterialConsumption.objects.filter(
            production_order=order
        ).aggregate(
            total=Sum(F('quantity') * F('unit_cost'))
        )['total'] or Decimal('0')
        
        # 2. تكلفة العمالة المباشرة (من ProductionTimeLog)
        labor_cost = ProductionTimeLog.objects.filter(
            production_order=order
        ).aggregate(
            total=Sum(F('hours_worked') * F('hourly_rate'))
        )['total'] or Decimal('0')
        
        # 3. التكاليف الإضافية (نسبة من تكلفة العمالة أو ساعات العمل)
        # يمكن تخصيصها حسب طريقة الشركة
        overhead_cost = ProductionCostingService._calculate_overhead(
            order=order,
            material_cost=material_cost,
            labor_cost=labor_cost
        )
        
        total_cost = material_cost + labor_cost + overhead_cost
        quantity = order.quantity or Decimal('1')
        unit_cost = total_cost / quantity if quantity > 0 else Decimal('0')
        
        return {
            'material_cost': material_cost,
            'labor_cost': labor_cost,
            'overhead_cost': overhead_cost,
            'total_cost': total_cost,
            'unit_cost': unit_cost,
            'quantity': quantity
        }
    
    @staticmethod
    def _calculate_overhead(order, material_cost: Decimal, labor_cost: Decimal) -> Decimal:
        """
        حساب التكاليف الإضافية (Overhead)
        
        الطرق المدعومة:
        1. نسبة من تكلفة العمالة (150% مثلاً)
        2. نسبة من تكلفة المواد
        3. معدل ثابت لكل ساعة عمل
        """
        # الطريقة الافتراضية: 100% من تكلفة العمالة
        # يمكن تغييرها من الإعدادات
        overhead_rate = Decimal('1.0')  # 100%
        
        # يمكن لاحقاً ربطها بنوع المنتج أو مركز العمل
        return labor_cost * overhead_rate
    
    @staticmethod
    def update_product_standard_cost(product_id: int) -> Decimal:
        """
        تحديث التكلفة المعيارية للمنتج بناءً على BOM
        
        Returns:
            Decimal: التكلفة المعيارية للوحدة
        """
        try:
            product = Product.objects.get(id=product_id)
            bom = BillOfMaterials.objects.filter(
                product=product,
                is_active=True
            ).first()
            
            if not bom:
                return product.cost or Decimal('0')
            
            # حساب تكلفة المواد من BOM
            material_cost = BOMItem.objects.filter(
                bom=bom
            ).aggregate(
                total=Sum(F('quantity') * F('material__cost'))
            )['total'] or Decimal('0')
            
            # تكلفة العمالة من BOM (إن وُجدت)
            labor_cost = bom.labor_cost or Decimal('0')
            
            # التكاليف الإضافية
            overhead_cost = bom.overhead_cost or Decimal('0')
            
            standard_cost = material_cost + labor_cost + overhead_cost
            
            # تحديث تكلفة المنتج
            product.cost = standard_cost
            product.save(update_fields=['cost'])
            
            return standard_cost
            
        except Product.DoesNotExist:
            return Decimal('0')


class ProductionPlanningService:
    """
    خدمة تخطيط الإنتاج
    
    Phase 2 Implementation:
    - جدولة أوامر الإنتاج
    - تحليل القدرات (Capacity Planning)
    - اكتشاف الاختناقات (Bottlenecks)
    """
    
    @staticmethod
    def get_work_center_utilization(
        work_center_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        حساب استخدام مركز العمل خلال فترة
        
        Returns:
            dict: {
                'capacity_hours': Decimal,
                'scheduled_hours': Decimal,
                'actual_hours': Decimal,
                'utilization_pct': Decimal,
                'available_hours': Decimal
            }
        """
        try:
            work_center = ProductionWorkCenter.objects.get(id=work_center_id)
        except ProductionWorkCenter.DoesNotExist:
            return {
                'capacity_hours': Decimal('0'),
                'scheduled_hours': Decimal('0'),
                'actual_hours': Decimal('0'),
                'utilization_pct': Decimal('0'),
                'available_hours': Decimal('0')
            }
        
        # حساب الطاقة الإنتاجية (Capacity)
        days = (end_date - start_date).days + 1
        capacity_hours = work_center.capacity_per_day * days
        
        # الساعات المجدولة (من أوامر الإنتاج قيد التنفيذ)
        scheduled_hours = ProductionOrderStage.objects.filter(
            work_center=work_center,
            production_order__scheduled_start_date__lte=end_date,
            production_order__scheduled_end_date__gte=start_date,
            production_order__status__in=['confirmed', 'in_progress']
        ).aggregate(
            total=Sum('estimated_hours')
        )['total'] or Decimal('0')
        
        # الساعات الفعلية (من سجلات الوقت)
        actual_hours = ProductionTimeLog.objects.filter(
            work_center=work_center,
            date__gte=start_date.date(),
            date__lte=end_date.date()
        ).aggregate(
            total=Sum('hours_worked')
        )['total'] or Decimal('0')
        
        utilization_pct = (actual_hours / capacity_hours * 100) if capacity_hours > 0 else Decimal('0')
        available_hours = capacity_hours - scheduled_hours
        
        return {
            'capacity_hours': capacity_hours,
            'scheduled_hours': scheduled_hours,
            'actual_hours': actual_hours,
            'utilization_pct': utilization_pct,
            'available_hours': available_hours,
            'is_bottleneck': scheduled_hours > capacity_hours
        }
    
    @staticmethod
    def identify_bottlenecks(start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        اكتشاف مراكز العمل المكتظة (Bottlenecks)
        
        Returns:
            list of dicts: مراكز العمل المتجاوزة للطاقة
        """
        work_centers = ProductionWorkCenter.objects.filter(is_active=True)
        bottlenecks = []
        
        for wc in work_centers:
            util = ProductionPlanningService.get_work_center_utilization(
                wc.id, start_date, end_date
            )
            
            if util['is_bottleneck']:
                bottlenecks.append({
                    'work_center': wc,
                    'overload_hours': util['scheduled_hours'] - util['capacity_hours'],
                    'utilization_pct': util['utilization_pct'],
                    'capacity_hours': util['capacity_hours'],
                    'scheduled_hours': util['scheduled_hours']
                })
        
        # ترتيب حسب الزيادة
        bottlenecks.sort(key=lambda x: x['overload_hours'], reverse=True)
        
        return bottlenecks


class WorkerProductivityService:
    """
    خدمة حساب إنتاجية العمال
    
    Phase 3: سيتم ربطها بالأجور
    """
    
    @staticmethod
    def calculate_worker_productivity(
        employee_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        حساب إنتاجية عامل خلال فترة
        
        Returns:
            dict: {
                'total_hours': Decimal,
                'units_produced': Decimal,
                'productivity_rate': Decimal (units/hour),
                'orders_count': int,
                'labor_cost': Decimal
            }
        """
        from hr.models import Employee
        
        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            return {
                'total_hours': Decimal('0'),
                'units_produced': Decimal('0'),
                'productivity_rate': Decimal('0'),
                'orders_count': 0,
                'labor_cost': Decimal('0')
            }
        
        # الساعات العاملة
        time_logs = ProductionTimeLog.objects.filter(
            employee=employee,
            date__gte=start_date.date(),
            date__lte=end_date.date()
        )
        
        total_hours = time_logs.aggregate(
            total=Sum('hours_worked')
        )['total'] or Decimal('0')
        
        # الوحدات المنتجة (من الأوامر المكتملة)
        completed_orders = ProductionOrder.objects.filter(
            time_logs__in=time_logs,
            status='completed'
        ).distinct()
        
        units_produced = completed_orders.aggregate(
            total=Sum('quantity_produced')
        )['total'] or Decimal('0')
        
        productivity_rate = units_produced / total_hours if total_hours > 0 else Decimal('0')
        
        # تكلفة العمالة
        labor_cost = time_logs.aggregate(
            total=Sum(F('hours_worked') * F('hourly_rate'))
        )['total'] or Decimal('0')
        
        return {
            'total_hours': total_hours,
            'units_produced': units_produced,
            'productivity_rate': productivity_rate,
            'orders_count': completed_orders.count(),
            'labor_cost': labor_cost,
            'avg_hourly_rate': labor_cost / total_hours if total_hours > 0 else Decimal('0')
        }
