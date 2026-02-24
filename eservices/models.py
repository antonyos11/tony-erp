"""
نماذج نظام الخدمات الإلكترونية - Tony ERP
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class ServiceCategory(models.Model):
    """فئات الخدمات"""
    name = models.CharField(_('اسم الفئة'), max_length=100)
    code = models.CharField(_('كود الفئة'), max_length=20, unique=True)
    icon = models.CharField(_('الأيقونة'), max_length=50, default='bi-gear')
    description = models.TextField(_('الوصف'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)

    class Meta:
        verbose_name = _('فئة خدمة')
        verbose_name_plural = _('فئات الخدمات')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class ServiceProvider(models.Model):
    """مزودي الخدمات"""
    name = models.CharField(_('اسم المزود'), max_length=200)
    code = models.CharField(_('كود المزود'), max_length=50, unique=True)
    logo = models.ImageField(_('الشعار'), upload_to='eservices/providers/', blank=True)
    description = models.TextField(_('الوصف'), blank=True)
    website = models.URLField(_('الموقع الإلكتروني'), blank=True)
    api_endpoint = models.URLField(_('نقطة API'), blank=True)
    api_key = models.CharField(_('مفتاح API'), max_length=255, blank=True)
    api_secret = models.CharField(_('سر API'), max_length=255, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    commission_rate = models.DecimalField(_('نسبة العمولة %'), max_digits=5, decimal_places=2, default=Decimal('0'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('مزود خدمة')
        verbose_name_plural = _('مزودي الخدمات')
        ordering = ['name']

    def __str__(self):
        return self.name


class EService(models.Model):
    """الخدمات الإلكترونية"""
    SERVICE_TYPES = [
        ('mobile_recharge', _('شحن رصيد')),
        ('bill_payment', _('دفع فواتير')),
        ('money_transfer', _('تحويل أموال')),
        ('government', _('خدمات حكومية')),
        ('subscription', _('اشتراكات')),
        ('booking', _('حجوزات')),
        ('other', _('أخرى')),
    ]

    name = models.CharField(_('اسم الخدمة'), max_length=200)
    code = models.CharField(_('كود الخدمة'), max_length=50, unique=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT,
                                  related_name='services', verbose_name=_('الفئة'))
    provider = models.ForeignKey(ServiceProvider, on_delete=models.PROTECT,
                                  related_name='services', verbose_name=_('المزود'))
    service_type = models.CharField(_('نوع الخدمة'), max_length=20, choices=SERVICE_TYPES)
    description = models.TextField(_('الوصف'))
    icon = models.CharField(_('الأيقونة'), max_length=50, default='bi-lightning')
    
    # التسعير
    base_fee = models.DecimalField(_('الرسوم الأساسية'), max_digits=10, decimal_places=2, default=Decimal('0'))
    percentage_fee = models.DecimalField(_('نسبة الرسوم %'), max_digits=5, decimal_places=2, default=Decimal('0'))
    min_amount = models.DecimalField(_('الحد الأدنى'), max_digits=10, decimal_places=2, default=Decimal('0'))
    max_amount = models.DecimalField(_('الحد الأقصى'), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # الإعدادات
    requires_account = models.BooleanField(_('يتطلب حساب'), default=False)
    requires_verification = models.BooleanField(_('يتطلب تحقق'), default=False)
    is_active = models.BooleanField(_('نشط'), default=True)
    is_featured = models.BooleanField(_('مميز'), default=False)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('خدمة إلكترونية')
        verbose_name_plural = _('الخدمات الإلكترونية')
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.provider.name})"

    def calculate_fee(self, amount):
        """حساب الرسوم"""
        fee = self.base_fee + (amount * self.percentage_fee / 100)
        return round(fee, 2)


class MobileOperator(models.Model):
    """مشغلي الاتصالات"""
    name = models.CharField(_('اسم المشغل'), max_length=100)
    code = models.CharField(_('الكود'), max_length=10, unique=True)
    logo = models.ImageField(_('الشعار'), upload_to='eservices/operators/', blank=True)
    prefixes = models.CharField(_('بادئات الأرقام'), max_length=100, 
                                 help_text=_('مفصولة بفاصلة مثل: 010,011,012'))
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('مشغل اتصالات')
        verbose_name_plural = _('مشغلي الاتصالات')

    def __str__(self):
        return self.name


class RechargePackage(models.Model):
    """باقات الشحن"""
    operator = models.ForeignKey(MobileOperator, on_delete=models.CASCADE,
                                  related_name='packages', verbose_name=_('المشغل'))
    name = models.CharField(_('اسم الباقة'), max_length=100)
    amount = models.DecimalField(_('المبلغ'), max_digits=10, decimal_places=2)
    bonus = models.CharField(_('المميزات'), max_length=200, blank=True)
    validity_days = models.PositiveIntegerField(_('صلاحية (أيام)'), default=30)
    is_active = models.BooleanField(_('نشط'), default=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)

    class Meta:
        verbose_name = _('باقة شحن')
        verbose_name_plural = _('باقات الشحن')
        ordering = ['operator', 'order', 'amount']

    def __str__(self):
        return f"{self.operator.name} - {self.name} ({self.amount})"


class BillType(models.Model):
    """أنواع الفواتير"""
    name = models.CharField(_('نوع الفاتورة'), max_length=100)
    code = models.CharField(_('الكود'), max_length=20, unique=True)
    icon = models.CharField(_('الأيقونة'), max_length=50, default='bi-receipt')
    provider = models.ForeignKey(ServiceProvider, on_delete=models.SET_NULL, 
                                  null=True, blank=True, verbose_name=_('المزود'))
    service_fee = models.DecimalField(_('رسوم الخدمة'), max_digits=10, decimal_places=2, default=Decimal('0'))
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('نوع فاتورة')
        verbose_name_plural = _('أنواع الفواتير')

    def __str__(self):
        return self.name


class ServiceTransaction(models.Model):
    """معاملات الخدمات"""
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('processing', _('قيد المعالجة')),
        ('completed', _('مكتملة')),
        ('failed', _('فشلت')),
        ('refunded', _('مستردة')),
        ('cancelled', _('ملغاة')),
    ]

    transaction_id = models.CharField(_('رقم المعاملة'), max_length=50, unique=True)
    service = models.ForeignKey(EService, on_delete=models.PROTECT,
                                 related_name='transactions', verbose_name=_('الخدمة'))
    user = models.ForeignKey(User, on_delete=models.PROTECT,
                              related_name='service_transactions', verbose_name=_('المستخدم'))
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # تفاصيل المعاملة
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    fee = models.DecimalField(_('الرسوم'), max_digits=10, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField(_('الإجمالي'), max_digits=12, decimal_places=2)
    
    # معلومات الخدمة
    service_number = models.CharField(_('رقم الخدمة'), max_length=50)  # رقم الجوال أو رقم الفاتورة
    service_data = models.JSONField(_('بيانات الخدمة'), default=dict, blank=True)
    
    # الاستجابة
    provider_reference = models.CharField(_('مرجع المزود'), max_length=100, blank=True)
    provider_response = models.JSONField(_('استجابة المزود'), default=dict, blank=True)
    error_message = models.TextField(_('رسالة الخطأ'), blank=True)
    
    # التوقيت
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    processed_at = models.DateTimeField(_('تاريخ المعالجة'), null=True, blank=True)
    completed_at = models.DateTimeField(_('تاريخ الإكمال'), null=True, blank=True)

    class Meta:
        verbose_name = _('معاملة خدمة')
        verbose_name_plural = _('معاملات الخدمات')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.service.name}"


class MobileRecharge(models.Model):
    """شحن الرصيد"""
    transaction = models.OneToOneField(ServiceTransaction, on_delete=models.CASCADE,
                                        related_name='recharge', verbose_name=_('المعاملة'))
    operator = models.ForeignKey(MobileOperator, on_delete=models.PROTECT,
                                  verbose_name=_('المشغل'))
    mobile_number = models.CharField(_('رقم الجوال'), max_length=20)
    package = models.ForeignKey(RechargePackage, on_delete=models.SET_NULL,
                                 null=True, blank=True, verbose_name=_('الباقة'))
    pin_code = models.CharField(_('كود الشحن'), max_length=50, blank=True)

    class Meta:
        verbose_name = _('شحن رصيد')
        verbose_name_plural = _('شحن الرصيد')

    def __str__(self):
        return f"{self.mobile_number} - {self.transaction.amount}"


class BillPayment(models.Model):
    """دفع الفواتير"""
    transaction = models.OneToOneField(ServiceTransaction, on_delete=models.CASCADE,
                                        related_name='bill_payment', verbose_name=_('المعاملة'))
    bill_type = models.ForeignKey(BillType, on_delete=models.PROTECT,
                                   verbose_name=_('نوع الفاتورة'))
    bill_number = models.CharField(_('رقم الفاتورة'), max_length=50)
    customer_name = models.CharField(_('اسم العميل'), max_length=200, blank=True)
    bill_amount = models.DecimalField(_('مبلغ الفاتورة'), max_digits=12, decimal_places=2)
    payment_reference = models.CharField(_('مرجع الدفع'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('دفع فاتورة')
        verbose_name_plural = _('دفع الفواتير')

    def __str__(self):
        return f"{self.bill_type.name} - {self.bill_number}"


class MoneyTransfer(models.Model):
    """تحويل الأموال"""
    TRANSFER_TYPES = [
        ('wallet', _('محفظة')),
        ('bank', _('بنك')),
        ('mobile', _('رصيد جوال')),
    ]

    transaction = models.OneToOneField(ServiceTransaction, on_delete=models.CASCADE,
                                        related_name='money_transfer', verbose_name=_('المعاملة'))
    transfer_type = models.CharField(_('نوع التحويل'), max_length=20, choices=TRANSFER_TYPES)
    sender_name = models.CharField(_('اسم المرسل'), max_length=200)
    sender_phone = models.CharField(_('هاتف المرسل'), max_length=20)
    receiver_name = models.CharField(_('اسم المستلم'), max_length=200)
    receiver_phone = models.CharField(_('هاتف المستلم'), max_length=20)
    receiver_account = models.CharField(_('حساب المستلم'), max_length=50, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)

    class Meta:
        verbose_name = _('تحويل مالي')
        verbose_name_plural = _('التحويلات المالية')

    def __str__(self):
        return f"{self.sender_name} -> {self.receiver_name}: {self.transaction.amount}"


class ServiceReport(models.Model):
    """تقارير الخدمات (للتجميع اليومي)"""
    date = models.DateField(_('التاريخ'), unique=True)
    total_transactions = models.PositiveIntegerField(_('عدد المعاملات'), default=0)
    total_amount = models.DecimalField(_('إجمالي المبالغ'), max_digits=14, decimal_places=2, default=Decimal('0'))
    total_fees = models.DecimalField(_('إجمالي الرسوم'), max_digits=12, decimal_places=2, default=Decimal('0'))
    successful_count = models.PositiveIntegerField(_('الناجحة'), default=0)
    failed_count = models.PositiveIntegerField(_('الفاشلة'), default=0)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('تقرير خدمات')
        verbose_name_plural = _('تقارير الخدمات')
        ordering = ['-date']

    def __str__(self):
        return f"تقرير {self.date}"
