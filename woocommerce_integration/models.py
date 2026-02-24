from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from decimal import Decimal


class WooCommerceConfig(models.Model):
    """WooCommerce Store Configuration"""
    
    name = models.CharField(_('اسم المتجر'), max_length=200)
    store_url = models.URLField(_('رابط المتجر'), validators=[URLValidator()])
    consumer_key = models.CharField(_('Consumer Key'), max_length=500)
    consumer_secret = models.CharField(_('Consumer Secret'), max_length=500)
    
    is_active = models.BooleanField(_('نشط'), default=True)
    is_default = models.BooleanField(_('افتراضي'), default=False)
    
    # Sync Settings
    auto_sync_products = models.BooleanField(_('مزامنة المنتجات تلقائياً'), default=True)
    auto_sync_orders = models.BooleanField(_('مزامنة الطلبات تلقائياً'), default=True)
    auto_sync_inventory = models.BooleanField(_('مزامنة المخزون تلقائياً'), default=True)
    
    sync_interval_minutes = models.PositiveIntegerField(_('فترة المزامنة (دقائق)'), default=15)
    
    # Mapping Settings
    default_location = models.ForeignKey(
        'inventory.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('موقع المخزون الافتراضي')
    )
    
    default_customer_type = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_('نوع العميل الافتراضي')
    )
    
    # Timestamps
    last_product_sync = models.DateTimeField(_('آخر مزامنة منتجات'), null=True, blank=True)
    last_order_sync = models.DateTimeField(_('آخر مزامنة طلبات'), null=True, blank=True)
    last_inventory_sync = models.DateTimeField(_('آخر مزامنة مخزون'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('إعداد WooCommerce')
        verbose_name_plural = _('إعدادات WooCommerce')
        ordering = ['-is_default', 'name']
        indexes = [
            models.Index(fields=['is_active', 'is_default']),
            models.Index(fields=['last_product_sync']),
            models.Index(fields=['last_order_sync']),
            models.Index(fields=['last_inventory_sync']),
        ]

    def __str__(self):
        return f"{self.name} ({self.store_url})"
    
    def clean(self):
        """تحققات أساسية على مستوى الموديل.

        - التأكد من أن فترة المزامنة أكبر من صفر.
        - منع وجود أكثر من سجل واحد افتراضي is_default=True.
        """
        errors = {}

        if self.sync_interval_minutes <= 0:
            errors['sync_interval_minutes'] = _('فترة المزامنة يجب أن تكون أكبر من صفر دقيقة.')

        if self.is_default:
            qs = WooCommerceConfig.objects.filter(is_default=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors['is_default'] = _('يوجد إعداد افتراضي آخر بالفعل، لا يمكن تعيين أكثر من إعداد افتراضي واحد.')

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Ensure only one default config
        if self.is_default:
            WooCommerceConfig.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class ProductMapping(models.Model):
    """Maps ERP Products to WooCommerce Products"""
    
    config = models.ForeignKey(
        WooCommerceConfig,
        on_delete=models.CASCADE,
        related_name='product_mappings',
        verbose_name=_('المتجر')
    )
    
    erp_product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='woo_mappings',
        verbose_name=_('منتج ERP')
    )
    
    woo_product_id = models.PositiveIntegerField(_('معرف WooCommerce'))
    woo_sku = models.CharField(_('SKU في WooCommerce'), max_length=200, blank=True)
    
    # Sync Control
    sync_enabled = models.BooleanField(_('المزامنة مفعلة'), default=True)
    sync_stock = models.BooleanField(_('مزامنة المخزون'), default=True)
    sync_price = models.BooleanField(_('مزامنة السعر'), default=True)
    
    last_synced = models.DateTimeField(_('آخر مزامنة'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('ربط منتج')
        verbose_name_plural = _('ربط المنتجات')
        unique_together = [['config', 'erp_product'], ['config', 'woo_product_id']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['woo_product_id']),
            models.Index(fields=['woo_sku']),
            models.Index(fields=['sync_enabled', 'last_synced']),
        ]

    def __str__(self):
        return f"{self.erp_product.name} → WooCommerce #{self.woo_product_id}"


class OrderMapping(models.Model):
    """Maps WooCommerce Orders to ERP Sales Invoices"""
    
    STATUS_CHOICES = [
        ('pending', _('معلق')),
        ('processing', _('قيد المعالجة')),
        ('completed', _('مكتمل')),
        ('failed', _('فشل')),
    ]
    
    config = models.ForeignKey(
        WooCommerceConfig,
        on_delete=models.CASCADE,
        related_name='order_mappings',
        verbose_name=_('المتجر')
    )
    
    woo_order_id = models.PositiveIntegerField(_('رقم طلب WooCommerce'))
    woo_order_number = models.CharField(_('رقم الطلب'), max_length=200)
    
    erp_invoice = models.ForeignKey(
        'sales.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='woo_mappings',
        verbose_name=_('فاتورة ERP')
    )
    
    erp_customer = models.ForeignKey(
        'partners.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='woo_orders',
        verbose_name=_('عميل ERP')
    )
    
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Order Data (JSON for flexibility)
    woo_data = models.JSONField(_('بيانات WooCommerce'), default=dict, blank=True)
    
    # Timestamps
    woo_created_at = models.DateTimeField(_('تاريخ الطلب في WooCommerce'))
    synced_at = models.DateTimeField(_('تاريخ المزامنة'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('ربط طلب')
        verbose_name_plural = _('ربط الطلبات')
        unique_together = [['config', 'woo_order_id']]
        ordering = ['-woo_created_at']
        indexes = [
            models.Index(fields=['-woo_created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"WooCommerce #{self.woo_order_number} → ERP Invoice #{self.erp_invoice.number if self.erp_invoice else 'N/A'}"


class CustomerMapping(models.Model):
    """Maps WooCommerce Customers to ERP Customers"""
    
    config = models.ForeignKey(
        WooCommerceConfig,
        on_delete=models.CASCADE,
        related_name='customer_mappings',
        verbose_name=_('المتجر')
    )
    
    woo_customer_id = models.PositiveIntegerField(_('معرف عميل WooCommerce'))
    woo_email = models.EmailField(_('البريد الإلكتروني'))
    
    erp_customer = models.ForeignKey(
        'partners.Customer',
        on_delete=models.CASCADE,
        related_name='woo_mappings',
        verbose_name=_('عميل ERP')
    )
    
    last_synced = models.DateTimeField(_('آخر مزامنة'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('ربط عميل')
        verbose_name_plural = _('ربط العملاء')
        unique_together = [['config', 'woo_customer_id'], ['config', 'erp_customer']]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.erp_customer.name} ← WooCommerce #{self.woo_customer_id}"


class SyncLog(models.Model):
    """Log of all sync operations"""
    
    SYNC_TYPE_CHOICES = [
        ('product_push', _('دفع منتج')),
        ('product_pull', _('سحب منتج')),
        ('inventory_push', _('دفع مخزون')),
        ('inventory_pull', _('سحب مخزون')),
        ('order_pull', _('سحب طلب')),
        ('customer_pull', _('سحب عميل')),
    ]
    
    STATUS_CHOICES = [
        ('success', _('نجح')),
        ('failed', _('فشل')),
        ('partial', _('جزئي')),
    ]
    
    config = models.ForeignKey(
        WooCommerceConfig,
        on_delete=models.CASCADE,
        verbose_name=_('المتجر')
    )
    
    sync_type = models.CharField(_('نوع المزامنة'), max_length=20, choices=SYNC_TYPE_CHOICES)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES)
    
    records_processed = models.PositiveIntegerField(_('عدد السجلات'), default=0)
    records_success = models.PositiveIntegerField(_('الناجحة'), default=0)
    records_failed = models.PositiveIntegerField(_('الفاشلة'), default=0)
    
    message = models.TextField(_('الرسالة'), blank=True)
    error_details = models.TextField(_('تفاصيل الأخطاء'), blank=True)
    
    started_at = models.DateTimeField(_('بدأ في'), auto_now_add=True)
    completed_at = models.DateTimeField(_('انتهى في'), null=True, blank=True)
    duration_seconds = models.DecimalField(_('المدة (ثواني)'), max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = _('سجل مزامنة')
        verbose_name_plural = _('سجلات المزامنة')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['status']),
            models.Index(fields=['sync_type']),
        ]

    def __str__(self):
        return f"{self.get_sync_type_display()} - {self.get_status_display()} ({self.started_at})"
