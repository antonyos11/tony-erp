"""
خدمة محاسبة التكاليف الكاملة
Full Cost Accounting Service
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta
from django.db.models import Sum, F, Q, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone

from production.models import (
    ProductionOrder, BillOfMaterials, BOMItem, MaterialConsumption,
    ProductionTimeLog, ProductionWorkCenter
)
from inventory.models import Product, StockBatch
from hr.models import Employee
from accounting.models import Account, CostCenter


class ProductCostingService:
    """خدمة حساب تكلفة المنتجات"""
    
    @staticmethod
    def calculate_material_cost(product: Product, quantity: Decimal = Decimal('1')) -> Dict:
        """
        حساب تكلفة المواد الخام لمنتج معين
        
        Returns:
            {
                'total_cost': Decimal,
                'cost_per_unit': Decimal,
                'materials': [{'material': Product, 'quantity': Decimal, 'cost': Decimal}]
            }
        """
        # البحث عن BOM للمنتج
        try:
            bom = BillOfMaterials.objects.filter(
                product=product, 
                is_active=True
            ).first()
            
            if not bom:
                return {
                    'total_cost': Decimal('0'),
                    'cost_per_unit': Decimal('0'),
                    'materials': [],
                    'error': 'لا يوجد BOM لهذا المنتج'
                }
            
            materials = []
            total_cost = Decimal('0')
            
            for item in bom.items.all():
                # حساب كمية المادة المطلوبة
                item_quantity = (item.quantity / bom.base_quantity) * quantity
                
                # حساب تكلفة المادة
                material_cost = item.material.cost or Decimal('0')
                item_total_cost = material_cost * item_quantity
                
                total_cost += item_total_cost
                
                materials.append({
                    'material': item.material,
                    'material_name': item.material.name,
                    'quantity': item_quantity,
                    'unit_cost': material_cost,
                    'total_cost': item_total_cost,
                    'uom': item.unit_of_measure
                })
            
            return {
                'total_cost': total_cost,
                'cost_per_unit': total_cost / quantity if quantity > 0 else Decimal('0'),
                'materials': materials,
                'bom': bom
            }
            
        except Exception as e:
            return {
                'total_cost': Decimal('0'),
                'cost_per_unit': Decimal('0'),
                'materials': [],
                'error': str(e)
            }
    
    @staticmethod
    def calculate_direct_labor_cost(
        product: Product, 
        quantity: Decimal = Decimal('1'),
        production_order: Optional[ProductionOrder] = None
    ) -> Dict:
        """
        حساب تكلفة العمالة المباشرة
        
        Returns:
            {
                'total_cost': Decimal,
                'cost_per_unit': Decimal,
                'labor_hours': Decimal,
                'workers': [{'worker': Employee, 'hours': Decimal, 'cost': Decimal}]
            }
        """
        total_cost = Decimal('0')
        total_hours = Decimal('0')
        workers_data = []
        
        if production_order:
            # حساب من أمر إنتاج فعلي
            time_logs = ProductionTimeLog.objects.filter(
                production_order=production_order
            ).select_related('employee', 'work_center')
            
            for log in time_logs:
                hours = log.hours_worked
                # حساب تكلفة الساعة للعامل
                hourly_rate = log.hourly_rate or Decimal('0')
                cost = hours * hourly_rate
                
                total_hours += hours
                total_cost += cost
                
                workers_data.append({
                    'worker': log.employee,
                    'worker_name': log.employee.arabic_name,
                    'hours': hours,
                    'hourly_rate': hourly_rate,
                    'cost': cost
                })
        else:
            # حساب من BOM (تقديري)
            try:
                bom = BillOfMaterials.objects.filter(
                    product=product,
                    is_active=True
                ).first()
                
                if bom:
                    # حساب من المراحل
                    for bom_stage in bom.stages.all():
                        stage = bom_stage.stage
                        stage_hours = stage.estimated_hours or Decimal('0')
                        labor_cost = stage.labor_cost_per_unit or Decimal('0')
                        
                        # تعديل حسب الكمية
                        adjusted_hours = (stage_hours / bom.base_quantity) * quantity
                        adjusted_cost = (labor_cost / bom.base_quantity) * quantity
                        
                        total_hours += adjusted_hours
                        total_cost += adjusted_cost
            except:
                pass
        
        return {
            'total_cost': total_cost,
            'cost_per_unit': total_cost / quantity if quantity > 0 else Decimal('0'),
            'labor_hours': total_hours,
            'workers': workers_data
        }
    
    @staticmethod
    def calculate_overhead_cost(
        product: Product,
        quantity: Decimal = Decimal('1'),
        material_cost: Optional[Decimal] = None,
        labor_cost: Optional[Decimal] = None,
        labor_hours: Optional[Decimal] = None
    ) -> Dict:
        """
        حساب التكاليف غير المباشرة (Overhead)
        
        يتم التوزيع حسب الطريقة المحددة في إعدادات الإنتاج
        """
        from production.models import ProductionSettings
        
        try:
            settings = ProductionSettings.objects.first()
            if not settings:
                # معدل افتراضي 15%
                overhead_rate = Decimal('0.15')
                method = 'labor_cost'
            else:
                overhead_rate = settings.overhead_rate or Decimal('1.5')
                method = settings.overhead_allocation_method
            
            # حساب التكاليف غير المباشرة
            if method == 'labor_hours' and labor_hours:
                overhead_cost = labor_hours * overhead_rate
            elif method == 'labor_cost' and labor_cost:
                overhead_cost = labor_cost * (overhead_rate / 100)
            elif method == 'material_cost' and material_cost:
                overhead_cost = material_cost * (overhead_rate / 100)
            else:
                # افتراضي: 15% من المواد + العمالة
                direct_cost = (material_cost or Decimal('0')) + (labor_cost or Decimal('0'))
                overhead_cost = direct_cost * Decimal('0.15')
            
            return {
                'total_cost': overhead_cost,
                'cost_per_unit': overhead_cost / quantity if quantity > 0 else Decimal('0'),
                'method': method,
                'rate': overhead_rate
            }
            
        except Exception as e:
            return {
                'total_cost': Decimal('0'),
                'cost_per_unit': Decimal('0'),
                'error': str(e)
            }
    
    @staticmethod
    def calculate_full_product_cost(
        product: Product,
        quantity: Decimal = Decimal('1'),
        production_order: Optional[ProductionOrder] = None
    ) -> Dict:
        """
        حساب التكلفة الكاملة للمنتج (مواد + أجور + مصاريف)
        
        Returns:
            {
                'material_cost': Decimal,
                'labor_cost': Decimal,
                'overhead_cost': Decimal,
                'total_cost': Decimal,
                'cost_per_unit': Decimal,
                'details': {...}
            }
        """
        # 1. تكلفة المواد
        material_result = ProductCostingService.calculate_material_cost(product, quantity)
        material_cost = material_result['total_cost']
        
        # 2. تكلفة العمالة
        labor_result = ProductCostingService.calculate_direct_labor_cost(
            product, quantity, production_order
        )
        labor_cost = labor_result['total_cost']
        labor_hours = labor_result['labor_hours']
        
        # 3. التكاليف غير المباشرة
        overhead_result = ProductCostingService.calculate_overhead_cost(
            product, quantity,
            material_cost=material_cost,
            labor_cost=labor_cost,
            labor_hours=labor_hours
        )
        overhead_cost = overhead_result['total_cost']
        
        # 4. الإجمالي
        total_cost = material_cost + labor_cost + overhead_cost
        cost_per_unit = total_cost / quantity if quantity > 0 else Decimal('0')
        
        # 5. هامش الربح
        selling_price = product.price or Decimal('0')
        profit_margin = selling_price - cost_per_unit
        profit_percentage = (profit_margin / cost_per_unit * 100) if cost_per_unit > 0 else Decimal('0')
        
        return {
            'product': product,
            'quantity': quantity,
            'material_cost': material_cost,
            'labor_cost': labor_cost,
            'overhead_cost': overhead_cost,
            'total_cost': total_cost,
            'cost_per_unit': cost_per_unit,
            'selling_price': selling_price,
            'profit_margin': profit_margin,
            'profit_percentage': profit_percentage,
            'details': {
                'materials': material_result,
                'labor': labor_result,
                'overhead': overhead_result
            }
        }


class OverheadDistributionService:
    """خدمة توزيع التكاليف غير المباشرة"""
    
    @staticmethod
    def collect_monthly_overhead_expenses(year: int, month: int) -> Dict:
        """
        جمع المصروفات غير المباشرة لشهر معين
        
        Returns:
            {
                'electricity': Decimal,
                'maintenance': Decimal,
                'rent': Decimal,
                'indirect_labor': Decimal,
                'other': Decimal,
                'total': Decimal
            }
        """
        from accounting.models import JournalEntry, JournalEntryItem
        from datetime import date
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # حسابات التكاليف غير المباشرة
        electricity_accounts = ['5.1.2.003']  # كهرباء ومياه - مصنع
        maintenance_accounts = ['5.1.2.010']  # صيانة آلات
        overhead_accounts = ['5.1.2.020']  # مصروفات صناعية غير مباشرة
        
        overhead_data = {
            'electricity': Decimal('0'),
            'maintenance': Decimal('0'),
            'rent': Decimal('0'),
            'indirect_labor': Decimal('0'),
            'other': Decimal('0')
        }
        
        try:
            # جمع القيود في الفترة
            entries = JournalEntryItem.objects.filter(
                entry__date__gte=start_date,
                entry__date__lt=end_date,
                entry__status='posted'
            ).select_related('account')
            
            for item in entries:
                account_code = item.account.code
                
                if account_code in electricity_accounts:
                    overhead_data['electricity'] += item.debit - item.credit
                elif account_code in maintenance_accounts:
                    overhead_data['maintenance'] += item.debit - item.credit
                elif account_code in overhead_accounts:
                    overhead_data['other'] += item.debit - item.credit
            
            overhead_data['total'] = sum(overhead_data.values())
            
        except Exception as e:
            print(f"Error collecting overhead: {e}")
        
        return overhead_data
    
    @staticmethod
    def distribute_overhead_to_products(
        year: int,
        month: int,
        method: str = 'labor_hours'
    ) -> Dict[int, Decimal]:
        """
        توزيع التكاليف غير المباشرة على المنتجات المنتجة في الشهر
        
        Returns:
            {product_id: overhead_allocated, ...}
        """
        # جمع التكاليف غير المباشرة
        overhead = OverheadDistributionService.collect_monthly_overhead_expenses(year, month)
        total_overhead = overhead['total']
        
        if total_overhead == 0:
            return {}
        
        # جمع الإنتاج في الشهر
        from datetime import date
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        orders = ProductionOrder.objects.filter(
            actual_end_date__gte=start_date,
            actual_end_date__lt=end_date,
            status='completed'
        ).select_related('product')
        
        # حساب مفتاح التوزيع
        if method == 'labor_hours':
            # توزيع حسب ساعات العمل
            total_hours = ProductionTimeLog.objects.filter(
                production_order__in=orders
            ).aggregate(
                total=Coalesce(Sum('hours_worked'), Decimal('0'))
            )['total']
            
            if total_hours == 0:
                return {}
            
            # حساب نصيب كل منتج
            distribution = {}
            for order in orders:
                order_hours = ProductionTimeLog.objects.filter(
                    production_order=order
                ).aggregate(
                    total=Coalesce(Sum('hours_worked'), Decimal('0'))
                )['total']
                
                if order_hours > 0:
                    order_overhead = (order_hours / total_hours) * total_overhead
                    product_id = order.product.id
                    
                    if product_id in distribution:
                        distribution[product_id] += order_overhead
                    else:
                        distribution[product_id] = order_overhead
            
            return distribution
        
        elif method == 'material_cost':
            # توزيع حسب تكلفة المواد
            distribution = {}
            total_material_cost = Decimal('0')
            
            # حساب تكلفة المواد لكل أمر
            order_materials = {}
            for order in orders:
                mat_cost = ProductCostingService.calculate_material_cost(
                    order.product,
                    order.produced_quantity
                )['total_cost']
                order_materials[order.id] = mat_cost
                total_material_cost += mat_cost
            
            if total_material_cost == 0:
                return {}
            
            # توزيع
            for order in orders:
                mat_cost = order_materials.get(order.id, Decimal('0'))
                if mat_cost > 0:
                    order_overhead = (mat_cost / total_material_cost) * total_overhead
                    product_id = order.product.id
                    
                    if product_id in distribution:
                        distribution[product_id] += order_overhead
                    else:
                        distribution[product_id] = order_overhead
            
            return distribution
        
        else:
            # توزيع متساوٍ (افتراضي)
            count = orders.count()
            if count == 0:
                return {}
            
            per_order = total_overhead / count
            distribution = {}
            
            for order in orders:
                product_id = order.product.id
                if product_id in distribution:
                    distribution[product_id] += per_order
                else:
                    distribution[product_id] = per_order
            
            return distribution


class WorkerProductivityService:
    """خدمة حساب إنتاجية العمال"""
    
    @staticmethod
    def calculate_worker_production(
        employee: Employee,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        حساب إنتاجية عامل في فترة معينة
        
        Returns:
            {
                'total_units': Decimal,
                'total_hours': Decimal,
                'units_per_hour': Decimal,
                'products': {product_id: quantity},
                'days_worked': int
            }
        """
        # سيتم تحديثه عند إضافة WorkerProductionEntry
        time_logs = ProductionTimeLog.objects.filter(
            employee=employee,
            start_time__date__gte=start_date,
            start_time__date__lte=end_date
        ).select_related('production_order__product')
        
        total_hours = Decimal('0')
        products = {}
        days_worked = set()
        
        for log in time_logs:
            log_hours = log.duration_hours if log.duration_hours else Decimal('0')
            total_hours += log_hours
            days_worked.add(log.start_time.date() if log.start_time else None)
            
            if log.production_order:
                product_id = log.production_order.product.id
                # تقدير الكمية المنتجة (بناءً على نسبة الساعات)
                if product_id in products:
                    products[product_id] += log_hours
                else:
                    products[product_id] = log_hours
        
        total_units = sum(products.values())
        
        return {
            'employee': employee,
            'total_units': total_units,
            'total_hours': total_hours,
            'units_per_hour': total_units / total_hours if total_hours > 0 else Decimal('0'),
            'products': products,
            'days_worked': len(days_worked)
        }
    
    @staticmethod
    def calculate_labor_cost_for_payroll(
        employee: Employee,
        year: int,
        month: int
    ) -> Decimal:
        """
        حساب تكلفة عمالة الموظف لاستخدامها في الرواتب
        (إذا كان أجر بالقطعة أو حافز)
        """
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # حساب الإنتاجية
        productivity = WorkerProductivityService.calculate_worker_production(
            employee, start_date, end_date
        )
        
        # إذا كان هناك معدل أجر قطعة في ملف الموظف
        # (يمكن إضافة حقل piece_rate في Employee model)
        # total_pay = productivity['total_units'] * piece_rate
        
        # حالياً نرجع ساعات العمل × معدل الساعة
        hourly_rate = employee.basic_salary / Decimal('160')  # 160 ساعة شهرياً تقريباً
        labor_cost = productivity['total_hours'] * hourly_rate
        
        return labor_cost

