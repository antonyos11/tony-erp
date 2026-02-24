"""
نظام تخطيط موارد الإنتاج (MRP)
Material Requirements Planning

يقوم هذا النظام بـ:
1. تخطيط الإنتاج بناءً على الطلبات
2. حساب احتياجات المواد الخام
3. جدولة أوامر الإنتاج
4. تتبع الطاقة الإنتاجية
5. تنبيهات نقص المواد الخام
"""

from decimal import Decimal
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from django.db import models, transaction
from django.db.models import Sum, F, Q, Avg, Count
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError


class MRPPriority(Enum):
    """أولويات أوامر الإنتاج"""
    URGENT = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class MaterialRequirement:
    """متطلبات المواد"""
    product_id: int
    product_name: str
    product_sku: str
    required_quantity: Decimal
    available_quantity: Decimal
    shortage: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    lead_time_days: int = 0
    suggested_order_date: date = None
    suppliers: List[Dict] = field(default_factory=list)
    
    @property
    def is_shortage(self) -> bool:
        return self.shortage > 0
    
    @property
    def coverage_percentage(self) -> float:
        if self.required_quantity == 0:
            return 100.0
        return float(min(self.available_quantity / self.required_quantity * 100, 100))


@dataclass
class ProductionScheduleItem:
    """عنصر جدول الإنتاج"""
    order_id: int
    order_number: str
    product_id: int
    product_name: str
    quantity: Decimal
    scheduled_date: date
    work_center_id: int
    work_center_name: str
    estimated_hours: Decimal
    priority: MRPPriority
    status: str
    materials_ready: bool = False
    capacity_available: bool = True


@dataclass
class CapacityInfo:
    """معلومات الطاقة الإنتاجية"""
    work_center_id: int
    work_center_name: str
    date: date
    total_capacity_hours: Decimal
    scheduled_hours: Decimal
    available_hours: Decimal
    utilization_percentage: float
    orders_count: int


class MRPService:
    """خدمة تخطيط موارد الإنتاج"""
    
    def __init__(self):
        from production.models import (
            ProductionOrder, BillOfMaterials, BOMItem,
            ProductionWorkCenter, ProductionSettings
        )
        from inventory.models import Product, Stock, Location
        from branches.models import Branch
        
        self.ProductionOrder = ProductionOrder
        self.BillOfMaterials = BillOfMaterials
        self.BOMItem = BOMItem
        self.ProductionWorkCenter = ProductionWorkCenter
        self.ProductionSettings = ProductionSettings
        self.Product = Product
        self.Stock = Stock
        self.Location = Location
        self.Branch = Branch
    
    def calculate_material_requirements(
        self,
        product_id: int,
        quantity: Decimal,
        check_stock: bool = True,
        location_id: Optional[int] = None
    ) -> List[MaterialRequirement]:
        """
        حساب متطلبات المواد لمنتج معين
        
        Args:
            product_id: معرف المنتج
            quantity: الكمية المطلوبة
            check_stock: التحقق من المخزون المتاح
            location_id: موقع المخزون (اختياري)
        
        Returns:
            قائمة بمتطلبات المواد
        """
        requirements = []
        
        # الحصول على قائمة المواد الافتراضية
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
        
        if not bom:
            return requirements
        
        # حساب المتطلبات لكل مادة
        for item in bom.items.select_related('material'):
            material = item.material
            required_qty = item.quantity_with_wastage * quantity / bom.base_quantity
            
            available_qty = Decimal('0')
            if check_stock:
                stock_filter = {'product': material}
                if location_id:
                    stock_filter['location_id'] = location_id
                
                stock_result = self.Stock.objects.filter(**stock_filter).aggregate(
                    total=Sum('quantity')
                )
                available_qty = stock_result['total'] or Decimal('0')
            
            shortage = max(Decimal('0'), required_qty - available_qty)
            unit_cost = material.cost or Decimal('0')
            
            # حساب تاريخ الطلب المقترح
            lead_time = getattr(material, 'lead_time_days', 7)
            suggested_date = date.today() + timedelta(days=1)
            if shortage > 0:
                suggested_date = date.today()
            
            # الحصول على الموردين
            suppliers = []
            if hasattr(material, 'supplier_products'):
                for sp in material.supplier_products.all()[:3]:
                    suppliers.append({
                        'id': sp.supplier_id,
                        'name': str(sp.supplier),
                        'price': float(sp.price or 0),
                        'lead_time': sp.lead_time_days or 7
                    })
            
            requirements.append(MaterialRequirement(
                product_id=material.id,
                product_name=material.name,
                product_sku=material.sku,
                required_quantity=required_qty,
                available_quantity=available_qty,
                shortage=shortage,
                unit_cost=unit_cost,
                total_cost=required_qty * unit_cost,
                lead_time_days=lead_time,
                suggested_order_date=suggested_date,
                suppliers=suppliers
            ))
        
        return requirements
    
    def calculate_multi_order_requirements(
        self,
        orders: List[Dict[str, Any]],
        consolidate: bool = True
    ) -> List[MaterialRequirement]:
        """
        حساب متطلبات المواد لعدة أوامر إنتاج
        
        Args:
            orders: قائمة الأوامر [{'product_id': int, 'quantity': Decimal}, ...]
            consolidate: دمج المتطلبات المتشابهة
        
        Returns:
            قائمة بمتطلبات المواد
        """
        all_requirements = []
        
        for order in orders:
            reqs = self.calculate_material_requirements(
                product_id=order['product_id'],
                quantity=order['quantity'],
                check_stock=False
            )
            all_requirements.extend(reqs)
        
        if not consolidate:
            return all_requirements
        
        # دمج المتطلبات المتشابهة
        consolidated = {}
        for req in all_requirements:
            key = req.product_id
            if key in consolidated:
                consolidated[key].required_quantity += req.required_quantity
                consolidated[key].total_cost += req.total_cost
            else:
                consolidated[key] = MaterialRequirement(
                    product_id=req.product_id,
                    product_name=req.product_name,
                    product_sku=req.product_sku,
                    required_quantity=req.required_quantity,
                    available_quantity=Decimal('0'),
                    shortage=Decimal('0'),
                    unit_cost=req.unit_cost,
                    total_cost=req.total_cost,
                    lead_time_days=req.lead_time_days,
                    suggested_order_date=req.suggested_order_date,
                    suppliers=req.suppliers
                )
        
        # تحديث المخزون المتاح والنقص
        for key, req in consolidated.items():
            stock_result = self.Stock.objects.filter(product_id=key).aggregate(
                total=Sum('quantity')
            )
            req.available_quantity = stock_result['total'] or Decimal('0')
            req.shortage = max(Decimal('0'), req.required_quantity - req.available_quantity)
        
        return list(consolidated.values())
    
    def check_materials_availability(
        self,
        production_order_id: int
    ) -> Tuple[bool, List[MaterialRequirement]]:
        """
        التحقق من توفر المواد لأمر إنتاج
        
        Returns:
            (متوفر: bool, قائمة المتطلبات)
        """
        order = self.ProductionOrder.objects.select_related('product').get(id=production_order_id)
        
        requirements = self.calculate_material_requirements(
            product_id=order.product_id,
            quantity=order.quantity,
            check_stock=True
        )
        
        all_available = all(not req.is_shortage for req in requirements)
        return all_available, requirements
    
    def get_work_center_capacity(
        self,
        work_center_id: int,
        from_date: date,
        to_date: date
    ) -> List[CapacityInfo]:
        """
        الحصول على طاقة مركز العمل لفترة معينة
        """
        work_center = self.ProductionWorkCenter.objects.get(id=work_center_id)
        
        capacity_list = []
        current_date = from_date
        
        while current_date <= to_date:
            # حساب الساعات المجدولة
            scheduled = self.ProductionOrder.objects.filter(
                work_center_id=work_center_id,
                scheduled_start_date__lte=current_date,
                scheduled_end_date__gte=current_date,
                status__in=['pending', 'in_progress', 'approved']
            ).aggregate(
                total_hours=Sum('estimated_time'),
                count=Count('id')
            )
            
            scheduled_hours = scheduled['total_hours'] or Decimal('0')
            orders_count = scheduled['count'] or 0
            
            total_capacity = work_center.working_hours_per_day
            available = max(Decimal('0'), total_capacity - scheduled_hours)
            
            utilization = float(scheduled_hours / total_capacity * 100) if total_capacity > 0 else 0
            
            capacity_list.append(CapacityInfo(
                work_center_id=work_center_id,
                work_center_name=work_center.name,
                date=current_date,
                total_capacity_hours=total_capacity,
                scheduled_hours=scheduled_hours,
                available_hours=available,
                utilization_percentage=utilization,
                orders_count=orders_count
            ))
            
            current_date += timedelta(days=1)
        
        return capacity_list
    
    def suggest_production_schedule(
        self,
        from_date: date,
        to_date: date,
        max_orders: int = 50
    ) -> List[ProductionScheduleItem]:
        """
        اقتراح جدول إنتاج للفترة المحددة
        """
        # الحصول على الأوامر المعلقة
        pending_orders = self.ProductionOrder.objects.filter(
            status__in=['draft', 'pending', 'approved'],
            scheduled_start_date__lte=to_date
        ).select_related('product', 'work_center').order_by(
            'priority', 'scheduled_start_date'
        )[:max_orders]
        
        schedule = []
        for order in pending_orders:
            # التحقق من توفر المواد
            materials_ready, _ = self.check_materials_availability(order.id)
            
            # التحقق من الطاقة المتاحة
            capacity_available = True
            if order.work_center:
                capacity = self.get_work_center_capacity(
                    order.work_center_id,
                    order.scheduled_start_date or from_date,
                    order.scheduled_end_date or to_date
                )
                if capacity:
                    capacity_available = capacity[0].available_hours >= (order.estimated_time or 0)
            
            # تحديد الأولوية
            priority = MRPPriority.NORMAL
            if hasattr(order, 'priority'):
                priority_map = {
                    'urgent': MRPPriority.URGENT,
                    'high': MRPPriority.HIGH,
                    'normal': MRPPriority.NORMAL,
                    'low': MRPPriority.LOW
                }
                priority = priority_map.get(order.priority, MRPPriority.NORMAL)
            
            schedule.append(ProductionScheduleItem(
                order_id=order.id,
                order_number=order.order_number,
                product_id=order.product_id,
                product_name=order.product.name,
                quantity=order.quantity,
                scheduled_date=order.scheduled_start_date or from_date,
                work_center_id=order.work_center_id if order.work_center else 0,
                work_center_name=order.work_center.name if order.work_center else 'غير محدد',
                estimated_hours=order.estimated_time or Decimal('0'),
                priority=priority,
                status=order.status,
                materials_ready=materials_ready,
                capacity_available=capacity_available
            ))
        
        return schedule
    
    def generate_purchase_suggestions(
        self,
        days_ahead: int = 30
    ) -> List[Dict]:
        """
        توليد اقتراحات الشراء بناءً على أوامر الإنتاج المخططة
        """
        to_date = date.today() + timedelta(days=days_ahead)
        
        # جمع أوامر الإنتاج المخططة
        planned_orders = self.ProductionOrder.objects.filter(
            status__in=['draft', 'pending', 'approved'],
            scheduled_start_date__lte=to_date
        ).values('product_id', 'quantity')
        
        orders_list = [
            {'product_id': o['product_id'], 'quantity': o['quantity']}
            for o in planned_orders
        ]
        
        if not orders_list:
            return []
        
        # حساب المتطلبات المجمعة
        requirements = self.calculate_multi_order_requirements(orders_list, consolidate=True)
        
        # إنشاء اقتراحات الشراء للمواد الناقصة
        suggestions = []
        for req in requirements:
            if req.is_shortage:
                suggestions.append({
                    'product_id': req.product_id,
                    'product_name': req.product_name,
                    'product_sku': req.product_sku,
                    'required_quantity': float(req.required_quantity),
                    'available_quantity': float(req.available_quantity),
                    'shortage_quantity': float(req.shortage),
                    'estimated_cost': float(req.shortage * req.unit_cost),
                    'suggested_order_date': req.suggested_order_date.isoformat() if req.suggested_order_date else None,
                    'lead_time_days': req.lead_time_days,
                    'suppliers': req.suppliers,
                    'urgency': 'urgent' if req.coverage_percentage < 30 else (
                        'high' if req.coverage_percentage < 60 else 'normal'
                    )
                })
        
        # ترتيب حسب الأولوية
        urgency_order = {'urgent': 0, 'high': 1, 'normal': 2}
        suggestions.sort(key=lambda x: urgency_order.get(x['urgency'], 3))
        
        return suggestions
    
    def get_production_alerts(self) -> List[Dict]:
        """
        الحصول على تنبيهات الإنتاج
        """
        alerts = []
        today = date.today()
        
        # 1. أوامر متأخرة
        overdue_orders = self.ProductionOrder.objects.filter(
            status__in=['pending', 'in_progress', 'approved'],
            scheduled_end_date__lt=today
        ).count()
        
        if overdue_orders > 0:
            alerts.append({
                'type': 'overdue_orders',
                'severity': 'danger',
                'title': 'أوامر إنتاج متأخرة',
                'message': f'يوجد {overdue_orders} أمر إنتاج متأخر عن موعده',
                'count': overdue_orders
            })
        
        # 2. مواد ناقصة للأوامر القادمة
        upcoming_orders = self.ProductionOrder.objects.filter(
            status__in=['pending', 'approved'],
            scheduled_start_date__lte=today + timedelta(days=7)
        )
        
        materials_shortage_count = 0
        for order in upcoming_orders[:20]:
            available, _ = self.check_materials_availability(order.id)
            if not available:
                materials_shortage_count += 1
        
        if materials_shortage_count > 0:
            alerts.append({
                'type': 'materials_shortage',
                'severity': 'warning',
                'title': 'نقص في المواد الخام',
                'message': f'{materials_shortage_count} أمر إنتاج يحتاج مواد غير متوفرة',
                'count': materials_shortage_count
            })
        
        # 3. طاقة إنتاجية منخفضة
        work_centers = self.ProductionWorkCenter.objects.filter(is_active=True)
        high_utilization = 0
        
        for wc in work_centers:
            capacity = self.get_work_center_capacity(wc.id, today, today + timedelta(days=7))
            avg_utilization = sum(c.utilization_percentage for c in capacity) / len(capacity) if capacity else 0
            if avg_utilization > 90:
                high_utilization += 1
        
        if high_utilization > 0:
            alerts.append({
                'type': 'high_capacity',
                'severity': 'info',
                'title': 'طاقة إنتاجية مرتفعة',
                'message': f'{high_utilization} مركز عمل بطاقة استخدام عالية',
                'count': high_utilization
            })
        
        return alerts


class MRPPlanningModel(models.Model):
    """
    نموذج خطة MRP
    """
    id = models.AutoField(primary_key=True)
    
    PLAN_TYPES = [
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغى'),
    ]
    
    name = models.CharField('اسم الخطة', max_length=200)
    plan_type = models.CharField('نوع الخطة', max_length=20, choices=PLAN_TYPES, default='monthly')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    start_date = models.DateField('تاريخ البداية')
    end_date = models.DateField('تاريخ النهاية')
    
    # ملخص الخطة
    total_orders = models.PositiveIntegerField('عدد الأوامر', default=0)
    total_products = models.PositiveIntegerField('عدد المنتجات', default=0)
    estimated_cost = models.DecimalField('التكلفة التقديرية', max_digits=14, decimal_places=2, default=Decimal('0'))
    
    # البيانات المفصلة (JSON)
    requirements_data = models.JSONField('بيانات المتطلبات', default=dict, blank=True)
    schedule_data = models.JSONField('بيانات الجدول', default=dict, blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='mrp_plans', verbose_name='أنشئ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'خطة MRP'
        verbose_name_plural = 'خطط MRP'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"
    
    def generate_plan(self):
        """توليد الخطة تلقائياً"""
        from production.models import ProductionOrder
        
        service = MRPService()
        
        # الحصول على الجدول المقترح
        schedule = service.suggest_production_schedule(self.start_date, self.end_date)
        
        # حساب المتطلبات
        orders_list = [
            {'product_id': item.product_id, 'quantity': item.quantity}
            for item in schedule
        ]
        requirements = service.calculate_multi_order_requirements(orders_list)
        
        # تحديث البيانات
        self.total_orders = len(schedule)
        self.total_products = len(set(item.product_id for item in schedule))
        self.estimated_cost = sum(r.total_cost for r in requirements)
        
        # حفظ البيانات التفصيلية
        self.schedule_data = {
            'items': [
                {
                    'order_id': item.order_id,
                    'order_number': item.order_number,
                    'product_name': item.product_name,
                    'quantity': float(item.quantity),
                    'scheduled_date': item.scheduled_date.isoformat(),
                    'work_center': item.work_center_name,
                    'materials_ready': item.materials_ready
                }
                for item in schedule
            ]
        }
        
        self.requirements_data = {
            'items': [
                {
                    'product_id': r.product_id,
                    'product_name': r.product_name,
                    'required': float(r.required_quantity),
                    'available': float(r.available_quantity),
                    'shortage': float(r.shortage),
                    'cost': float(r.total_cost)
                }
                for r in requirements
            ]
        }
        
        self.save()
        return True


class MaterialReorderPoint(models.Model):
    """
    نقاط إعادة الطلب للمواد
    """
    id = models.AutoField(primary_key=True)
    
    product = models.OneToOneField(
        'inventory.Product', on_delete=models.CASCADE,
        related_name='reorder_point', verbose_name='المنتج'
    )
    
    # نقاط إعادة الطلب
    minimum_quantity = models.DecimalField('الحد الأدنى', max_digits=12, decimal_places=3, default=Decimal('0'))
    reorder_point = models.DecimalField('نقطة إعادة الطلب', max_digits=12, decimal_places=3, default=Decimal('0'))
    maximum_quantity = models.DecimalField('الحد الأقصى', max_digits=12, decimal_places=3, default=Decimal('0'))
    
    # كمية الطلب
    economic_order_quantity = models.DecimalField(
        'الكمية الاقتصادية للطلب (EOQ)', 
        max_digits=12, decimal_places=3, 
        default=Decimal('0')
    )
    
    # أوقات التوريد
    lead_time_days = models.PositiveIntegerField('وقت التوريد (أيام)', default=7)
    safety_stock_days = models.PositiveIntegerField('أيام المخزون الآمن', default=3)
    
    # حساب تلقائي
    auto_calculate = models.BooleanField('حساب تلقائي', default=True)
    last_calculated = models.DateTimeField('آخر حساب', null=True, blank=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'نقطة إعادة الطلب'
        verbose_name_plural = 'نقاط إعادة الطلب'
    
    def __str__(self):
        return f"{self.product.name}: ROP={self.reorder_point}"
    
    def calculate_from_consumption(self, days: int = 90):
        """
        حساب نقاط إعادة الطلب من بيانات الاستهلاك
        """
        from inventory.models import StockMovement
        from django.db.models import Avg
        
        since = timezone.now() - timedelta(days=days)
        
        # حساب متوسط الاستهلاك اليومي
        consumption = StockMovement.objects.filter(
            product=self.product,
            movement_type='out',
            created_at__gte=since
        ).aggregate(
            total=Sum('quantity')
        )
        
        total_consumed = consumption['total'] or Decimal('0')
        avg_daily = total_consumed / days if days > 0 else Decimal('0')
        
        # حساب نقطة إعادة الطلب
        safety_stock = avg_daily * self.safety_stock_days
        self.reorder_point = (avg_daily * self.lead_time_days) + safety_stock
        self.minimum_quantity = safety_stock
        self.maximum_quantity = self.reorder_point * 2
        
        # حساب EOQ (صيغة مبسطة)
        if avg_daily > 0:
            # افتراض تكلفة طلب ثابتة
            ordering_cost = Decimal('100')  # يمكن جعلها قابلة للتكوين
            holding_cost = self.product.cost * Decimal('0.25')  # 25% من قيمة المنتج
            
            if holding_cost > 0:
                annual_demand = avg_daily * 365
                eoq_squared = (2 * annual_demand * ordering_cost) / holding_cost
                self.economic_order_quantity = Decimal(str(eoq_squared ** Decimal('0.5')))
        
        self.last_calculated = timezone.now()
        self.save()
        
        return self
