"""
Product Traceability & Recall System
نظام تتبع المنتجات والاسترجاع

يوفر تتبع كامل من الخامة إلى العميل
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from typing import List, Dict, Optional


class ProductTraceability(models.Model):
    """تتبع المنتج الكامل"""
    
    TRACE_TYPE_CHOICES = [
        ('raw_material', 'خامة'),
        ('wip', 'نصف مصنع'),
        ('finished', 'منتج تام'),
        ('sold', 'مباع'),
    ]
    
    trace_id = models.CharField('معرف التتبع', max_length=100, unique=True, db_index=True)
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, verbose_name='المنتج')
    batch_number = models.CharField('رقم الدفعة', max_length=100, db_index=True)
    lot_number = models.CharField('رقم اللوت', max_length=100, blank=True, db_index=True)
    
    # المصدر
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المورد')
    purchase_bill = models.ForeignKey('purchases.PurchaseBill', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='فاتورة الشراء')
    received_date = models.DateField('تاريخ الاستلام')
    
    # الإنتاج
    production_order = models.ForeignKey('production.ProductionOrder', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='أمر الإنتاج')
    production_date = models.DateField('تاريخ الإنتاج', null=True, blank=True)
    work_center = models.ForeignKey('production.ProductionWorkCenter', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='خط الإنتاج')
    
    # البيع
    invoice = models.ForeignKey('sales.Invoice', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الفاتورة')
    customer = models.ForeignKey('crm.Customer', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='العميل')
    sale_date = models.DateField('تاريخ البيع', null=True, blank=True)
    
    # الموقع الحالي
    current_location = models.ForeignKey('inventory.Location', on_delete=models.SET_NULL, null=True, verbose_name='الموقع الحالي')
    current_status = models.CharField('الحالة الحالية', max_length=20, choices=TRACE_TYPE_CHOICES, default='raw_material')
    
    quantity = models.DecimalField('الكمية', max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField('تكلفة الوحدة', max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # فحص الجودة
    quality_inspection = models.ForeignKey('quality_control.QualityInspection', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='فحص الجودة')
    quality_status = models.CharField('حالة الجودة', max_length=20, default='pending')
    
    # الخامات المستخدمة (للمنتج التام)
    raw_materials_used = models.JSONField('الخامات المستخدمة', default=list, blank=True)
    
    is_recalled = models.BooleanField('تم استرجاعه', default=False)
    recall_order = models.ForeignKey('quality_control.RecallOrder', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='أمر الاسترجاع')
    
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تتبع منتج'
        verbose_name_plural = 'تتبع المنتجات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['trace_id']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['product', 'batch_number']),
            models.Index(fields=['current_status', 'is_recalled']),
        ]
    
    def __str__(self):
        return f"{self.trace_id} - {self.product.name}"
    
    def get_full_trace(self) -> Dict:
        """الحصول على التتبع الكامل للمنتج"""
        return {
            'trace_id': self.trace_id,
            'product': {
                'id': self.product.id,
                'name': self.product.name,
                'sku': self.product.sku
            },
            'batch_number': self.batch_number,
            'origin': {
                'supplier': self.supplier.name if self.supplier else None,
                'purchase_bill': self.purchase_bill.number if self.purchase_bill else None,
                'received_date': self.received_date.isoformat() if self.received_date else None
            },
            'production': {
                'order': self.production_order.order_number if self.production_order else None,
                'date': self.production_date.isoformat() if self.production_date else None,
                'work_center': self.work_center.name if self.work_center else None,
                'raw_materials': self.raw_materials_used
            },
            'sale': {
                'invoice': self.invoice.invoice_number if self.invoice else None,
                'customer': self.customer.name if self.customer else None,
                'date': self.sale_date.isoformat() if self.sale_date else None
            },
            'quality': {
                'inspection': self.quality_inspection.code if self.quality_inspection else None,
                'status': self.quality_status
            },
            'current': {
                'location': self.current_location.name if self.current_location else None,
                'status': self.current_status,
                'quantity': float(self.quantity)
            },
            'recalled': self.is_recalled
        }


class RecallOrder(models.Model):
    """أمر استرجاع منتج"""
    
    SEVERITY_CHOICES = [
        ('low', 'منخفض - احتياطي'),
        ('medium', 'متوسط - مشكلة جودة'),
        ('high', 'عالي - خطر على السلامة'),
        ('critical', 'حرج - خطر شديد'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغى'),
    ]
    
    recall_number = models.CharField('رقم الاسترجاع', max_length=50, unique=True)
    title = models.CharField('عنوان الاسترجاع', max_length=200)
    description = models.TextField('الوصف')
    
    severity = models.CharField('مستوى الخطورة', max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # نطاق الاسترجاع
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, verbose_name='المنتج', null=True, blank=True)
    batch_numbers = models.JSONField('أرقام الدفعات', default=list)  # قائمة أرقام الدفعات المتأثرة
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المورد المتأثر')
    
    # التواريخ
    issue_date = models.DateField('تاريخ اكتشاف المشكلة')
    recall_start_date = models.DateField('تاريخ بدء الاسترجاع')
    target_completion_date = models.DateField('الموعد المستهدف للإنهاء')
    actual_completion_date = models.DateField('تاريخ الإنهاء الفعلي', null=True, blank=True)
    
    # السبب
    root_cause = models.TextField('السبب الجذري')
    defect_type = models.CharField('نوع العيب', max_length=100)
    
    # الإجراءات
    corrective_action = models.TextField('الإجراء التصحيحي')
    preventive_action = models.TextField('الإجراء الوقائي')
    
    # المسؤولون
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='initiated_recalls', verbose_name='أنشئ بواسطة')
    responsible_person = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='responsible_recalls', verbose_name='المسؤول')
    
    # الإحصائيات
    total_units_affected = models.IntegerField('إجمالي الوحدات المتأثرة', default=0)
    units_recalled = models.IntegerField('الوحدات المسترجعة', default=0)
    units_in_stock = models.IntegerField('وحدات في المخزون', default=0)
    units_sold = models.IntegerField('وحدات مباعة', default=0)
    
    # التكاليف
    estimated_cost = models.DecimalField('التكلفة المقدرة', max_digits=15, decimal_places=2, default=Decimal('0'))
    actual_cost = models.DecimalField('التكلفة الفعلية', max_digits=15, decimal_places=2, default=Decimal('0'))
    
    # الاتصالات
    customers_notified = models.BooleanField('تم إخطار العملاء', default=False)
    notification_date = models.DateField('تاريخ الإخطار', null=True, blank=True)
    notification_method = models.CharField('طريقة الإخطار', max_length=100, blank=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    attachments = models.JSONField('المرفقات', default=list, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'أمر استرجاع'
        verbose_name_plural = 'أوامر الاسترجاع'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recall_number} - {self.title}"
    
    def activate(self):
        """تفعيل أمر الاسترجاع"""
        if self.status == 'draft':
            self.status = 'active'
            self.recall_start_date = timezone.now().date()
            self.save()
            
            # تحديث حالة المنتجات المتتبعة
            ProductTraceability.objects.filter(
                product=self.product,
                batch_number__in=self.batch_numbers,
                is_recalled=False
            ).update(
                is_recalled=True,
                recall_order=self
            )
            
            return True
        return False
    
    def calculate_statistics(self):
        """حساب الإحصائيات"""
        traces = ProductTraceability.objects.filter(
            product=self.product,
            batch_number__in=self.batch_numbers
        )
        
        self.total_units_affected = traces.count()
        self.units_in_stock = traces.filter(current_status__in=['raw_material', 'wip', 'finished']).count()
        self.units_sold = traces.filter(current_status='sold').count()
        self.save()


class RecallItem(models.Model):
    """عنصر في أمر الاسترجاع"""
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('contacted', 'تم الاتصال'),
        ('returned', 'تم الاسترجاع'),
        ('refused', 'رفض الاسترجاع'),
        ('destroyed', 'تم الإتلاف'),
    ]
    
    recall_order = models.ForeignKey(RecallOrder, on_delete=models.CASCADE, related_name='items', verbose_name='أمر الاسترجاع')
    traceability = models.ForeignKey(ProductTraceability, on_delete=models.CASCADE, verbose_name='تتبع المنتج')
    
    customer = models.ForeignKey('crm.Customer', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='العميل')
    invoice = models.ForeignKey('sales.Invoice', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الفاتورة')
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # الاتصال
    contact_attempts = models.IntegerField('محاولات الاتصال', default=0)
    last_contact_date = models.DateField('آخر محاولة اتصال', null=True, blank=True)
    contact_notes = models.TextField('ملاحظات الاتصال', blank=True)
    
    # الاسترجاع
    return_date = models.DateField('تاريخ الاسترجاع', null=True, blank=True)
    return_method = models.CharField('طريقة الاسترجاع', max_length=100, blank=True)
    
    # التعويض
    refund_amount = models.DecimalField('مبلغ الاسترداد', max_digits=12, decimal_places=2, default=Decimal('0'))
    replacement_provided = models.BooleanField('تم توفير بديل', default=False)
    
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='تم التعامل بواسطة')
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'عنصر استرجاع'
        verbose_name_plural = 'عناصر الاسترجاع'
        ordering = ['status', '-created_at']
    
    def __str__(self):
        return f"{self.recall_order.recall_number} - {self.traceability.trace_id}"


class TraceabilityService:
    """خدمة التتبع"""
    
    @staticmethod
    def create_trace_from_purchase(purchase_item) -> ProductTraceability:
        """إنشاء تتبع من فاتورة شراء"""
        trace_id = f"PUR-{purchase_item.bill.number}-{purchase_item.product.sku}-{timezone.now().timestamp()}"
        
        trace = ProductTraceability.objects.create(
            trace_id=trace_id,
            product=purchase_item.product,
            batch_number=purchase_item.bill.number,
            lot_number=getattr(purchase_item, 'lot_number', ''),
            supplier=purchase_item.bill.supplier,
            purchase_bill=purchase_item.bill,
            received_date=purchase_item.bill.date,
            current_location=purchase_item.location,
            current_status='raw_material',
            quantity=purchase_item.quantity,
            unit_cost=purchase_item.cost
        )
        
        return trace
    
    @staticmethod
    def create_trace_from_production(production_order, finished_product) -> ProductTraceability:
        """إنشاء تتبع من أمر إنتاج"""
        trace_id = f"PRD-{production_order.order_number}-{finished_product.sku}-{timezone.now().timestamp()}"
        
        # جمع الخامات المستخدمة
        raw_materials = []
        if hasattr(production_order, 'material_issues'):
            for issue in production_order.material_issues.all():
                for item in issue.items.all():
                    raw_materials.append({
                        'product': item.product.name,
                        'sku': item.product.sku,
                        'quantity': float(item.quantity),
                        'batch': getattr(item, 'batch_number', '')
                    })
        
        trace = ProductTraceability.objects.create(
            trace_id=trace_id,
            product=finished_product,
            batch_number=production_order.order_number,
            production_order=production_order,
            production_date=timezone.now().date(),
            work_center=production_order.work_center if hasattr(production_order, 'work_center') else None,
            current_status='finished',
            quantity=production_order.quantity_to_produce,
            raw_materials_used=raw_materials
        )
        
        return trace
    
    @staticmethod
    def trace_product_journey(trace_id: str) -> Dict:
        """تتبع رحلة المنتج الكاملة"""
        try:
            trace = ProductTraceability.objects.get(trace_id=trace_id)
            return trace.get_full_trace()
        except ProductTraceability.DoesNotExist:
            return {'error': 'Trace ID not found'}
    
    @staticmethod
    def find_affected_products(batch_number: str, product=None) -> List[ProductTraceability]:
        """البحث عن جميع المنتجات المتأثرة بدفعة معينة"""
        query = models.Q(batch_number=batch_number)
        if product:
            query &= models.Q(product=product)
        
        return ProductTraceability.objects.filter(query).select_related(
            'product', 'supplier', 'customer', 'current_location'
        )
