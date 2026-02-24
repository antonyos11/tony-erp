"""
نماذج نظام إدارة المشتريات المتقدم
========================================
- طلبات الشراء (Purchase Request - PR)
- طلب عروض أسعار (Request for Quotation - RFQ)
- عروض الموردين (Supplier Quotation)
- مقارنة العروض والسجل التاريخي للأسعار
- جدول التسليم وتتبع الشحنات
- استلام الواردات مع اختلاف الكميات والجودة
"""

from django.db import models, transaction
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from inventory.models import Product, Location, Stock
from partners.models import Partner
from core.sequence_utils import next_sequence, format_code


# ===========================
# طلبات الشراء (PR)
# ===========================

class PurchaseRequest(models.Model):
    """طلب شراء (PR) - يُنشأ من قبل الأقسام ويُحوّل لأمر شراء بعد الاعتماد"""

    STATUS_CHOICES = [
        ("draft", _("مسودة")),
        ("pending", _("قيد المراجعة")),
        ("approved", _("معتمد")),
        ("rejected", _("مرفوض")),
        ("converted", _("مُحوّل لأمر شراء")),
        ("cancelled", _("ملغى")),
    ]

    PRIORITY_CHOICES = [
        ("low", _("منخفضة")),
        ("normal", _("عادية")),
        ("high", _("عالية")),
        ("urgent", _("عاجلة")),
    ]

    id = models.AutoField(primary_key=True)
    number = models.CharField(_("رقم الطلب"), max_length=50, unique=True)
    department = models.CharField(_("القسم الطالب"), max_length=100, blank=True)
    requested_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='purchase_requests',
        verbose_name=_('طلب بواسطة')
    )
    date = models.DateField(_("تاريخ الطلب"), default=timezone.now)
    required_date = models.DateField(_("تاريخ الحاجة"), null=True, blank=True)
    status = models.CharField(_("الحالة"), max_length=20, choices=STATUS_CHOICES, default="draft")
    priority = models.CharField(_("الأولوية"), max_length=20, choices=PRIORITY_CHOICES, default="normal")
    notes = models.TextField(_("ملاحظات"), blank=True)
    justification = models.TextField(_("التبرير/السبب"), blank=True)

    # الاعتماد
    approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_purchase_requests',
        verbose_name=_('اعتمد بواسطة')
    )
    approved_at = models.DateTimeField(_("تاريخ الاعتماد"), null=True, blank=True)
    approval_notes = models.TextField(_("ملاحظات الاعتماد"), blank=True)

    # الرفض
    rejected_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_purchase_requests',
        verbose_name=_('رفض بواسطة')
    )
    rejected_at = models.DateTimeField(_("تاريخ الرفض"), null=True, blank=True)
    rejection_reason = models.TextField(_("سبب الرفض"), blank=True)

    # الربط بأمر الشراء
    purchase_order = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_requests',
        verbose_name=_('أمر الشراء المُحوّل')
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = _("طلب شراء")
        verbose_name_plural = _("طلبات الشراء")
        indexes = [
            models.Index(fields=['status', 'date']),
            models.Index(fields=['requested_by', 'date']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['required_date']),
        ]

    def __str__(self):
        return f"{self.number} - {self.get_status_display()}"

    @property
    def total_estimated_amount(self):
        """إجمالي القيمة التقديرية"""
        return sum(item.total_estimated for item in self.items.all())

    @property
    def is_editable(self):
        """هل يمكن تعديل الطلب؟"""
        return self.status in ['draft', 'pending']

    @property
    def is_approvable(self):
        """هل يمكن اعتماد الطلب؟"""
        return self.status == 'pending'

    def save(self, *args, **kwargs):
        if not self.number:
            seq = next_sequence('PURCHASE_REQUEST')
            self.number = format_code('PR', seq)
        super().save(*args, **kwargs)


class PurchaseRequestItem(models.Model):
    """بنود طلب الشراء"""
    
    id = models.AutoField(primary_key=True)
    request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('طلب الشراء')
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name=_('المنتج'))
    quantity = models.DecimalField(_("الكمية المطلوبة"), max_digits=12, decimal_places=2)
    unit = models.CharField(_("الوحدة"), max_length=50, blank=True)
    estimated_price = models.DecimalField(
        _("السعر التقديري"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    specifications = models.TextField(_("المواصفات المطلوبة"), blank=True)
    notes = models.TextField(_("ملاحظات"), blank=True)
    
    class Meta:
        verbose_name = _("بند طلب شراء")
        verbose_name_plural = _("بنود طلبات الشراء")
    
    @property
    def total_estimated(self):
        return self.quantity * self.estimated_price
    
    def __str__(self):
        return f"{self.request.number} - {self.product.name}"


# ===========================
# طلب عروض أسعار (RFQ)
# ===========================

class RFQ(models.Model):
    """طلب عروض أسعار (Request for Quotation)"""

    STATUS_CHOICES = [
        ("draft", _("مسودة")),
        ("sent", _("مُرسل")),
        ("received", _("استُلمت عروض")),
        ("evaluated", _("تم التقييم")),
        ("awarded", _("تم الترسية")),
        ("cancelled", _("ملغى")),
        ("closed", _("مغلق")),
    ]

    id = models.AutoField(primary_key=True)
    number = models.CharField(_("رقم RFQ"), max_length=50, unique=True)
    title = models.CharField(_("العنوان"), max_length=200, blank=True)
    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rfqs',
        verbose_name=_('طلب الشراء')
    )
    title = models.CharField(_("العنوان"), max_length=200)
    date = models.DateField(_("تاريخ الإصدار"), default=timezone.now)
    deadline = models.DateField(_("آخر موعد لتقديم العروض"))
    status = models.CharField(_("الحالة"), max_length=20, choices=STATUS_CHOICES, default="draft")
    terms_conditions = models.TextField(_("الشروط والأحكام"), blank=True)
    payment_terms = models.TextField(_("شروط الدفع"), blank=True)
    delivery_terms = models.TextField(_("شروط التسليم"), blank=True)
    notes = models.TextField(_("ملاحظات"), blank=True)
    
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_rfqs',
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-id']
        verbose_name = _("طلب عرض أسعار")
        verbose_name_plural = _("طلبات عروض الأسعار")
    
    def __str__(self):
        return f"{self.number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            seq = next_sequence('RFQ')
            self.number = format_code('RFQ', seq)
        super().save(*args, **kwargs)


class RFQItem(models.Model):
    """بنود طلب عروض الأسعار"""
    
    id = models.AutoField(primary_key=True)
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='items', verbose_name=_('RFQ'))
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name=_('المنتج'))
    quantity = models.DecimalField(_("الكمية المطلوبة"), max_digits=12, decimal_places=2)
    unit = models.CharField(_("الوحدة"), max_length=50, blank=True)
    specifications = models.TextField(_("المواصفات"), blank=True)
    target_price = models.DecimalField(
        _("السعر المستهدف"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _("بند طلب عرض أسعار")
        verbose_name_plural = _("بنود طلبات عروض الأسعار")
    
    def __str__(self):
        return f"{self.rfq.number} - {self.product.name}"


class RFQSupplier(models.Model):
    """الموردون المدعوون لتقديم عروض"""
    
    id = models.AutoField(primary_key=True)
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='invited_suppliers')
    supplier = models.ForeignKey(Partner, on_delete=models.PROTECT, verbose_name=_('المورد'))
    invited_date = models.DateTimeField(_("تاريخ الدعوة"), default=timezone.now)
    email_sent = models.BooleanField(_("تم إرسال البريد"), default=False)
    quotation_received = models.BooleanField(_("استلام العرض"), default=False)
    notes = models.TextField(_("ملاحظات"), blank=True)
    
    class Meta:
        unique_together = [['rfq', 'supplier']]
        verbose_name = _("مورد مدعو")
        verbose_name_plural = _("الموردون المدعوون")
    
    def __str__(self):
        return f"{self.rfq.number} - {self.supplier.name}"


# ===========================
# عروض الموردين
# ===========================

class SupplierQuotation(models.Model):
    """عرض سعر من مورد"""
    
    STATUS_CHOICES = [
        ("draft", _("مسودة")),
        ("submitted", _("مُقدم")),
        ("under_review", _("قيد المراجعة")),
        ("accepted", _("مقبول")),
        ("rejected", _("مرفوض")),
        ("expired", _("منتهي")),
    ]
    
    id = models.AutoField(primary_key=True)
    number = models.CharField(_("رقم العرض"), max_length=50, unique=True)
    rfq = models.ForeignKey(
        RFQ,
        on_delete=models.PROTECT,
        related_name='quotations',
        verbose_name=_('RFQ')
    )
    supplier = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name='quotations',
        verbose_name=_('المورد')
    )
    quotation_date = models.DateField(_("تاريخ العرض"), default=timezone.now)
    valid_until = models.DateField(_("صالح حتى"))
    status = models.CharField(_("الحالة"), max_length=20, choices=STATUS_CHOICES, default="draft")
    
    # شروط العرض
    payment_terms = models.TextField(_("شروط الدفع"), blank=True)
    delivery_time = models.IntegerField(_("مدة التوريد (أيام)"), default=0)
    warranty_period = models.CharField(_("فترة الضمان"), max_length=100, blank=True)
    
    # التكاليف الإضافية
    shipping_cost = models.DecimalField(
        _("تكلفة الشحن"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    tax_amount = models.DecimalField(
        _("قيمة الضريبة"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    discount = models.DecimalField(
        _("الخصم"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    
    notes = models.TextField(_("ملاحظات"), blank=True)
    attachments = models.FileField(
        _("المرفقات"),
        upload_to='quotations/%Y/%m/',
        null=True,
        blank=True
    )
    
    # التقييم
    evaluation_score = models.DecimalField(
        _("درجة التقييم"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    evaluation_notes = models.TextField(_("ملاحظات التقييم"), blank=True)
    evaluated_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evaluated_quotations',
        verbose_name=_('قيّم بواسطة')
    )
    evaluated_at = models.DateTimeField(_("تاريخ التقييم"), null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-quotation_date', '-id']
        verbose_name = _("عرض سعر مورد")
        verbose_name_plural = _("عروض أسعار الموردين")
        indexes = [
            models.Index(fields=['rfq', 'supplier']),
            models.Index(fields=['status', 'quotation_date']),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.supplier.name}"
    
    @property
    def subtotal(self):
        """المجموع الفرعي (قبل الشحن والضرائب)"""
        return sum(item.total for item in self.items.all())
    
    @property
    def total(self):
        """المجموع النهائي"""
        return self.subtotal + self.shipping_cost + self.tax_amount - self.discount
    
    def save(self, *args, **kwargs):
        if not self.number:
            seq = next_sequence('QUOTATION')
            self.number = format_code('QT', seq)
        super().save(*args, **kwargs)


class QuotationItem(models.Model):
    """بنود عرض سعر المورد"""
    
    id = models.AutoField(primary_key=True)
    quotation = models.ForeignKey(
        SupplierQuotation,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('عرض السعر')
    )
    rfq_item = models.ForeignKey(
        RFQItem,
        on_delete=models.PROTECT,
        verbose_name=_('بند RFQ')
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT, 
        related_name='purchase_quotation_items',
        verbose_name=_('المنتج')
    )
    quantity = models.DecimalField(_("الكمية"), max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(_("سعر الوحدة"), max_digits=12, decimal_places=2)
    unit = models.CharField(_("الوحدة"), max_length=50, blank=True)
    brand = models.CharField(_("الماركة/المصنع"), max_length=100, blank=True)
    model = models.CharField(_("الموديل"), max_length=100, blank=True)
    specifications = models.TextField(_("المواصفات"), blank=True)
    notes = models.TextField(_("ملاحظات"), blank=True)
    
    class Meta:
        verbose_name = _("بند عرض سعر")
        verbose_name_plural = _("بنود عروض الأسعار")
    
    @property
    def total(self):
        return self.quantity * self.unit_price
    
    def __str__(self):
        return f"{self.quotation.number} - {self.product.name}"


# ===========================
# السجل التاريخي للأسعار
# ===========================

class ProductPriceHistory(models.Model):
    """السجل التاريخي لأسعار المواد من الموردين"""
    
    SOURCE_CHOICES = [
        ("quotation", _("عرض سعر")),
        ("purchase_bill", _("فاتورة شراء")),
        ("purchase_order", _("أمر شراء")),
        ("manual", _("إدخال يدوي")),
    ]
    
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name=_('المنتج')
    )
    supplier = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='product_prices',
        verbose_name=_('المورد')
    )
    price = models.DecimalField(_("السعر"), max_digits=12, decimal_places=2)
    quantity = models.DecimalField(_("الكمية"), max_digits=12, decimal_places=2, default=Decimal('1'))
    currency = models.CharField(_("العملة"), max_length=10, default="EGP")
    date = models.DateField(_("التاريخ"), default=timezone.now)
    source = models.CharField(_("المصدر"), max_length=20, choices=SOURCE_CHOICES)
    
    # الإشارة للمستند المصدر
    quotation = models.ForeignKey(
        SupplierQuotation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='price_records'
    )
    purchase_bill = models.ForeignKey(
        'PurchaseBill',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='price_records'
    )
    purchase_order = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='price_records'
    )
    
    notes = models.TextField(_("ملاحظات"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', '-id']
        verbose_name = _("سجل سعر منتج")
        verbose_name_plural = _("السجل التاريخي للأسعار")
        indexes = [
            models.Index(fields=['product', 'supplier', 'date']),
            models.Index(fields=['product', 'date']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.supplier.name} - {self.price}"


# ===========================
# جدول التسليم والشحنات
# ===========================

class SupplierLeadTime(models.Model):
    """جدول التسليم للموردين (Lead Time)"""
    
    id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='lead_times',
        verbose_name=_('المورد')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='supplier_lead_times',
        verbose_name=_('المنتج')
    )
    product_category = models.CharField(_("فئة المنتج"), max_length=100, blank=True)
    lead_time_days = models.IntegerField(_("مدة التوريد (أيام)"))
    min_order_quantity = models.DecimalField(
        _("الحد الأدنى للطلب"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    max_order_quantity = models.DecimalField(
        _("الحد الأقصى للطلب"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    is_active = models.BooleanField(_("نشط"), default=True)
    notes = models.TextField(_("ملاحظات"), blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("جدول توريد مورد")
        verbose_name_plural = _("جداول التوريد")
        unique_together = [['supplier', 'product']]
        indexes = [
            models.Index(fields=['supplier', 'is_active']),
        ]
    
    def __str__(self):
        product_str = self.product.name if self.product else self.product_category
        return f"{self.supplier.name} - {product_str} - {self.lead_time_days} يوم"


class Shipment(models.Model):
    """تتبع الشحنات"""
    
    STATUS_CHOICES = [
        ("pending", _("معلقة")),
        ("in_transit", _("في الطريق")),
        ("customs", _("في الجمارك")),
        ("arrived", _("وصلت")),
        ("received", _("استُلمت")),
        ("delayed", _("متأخرة")),
        ("cancelled", _("ملغاة")),
    ]
    
    id = models.AutoField(primary_key=True)
    number = models.CharField(_("رقم الشحنة"), max_length=50, unique=True)
    purchase_order = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.PROTECT,
        related_name='shipments',
        verbose_name=_('أمر الشراء')
    )
    supplier = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name='shipments',
        verbose_name=_('المورد')
    )
    
    # معلومات الشحن
    shipping_method = models.CharField(_("طريقة الشحن"), max_length=100, blank=True)
    carrier = models.CharField(_("شركة الشحن"), max_length=100, blank=True)
    tracking_number = models.CharField(_("رقم التتبع"), max_length=100, blank=True)
    awb_bl_number = models.CharField(_("رقم بوليصة الشحن"), max_length=100, blank=True)
    
    # التواريخ
    shipped_date = models.DateField(_("تاريخ الشحن"), null=True, blank=True)
    estimated_arrival = models.DateField(_("التاريخ المتوقع للوصول"), null=True, blank=True)
    actual_arrival = models.DateField(_("تاريخ الوصول الفعلي"), null=True, blank=True)
    
    status = models.CharField(_("الحالة"), max_length=20, choices=STATUS_CHOICES, default="pending")
    
    # التكاليف
    shipping_cost = models.DecimalField(
        _("تكلفة الشحن"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    customs_cost = models.DecimalField(
        _("تكلفة الجمارك"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    insurance_cost = models.DecimalField(
        _("تكلفة التأمين"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    
    notes = models.TextField(_("ملاحظات"), blank=True)
    attachments = models.FileField(
        _("المستندات"),
        upload_to='shipments/%Y/%m/',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-shipped_date', '-id']
        verbose_name = _("شحنة")
        verbose_name_plural = _("الشحنات")
        indexes = [
            models.Index(fields=['purchase_order', 'status']),
            models.Index(fields=['tracking_number']),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.purchase_order.number}"
    
    @property
    def total_cost(self):
        """إجمالي تكاليف الشحن"""
        return self.shipping_cost + self.customs_cost + self.insurance_cost
    
    @property
    def is_delayed(self):
        """هل الشحنة متأخرة؟"""
        if self.estimated_arrival and not self.actual_arrival:
            from django.utils import timezone
            return timezone.now().date() > self.estimated_arrival
        return False
    
    def save(self, *args, **kwargs):
        if not self.number:
            seq = next_sequence('SHIPMENT')
            self.number = format_code('SHP', seq)
        super().save(*args, **kwargs)


# ===========================
# استلام الواردات المتقدم
# ===========================

class GoodsReceipt(models.Model):
    """سجل استلام الواردات (مع إمكانية اختلاف الكميات والجودة)"""
    
    STATUS_CHOICES = [
        ("draft", _("مسودة")),
        ("completed", _("مكتمل")),
        ("with_variance", _("مع اختلافات")),
        ("rejected", _("مرفوض")),
    ]
    
    QUALITY_STATUS_CHOICES = [
        ("passed", _("مقبول")),
        ("failed", _("مرفوض")),
        ("partial", _("قبول جزئي")),
        ("pending", _("قيد الفحص")),
    ]
    
    id = models.AutoField(primary_key=True)
    number = models.CharField(_("رقم سند الاستلام"), max_length=50, unique=True)
    purchase_order = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.PROTECT,
        related_name='goods_receipts',
        verbose_name=_('أمر الشراء')
    )
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='goods_receipts',
        verbose_name=_('الشحنة')
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='goods_receipts',
        verbose_name=_('الموقع')
    )
    
    receipt_date = models.DateTimeField(_("تاريخ الاستلام"), default=timezone.now)
    status = models.CharField(_("الحالة"), max_length=20, choices=STATUS_CHOICES, default="draft")
    quality_status = models.CharField(
        _("حالة الجودة"),
        max_length=20,
        choices=QUALITY_STATUS_CHOICES,
        default="pending"
    )
    
    # الفحص الجودة
    inspected_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inspected_receipts',
        verbose_name=_('فُحص بواسطة')
    )
    inspection_date = models.DateTimeField(_("تاريخ الفحص"), null=True, blank=True)
    inspection_notes = models.TextField(_("ملاحظات الفحص"), blank=True)
    
    # الاستلام
    received_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_goods',
        verbose_name=_('استلم بواسطة')
    )
    
    notes = models.TextField(_("ملاحظات"), blank=True)
    attachments = models.FileField(
        _("المرفقات"),
        upload_to='receipts/%Y/%m/',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-receipt_date', '-id']
        verbose_name = _("سند استلام")
        verbose_name_plural = _("سندات الاستلام")
        indexes = [
            models.Index(fields=['purchase_order', 'status']),
            models.Index(fields=['receipt_date']),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.purchase_order.number}"
    
    @property
    def has_variance(self):
        """هل يوجد اختلاف في الكميات؟"""
        return any(item.variance_quantity != 0 for item in self.items.all())
    
    @property
    def has_quality_issues(self):
        """هل يوجد مشاكل في الجودة؟"""
        return self.quality_status in ['failed', 'partial']
    
    def save(self, *args, **kwargs):
        if not self.number:
            seq = next_sequence('GOODS_RECEIPT')
            self.number = format_code('GR', seq)
        super().save(*args, **kwargs)


class GoodsReceiptItem(models.Model):
    """بنود سند الاستلام"""
    
    QUALITY_CHOICES = [
        ("excellent", _("ممتاز")),
        ("good", _("جيد")),
        ("acceptable", _("مقبول")),
        ("poor", _("ضعيف")),
        ("rejected", _("مرفوض")),
    ]
    
    id = models.AutoField(primary_key=True)
    receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('سند الاستلام')
    )
    purchase_order_item = models.ForeignKey(
        'PurchaseOrderItem',
        on_delete=models.PROTECT,
        verbose_name=_('بند أمر الشراء')
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name=_('المنتج'))
    
    # الكميات
    ordered_quantity = models.DecimalField(_("الكمية المطلوبة"), max_digits=12, decimal_places=2)
    received_quantity = models.DecimalField(_("الكمية المستلمة"), max_digits=12, decimal_places=2)
    accepted_quantity = models.DecimalField(
        _("الكمية المقبولة"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    rejected_quantity = models.DecimalField(
        _("الكمية المرفوضة"),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    
    # الجودة
    quality_grade = models.CharField(
        _("تقييم الجودة"),
        max_length=20,
        choices=QUALITY_CHOICES,
        default="good"
    )
    quality_notes = models.TextField(_("ملاحظات الجودة"), blank=True)
    
    # أسباب الاختلاف/الرفض
    variance_reason = models.TextField(_("سبب الاختلاف"), blank=True)
    rejection_reason = models.TextField(_("سبب الرفض"), blank=True)
    
    notes = models.TextField(_("ملاحظات"), blank=True)
    
    class Meta:
        verbose_name = _("بند سند استلام")
        verbose_name_plural = _("بنود سندات الاستلام")
    
    @property
    def variance_quantity(self):
        """فرق الكمية (المستلمة - المطلوبة)"""
        return self.received_quantity - self.ordered_quantity
    
    @property
    def variance_percentage(self):
        """نسبة الاختلاف"""
        if self.ordered_quantity == 0:
            return 0
        return (self.variance_quantity / self.ordered_quantity) * 100
    
    def __str__(self):
        return f"{self.receipt.number} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        # التحقق من أن المجموع صحيح
        if self.received_quantity != (self.accepted_quantity + self.rejected_quantity):
            # تعديل تلقائي: إذا لم يتم تحديد المقبول والمرفوض
            if self.accepted_quantity == 0 and self.rejected_quantity == 0:
                self.accepted_quantity = self.received_quantity
        super().save(*args, **kwargs)


# ===========================
# ربط الفواتير تلقائياً
# ===========================

@receiver(post_save, sender='purchases.PurchaseBill')
def auto_link_purchase_bill_to_order(sender, instance, created, **kwargs):
    """ربط فاتورة الشراء تلقائياً بأمر الشراء إذا كان مرتبطاً"""
    if created and hasattr(instance, 'source_order') and instance.source_order:
        # تسجيل السعر في السجل التاريخي
        for item in instance.items.all():
            ProductPriceHistory.objects.create(
                product=item.product,
                supplier=instance.supplier,
                price=item.cost,
                quantity=item.quantity,
                date=instance.date,
                source='purchase_bill',
                purchase_bill=instance
            )


@receiver(post_save, sender=SupplierQuotation)
def save_quotation_prices_to_history(sender, instance, created, **kwargs):
    """حفظ أسعار العروض في السجل التاريخي"""
    if instance.status == 'accepted':
        for item in instance.items.all():
            ProductPriceHistory.objects.create(
                product=item.product,
                supplier=instance.supplier,
                price=item.unit_price,
                quantity=item.quantity,
                date=instance.quotation_date,
                source='quotation',
                quotation=instance
            )
