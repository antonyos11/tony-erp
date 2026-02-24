"""
نماذج نظام إدارة الشحن - Tony ERP
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class ShippingCompany(models.Model):
    """شركات الشحن"""
    name = models.CharField(_('اسم الشركة'), max_length=200)
    code = models.CharField(_('كود الشركة'), max_length=50, unique=True)
    contact_person = models.CharField(_('مسؤول التواصل'), max_length=100, blank=True)
    phone = models.CharField(_('رقم الهاتف'), max_length=20, blank=True)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    website = models.URLField(_('الموقع الإلكتروني'), blank=True)
    api_key = models.CharField(_('مفتاح API'), max_length=255, blank=True)
    api_secret = models.CharField(_('سر API'), max_length=255, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('شركة شحن')
        verbose_name_plural = _('شركات الشحن')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class ShippingZone(models.Model):
    """مناطق الشحن"""
    name = models.CharField(_('اسم المنطقة'), max_length=100)
    code = models.CharField(_('كود المنطقة'), max_length=20, unique=True)
    country = models.CharField(_('الدولة'), max_length=100)
    cities = models.TextField(_('المدن'), help_text=_('أدخل المدن مفصولة بفاصلة'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('منطقة شحن')
        verbose_name_plural = _('مناطق الشحن')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.country}"


class ShippingRate(models.Model):
    """تعريفات أسعار الشحن"""
    company = models.ForeignKey(ShippingCompany, on_delete=models.CASCADE, 
                                 related_name='rates', verbose_name=_('شركة الشحن'))
    zone = models.ForeignKey(ShippingZone, on_delete=models.CASCADE,
                              related_name='rates', verbose_name=_('المنطقة'))
    weight_from = models.DecimalField(_('الوزن من (كجم)'), max_digits=10, decimal_places=2, default=Decimal('0'))
    weight_to = models.DecimalField(_('الوزن إلى (كجم)'), max_digits=10, decimal_places=2)
    base_rate = models.DecimalField(_('السعر الأساسي'), max_digits=10, decimal_places=2)
    extra_kg_rate = models.DecimalField(_('سعر الكيلو الإضافي'), max_digits=10, decimal_places=2, default=Decimal('0'))
    delivery_days = models.PositiveIntegerField(_('أيام التوصيل'), default=3)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('تعريفة شحن')
        verbose_name_plural = _('تعريفات الشحن')
        ordering = ['company', 'zone', 'weight_from']

    def __str__(self):
        return f"{self.company.name} - {self.zone.name}: {self.base_rate}"


class Shipment(models.Model):
    """الشحنات"""
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('picked_up', _('تم الاستلام')),
        ('in_transit', _('في الطريق')),
        ('out_for_delivery', _('خارج للتوصيل')),
        ('delivered', _('تم التوصيل')),
        ('returned', _('مرتجع')),
        ('cancelled', _('ملغي')),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('prepaid', _('مدفوع مسبقاً')),
        ('cod', _('الدفع عند الاستلام')),
        ('account', _('على الحساب')),
    ]

    tracking_number = models.CharField(_('رقم التتبع'), max_length=50, unique=True)
    company = models.ForeignKey(ShippingCompany, on_delete=models.PROTECT,
                                 related_name='shipments', verbose_name=_('شركة الشحن'))
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # معلومات المرسل
    sender_name = models.CharField(_('اسم المرسل'), max_length=200)
    sender_phone = models.CharField(_('هاتف المرسل'), max_length=20)
    sender_address = models.TextField(_('عنوان المرسل'))
    sender_city = models.CharField(_('مدينة المرسل'), max_length=100)
    
    # معلومات المستلم
    receiver_name = models.CharField(_('اسم المستلم'), max_length=200)
    receiver_phone = models.CharField(_('هاتف المستلم'), max_length=20)
    receiver_address = models.TextField(_('عنوان المستلم'))
    receiver_city = models.CharField(_('مدينة المستلم'), max_length=100)
    zone = models.ForeignKey(ShippingZone, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='shipments', verbose_name=_('منطقة الشحن'))
    
    # تفاصيل الشحنة
    description = models.TextField(_('وصف المحتويات'))
    weight = models.DecimalField(_('الوزن (كجم)'), max_digits=10, decimal_places=2)
    pieces = models.PositiveIntegerField(_('عدد القطع'), default=1)
    dimensions = models.CharField(_('الأبعاد'), max_length=50, blank=True, 
                                   help_text=_('الطول × العرض × الارتفاع'))
    
    # المالية
    payment_type = models.CharField(_('نوع الدفع'), max_length=20, 
                                     choices=PAYMENT_TYPE_CHOICES, default='prepaid')
    shipping_cost = models.DecimalField(_('تكلفة الشحن'), max_digits=10, decimal_places=2)
    cod_amount = models.DecimalField(_('مبلغ COD'), max_digits=10, decimal_places=2, default=Decimal('0'))
    insurance_amount = models.DecimalField(_('مبلغ التأمين'), max_digits=10, decimal_places=2, default=Decimal('0'))
    
    # التتبع
    pickup_date = models.DateTimeField(_('تاريخ الاستلام'), null=True, blank=True)
    expected_delivery = models.DateField(_('التوصيل المتوقع'), null=True, blank=True)
    actual_delivery = models.DateTimeField(_('التوصيل الفعلي'), null=True, blank=True)
    
    # مرجعية
    reference_number = models.CharField(_('رقم المرجع'), max_length=50, blank=True)
    order_id = models.CharField(_('رقم الطلب'), max_length=50, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='created_shipments', verbose_name=_('أنشأ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('شحنة')
        verbose_name_plural = _('الشحنات')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tracking_number} - {self.receiver_name}"

    @property
    def total_cost(self):
        """إجمالي التكلفة"""
        return self.shipping_cost + self.insurance_amount


class ShipmentTracking(models.Model):
    """تتبع الشحنات"""
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE,
                                  related_name='tracking_history', verbose_name=_('الشحنة'))
    status = models.CharField(_('الحالة'), max_length=20, choices=Shipment.STATUS_CHOICES)
    location = models.CharField(_('الموقع'), max_length=200, blank=True)
    description = models.TextField(_('الوصف'))
    timestamp = models.DateTimeField(_('الوقت'), auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    verbose_name=_('تم بواسطة'))

    class Meta:
        verbose_name = _('تتبع شحنة')
        verbose_name_plural = _('تتبع الشحنات')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.shipment.tracking_number} - {self.status}"


class ShippingPickup(models.Model):
    """طلبات الاستلام"""
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('confirmed', _('مؤكد')),
        ('picked_up', _('تم الاستلام')),
        ('cancelled', _('ملغي')),
    ]

    company = models.ForeignKey(ShippingCompany, on_delete=models.PROTECT,
                                 related_name='pickups', verbose_name=_('شركة الشحن'))
    pickup_number = models.CharField(_('رقم الاستلام'), max_length=50, unique=True)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    pickup_address = models.TextField(_('عنوان الاستلام'))
    pickup_city = models.CharField(_('المدينة'), max_length=100)
    contact_name = models.CharField(_('اسم المسؤول'), max_length=100)
    contact_phone = models.CharField(_('هاتف المسؤول'), max_length=20)
    
    scheduled_date = models.DateField(_('تاريخ الاستلام المحدد'))
    scheduled_time_from = models.TimeField(_('من الساعة'))
    scheduled_time_to = models.TimeField(_('إلى الساعة'))
    
    pieces_count = models.PositiveIntegerField(_('عدد القطع المتوقع'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    verbose_name=_('أنشأ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('طلب استلام')
        verbose_name_plural = _('طلبات الاستلام')
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.pickup_number} - {self.scheduled_date}"


class ShippingInvoice(models.Model):
    """فواتير الشحن"""
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('sent', _('مرسلة')),
        ('paid', _('مدفوعة')),
        ('cancelled', _('ملغاة')),
    ]

    invoice_number = models.CharField(_('رقم الفاتورة'), max_length=50, unique=True)
    company = models.ForeignKey(ShippingCompany, on_delete=models.PROTECT,
                                 related_name='invoices', verbose_name=_('شركة الشحن'))
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    invoice_date = models.DateField(_('تاريخ الفاتورة'))
    due_date = models.DateField(_('تاريخ الاستحقاق'))
    
    subtotal = models.DecimalField(_('الإجمالي الفرعي'), max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(_('الضريبة'), max_digits=12, decimal_places=2, default=Decimal('0'))
    discount = models.DecimalField(_('الخصم'), max_digits=12, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField(_('الإجمالي'), max_digits=12, decimal_places=2)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('فاتورة شحن')
        verbose_name_plural = _('فواتير الشحن')
        ordering = ['-invoice_date']

    def __str__(self):
        return f"{self.invoice_number} - {self.total}"


class ShippingInvoiceItem(models.Model):
    """بنود فواتير الشحن"""
    invoice = models.ForeignKey(ShippingInvoice, on_delete=models.CASCADE,
                                 related_name='items', verbose_name=_('الفاتورة'))
    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT,
                                  related_name='invoice_items', verbose_name=_('الشحنة'))
    description = models.CharField(_('الوصف'), max_length=255)
    amount = models.DecimalField(_('المبلغ'), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _('بند فاتورة')
        verbose_name_plural = _('بنود الفواتير')

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.shipment.tracking_number}"
