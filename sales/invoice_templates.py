"""
نماذج وميزات محسنة للفواتير
Invoice Templates & Enhanced Features
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import json


class InvoiceTemplate(models.Model):
    """قوالب الفواتير المتكررة"""
    name = models.CharField(_('اسم النموذج'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    customer = models.ForeignKey('partners.Customer', on_delete=models.CASCADE, verbose_name=_('العميل'))
    payment_method = models.ForeignKey('payments.PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('طريقة الدفع'))
    discount = models.DecimalField(_('الخصم'), max_digits=12, decimal_places=2, default=Decimal('0'))
    is_tax_inclusive = models.BooleanField(_('السعر شامل الضريبة'), default=False)
    items_data = models.JSONField(_('بيانات الأصناف'), default=list, help_text=_('قائمة الأصناف بصيغة JSON'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoice_templates', verbose_name=_('أنشأه'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    usage_count = models.PositiveIntegerField(_('عدد مرات الاستخدام'), default=0)
    
    class Meta:
        verbose_name = _('نموذج فاتورة')
        verbose_name_plural = _('نماذج الفواتير')
        ordering = ['-usage_count', '-created_at']
        indexes = [
            models.Index(fields=['customer', 'is_active']),
            models.Index(fields=['created_by', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.customer.name}"
    
    def increment_usage(self):
        """زيادة عداد الاستخدام"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class InvoiceAutosave(models.Model):
    """الحفظ التلقائي للفواتير قيد الإنشاء"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('المستخدم'))
    session_key = models.CharField(_('مفتاح الجلسة'), max_length=100, db_index=True)
    form_data = models.JSONField(_('بيانات النموذج'), default=dict)
    items_data = models.JSONField(_('بيانات الأصناف'), default=list)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    expires_at = models.DateTimeField(_('تاريخ الانتهاء'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('حفظ تلقائي')
        verbose_name_plural = _('الحفظ التلقائي')
        ordering = ['-updated_at']
        unique_together = [['user', 'session_key']]
        indexes = [
            models.Index(fields=['user', 'updated_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Autosave for {self.user.username} at {self.updated_at}"
    
    def is_expired(self):
        """التحقق من انتهاء صلاحية الحفظ"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @classmethod
    def cleanup_expired(cls):
        """حذف البيانات المنتهية"""
        cls.objects.filter(expires_at__lt=timezone.now()).delete()


class InvoiceAttachment(models.Model):
    """مرفقات الفواتير"""
    invoice = models.ForeignKey('sales.Invoice', on_delete=models.CASCADE, related_name='attachments', verbose_name=_('الفاتورة'))
    file = models.FileField(_('الملف'), upload_to='invoices/attachments/%Y/%m/')
    original_filename = models.CharField(_('اسم الملف الأصلي'), max_length=255)
    file_type = models.CharField(_('نوع الملف'), max_length=50, blank=True)
    file_size = models.PositiveIntegerField(_('حجم الملف (بايت)'), default=0)
    description = models.CharField(_('الوصف'), max_length=200, blank=True)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('رفعه'))
    uploaded_at = models.DateTimeField(_('تاريخ الرفع'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('مرفق فاتورة')
        verbose_name_plural = _('مرفقات الفواتير')
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.original_filename} - {self.invoice.number}"
    
    def get_file_extension(self):
        """الحصول على امتداد الملف"""
        return self.original_filename.split('.')[-1].lower() if '.' in self.original_filename else ''
    
    def is_image(self):
        """التحقق من كون الملف صورة"""
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        return self.get_file_extension() in image_extensions


class InvoiceHistory(models.Model):
    """سجل تغييرات الفواتير"""
    ACTION_CREATED = 'created'
    ACTION_UPDATED = 'updated'
    ACTION_DELETED = 'deleted'
    ACTION_RESTORED = 'restored'
    ACTION_ITEM_ADDED = 'item_added'
    ACTION_ITEM_REMOVED = 'item_removed'
    ACTION_PAYMENT_ADDED = 'payment_added'
    
    ACTION_CHOICES = [
        (ACTION_CREATED, _('إنشاء')),
        (ACTION_UPDATED, _('تحديث')),
        (ACTION_DELETED, _('حذف')),
        (ACTION_RESTORED, _('استعادة')),
        (ACTION_ITEM_ADDED, _('إضافة صنف')),
        (ACTION_ITEM_REMOVED, _('حذف صنف')),
        (ACTION_PAYMENT_ADDED, _('إضافة دفعة')),
    ]
    
    invoice = models.ForeignKey('sales.Invoice', on_delete=models.CASCADE, related_name='history', verbose_name=_('الفاتورة'))
    action = models.CharField(_('الإجراء'), max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('المستخدم'))
    timestamp = models.DateTimeField(_('الوقت'), auto_now_add=True)
    changes = models.JSONField(_('التغييرات'), default=dict)
    previous_data = models.JSONField(_('البيانات السابقة'), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    user_agent = models.CharField(_('متصفح المستخدم'), max_length=255, blank=True)
    
    class Meta:
        verbose_name = _('سجل تغيير فاتورة')
        verbose_name_plural = _('سجل تغييرات الفواتير')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['invoice', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.invoice.number} - {self.timestamp}"


class CustomerCreditLimit(models.Model):
    """حدود الائتمان للعملاء"""
    customer = models.OneToOneField('partners.Customer', on_delete=models.CASCADE, related_name='credit_limit_info', verbose_name=_('العميل'))
    credit_limit = models.DecimalField(_('حد الائتمان'), max_digits=12, decimal_places=2, default=Decimal('0'))
    current_balance = models.DecimalField(_('الرصيد الحالي'), max_digits=12, decimal_places=2, default=Decimal('0'))
    payment_days = models.PositiveIntegerField(_('أيام الدفع'), default=0, help_text=_('عدد الأيام المسموح بها للدفع'))
    
    is_blocked = models.BooleanField(_('محظور'), default=False)
    block_reason = models.TextField(_('سبب الحظر'), blank=True)
    
    last_transaction_date = models.DateField(_('تاريخ آخر معاملة'), null=True, blank=True)
    last_payment_date = models.DateField(_('تاريخ آخر دفعة'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('حد ائتمان عميل')
        verbose_name_plural = _('حدود ائتمان العملاء')
    
    def __str__(self):
        return f"{self.customer.name} - {self.credit_limit}"
    
    def is_over_limit(self):
        """التحقق من تجاوز حد الائتمان"""
        return self.current_balance > self.credit_limit
    
    def available_credit(self):
        """حساب الائتمان المتاح"""
        return max(Decimal('0'), self.credit_limit - self.current_balance)
    
    def update_balance(self):
        """تحديث الرصيد الحالي من الفواتير"""
        from sales.models import Invoice
        from django.db.models import Sum
        
        total = Invoice.objects.filter(
            customer=self.customer,
            is_deleted=False
        ).aggregate(
            total=Sum('cached_total')
        )['total'] or Decimal('0')
        
        self.current_balance = total
        self.save(update_fields=['current_balance', 'updated_at'])
