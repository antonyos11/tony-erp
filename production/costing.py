"""
نظام التكلفة الصناعية المتقدم
Advanced Manufacturing Costing System

يوفر هذا النظام:
1. التكلفة المعيارية مقابل الفعلية
2. تحليل انحرافات التكلفة
3. توزيع التكاليف غير المباشرة
4. تقارير هامش الربح لكل منتج
5. تتبع تكلفة أمر الإنتاج
"""

from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from django.db import models, transaction
from django.db.models import Sum, F, Q, Avg, Count
from django.utils import timezone
from django.conf import settings


class CostType(Enum):
    """أنواع التكاليف"""
    DIRECT_MATERIAL = 'direct_material'
    DIRECT_LABOR = 'direct_labor'
    OVERHEAD = 'overhead'
    VARIABLE = 'variable'
    FIXED = 'fixed'


class VarianceType(Enum):
    """أنواع الانحرافات"""
    FAVORABLE = 'favorable'
    UNFAVORABLE = 'unfavorable'
    NONE = 'none'


@dataclass
class CostBreakdown:
    """تفصيل التكلفة"""
    material_cost: Decimal = Decimal('0')
    labor_cost: Decimal = Decimal('0')
    overhead_cost: Decimal = Decimal('0')
    other_cost: Decimal = Decimal('0')
    
    @property
    def total(self) -> Decimal:
        return self.material_cost + self.labor_cost + self.overhead_cost + self.other_cost
    
    @property
    def percentage_breakdown(self) -> Dict[str, float]:
        total = self.total
        if total == 0:
            return {'material': 0, 'labor': 0, 'overhead': 0, 'other': 0}
        return {
            'material': float(self.material_cost / total * 100),
            'labor': float(self.labor_cost / total * 100),
            'overhead': float(self.overhead_cost / total * 100),
            'other': float(self.other_cost / total * 100)
        }


@dataclass
class CostVariance:
    """انحراف التكلفة"""
    cost_type: str
    standard_cost: Decimal
    actual_cost: Decimal
    variance_amount: Decimal
    variance_percentage: float
    variance_type: VarianceType
    
    @property
    def is_favorable(self) -> bool:
        return self.variance_type == VarianceType.FAVORABLE


@dataclass
class ProductCostAnalysis:
    """تحليل تكلفة المنتج"""
    product_id: int
    product_name: str
    standard_cost: CostBreakdown
    actual_cost: CostBreakdown
    variances: List[CostVariance]
    selling_price: Decimal
    margin_amount: Decimal
    margin_percentage: float
    production_quantity: Decimal
    period_start: date
    period_end: date


class ManufacturingCostService:
    """خدمة حساب التكلفة الصناعية"""
    
    def __init__(self):
        from production.models import (
            ProductionOrder, BillOfMaterials, BOMItem,
            ProductionOrderMaterial, ProductionOrderLabor,
            ProductionWorkCenter, ProductionSettings
        )
        from inventory.models import Product, Stock
        from accounting.models import Account, JournalEntry
        
        self.ProductionOrder = ProductionOrder
        self.BillOfMaterials = BillOfMaterials
        self.BOMItem = BOMItem
        self.ProductionOrderMaterial = ProductionOrderMaterial
        self.ProductionOrderLabor = ProductionOrderLabor
        self.ProductionWorkCenter = ProductionWorkCenter
        self.ProductionSettings = ProductionSettings
        self.Product = Product
        self.Stock = Stock
        self.Account = Account
        self.JournalEntry = JournalEntry
    
    def calculate_standard_cost(self, product_id: int, quantity: Decimal = Decimal('1')) -> CostBreakdown:
        """
        حساب التكلفة المعيارية للمنتج
        """
        breakdown = CostBreakdown()
        
        # الحصول على BOM
        bom = self.BillOfMaterials.objects.filter(
            product_id=product_id,
            is_active=True,
            is_default=True
        ).first()
        
        if not bom:
            bom = self.BillOfMaterials.objects.filter(
                product_id=product_id,
                is_active=True
            ).first()
        
        if bom:
            # تكلفة المواد المعيارية
            for item in bom.items.all():
                breakdown.material_cost += item.total_cost * quantity / bom.base_quantity
            
            # تكلفة العمالة المعيارية (من مراحل الإنتاج)
            if hasattr(bom, 'production_stages'):
                for stage in bom.production_stages.all():
                    if stage.work_center:
                        hours = (stage.total_time_per_unit or Decimal('0')) / 60  # تحويل من دقائق لساعات
                        labor_rate = stage.work_center.hourly_rate or Decimal('0')
                        breakdown.labor_cost += hours * labor_rate * quantity
            
            # التكاليف الإضافية
            breakdown.overhead_cost = bom.total_overhead_cost * quantity / bom.base_quantity
        
        return breakdown
    
    def calculate_actual_cost(self, production_order_id: int) -> CostBreakdown:
        """
        حساب التكلفة الفعلية لأمر إنتاج
        """
        breakdown = CostBreakdown()
        
        try:
            order = self.ProductionOrder.objects.get(id=production_order_id)
        except self.ProductionOrder.DoesNotExist:
            return breakdown
        
        # تكلفة المواد الفعلية
        if hasattr(order, 'materials'):
            materials = order.materials.aggregate(
                total=Sum(F('quantity_used') * F('unit_cost'))
            )
            breakdown.material_cost = materials['total'] or Decimal('0')
        
        # تكلفة العمالة الفعلية
        if hasattr(order, 'labor_records'):
            labor = order.labor_records.aggregate(
                total=Sum(F('hours_worked') * F('hourly_rate'))
            )
            breakdown.labor_cost = labor['total'] or Decimal('0')
        
        # التكاليف الإضافية
        if hasattr(order, 'overhead_cost'):
            breakdown.overhead_cost = order.overhead_cost or Decimal('0')
        
        return breakdown
    
    def calculate_variances(
        self,
        product_id: int,
        from_date: date,
        to_date: date
    ) -> List[CostVariance]:
        """
        حساب انحرافات التكلفة لفترة معينة
        """
        variances = []
        
        # حساب التكلفة المعيارية
        standard = self.calculate_standard_cost(product_id)
        
        # جمع أوامر الإنتاج المكتملة
        completed_orders = self.ProductionOrder.objects.filter(
            product_id=product_id,
            status='completed',
            actual_end_date__gte=from_date,
            actual_end_date__lte=to_date
        )
        
        if not completed_orders.exists():
            return variances
        
        # حساب متوسط التكلفة الفعلية
        total_quantity = Decimal('0')
        total_material = Decimal('0')
        total_labor = Decimal('0')
        total_overhead = Decimal('0')
        
        for order in completed_orders:
            actual = self.calculate_actual_cost(order.id)
            total_quantity += order.quantity
            total_material += actual.material_cost
            total_labor += actual.labor_cost
            total_overhead += actual.overhead_cost
        
        if total_quantity == 0:
            return variances
        
        # تكلفة الوحدة الفعلية
        actual_material_per_unit = total_material / total_quantity
        actual_labor_per_unit = total_labor / total_quantity
        actual_overhead_per_unit = total_overhead / total_quantity
        
        # حساب الانحرافات
        cost_pairs = [
            ('المواد المباشرة', standard.material_cost, actual_material_per_unit),
            ('العمالة المباشرة', standard.labor_cost, actual_labor_per_unit),
            ('التكاليف الإضافية', standard.overhead_cost, actual_overhead_per_unit),
        ]
        
        for cost_name, std, actual in cost_pairs:
            variance_amount = std - actual  # إيجابي = مفضل
            variance_pct = float(variance_amount / std * 100) if std > 0 else 0
            
            if variance_amount > 0:
                v_type = VarianceType.FAVORABLE
            elif variance_amount < 0:
                v_type = VarianceType.UNFAVORABLE
            else:
                v_type = VarianceType.NONE
            
            variances.append(CostVariance(
                cost_type=cost_name,
                standard_cost=std,
                actual_cost=actual,
                variance_amount=abs(variance_amount),
                variance_percentage=abs(variance_pct),
                variance_type=v_type
            ))
        
        return variances
    
    def calculate_product_margin(
        self,
        product_id: int,
        use_standard_cost: bool = True
    ) -> Dict:
        """
        حساب هامش الربح للمنتج
        """
        product = self.Product.objects.get(id=product_id)
        selling_price = product.price or Decimal('0')
        
        if use_standard_cost:
            cost = self.calculate_standard_cost(product_id)
        else:
            # استخدام متوسط التكلفة الفعلية
            recent_orders = self.ProductionOrder.objects.filter(
                product_id=product_id,
                status='completed'
            ).order_by('-actual_end_date')[:10]
            
            if recent_orders.exists():
                total_cost = Decimal('0')
                total_qty = Decimal('0')
                for order in recent_orders:
                    actual = self.calculate_actual_cost(order.id)
                    total_cost += actual.total
                    total_qty += order.quantity
                
                unit_cost = total_cost / total_qty if total_qty > 0 else Decimal('0')
                cost = CostBreakdown(
                    material_cost=unit_cost * Decimal('0.6'),  # تقدير
                    labor_cost=unit_cost * Decimal('0.25'),
                    overhead_cost=unit_cost * Decimal('0.15')
                )
            else:
                cost = self.calculate_standard_cost(product_id)
        
        total_cost = cost.total
        margin_amount = selling_price - total_cost
        margin_pct = float(margin_amount / selling_price * 100) if selling_price > 0 else 0
        
        return {
            'product_id': product_id,
            'product_name': product.name,
            'selling_price': float(selling_price),
            'cost_breakdown': {
                'material': float(cost.material_cost),
                'labor': float(cost.labor_cost),
                'overhead': float(cost.overhead_cost),
                'total': float(total_cost)
            },
            'cost_percentages': cost.percentage_breakdown,
            'margin_amount': float(margin_amount),
            'margin_percentage': margin_pct,
            'is_profitable': margin_amount > 0
        }
    
    def allocate_overhead(
        self,
        work_center_id: int,
        period_start: date,
        period_end: date,
        allocation_method: str = 'labor_hours'
    ) -> List[Dict]:
        """
        توزيع التكاليف غير المباشرة على أوامر الإنتاج
        
        allocation_method:
            - labor_hours: ساعات العمل
            - labor_cost: تكلفة العمالة
            - material_cost: تكلفة المواد
            - machine_hours: ساعات التشغيل
            - equal: بالتساوي
        """
        # جمع أوامر الإنتاج للفترة
        orders = self.ProductionOrder.objects.filter(
            work_center_id=work_center_id,
            status='completed',
            actual_end_date__gte=period_start,
            actual_end_date__lte=period_end
        )
        
        if not orders.exists():
            return []
        
        # حساب إجمالي التكاليف غير المباشرة
        settings = self.ProductionSettings.objects.first()
        overhead_rate = settings.overhead_rate if settings else Decimal('1.5')
        
        # حساب قاعدة التوزيع
        allocation_base = {}
        total_base = Decimal('0')
        
        for order in orders:
            if allocation_method == 'labor_hours':
                base_value = order.actual_time or order.estimated_time or Decimal('0')
            elif allocation_method == 'labor_cost':
                actual = self.calculate_actual_cost(order.id)
                base_value = actual.labor_cost
            elif allocation_method == 'material_cost':
                actual = self.calculate_actual_cost(order.id)
                base_value = actual.material_cost
            elif allocation_method == 'equal':
                base_value = Decimal('1')
            else:
                base_value = order.estimated_time or Decimal('1')
            
            allocation_base[order.id] = base_value
            total_base += base_value
        
        # حساب إجمالي التكاليف الإضافية للفترة
        work_center = self.ProductionWorkCenter.objects.get(id=work_center_id)
        days = (period_end - period_start).days + 1
        total_overhead = work_center.hourly_rate * work_center.working_hours_per_day * days * overhead_rate
        
        # توزيع التكاليف
        allocations = []
        for order in orders:
            if total_base > 0:
                allocation_pct = allocation_base[order.id] / total_base
                allocated_amount = total_overhead * allocation_pct
            else:
                allocated_amount = Decimal('0')
            
            allocations.append({
                'order_id': order.id,
                'order_number': order.order_number,
                'allocation_base': float(allocation_base[order.id]),
                'allocation_percentage': float(allocation_pct * 100) if total_base > 0 else 0,
                'allocated_overhead': float(allocated_amount),
                'allocation_method': allocation_method
            })
        
        return allocations
    
    def get_cost_analysis_report(
        self,
        product_ids: Optional[List[int]] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[ProductCostAnalysis]:
        """
        تقرير تحليل التكلفة للمنتجات
        """
        if not from_date:
            from_date = date.today() - timedelta(days=30)
        if not to_date:
            to_date = date.today()
        
        if product_ids:
            products = self.Product.objects.filter(id__in=product_ids)
        else:
            # المنتجات التي لديها أوامر إنتاج مكتملة
            completed_product_ids = self.ProductionOrder.objects.filter(
                status='completed',
                actual_end_date__gte=from_date,
                actual_end_date__lte=to_date
            ).values_list('product_id', flat=True).distinct()
            products = self.Product.objects.filter(id__in=completed_product_ids)
        
        analysis_list = []
        
        for product in products:
            # التكلفة المعيارية
            standard = self.calculate_standard_cost(product.id)
            
            # التكلفة الفعلية (متوسط الفترة)
            orders = self.ProductionOrder.objects.filter(
                product_id=product.id,
                status='completed',
                actual_end_date__gte=from_date,
                actual_end_date__lte=to_date
            )
            
            total_qty = Decimal('0')
            actual_breakdown = CostBreakdown()
            
            for order in orders:
                actual = self.calculate_actual_cost(order.id)
                qty = order.quantity
                total_qty += qty
                actual_breakdown.material_cost += actual.material_cost
                actual_breakdown.labor_cost += actual.labor_cost
                actual_breakdown.overhead_cost += actual.overhead_cost
            
            # تحويل للتكلفة لكل وحدة
            if total_qty > 0:
                actual_per_unit = CostBreakdown(
                    material_cost=actual_breakdown.material_cost / total_qty,
                    labor_cost=actual_breakdown.labor_cost / total_qty,
                    overhead_cost=actual_breakdown.overhead_cost / total_qty
                )
            else:
                actual_per_unit = CostBreakdown()
            
            # الانحرافات
            variances = self.calculate_variances(product.id, from_date, to_date)
            
            # هامش الربح
            selling_price = product.price or Decimal('0')
            margin_amount = selling_price - actual_per_unit.total
            margin_pct = float(margin_amount / selling_price * 100) if selling_price > 0 else 0
            
            analysis_list.append(ProductCostAnalysis(
                product_id=product.id,
                product_name=product.name,
                standard_cost=standard,
                actual_cost=actual_per_unit,
                variances=variances,
                selling_price=selling_price,
                margin_amount=margin_amount,
                margin_percentage=margin_pct,
                production_quantity=total_qty,
                period_start=from_date,
                period_end=to_date
            ))
        
        return analysis_list


# ==================== نماذج قاعدة البيانات ====================

class StandardCost(models.Model):
    """
    التكلفة المعيارية للمنتجات
    """
    id = models.AutoField(primary_key=True)
    
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.CASCADE,
        related_name='standard_costs', verbose_name='المنتج'
    )
    
    effective_date = models.DateField('تاريخ السريان', default=timezone.now)
    expiry_date = models.DateField('تاريخ الانتهاء', null=True, blank=True)
    
    # التكاليف المعيارية
    material_cost = models.DecimalField('تكلفة المواد', max_digits=12, decimal_places=2, default=Decimal('0'))
    labor_cost = models.DecimalField('تكلفة العمالة', max_digits=12, decimal_places=2, default=Decimal('0'))
    overhead_cost = models.DecimalField('التكاليف الإضافية', max_digits=12, decimal_places=2, default=Decimal('0'))
    other_cost = models.DecimalField('تكاليف أخرى', max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # تفاصيل إضافية
    labor_hours = models.DecimalField('ساعات العمل', max_digits=8, decimal_places=2, default=Decimal('0'))
    machine_hours = models.DecimalField('ساعات التشغيل', max_digits=8, decimal_places=2, default=Decimal('0'))
    
    is_active = models.BooleanField('نشط', default=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='standard_costs_created', verbose_name='أنشئ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تكلفة معيارية'
        verbose_name_plural = 'التكاليف المعيارية'
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['product', 'effective_date']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.effective_date}"
    
    @property
    def total_cost(self) -> Decimal:
        return self.material_cost + self.labor_cost + self.overhead_cost + self.other_cost
    
    def save(self, *args, **kwargs):
        if self.is_active:
            # إلغاء التكاليف المعيارية السابقة
            StandardCost.objects.filter(
                product=self.product,
                is_active=True
            ).exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)


class CostVarianceRecord(models.Model):
    """
    سجل انحرافات التكلفة
    """
    id = models.AutoField(primary_key=True)
    
    VARIANCE_TYPES = [
        ('material_price', 'انحراف سعر المواد'),
        ('material_quantity', 'انحراف كمية المواد'),
        ('labor_rate', 'انحراف معدل العمالة'),
        ('labor_efficiency', 'انحراف كفاءة العمالة'),
        ('overhead_spending', 'انحراف إنفاق التكاليف الإضافية'),
        ('overhead_efficiency', 'انحراف كفاءة التكاليف الإضافية'),
    ]
    
    production_order = models.ForeignKey(
        'production.ProductionOrder', on_delete=models.CASCADE,
        related_name='cost_variances', verbose_name='أمر الإنتاج'
    )
    
    variance_type = models.CharField('نوع الانحراف', max_length=30, choices=VARIANCE_TYPES)
    variance_date = models.DateField('تاريخ الانحراف', default=timezone.now)
    
    standard_value = models.DecimalField('القيمة المعيارية', max_digits=12, decimal_places=2)
    actual_value = models.DecimalField('القيمة الفعلية', max_digits=12, decimal_places=2)
    variance_amount = models.DecimalField('مبلغ الانحراف', max_digits=12, decimal_places=2)
    
    is_favorable = models.BooleanField('انحراف مفضل', default=False)
    
    analysis = models.TextField('تحليل الانحراف', blank=True)
    corrective_action = models.TextField('الإجراء التصحيحي', blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='variance_records_created', verbose_name='أنشئ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'سجل انحراف تكلفة'
        verbose_name_plural = 'سجلات انحرافات التكلفة'
        ordering = ['-variance_date', '-created_at']
        indexes = [
            models.Index(fields=['production_order', 'variance_type']),
            models.Index(fields=['variance_date']),
        ]
    
    def __str__(self):
        return f"{self.production_order.order_number} - {self.get_variance_type_display()}"
    
    def save(self, *args, **kwargs):
        self.variance_amount = self.standard_value - self.actual_value
        self.is_favorable = self.variance_amount > 0
        super().save(*args, **kwargs)


class OverheadAllocation(models.Model):
    """
    توزيع التكاليف غير المباشرة
    """
    id = models.AutoField(primary_key=True)
    
    ALLOCATION_METHODS = [
        ('labor_hours', 'ساعات العمل'),
        ('labor_cost', 'تكلفة العمالة'),
        ('material_cost', 'تكلفة المواد'),
        ('machine_hours', 'ساعات التشغيل'),
        ('units_produced', 'الوحدات المنتجة'),
        ('equal', 'بالتساوي'),
    ]
    
    production_order = models.ForeignKey(
        'production.ProductionOrder', on_delete=models.CASCADE,
        related_name='overhead_allocations', verbose_name='أمر الإنتاج'
    )
    work_center = models.ForeignKey(
        'production.ProductionWorkCenter', on_delete=models.CASCADE,
        related_name='overhead_allocations', verbose_name='مركز العمل'
    )
    
    period_start = models.DateField('بداية الفترة')
    period_end = models.DateField('نهاية الفترة')
    
    allocation_method = models.CharField('طريقة التوزيع', max_length=20, choices=ALLOCATION_METHODS)
    allocation_base = models.DecimalField('قاعدة التوزيع', max_digits=12, decimal_places=2)
    allocation_rate = models.DecimalField('معدل التوزيع', max_digits=10, decimal_places=4)
    allocated_amount = models.DecimalField('المبلغ الموزع', max_digits=12, decimal_places=2)
    
    is_posted = models.BooleanField('تم الترحيل', default=False)
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='overhead_allocations', verbose_name='القيد المحاسبي'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='overhead_allocations_created', verbose_name='أنشئ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'توزيع تكاليف إضافية'
        verbose_name_plural = 'توزيعات التكاليف الإضافية'
        ordering = ['-period_start']
    
    def __str__(self):
        return f"{self.production_order.order_number} - {self.allocated_amount}"
