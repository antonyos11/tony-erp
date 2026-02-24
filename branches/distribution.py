"""
نظام توزيع المعارض
Showroom Distribution System

يوفر هذا النظام:
1. طلبات تموين المعارض
2. تحديد كميات إعادة الطلب
3. شحنات من المصنع للمعرض
4. تتبع المنقولات
5. تقارير حركة بين المستودعات
"""

from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from django.db import models, transaction
from django.db.models import Sum, F, Q, Avg, Count, Min
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError


class ReplenishmentPriority(Enum):
    """أولويات التموين"""
    URGENT = 'urgent'
    HIGH = 'high'
    NORMAL = 'normal'
    LOW = 'low'


@dataclass
class StockLevel:
    """مستوى المخزون"""
    product_id: int
    product_name: str
    branch_id: int
    branch_name: str
    current_quantity: Decimal
    minimum_quantity: Decimal
    reorder_point: Decimal
    maximum_quantity: Decimal
    
    @property
    def needs_replenishment(self) -> bool:
        return self.current_quantity <= self.reorder_point
    
    @property
    def is_critical(self) -> bool:
        return self.current_quantity <= self.minimum_quantity
    
    @property
    def suggested_quantity(self) -> Decimal:
        return max(Decimal('0'), self.maximum_quantity - self.current_quantity)
    
    @property
    def fill_rate(self) -> float:
        if self.maximum_quantity == 0:
            return 0
        return float(self.current_quantity / self.maximum_quantity * 100)


@dataclass
class ReplenishmentSuggestion:
    """اقتراح تموين"""
    branch_id: int
    branch_name: str
    product_id: int
    product_name: str
    product_sku: str
    current_stock: Decimal
    suggested_quantity: Decimal
    source_branch_id: int
    source_branch_name: str
    source_available: Decimal
    priority: ReplenishmentPriority
    estimated_days_until_stockout: int
    unit_cost: Decimal
    total_cost: Decimal


class ShowroomDistributionService:
    """خدمة توزيع المعارض"""
    
    def __init__(self):
        from branches.models import Branch, BranchTransfer, BranchTransferItem
        from inventory.models import Product, Stock, Location
        from production.models import ProductionOrder
        
        self.Branch = Branch
        self.BranchTransfer = BranchTransfer
        self.BranchTransferItem = BranchTransferItem
        self.Product = Product
        self.Stock = Stock
        self.Location = Location
        self.ProductionOrder = ProductionOrder
    
    def get_branch_stock_levels(
        self,
        branch_id: int,
        product_ids: Optional[List[int]] = None
    ) -> List[StockLevel]:
        """
        الحصول على مستويات المخزون لفرع معين
        """
        branch = self.Branch.objects.get(id=branch_id)
        
        if not branch.location:
            return []
        
        stock_query = self.Stock.objects.filter(
            location=branch.location
        ).select_related('product')
        
        if product_ids:
            stock_query = stock_query.filter(product_id__in=product_ids)
        
        levels = []
        for stock in stock_query:
            product = stock.product
            
            # الحصول على نقاط إعادة الطلب
            min_qty = getattr(product, 'min_stock', 0) or Decimal('0')
            reorder_point = min_qty * Decimal('1.5')
            max_qty = min_qty * Decimal('3')
            
            # التحقق من وجود إعدادات مخصصة للمعرض
            if hasattr(product, 'branch_stock_settings'):
                settings = product.branch_stock_settings.filter(branch=branch).first()
                if settings:
                    min_qty = settings.minimum_quantity
                    reorder_point = settings.reorder_point
                    max_qty = settings.maximum_quantity
            
            levels.append(StockLevel(
                product_id=product.id,
                product_name=product.name,
                branch_id=branch.id,
                branch_name=branch.name,
                current_quantity=stock.quantity,
                minimum_quantity=min_qty,
                reorder_point=reorder_point,
                maximum_quantity=max_qty
            ))
        
        return levels
    
    def get_replenishment_suggestions(
        self,
        branch_id: Optional[int] = None,
        include_non_critical: bool = False
    ) -> List[ReplenishmentSuggestion]:
        """
        الحصول على اقتراحات التموين
        """
        suggestions = []
        
        # تحديد الفروع المستهدفة
        if branch_id:
            target_branches = [self.Branch.objects.get(id=branch_id)]
        else:
            target_branches = self.Branch.objects.filter(
                is_active=True,
                branch_type__in=['showroom', 'store', 'branch']
            )
        
        # الحصول على المصنع/المستودع الرئيسي
        source_branch = self.Branch.objects.filter(
            is_active=True,
            branch_type__in=['factory', 'warehouse', 'main']
        ).first()
        
        if not source_branch:
            return suggestions
        
        for branch in target_branches:
            stock_levels = self.get_branch_stock_levels(branch.id)
            
            for level in stock_levels:
                if not level.needs_replenishment and not include_non_critical:
                    continue
                
                # الحصول على المتاح في المصدر
                source_stock = self.Stock.objects.filter(
                    location=source_branch.location,
                    product_id=level.product_id
                ).first()
                
                source_available = source_stock.quantity if source_stock else Decimal('0')
                
                # تحديد الأولوية
                if level.is_critical:
                    priority = ReplenishmentPriority.URGENT
                elif level.fill_rate < 30:
                    priority = ReplenishmentPriority.HIGH
                elif level.needs_replenishment:
                    priority = ReplenishmentPriority.NORMAL
                else:
                    priority = ReplenishmentPriority.LOW
                
                # حساب أيام حتى نفاد المخزون (تقدير)
                avg_daily_sales = self._get_avg_daily_sales(branch.id, level.product_id)
                if avg_daily_sales > 0:
                    days_until_stockout = int(level.current_quantity / avg_daily_sales)
                else:
                    days_until_stockout = 999
                
                # تكلفة
                product = self.Product.objects.get(id=level.product_id)
                unit_cost = product.cost or Decimal('0')
                suggested_qty = level.suggested_quantity
                
                suggestions.append(ReplenishmentSuggestion(
                    branch_id=branch.id,
                    branch_name=branch.name,
                    product_id=level.product_id,
                    product_name=level.product_name,
                    product_sku=product.sku,
                    current_stock=level.current_quantity,
                    suggested_quantity=suggested_qty,
                    source_branch_id=source_branch.id,
                    source_branch_name=source_branch.name,
                    source_available=source_available,
                    priority=priority,
                    estimated_days_until_stockout=days_until_stockout,
                    unit_cost=unit_cost,
                    total_cost=suggested_qty * unit_cost
                ))
        
        # ترتيب حسب الأولوية
        priority_order = {
            ReplenishmentPriority.URGENT: 0,
            ReplenishmentPriority.HIGH: 1,
            ReplenishmentPriority.NORMAL: 2,
            ReplenishmentPriority.LOW: 3
        }
        suggestions.sort(key=lambda x: (priority_order[x.priority], x.estimated_days_until_stockout))
        
        return suggestions
    
    def _get_avg_daily_sales(self, branch_id: int, product_id: int, days: int = 30) -> Decimal:
        """حساب متوسط المبيعات اليومية"""
        from sales.models import SaleItem
        
        since = timezone.now() - timedelta(days=days)
        
        try:
            result = SaleItem.objects.filter(
                sale__branch_id=branch_id,
                product_id=product_id,
                sale__created_at__gte=since
            ).aggregate(total=Sum('quantity'))
            
            total_sold = result['total'] or Decimal('0')
            return total_sold / days
        except:
            return Decimal('0')
    
    @transaction.atomic
    def create_replenishment_order(
        self,
        suggestions: List[ReplenishmentSuggestion],
        user,
        notes: str = ''
    ) -> Dict[int, 'BranchTransfer']:
        """
        إنشاء أوامر تموين من الاقتراحات
        يتم تجميع الاقتراحات حسب الفرع المستهدف
        """
        transfers = {}
        
        # تجميع حسب الفرع
        by_branch = {}
        for suggestion in suggestions:
            if suggestion.branch_id not in by_branch:
                by_branch[suggestion.branch_id] = []
            by_branch[suggestion.branch_id].append(suggestion)
        
        for branch_id, branch_suggestions in by_branch.items():
            if not branch_suggestions:
                continue
            
            # إنشاء التحويل
            source_branch = self.Branch.objects.get(id=branch_suggestions[0].source_branch_id)
            target_branch = self.Branch.objects.get(id=branch_id)
            
            transfer = self.BranchTransfer.objects.create(
                from_branch=source_branch,
                to_branch=target_branch,
                status='pending',
                transfer_date=timezone.now().date(),
                requested_by=user,
                notes=f"طلب تموين تلقائي - {notes}"
            )
            
            # إضافة البنود
            for suggestion in branch_suggestions:
                # التحقق من توفر الكمية في المصدر
                actual_qty = min(suggestion.suggested_quantity, suggestion.source_available)
                
                if actual_qty > 0:
                    self.BranchTransferItem.objects.create(
                        transfer=transfer,
                        product_id=suggestion.product_id,
                        quantity=actual_qty,
                        unit_cost=suggestion.unit_cost
                    )
            
            transfers[branch_id] = transfer
        
        return transfers
    
    def get_distribution_dashboard(self) -> Dict:
        """
        لوحة معلومات التوزيع
        """
        # إحصائيات عامة
        showrooms = self.Branch.objects.filter(
            is_active=True,
            branch_type__in=['showroom', 'store']
        )
        
        total_showrooms = showrooms.count()
        
        # المعارض التي تحتاج تموين
        needs_replenishment = 0
        critical_items = 0
        
        for showroom in showrooms:
            levels = self.get_branch_stock_levels(showroom.id)
            if any(l.needs_replenishment for l in levels):
                needs_replenishment += 1
            critical_items += sum(1 for l in levels if l.is_critical)
        
        # التحويلات المعلقة
        pending_transfers = self.BranchTransfer.objects.filter(
            status__in=['pending', 'approved', 'in_transit']
        ).count()
        
        # قيمة التحويلات في الطريق
        in_transit_value = self.BranchTransferItem.objects.filter(
            transfer__status='in_transit'
        ).aggregate(
            total=Sum(F('quantity') * F('unit_cost'))
        )['total'] or Decimal('0')
        
        # أفضل المعارض أداءً (المخزون الأكثر تدويراً)
        # (تحتاج بيانات المبيعات لحساب دقيق)
        
        return {
            'total_showrooms': total_showrooms,
            'showrooms_need_replenishment': needs_replenishment,
            'critical_items_count': critical_items,
            'pending_transfers': pending_transfers,
            'in_transit_value': float(in_transit_value),
            'timestamp': timezone.now().isoformat()
        }
    
    def get_inter_branch_movements(
        self,
        from_date: date,
        to_date: date,
        branch_id: Optional[int] = None
    ) -> List[Dict]:
        """
        تقرير حركة المخزون بين الفروع
        """
        transfers_query = self.BranchTransfer.objects.filter(
            transfer_date__gte=from_date,
            transfer_date__lte=to_date,
            status='received'
        ).select_related('from_branch', 'to_branch')
        
        if branch_id:
            transfers_query = transfers_query.filter(
                Q(from_branch_id=branch_id) | Q(to_branch_id=branch_id)
            )
        
        movements = []
        for transfer in transfers_query:
            items_data = list(transfer.items.values(
                'product__name', 'product__sku', 'quantity', 'unit_cost'
            ))
            
            total_value = sum(
                (item['quantity'] or 0) * (item['unit_cost'] or 0)
                for item in items_data
            )
            
            movements.append({
                'transfer_id': transfer.id,
                'transfer_number': transfer.transfer_number,
                'from_branch': transfer.from_branch.name,
                'to_branch': transfer.to_branch.name,
                'transfer_date': transfer.transfer_date.isoformat(),
                'received_date': transfer.actual_arrival.isoformat() if transfer.actual_arrival else None,
                'items_count': len(items_data),
                'total_quantity': sum(item['quantity'] or 0 for item in items_data),
                'total_value': float(total_value),
                'items': items_data
            })
        
        return movements


# ==================== نماذج قاعدة البيانات ====================

class ShowroomReplenishmentRequest(models.Model):
    """
    طلب تموين المعرض
    """
    id = models.AutoField(primary_key=True)
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('pending', 'قيد الانتظار'),
        ('approved', 'معتمد'),
        ('processing', 'قيد التنفيذ'),
        ('shipped', 'تم الشحن'),
        ('received', 'مستلم'),
        ('cancelled', 'ملغى'),
    ]
    
    PRIORITY_CHOICES = [
        ('urgent', 'عاجل'),
        ('high', 'مرتفع'),
        ('normal', 'عادي'),
        ('low', 'منخفض'),
    ]
    
    request_number = models.CharField('رقم الطلب', max_length=50, unique=True)
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.CASCADE,
        related_name='replenishment_requests', verbose_name='المعرض'
    )
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField('الأولوية', max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    request_date = models.DateField('تاريخ الطلب', default=timezone.now)
    required_date = models.DateField('التاريخ المطلوب', null=True, blank=True)
    
    # المسؤولين
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='replenishment_requests', verbose_name='طلب بواسطة'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='replenishment_approvals', verbose_name='اعتمد بواسطة'
    )
    
    # الربط بالتحويل
    transfer = models.ForeignKey(
        'branches.BranchTransfer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='replenishment_requests', verbose_name='أمر التحويل'
    )
    
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'طلب تموين معرض'
        verbose_name_plural = 'طلبات تموين المعارض'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['branch', 'status']),
            models.Index(fields=['request_date']),
        ]
    
    def __str__(self):
        return f"{self.request_number} - {self.branch.name}"
    
    def save(self, *args, **kwargs):
        if not self.request_number:
            ym = timezone.now().strftime('%Y%m')
            last = ShowroomReplenishmentRequest.objects.filter(
                request_number__startswith=f'REP-{ym}-'
            ).order_by('id').last()
            seq = 1
            if last and last.request_number:
                try:
                    seq = int(last.request_number.split('-')[-1]) + 1
                except:
                    pass
            self.request_number = f'REP-{ym}-{seq:04d}'
        super().save(*args, **kwargs)


class ReplenishmentRequestItem(models.Model):
    """
    بند طلب التموين
    """
    id = models.AutoField(primary_key=True)
    
    request = models.ForeignKey(
        ShowroomReplenishmentRequest, on_delete=models.CASCADE,
        related_name='items', verbose_name='الطلب'
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.CASCADE,
        related_name='replenishment_items', verbose_name='المنتج'
    )
    
    requested_quantity = models.DecimalField('الكمية المطلوبة', max_digits=12, decimal_places=3)
    approved_quantity = models.DecimalField('الكمية المعتمدة', max_digits=12, decimal_places=3, default=Decimal('0'))
    shipped_quantity = models.DecimalField('الكمية المشحونة', max_digits=12, decimal_places=3, default=Decimal('0'))
    received_quantity = models.DecimalField('الكمية المستلمة', max_digits=12, decimal_places=3, default=Decimal('0'))
    
    current_stock = models.DecimalField('المخزون الحالي', max_digits=12, decimal_places=3, default=Decimal('0'))
    reorder_point = models.DecimalField('نقطة إعادة الطلب', max_digits=12, decimal_places=3, default=Decimal('0'))
    
    notes = models.CharField('ملاحظات', max_length=255, blank=True)
    
    class Meta:
        verbose_name = 'بند طلب تموين'
        verbose_name_plural = 'بنود طلبات التموين'
        unique_together = ['request', 'product']
    
    def __str__(self):
        return f"{self.product.name} x {self.requested_quantity}"


class BranchStockSettings(models.Model):
    """
    إعدادات المخزون لكل فرع/منتج
    """
    id = models.AutoField(primary_key=True)
    
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.CASCADE,
        related_name='stock_settings', verbose_name='الفرع'
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.CASCADE,
        related_name='branch_stock_settings', verbose_name='المنتج'
    )
    
    minimum_quantity = models.DecimalField('الحد الأدنى', max_digits=12, decimal_places=3, default=Decimal('0'))
    reorder_point = models.DecimalField('نقطة إعادة الطلب', max_digits=12, decimal_places=3, default=Decimal('0'))
    maximum_quantity = models.DecimalField('الحد الأقصى', max_digits=12, decimal_places=3, default=Decimal('0'))
    
    auto_replenish = models.BooleanField('تموين تلقائي', default=False)
    
    # مصدر التموين المفضل
    preferred_source = models.ForeignKey(
        'branches.Branch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='supplied_products', verbose_name='مصدر التموين المفضل'
    )
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'إعدادات مخزون فرع'
        verbose_name_plural = 'إعدادات مخزون الفروع'
        unique_together = ['branch', 'product']
        indexes = [
            models.Index(fields=['branch', 'product']),
        ]
    
    def __str__(self):
        return f"{self.branch.code} - {self.product.name}"


class AutoReplenishmentRule(models.Model):
    """
    قواعد التموين التلقائي
    """
    id = models.AutoField(primary_key=True)
    
    name = models.CharField('اسم القاعدة', max_length=200)
    is_active = models.BooleanField('نشط', default=True)
    
    # الفروع المستهدفة
    target_branches = models.ManyToManyField(
        'branches.Branch', related_name='auto_replenishment_rules',
        blank=True, verbose_name='الفروع المستهدفة'
    )
    apply_to_all_showrooms = models.BooleanField('تطبيق على جميع المعارض', default=False)
    
    # المنتجات
    target_products = models.ManyToManyField(
        'inventory.Product', related_name='auto_replenishment_rules',
        blank=True, verbose_name='المنتجات المستهدفة'
    )
    target_categories = models.ManyToManyField(
        'inventory.Category', related_name='auto_replenishment_rules',
        blank=True, verbose_name='فئات المنتجات'
    )
    apply_to_all_products = models.BooleanField('تطبيق على جميع المنتجات', default=False)
    
    # شروط التموين
    trigger_at_reorder_point = models.BooleanField('التشغيل عند نقطة إعادة الطلب', default=True)
    trigger_at_minimum = models.BooleanField('التشغيل عند الحد الأدنى', default=False)
    
    # كمية التموين
    replenish_to_maximum = models.BooleanField('التموين للحد الأقصى', default=True)
    fixed_replenish_quantity = models.DecimalField(
        'كمية تموين ثابتة', max_digits=12, decimal_places=3,
        null=True, blank=True
    )
    
    # الجدولة
    check_frequency_hours = models.PositiveIntegerField('تكرار الفحص (ساعات)', default=24)
    last_run = models.DateTimeField('آخر تشغيل', null=True, blank=True)
    
    # الإشعارات
    notify_on_trigger = models.BooleanField('إشعار عند التشغيل', default=True)
    notification_emails = models.TextField('بريد الإشعارات', blank=True,
        help_text='بريد إلكتروني واحد في كل سطر')
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='auto_replenishment_rules', verbose_name='أنشئ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'قاعدة تموين تلقائي'
        verbose_name_plural = 'قواعد التموين التلقائي'
    
    def __str__(self):
        return self.name
    
    def should_run(self) -> bool:
        """هل يجب تشغيل القاعدة؟"""
        if not self.is_active:
            return False
        
        if not self.last_run:
            return True
        
        next_run = self.last_run + timedelta(hours=self.check_frequency_hours)
        return timezone.now() >= next_run
