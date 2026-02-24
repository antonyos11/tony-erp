"""
نظام تكامل المصنع والمعارض
Factory-Showroom Integration System

يوفر هذا النظام:
1. ربط طلبات المعارض بأوامر الإنتاج
2. تحويل طلبات التموين إلى أوامر إنتاج تلقائياً
3. تتبع حالة الطلبات من الطلب حتى التسليم
4. إشعارات متبادلة بين المصنع والمعارض
5. تقارير تكامل شاملة
"""

from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from django.db import models, transaction
from django.db.models import Sum, F, Q, Count
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError


class DemandSource(Enum):
    """مصادر الطلب"""
    SHOWROOM_REQUEST = 'showroom_request'
    SALES_ORDER = 'sales_order'
    MINIMUM_STOCK = 'minimum_stock'
    FORECAST = 'forecast'
    MANUAL = 'manual'


class FulfillmentStatus(Enum):
    """حالة التنفيذ"""
    PENDING = 'pending'
    PRODUCTION_SCHEDULED = 'production_scheduled'
    IN_PRODUCTION = 'in_production'
    READY_TO_SHIP = 'ready_to_ship'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'


@dataclass
class DemandItem:
    """عنصر طلب"""
    product_id: int
    product_name: str
    product_sku: str
    requested_quantity: Decimal
    source: DemandSource
    source_id: Optional[int]
    source_branch_id: Optional[int]
    source_branch_name: str
    required_date: date
    priority: int = 3  # 1=عاجل, 5=منخفض
    
    # حالة التنفيذ
    scheduled_quantity: Decimal = Decimal('0')
    produced_quantity: Decimal = Decimal('0')
    shipped_quantity: Decimal = Decimal('0')
    
    @property
    def is_fully_scheduled(self) -> bool:
        return self.scheduled_quantity >= self.requested_quantity
    
    @property
    def is_fully_produced(self) -> bool:
        return self.produced_quantity >= self.requested_quantity
    
    @property
    def is_fully_shipped(self) -> bool:
        return self.shipped_quantity >= self.requested_quantity


@dataclass
class ProductionToShowroomLink:
    """رابط بين أمر الإنتاج والمعرض"""
    production_order_id: int
    production_order_number: str
    showroom_request_id: Optional[int]
    target_branch_id: int
    target_branch_name: str
    product_id: int
    product_name: str
    quantity: Decimal
    status: str
    production_status: str
    transfer_status: Optional[str]
    transfer_id: Optional[int]


class FactoryShowroomIntegration:
    """خدمة تكامل المصنع والمعارض"""
    
    def __init__(self):
        from branches.models import Branch, BranchTransfer, BranchTransferItem
        from branches.distribution import ShowroomReplenishmentRequest, ReplenishmentRequestItem
        from inventory.models import Product, Stock
        from production.models import ProductionOrder, BillOfMaterials
        from sales.models import Sale, SaleItem
        
        self.Branch = Branch
        self.BranchTransfer = BranchTransfer
        self.BranchTransferItem = BranchTransferItem
        self.ShowroomReplenishmentRequest = ShowroomReplenishmentRequest
        self.ReplenishmentRequestItem = ReplenishmentRequestItem
        self.Product = Product
        self.Stock = Stock
        self.ProductionOrder = ProductionOrder
        self.BillOfMaterials = BillOfMaterials
        self.Sale = Sale
        self.SaleItem = SaleItem
    
    def collect_demands(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        branch_ids: Optional[List[int]] = None
    ) -> List[DemandItem]:
        """
        جمع جميع الطلبات من مصادر مختلفة
        """
        if not from_date:
            from_date = timezone.now().date()
        if not to_date:
            to_date = from_date + timedelta(days=30)
        
        demands = []
        
        # 1. طلبات تموين المعارض
        requests_query = self.ShowroomReplenishmentRequest.objects.filter(
            status__in=['pending', 'approved'],
            required_date__gte=from_date,
            required_date__lte=to_date
        ).select_related('branch')
        
        if branch_ids:
            requests_query = requests_query.filter(branch_id__in=branch_ids)
        
        for request in requests_query:
            for item in request.items.select_related('product'):
                demands.append(DemandItem(
                    product_id=item.product_id,
                    product_name=item.product.name,
                    product_sku=item.product.sku,
                    requested_quantity=item.requested_quantity,
                    source=DemandSource.SHOWROOM_REQUEST,
                    source_id=request.id,
                    source_branch_id=request.branch_id,
                    source_branch_name=request.branch.name,
                    required_date=request.required_date or to_date,
                    priority=self._get_priority_from_status(request.priority)
                ))
        
        # 2. طلبات من نقص المخزون التلقائي
        low_stock_demands = self._get_low_stock_demands(branch_ids)
        demands.extend(low_stock_demands)
        
        # 3. دمج وتجميع الطلبات المتشابهة
        consolidated = self._consolidate_demands(demands)
        
        # 4. تحديث حالة التنفيذ
        for demand in consolidated:
            self._update_demand_status(demand)
        
        return consolidated
    
    def _get_priority_from_status(self, priority_str: str) -> int:
        """تحويل الأولوية النصية إلى رقم"""
        mapping = {
            'urgent': 1,
            'high': 2,
            'normal': 3,
            'low': 4
        }
        return mapping.get(priority_str, 3)
    
    def _get_low_stock_demands(self, branch_ids: Optional[List[int]] = None) -> List[DemandItem]:
        """الحصول على طلبات من نقص المخزون"""
        demands = []
        
        branches_query = self.Branch.objects.filter(
            is_active=True,
            branch_type__in=['showroom', 'store']
        )
        
        if branch_ids:
            branches_query = branches_query.filter(id__in=branch_ids)
        
        for branch in branches_query:
            if not branch.location:
                continue
            
            # المنتجات منخفضة المخزون
            low_stock_items = self.Stock.objects.filter(
                location=branch.location,
                quantity__lte=F('product__min_stock')
            ).select_related('product')
            
            for stock in low_stock_items:
                product = stock.product
                min_stock = product.min_stock or 0
                max_stock = min_stock * 3  # افتراضي
                
                needed = Decimal(str(max_stock)) - stock.quantity
                if needed > 0:
                    demands.append(DemandItem(
                        product_id=product.id,
                        product_name=product.name,
                        product_sku=product.sku,
                        requested_quantity=needed,
                        source=DemandSource.MINIMUM_STOCK,
                        source_id=None,
                        source_branch_id=branch.id,
                        source_branch_name=branch.name,
                        required_date=timezone.now().date() + timedelta(days=7),
                        priority=2 if stock.quantity <= 0 else 3
                    ))
        
        return demands
    
    def _consolidate_demands(self, demands: List[DemandItem]) -> List[DemandItem]:
        """دمج الطلبات المتشابهة"""
        # تجميع حسب المنتج
        by_product = {}
        for demand in demands:
            key = demand.product_id
            if key not in by_product:
                by_product[key] = DemandItem(
                    product_id=demand.product_id,
                    product_name=demand.product_name,
                    product_sku=demand.product_sku,
                    requested_quantity=Decimal('0'),
                    source=DemandSource.MANUAL,  # مجمع
                    source_id=None,
                    source_branch_id=None,
                    source_branch_name='متعدد',
                    required_date=demand.required_date,
                    priority=demand.priority
                )
            
            by_product[key].requested_quantity += demand.requested_quantity
            # استخدام أقرب تاريخ
            if demand.required_date < by_product[key].required_date:
                by_product[key].required_date = demand.required_date
            # استخدام أعلى أولوية
            if demand.priority < by_product[key].priority:
                by_product[key].priority = demand.priority
        
        return list(by_product.values())
    
    def _update_demand_status(self, demand: DemandItem):
        """تحديث حالة تنفيذ الطلب"""
        # الكمية المجدولة في أوامر الإنتاج
        scheduled = self.ProductionOrder.objects.filter(
            product_id=demand.product_id,
            status__in=['draft', 'pending', 'approved', 'in_progress']
        ).aggregate(total=Sum('quantity'))
        demand.scheduled_quantity = scheduled['total'] or Decimal('0')
        
        # الكمية المنتجة
        produced = self.ProductionOrder.objects.filter(
            product_id=demand.product_id,
            status='completed',
            actual_end_date__gte=timezone.now().date() - timedelta(days=30)
        ).aggregate(total=Sum('actual_quantity'))
        demand.produced_quantity = produced['total'] or Decimal('0')
    
    @transaction.atomic
    def create_production_from_demands(
        self,
        demands: List[DemandItem],
        user,
        work_center_id: Optional[int] = None
    ) -> List['ProductionOrder']:
        """
        إنشاء أوامر إنتاج من الطلبات
        """
        from production.models import ProductionOrder, ProductionWorkCenter
        
        created_orders = []
        
        # الحصول على مركز العمل الافتراضي
        if work_center_id:
            work_center = ProductionWorkCenter.objects.get(id=work_center_id)
        else:
            work_center = ProductionWorkCenter.objects.filter(is_active=True).first()
        
        for demand in demands:
            # التحقق من عدم وجود أمر إنتاج كافي
            existing = self.ProductionOrder.objects.filter(
                product_id=demand.product_id,
                status__in=['draft', 'pending', 'approved', 'in_progress']
            ).aggregate(total=Sum('quantity'))
            
            existing_qty = existing['total'] or Decimal('0')
            needed_qty = demand.requested_quantity - existing_qty
            
            if needed_qty <= 0:
                continue
            
            # التحقق من وجود BOM
            bom = self.BillOfMaterials.objects.filter(
                product_id=demand.product_id,
                is_active=True
            ).first()
            
            if not bom:
                continue
            
            # إنشاء أمر الإنتاج
            order = ProductionOrder.objects.create(
                product_id=demand.product_id,
                bom=bom,
                quantity=needed_qty,
                status='pending',
                priority='high' if demand.priority <= 2 else 'normal',
                scheduled_start_date=timezone.now().date(),
                scheduled_end_date=demand.required_date,
                work_center=work_center,
                created_by=user,
                notes=f"تم إنشاؤه تلقائياً من طلب معرض: {demand.source_branch_name}"
            )
            
            created_orders.append(order)
            
            # إنشاء رابط مع طلب التموين إن وجد
            if demand.source == DemandSource.SHOWROOM_REQUEST and demand.source_id:
                ProductionShowroomLink.objects.create(
                    production_order=order,
                    replenishment_request_id=demand.source_id,
                    target_branch_id=demand.source_branch_id,
                    quantity=needed_qty,
                    status='scheduled'
                )
        
        return created_orders
    
    @transaction.atomic
    def create_transfer_from_production(
        self,
        production_order_id: int,
        target_branch_id: int,
        user
    ) -> 'BranchTransfer':
        """
        إنشاء أمر تحويل من أمر إنتاج مكتمل
        """
        order = self.ProductionOrder.objects.get(id=production_order_id)
        
        if order.status != 'completed':
            raise ValidationError("أمر الإنتاج غير مكتمل")
        
        # الحصول على المصنع
        factory = self.Branch.objects.filter(
            is_active=True,
            branch_type='factory'
        ).first()
        
        if not factory:
            factory = self.Branch.objects.filter(
                is_active=True,
                is_main=True
            ).first()
        
        if not factory:
            raise ValidationError("لم يتم العثور على المصنع")
        
        target_branch = self.Branch.objects.get(id=target_branch_id)
        
        # إنشاء التحويل
        transfer = self.BranchTransfer.objects.create(
            from_branch=factory,
            to_branch=target_branch,
            status='approved',
            transfer_date=timezone.now().date(),
            requested_by=user,
            approved_by=user,
            approved_at=timezone.now(),
            notes=f"تحويل من أمر إنتاج رقم {order.order_number}"
        )
        
        # إضافة البند
        self.BranchTransferItem.objects.create(
            transfer=transfer,
            product=order.product,
            quantity=order.actual_quantity or order.quantity,
            unit_cost=order.product.cost or Decimal('0')
        )
        
        # تحديث الرابط
        link = ProductionShowroomLink.objects.filter(
            production_order=order,
            target_branch_id=target_branch_id
        ).first()
        
        if link:
            link.transfer = transfer
            link.status = 'shipped'
            link.save()
        
        return transfer
    
    def get_production_showroom_links(
        self,
        branch_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[ProductionToShowroomLink]:
        """
        الحصول على روابط الإنتاج-المعرض
        """
        links_query = ProductionShowroomLink.objects.select_related(
            'production_order', 'production_order__product',
            'target_branch', 'transfer'
        )
        
        if branch_id:
            links_query = links_query.filter(target_branch_id=branch_id)
        
        if status:
            links_query = links_query.filter(status=status)
        
        result = []
        for link in links_query:
            order = link.production_order
            result.append(ProductionToShowroomLink(
                production_order_id=order.id,
                production_order_number=order.order_number,
                showroom_request_id=link.replenishment_request_id,
                target_branch_id=link.target_branch_id,
                target_branch_name=link.target_branch.name if link.target_branch else '',
                product_id=order.product_id,
                product_name=order.product.name,
                quantity=link.quantity,
                status=link.status,
                production_status=order.status,
                transfer_status=link.transfer.status if link.transfer else None,
                transfer_id=link.transfer_id
            ))
        
        return result
    
    def get_integration_dashboard(self) -> Dict:
        """
        لوحة معلومات التكامل
        """
        today = timezone.now().date()
        
        # طلبات التموين المعلقة
        pending_requests = self.ShowroomReplenishmentRequest.objects.filter(
            status='pending'
        ).count()
        
        # طلبات تحتاج إنتاج
        demands = self.collect_demands()
        needs_production = sum(
            1 for d in demands
            if not d.is_fully_scheduled
        )
        
        # أوامر إنتاج مرتبطة بمعارض
        linked_orders = ProductionShowroomLink.objects.filter(
            status__in=['scheduled', 'in_production']
        ).count()
        
        # جاهز للشحن
        ready_to_ship = ProductionShowroomLink.objects.filter(
            status='ready',
            production_order__status='completed'
        ).count()
        
        # في الطريق
        in_transit = ProductionShowroomLink.objects.filter(
            status='shipped',
            transfer__status='in_transit'
        ).count()
        
        # مكتمل اليوم
        completed_today = ProductionShowroomLink.objects.filter(
            status='delivered',
            transfer__actual_arrival=today
        ).count()
        
        return {
            'pending_requests': pending_requests,
            'needs_production': needs_production,
            'linked_production_orders': linked_orders,
            'ready_to_ship': ready_to_ship,
            'in_transit': in_transit,
            'completed_today': completed_today,
            'demands_summary': [
                {
                    'product_name': d.product_name,
                    'requested': float(d.requested_quantity),
                    'scheduled': float(d.scheduled_quantity),
                    'priority': d.priority
                }
                for d in demands[:10]
            ]
        }
    
    def auto_process_demands(self, user) -> Dict:
        """
        معالجة تلقائية للطلبات
        تجمع الطلبات → تنشئ أوامر إنتاج → تنشئ تحويلات للمكتمل
        """
        result = {
            'demands_collected': 0,
            'production_orders_created': 0,
            'transfers_created': 0,
            'errors': []
        }
        
        try:
            # 1. جمع الطلبات
            demands = self.collect_demands()
            result['demands_collected'] = len(demands)
            
            # 2. إنشاء أوامر إنتاج
            if demands:
                orders = self.create_production_from_demands(demands, user)
                result['production_orders_created'] = len(orders)
            
            # 3. إنشاء تحويلات للمكتمل
            completed_links = ProductionShowroomLink.objects.filter(
                status='ready',
                production_order__status='completed',
                transfer__isnull=True
            ).select_related('production_order', 'target_branch')
            
            for link in completed_links:
                try:
                    self.create_transfer_from_production(
                        link.production_order_id,
                        link.target_branch_id,
                        user
                    )
                    result['transfers_created'] += 1
                except Exception as e:
                    result['errors'].append(str(e))
        
        except Exception as e:
            result['errors'].append(str(e))
        
        return result


# ==================== نماذج قاعدة البيانات ====================

class ProductionShowroomLink(models.Model):
    """
    رابط بين أمر الإنتاج وطلب المعرض
    """
    id = models.AutoField(primary_key=True)
    
    STATUS_CHOICES = [
        ('scheduled', 'مجدول'),
        ('in_production', 'قيد الإنتاج'),
        ('ready', 'جاهز للشحن'),
        ('shipped', 'تم الشحن'),
        ('delivered', 'تم التسليم'),
        ('cancelled', 'ملغى'),
    ]
    
    production_order = models.ForeignKey(
        'production.ProductionOrder', on_delete=models.CASCADE,
        related_name='showroom_links', verbose_name='أمر الإنتاج'
    )
    
    replenishment_request = models.ForeignKey(
        'branches.ShowroomReplenishmentRequest', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='production_links', verbose_name='طلب التموين'
    )
    
    target_branch = models.ForeignKey(
        'branches.Branch', on_delete=models.CASCADE,
        related_name='production_links', verbose_name='الفرع المستهدف'
    )
    
    transfer = models.ForeignKey(
        'branches.BranchTransfer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='production_links', verbose_name='أمر التحويل'
    )
    
    quantity = models.DecimalField('الكمية', max_digits=12, decimal_places=3)
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'رابط إنتاج-معرض'
        verbose_name_plural = 'روابط الإنتاج-المعارض'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['production_order', 'target_branch']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.production_order.order_number} → {self.target_branch.name}"
    
    def update_status_from_production(self):
        """تحديث الحالة بناءً على أمر الإنتاج"""
        order = self.production_order
        
        if order.status == 'in_progress':
            self.status = 'in_production'
        elif order.status == 'completed':
            if not self.transfer:
                self.status = 'ready'
        elif order.status == 'cancelled':
            self.status = 'cancelled'
        
        self.save()
    
    def update_status_from_transfer(self):
        """تحديث الحالة بناءً على التحويل"""
        if not self.transfer:
            return
        
        transfer = self.transfer
        
        if transfer.status == 'in_transit':
            self.status = 'shipped'
        elif transfer.status == 'received':
            self.status = 'delivered'
        elif transfer.status in ('rejected', 'cancelled'):
            self.status = 'ready'  # العودة لجاهز للشحن
        
        self.save()


class DemandForecast(models.Model):
    """
    توقعات الطلب
    """
    id = models.AutoField(primary_key=True)
    
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.CASCADE,
        related_name='demand_forecasts', verbose_name='المنتج'
    )
    
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.CASCADE,
        null=True, blank=True, related_name='demand_forecasts', verbose_name='الفرع'
    )
    
    forecast_date = models.DateField('تاريخ التوقع')
    forecast_quantity = models.DecimalField('الكمية المتوقعة', max_digits=12, decimal_places=3)
    
    # البيانات التاريخية المستخدمة
    historical_avg = models.DecimalField('متوسط تاريخي', max_digits=12, decimal_places=3, default=Decimal('0'))
    trend_factor = models.DecimalField('معامل الاتجاه', max_digits=6, decimal_places=4, default=Decimal('1'))
    seasonality_factor = models.DecimalField('معامل الموسمية', max_digits=6, decimal_places=4, default=Decimal('1'))
    
    confidence_level = models.DecimalField('مستوى الثقة %', max_digits=5, decimal_places=2, default=Decimal('80'))
    
    is_active = models.BooleanField('نشط', default=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'توقع طلب'
        verbose_name_plural = 'توقعات الطلب'
        ordering = ['forecast_date']
        unique_together = ['product', 'branch', 'forecast_date']
    
    def __str__(self):
        return f"{self.product.name} - {self.forecast_date}: {self.forecast_quantity}"


class IntegrationLog(models.Model):
    """
    سجل عمليات التكامل
    """
    id = models.AutoField(primary_key=True)
    
    ACTION_TYPES = [
        ('demand_collected', 'جمع طلبات'),
        ('production_created', 'إنشاء أمر إنتاج'),
        ('transfer_created', 'إنشاء تحويل'),
        ('status_updated', 'تحديث حالة'),
        ('auto_process', 'معالجة تلقائية'),
        ('error', 'خطأ'),
    ]
    
    action_type = models.CharField('نوع العملية', max_length=30, choices=ACTION_TYPES)
    action_date = models.DateTimeField('تاريخ العملية', auto_now_add=True)
    
    # المراجع
    production_order = models.ForeignKey(
        'production.ProductionOrder', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='integration_logs', verbose_name='أمر الإنتاج'
    )
    transfer = models.ForeignKey(
        'branches.BranchTransfer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='integration_logs', verbose_name='التحويل'
    )
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='integration_logs', verbose_name='الفرع'
    )
    
    # التفاصيل
    details = models.JSONField('التفاصيل', default=dict, blank=True)
    message = models.TextField('الرسالة', blank=True)
    
    # المستخدم
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='integration_logs', verbose_name='المستخدم'
    )
    
    class Meta:
        verbose_name = 'سجل تكامل'
        verbose_name_plural = 'سجلات التكامل'
        ordering = ['-action_date']
        indexes = [
            models.Index(fields=['action_type', 'action_date']),
        ]
    
    def __str__(self):
        return f"{self.get_action_type_display()} - {self.action_date}"
