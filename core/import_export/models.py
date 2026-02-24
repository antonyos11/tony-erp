# -*- coding: utf-8 -*-
"""
نماذج موديول الاستيراد والتصدير
Import/Export Models
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class ShippingAgent(models.Model):
    """وكيل الشحن"""
    
    class AgentType(models.TextChoices):
        SHIPPING = 'shipping', _('شحن بحري')
        AIR = 'air', _('شحن جوي')
        LAND = 'land', _('شحن بري')
        CUSTOMS = 'customs', _('تخليص جمركي')
        FORWARDING = 'forwarding', _('توكيل ملاحي')
        MULTI = 'multi', _('متعدد الخدمات')
    
    code = models.CharField(_('كود الوكيل'), max_length=20, unique=True)
    name = models.CharField(_('اسم الوكيل'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    agent_type = models.CharField(_('نوع الوكيل'), max_length=20, choices=AgentType.choices, default=AgentType.MULTI)
    
    # بيانات الاتصال
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    mobile = models.CharField(_('الجوال'), max_length=50, blank=True)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    fax = models.CharField(_('الفاكس'), max_length=50, blank=True)
    website = models.URLField(_('الموقع الإلكتروني'), blank=True)
    
    # العنوان
    address = models.TextField(_('العنوان'), blank=True)
    city = models.CharField(_('المدينة'), max_length=100, blank=True)
    country = models.ForeignKey(
        'core.Country',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('الدولة')
    )
    
    # معلومات التسجيل
    license_number = models.CharField(_('رقم الترخيص'), max_length=100, blank=True)
    license_expiry = models.DateField(_('تاريخ انتهاء الترخيص'), null=True, blank=True)
    tax_number = models.CharField(_('الرقم الضريبي'), max_length=100, blank=True)
    commercial_reg = models.CharField(_('السجل التجاري'), max_length=100, blank=True)
    
    # جهة الاتصال
    contact_person = models.CharField(_('جهة الاتصال'), max_length=200, blank=True)
    contact_phone = models.CharField(_('هاتف جهة الاتصال'), max_length=50, blank=True)
    contact_email = models.EmailField(_('بريد جهة الاتصال'), blank=True)
    
    # معلومات مالية
    credit_limit = models.DecimalField(_('حد الائتمان'), max_digits=15, decimal_places=2, default=Decimal('0'))
    payment_terms = models.CharField(_('شروط الدفع'), max_length=100, blank=True)
    currency = models.ForeignKey(
        'core.Currency',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('العملة الافتراضية')
    )
    
    # الحساب المحاسبي
    account = models.ForeignKey(
        'accounting.Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('الحساب المحاسبي')
    )
    
    # الحالة
    is_active = models.BooleanField(_('نشط'), default=True)
    is_preferred = models.BooleanField(_('مفضل'), default=False)
    rating = models.IntegerField(_('التقييم'), default=0, choices=[(i, str(i)) for i in range(1, 6)])
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_shipping_agents',
        verbose_name=_('أنشئ بواسطة')
    )
    
    class Meta:
        verbose_name = _('وكيل شحن')
        verbose_name_plural = _('وكلاء الشحن')
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['agent_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            from core.sequence_utils import next_sequence, format_code
            seq = next_sequence('SHIP_AGENT')
            self.code = format_code('SA', seq)
        super().save(*args, **kwargs)


class ExportOrder(models.Model):
    """طلب تصدير خارجي"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('مسودة')
        PENDING = 'pending', _('في انتظار الموافقة')
        APPROVED = 'approved', _('موافق عليه')
        PROCESSING = 'processing', _('قيد التنفيذ')
        SHIPPED = 'shipped', _('تم الشحن')
        DELIVERED = 'delivered', _('تم التسليم')
        CANCELLED = 'cancelled', _('ملغى')
    
    class ShipmentType(models.TextChoices):
        SEA = 'sea', _('بحري')
        AIR = 'air', _('جوي')
        LAND = 'land', _('بري')
        MULTI = 'multi', _('متعدد')
    
    number = models.CharField(_('رقم الطلب'), max_length=50, unique=True, editable=False)
    reference = models.CharField(_('المرجع'), max_length=100, blank=True)
    
    # العميل
    customer = models.ForeignKey(
        'partners.Customer',
        on_delete=models.PROTECT,
        verbose_name=_('العميل')
    )
    
    # الوجهة
    destination_country = models.ForeignKey(
        'core.Country',
        on_delete=models.SET_NULL,
        null=True,
        related_name='export_orders',
        verbose_name=_('دولة الوجهة')
    )
    destination_port = models.CharField(_('ميناء الوصول'), max_length=200, blank=True)
    origin_port = models.CharField(_('ميناء الشحن'), max_length=200, blank=True)
    
    # التواريخ
    order_date = models.DateField(_('تاريخ الطلب'), default=timezone.localdate)
    expected_ship_date = models.DateField(_('تاريخ الشحن المتوقع'), null=True, blank=True)
    actual_ship_date = models.DateField(_('تاريخ الشحن الفعلي'), null=True, blank=True)
    expected_arrival_date = models.DateField(_('تاريخ الوصول المتوقع'), null=True, blank=True)
    
    # معلومات الشحن
    shipment_type = models.CharField(_('نوع الشحن'), max_length=20, choices=ShipmentType.choices, default=ShipmentType.SEA)
    shipping_agent = models.ForeignKey(
        ShippingAgent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('وكيل الشحن')
    )
    container_type = models.CharField(_('نوع الحاوية'), max_length=100, blank=True)
    container_count = models.IntegerField(_('عدد الحاويات'), default=1)
    
    # شروط التسليم
    incoterm = models.CharField(_('شروط التسليم'), max_length=20, blank=True)  # FOB, CIF, EXW, etc
    
    # المبالغ
    subtotal = models.DecimalField(_('المجموع الفرعي'), max_digits=15, decimal_places=2, default=Decimal('0'))
    shipping_cost = models.DecimalField(_('تكلفة الشحن'), max_digits=15, decimal_places=2, default=Decimal('0'))
    insurance_cost = models.DecimalField(_('تكلفة التأمين'), max_digits=15, decimal_places=2, default=Decimal('0'))
    customs_cost = models.DecimalField(_('الرسوم الجمركية'), max_digits=15, decimal_places=2, default=Decimal('0'))
    other_costs = models.DecimalField(_('تكاليف أخرى'), max_digits=15, decimal_places=2, default=Decimal('0'))
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=2, default=Decimal('0'))
    
    currency = models.ForeignKey(
        'core.Currency',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('العملة')
    )
    exchange_rate = models.DecimalField(_('سعر الصرف'), max_digits=12, decimal_places=6, default=Decimal('1'))
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # المرفقات والملاحظات
    notes = models.TextField(_('ملاحظات'), blank=True)
    special_instructions = models.TextField(_('تعليمات خاصة'), blank=True)
    
    # التتبع
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_export_orders',
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('طلب تصدير')
        verbose_name_plural = _('طلبات التصدير')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['order_date']),
            models.Index(fields=['customer']),
        ]
        permissions = [
            ('can_approve_export', _('يمكنه الموافقة على طلبات التصدير')),
            ('can_ship_export', _('يمكنه تأكيد الشحن')),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.customer}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence, format_code
            seq = next_sequence('EXP_ORDER')
            self.number = format_code('EXP', seq)
        
        # حساب المجموع
        self.total_amount = (
            self.subtotal + self.shipping_cost + self.insurance_cost + 
            self.customs_cost + self.other_costs
        )
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """حساب المجاميع من البنود"""
        self.subtotal = sum(item.total_amount for item in self.items.all())
        self.save(update_fields=['subtotal', 'total_amount'])


class ExportOrderItem(models.Model):
    """بند طلب تصدير"""
    
    order = models.ForeignKey(
        ExportOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('طلب التصدير')
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        verbose_name=_('المنتج')
    )
    description = models.CharField(_('الوصف'), max_length=500, blank=True)
    
    quantity = models.DecimalField(_('الكمية'), max_digits=12, decimal_places=3)
    unit = models.CharField(_('الوحدة'), max_length=50, default='قطعة')
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=15, decimal_places=2)
    
    # معلومات جمركية
    hs_code = models.CharField(_('كود النظام المنسق'), max_length=20, blank=True)  # Harmonized System Code
    country_of_origin = models.ForeignKey(
        'core.Country',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('بلد المنشأ')
    )
    
    # الأوزان
    gross_weight = models.DecimalField(_('الوزن الإجمالي'), max_digits=12, decimal_places=3, default=Decimal('0'))
    net_weight = models.DecimalField(_('الوزن الصافي'), max_digits=12, decimal_places=3, default=Decimal('0'))
    
    # التغليف
    packages_count = models.IntegerField(_('عدد الطرود'), default=1)
    package_type = models.CharField(_('نوع التغليف'), max_length=100, blank=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    class Meta:
        verbose_name = _('بند تصدير')
        verbose_name_plural = _('بنود التصدير')
    
    def __str__(self):
        return f"{self.product} - {self.quantity}"
    
    @property
    def total_amount(self):
        return self.quantity * self.unit_price


class ExportCertificate(models.Model):
    """شهادة التصدير"""
    
    class CertificateType(models.TextChoices):
        ORIGIN = 'origin', _('شهادة منشأ')
        HEALTH = 'health', _('شهادة صحية')
        QUALITY = 'quality', _('شهادة جودة')
        PHYTO = 'phyto', _('شهادة صحة نباتية')
        HALAL = 'halal', _('شهادة حلال')
        EXPORT = 'export', _('رخصة تصدير')
        OTHER = 'other', _('أخرى')
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('مسودة')
        REQUESTED = 'requested', _('مطلوبة')
        PROCESSING = 'processing', _('قيد الإصدار')
        ISSUED = 'issued', _('صادرة')
        REJECTED = 'rejected', _('مرفوضة')
        EXPIRED = 'expired', _('منتهية')
    
    number = models.CharField(_('رقم الشهادة'), max_length=100, unique=True)
    certificate_type = models.CharField(_('نوع الشهادة'), max_length=20, choices=CertificateType.choices)
    
    export_order = models.ForeignKey(
        ExportOrder,
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name=_('طلب التصدير')
    )
    
    # الجهة المصدرة
    issuing_authority = models.CharField(_('الجهة المصدرة'), max_length=200)
    issue_date = models.DateField(_('تاريخ الإصدار'), null=True, blank=True)
    expiry_date = models.DateField(_('تاريخ الانتهاء'), null=True, blank=True)
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # التكلفة
    cost = models.DecimalField(_('التكلفة'), max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # المرفقات
    document = models.FileField(_('الشهادة'), upload_to='export_certificates/', null=True, blank=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('شهادة تصدير')
        verbose_name_plural = _('شهادات التصدير')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_certificate_type_display()} - {self.number}"


class FinancialApproval(models.Model):
    """الموافقة المالية على التصدير"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('في الانتظار')
        APPROVED = 'approved', _('موافق عليه')
        REJECTED = 'rejected', _('مرفوض')
        CONDITIONAL = 'conditional', _('موافقة مشروطة')
    
    number = models.CharField(_('رقم الموافقة'), max_length=50, unique=True, editable=False)
    
    export_order = models.ForeignKey(
        ExportOrder,
        on_delete=models.CASCADE,
        related_name='financial_approvals',
        verbose_name=_('طلب التصدير')
    )
    
    # المبالغ
    requested_amount = models.DecimalField(_('المبلغ المطلوب'), max_digits=15, decimal_places=2)
    approved_amount = models.DecimalField(_('المبلغ الموافق عليه'), max_digits=15, decimal_places=2, default=Decimal('0'))
    
    currency = models.ForeignKey(
        'core.Currency',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('العملة')
    )
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # المعتمدون
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='requested_financial_approvals',
        verbose_name=_('مقدم الطلب')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_financial_approvals',
        verbose_name=_('المعتمد')
    )
    
    # التواريخ
    request_date = models.DateField(_('تاريخ الطلب'), default=timezone.localdate)
    approval_date = models.DateField(_('تاريخ الموافقة'), null=True, blank=True)
    
    # التفاصيل
    justification = models.TextField(_('المبررات'), blank=True)
    conditions = models.TextField(_('الشروط'), blank=True)
    rejection_reason = models.TextField(_('سبب الرفض'), blank=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('موافقة مالية')
        verbose_name_plural = _('الموافقات المالية')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.number} - {self.export_order.number}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence, format_code
            seq = next_sequence('FIN_APPR')
            self.number = format_code('FA', seq)
        super().save(*args, **kwargs)


class PreExportInvoice(models.Model):
    """الفاتورة المبدئية قبل التصدير (Proforma Invoice)"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('مسودة')
        SENT = 'sent', _('مرسلة')
        ACCEPTED = 'accepted', _('مقبولة')
        REJECTED = 'rejected', _('مرفوضة')
        CONVERTED = 'converted', _('تم تحويلها لفاتورة')
    
    number = models.CharField(_('رقم الفاتورة المبدئية'), max_length=50, unique=True, editable=False)
    
    export_order = models.ForeignKey(
        ExportOrder,
        on_delete=models.CASCADE,
        related_name='proforma_invoices',
        verbose_name=_('طلب التصدير')
    )
    
    # التواريخ
    invoice_date = models.DateField(_('تاريخ الفاتورة'), default=timezone.localdate)
    validity_date = models.DateField(_('صالحة حتى'), null=True, blank=True)
    
    # المبالغ
    subtotal = models.DecimalField(_('المجموع الفرعي'), max_digits=15, decimal_places=2, default=Decimal('0'))
    discount = models.DecimalField(_('الخصم'), max_digits=15, decimal_places=2, default=Decimal('0'))
    tax_amount = models.DecimalField(_('الضريبة'), max_digits=15, decimal_places=2, default=Decimal('0'))
    shipping_cost = models.DecimalField(_('تكلفة الشحن'), max_digits=15, decimal_places=2, default=Decimal('0'))
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=2, default=Decimal('0'))
    
    currency = models.ForeignKey(
        'core.Currency',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('العملة')
    )
    
    # شروط الدفع
    payment_terms = models.TextField(_('شروط الدفع'), blank=True)
    bank_details = models.TextField(_('تفاصيل البنك'), blank=True)
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('فاتورة مبدئية')
        verbose_name_plural = _('الفواتير المبدئية')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.number}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence, format_code
            seq = next_sequence('PROFORMA')
            self.number = format_code('PI', seq)
        
        # حساب المجموع
        self.total_amount = self.subtotal - self.discount + self.tax_amount + self.shipping_cost
        super().save(*args, **kwargs)


# ============= موديلات الاستيراد =============

class CustomsClearance(models.Model):
    """المخلص الجمركي"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('نشط')
        SUSPENDED = 'suspended', _('موقوف')
        INACTIVE = 'inactive', _('غير نشط')
    
    code = models.CharField(_('كود المخلص'), max_length=20, unique=True)
    name = models.CharField(_('اسم المخلص'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    
    # بيانات الاتصال
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    mobile = models.CharField(_('الجوال'), max_length=50, blank=True)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    
    # العنوان
    address = models.TextField(_('العنوان'), blank=True)
    
    # معلومات التسجيل
    license_number = models.CharField(_('رقم رخصة التخليص'), max_length=100)
    license_expiry = models.DateField(_('تاريخ انتهاء الرخصة'), null=True, blank=True)
    
    # الحساب المحاسبي
    account = models.ForeignKey(
        'accounting.Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('الحساب المحاسبي')
    )
    
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('مخلص جمركي')
        verbose_name_plural = _('المخلصون الجمركيون')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            from core.sequence_utils import next_sequence, format_code
            seq = next_sequence('CUSTOMS_CL')
            self.code = format_code('CC', seq)
        super().save(*args, **kwargs)


class ImportOrder(models.Model):
    """أمر استيراد"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('مسودة')
        PENDING = 'pending', _('في الانتظار')
        APPROVED = 'approved', _('موافق عليه')
        SHIPPED = 'shipped', _('في الطريق')
        ARRIVED = 'arrived', _('وصل الميناء')
        CLEARING = 'clearing', _('قيد التخليص')
        CLEARED = 'cleared', _('تم التخليص')
        DELIVERED = 'delivered', _('تم التسليم')
        CANCELLED = 'cancelled', _('ملغى')
    
    class ShipmentType(models.TextChoices):
        SEA = 'sea', _('بحري')
        AIR = 'air', _('جوي')
        LAND = 'land', _('بري')
        MULTI = 'multi', _('متعدد')
    
    number = models.CharField(_('رقم أمر الاستيراد'), max_length=50, unique=True, editable=False)
    reference = models.CharField(_('المرجع'), max_length=100, blank=True)
    
    # المورد
    supplier = models.ForeignKey(
        'partners.Supplier',
        on_delete=models.PROTECT,
        verbose_name=_('المورد')
    )
    
    # بلد المنشأ والوجهة
    origin_country = models.ForeignKey(
        'core.Country',
        on_delete=models.SET_NULL,
        null=True,
        related_name='import_orders_origin',
        verbose_name=_('بلد المنشأ')
    )
    origin_port = models.CharField(_('ميناء الشحن'), max_length=200, blank=True)
    destination_port = models.CharField(_('ميناء الوصول'), max_length=200, blank=True)
    
    # التواريخ
    order_date = models.DateField(_('تاريخ الأمر'), default=timezone.localdate)
    expected_ship_date = models.DateField(_('تاريخ الشحن المتوقع'), null=True, blank=True)
    actual_ship_date = models.DateField(_('تاريخ الشحن الفعلي'), null=True, blank=True)
    expected_arrival_date = models.DateField(_('تاريخ الوصول المتوقع'), null=True, blank=True)
    actual_arrival_date = models.DateField(_('تاريخ الوصول الفعلي'), null=True, blank=True)
    
    # معلومات الشحن
    shipment_type = models.CharField(_('نوع الشحن'), max_length=20, choices=ShipmentType.choices, default=ShipmentType.SEA)
    shipping_agent = models.ForeignKey(
        ShippingAgent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('وكيل الشحن')
    )
    customs_clearance = models.ForeignKey(
        CustomsClearance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('المخلص الجمركي')
    )
    
    # معلومات الشحنة
    bl_number = models.CharField(_('رقم بوليصة الشحن'), max_length=100, blank=True)  # Bill of Lading
    container_numbers = models.TextField(_('أرقام الحاويات'), blank=True)
    
    # شروط التسليم
    incoterm = models.CharField(_('شروط التسليم'), max_length=20, blank=True)
    
    # المبالغ
    subtotal = models.DecimalField(_('قيمة البضاعة'), max_digits=15, decimal_places=2, default=Decimal('0'))
    shipping_cost = models.DecimalField(_('تكلفة الشحن'), max_digits=15, decimal_places=2, default=Decimal('0'))
    insurance_cost = models.DecimalField(_('تكلفة التأمين'), max_digits=15, decimal_places=2, default=Decimal('0'))
    customs_duties = models.DecimalField(_('الرسوم الجمركية'), max_digits=15, decimal_places=2, default=Decimal('0'))
    customs_vat = models.DecimalField(_('ضريبة القيمة المضافة الجمركية'), max_digits=15, decimal_places=2, default=Decimal('0'))
    clearance_fees = models.DecimalField(_('رسوم التخليص'), max_digits=15, decimal_places=2, default=Decimal('0'))
    other_costs = models.DecimalField(_('تكاليف أخرى'), max_digits=15, decimal_places=2, default=Decimal('0'))
    total_cost = models.DecimalField(_('التكلفة الإجمالية'), max_digits=15, decimal_places=2, default=Decimal('0'))
    
    currency = models.ForeignKey(
        'core.Currency',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('العملة')
    )
    exchange_rate = models.DecimalField(_('سعر الصرف'), max_digits=12, decimal_places=6, default=Decimal('1'))
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_import_orders',
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('أمر استيراد')
        verbose_name_plural = _('أوامر الاستيراد')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['order_date']),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.supplier}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence, format_code
            seq = next_sequence('IMP_ORDER')
            self.number = format_code('IMP', seq)
        
        # حساب المجموع
        self.total_cost = (
            self.subtotal + self.shipping_cost + self.insurance_cost + 
            self.customs_duties + self.customs_vat + self.clearance_fees + self.other_costs
        )
        super().save(*args, **kwargs)


class ImportOrderItem(models.Model):
    """بند أمر استيراد"""
    
    order = models.ForeignKey(
        ImportOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('أمر الاستيراد')
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        verbose_name=_('المنتج')
    )
    description = models.CharField(_('الوصف'), max_length=500, blank=True)
    
    quantity = models.DecimalField(_('الكمية'), max_digits=12, decimal_places=3)
    unit = models.CharField(_('الوحدة'), max_length=50, default='قطعة')
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=15, decimal_places=2)
    
    # معلومات جمركية
    hs_code = models.CharField(_('كود النظام المنسق'), max_length=20, blank=True)
    customs_rate = models.DecimalField(_('نسبة الجمرك'), max_digits=5, decimal_places=2, default=Decimal('0'))
    
    # الأوزان
    gross_weight = models.DecimalField(_('الوزن الإجمالي'), max_digits=12, decimal_places=3, default=Decimal('0'))
    net_weight = models.DecimalField(_('الوزن الصافي'), max_digits=12, decimal_places=3, default=Decimal('0'))
    
    # الكميات المستلمة
    quantity_received = models.DecimalField(_('الكمية المستلمة'), max_digits=12, decimal_places=3, default=Decimal('0'))
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    class Meta:
        verbose_name = _('بند استيراد')
        verbose_name_plural = _('بنود الاستيراد')
    
    def __str__(self):
        return f"{self.product} - {self.quantity}"
    
    @property
    def total_amount(self):
        return self.quantity * self.unit_price


class ImportCertificate(models.Model):
    """شهادة استيراد"""
    
    class CertificateType(models.TextChoices):
        ORIGIN = 'origin', _('شهادة منشأ')
        CONFORMITY = 'conformity', _('شهادة مطابقة')
        HEALTH = 'health', _('شهادة صحية')
        QUALITY = 'quality', _('شهادة جودة')
        INSPECTION = 'inspection', _('شهادة فحص')
        OTHER = 'other', _('أخرى')
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('في الانتظار')
        RECEIVED = 'received', _('مستلمة')
        VERIFIED = 'verified', _('تم التحقق')
        REJECTED = 'rejected', _('مرفوضة')
    
    number = models.CharField(_('رقم الشهادة'), max_length=100)
    certificate_type = models.CharField(_('نوع الشهادة'), max_length=20, choices=CertificateType.choices)
    
    import_order = models.ForeignKey(
        ImportOrder,
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name=_('أمر الاستيراد')
    )
    
    issuing_authority = models.CharField(_('الجهة المصدرة'), max_length=200)
    issue_date = models.DateField(_('تاريخ الإصدار'), null=True, blank=True)
    expiry_date = models.DateField(_('تاريخ الانتهاء'), null=True, blank=True)
    
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.PENDING)
    
    document = models.FileField(_('الشهادة'), upload_to='import_certificates/', null=True, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('شهادة استيراد')
        verbose_name_plural = _('شهادات الاستيراد')
    
    def __str__(self):
        return f"{self.get_certificate_type_display()} - {self.number}"


class ReleaseOrder(models.Model):
    """إذن إفراج جمركي"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('في الانتظار')
        PROCESSING = 'processing', _('قيد المعالجة')
        APPROVED = 'approved', _('موافق عليه')
        RELEASED = 'released', _('تم الإفراج')
        REJECTED = 'rejected', _('مرفوض')
    
    number = models.CharField(_('رقم إذن الإفراج'), max_length=50, unique=True, editable=False)
    
    import_order = models.ForeignKey(
        ImportOrder,
        on_delete=models.CASCADE,
        related_name='release_orders',
        verbose_name=_('أمر الاستيراد')
    )
    
    # تفاصيل الجمرك
    customs_declaration_number = models.CharField(_('رقم البيان الجمركي'), max_length=100, blank=True)
    customs_office = models.CharField(_('المكتب الجمركي'), max_length=200, blank=True)
    
    # التواريخ
    request_date = models.DateField(_('تاريخ الطلب'), default=timezone.localdate)
    release_date = models.DateField(_('تاريخ الإفراج'), null=True, blank=True)
    
    # الرسوم
    duties_paid = models.DecimalField(_('الرسوم المدفوعة'), max_digits=15, decimal_places=2, default=Decimal('0'))
    vat_paid = models.DecimalField(_('الضريبة المدفوعة'), max_digits=15, decimal_places=2, default=Decimal('0'))
    other_fees = models.DecimalField(_('رسوم أخرى'), max_digits=15, decimal_places=2, default=Decimal('0'))
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.PENDING)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('إذن إفراج')
        verbose_name_plural = _('أذون الإفراج')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.number}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence, format_code
            seq = next_sequence('RELEASE')
            self.number = format_code('REL', seq)
        super().save(*args, **kwargs)


class ImportWaiver(models.Model):
    """التنازل عن الشحنة"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('مسودة')
        SUBMITTED = 'submitted', _('مقدم')
        APPROVED = 'approved', _('موافق عليه')
        REJECTED = 'rejected', _('مرفوض')
        COMPLETED = 'completed', _('مكتمل')
    
    class WaiverType(models.TextChoices):
        PARTIAL = 'partial', _('تنازل جزئي')
        FULL = 'full', _('تنازل كلي')
        TRANSFER = 'transfer', _('نقل ملكية')
    
    number = models.CharField(_('رقم التنازل'), max_length=50, unique=True, editable=False)
    
    import_order = models.ForeignKey(
        ImportOrder,
        on_delete=models.CASCADE,
        related_name='waivers',
        verbose_name=_('أمر الاستيراد')
    )
    
    waiver_type = models.CharField(_('نوع التنازل'), max_length=20, choices=WaiverType.choices)
    
    # المتنازل له
    waivee_name = models.CharField(_('اسم المتنازل له'), max_length=200)
    waivee_id = models.CharField(_('رقم هوية المتنازل له'), max_length=50, blank=True)
    waivee_phone = models.CharField(_('هاتف المتنازل له'), max_length=50, blank=True)
    
    # التفاصيل
    waiver_date = models.DateField(_('تاريخ التنازل'), default=timezone.localdate)
    reason = models.TextField(_('سبب التنازل'), blank=True)
    
    # المبلغ إن وجد
    waiver_amount = models.DecimalField(_('مبلغ التنازل'), max_digits=15, decimal_places=2, default=Decimal('0'))
    
    # الحالة
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('تنازل')
        verbose_name_plural = _('التنازلات')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.number}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from core.sequence_utils import next_sequence, format_code
            seq = next_sequence('WAIVER')
            self.number = format_code('WVR', seq)
        super().save(*args, **kwargs)
