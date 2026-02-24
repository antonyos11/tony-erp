from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum

User = get_user_model()


class TaxSettings(models.Model):
    """إعدادات الضرائب العامة"""
    
    # معلومات التسجيل الضريبي
    tax_registration_number = models.CharField(
        max_length=50, 
        verbose_name=_('رقم التسجيل الضريبي'),
        help_text=_('رقم التسجيل في مصلحة الضرائب')
    )
    tax_file_number = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name=_('رقم الملف الضريبي')
    )
    commercial_registration = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name=_('السجل التجاري')
    )
    
    # نسب الضريبة
    default_vat_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('14.00'),
        verbose_name=_('نسبة ضريبة القيمة المضافة الافتراضية %')
    )
    
    # إعدادات الفواتير الإلكترونية
    einvoice_enabled = models.BooleanField(
        default=False,
        verbose_name=_('تفعيل الفاتورة الإلكترونية')
    )
    einvoice_api_key = models.CharField(
        max_length=500, 
        blank=True,
        verbose_name=_('مفتاح API للفاتورة الإلكترونية')
    )
    einvoice_client_id = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name=_('Client ID')
    )
    einvoice_client_secret = models.CharField(
        max_length=500, 
        blank=True,
        verbose_name=_('Client Secret')
    )
    einvoice_environment = models.CharField(
        max_length=20,
        choices=[('production', 'إنتاج'), ('preprod', 'اختبار')],
        default='preprod',
        verbose_name=_('بيئة العمل')
    )
    
    # حدود الإعفاء
    exemption_threshold = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('500000.00'),
        verbose_name=_('حد الإعفاء السنوي'),
        help_text=_('المبيعات السنوية التي تعفى من الضريبة إذا كانت أقل من هذا الحد')
    )
    
    is_exempt = models.BooleanField(
        default=False,
        verbose_name=_('معفى من الضريبة'),
        help_text=_('هل الشركة معفاة من ضريبة القيمة المضافة؟')
    )
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('إعدادات الضرائب')
        verbose_name_plural = _('إعدادات الضرائب')
    
    def __str__(self):
        return f"إعدادات الضرائب - {self.tax_registration_number}"
    
    @classmethod
    def get_settings(cls):
        """الحصول على الإعدادات أو إنشاء افتراضية"""
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={'tax_registration_number': ''}
        )
        return settings


class TaxCategory(models.Model):
    """فئات الضريبة (مختلفة حسب نوع المنتج/الخدمة)"""
    
    name = models.CharField(max_length=100, verbose_name=_('اسم الفئة'))
    code = models.CharField(max_length=20, unique=True, verbose_name=_('كود الفئة'))
    rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        verbose_name=_('نسبة الضريبة %')
    )
    description = models.TextField(blank=True, verbose_name=_('الوصف'))
    is_exempt = models.BooleanField(default=False, verbose_name=_('معفى'))
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
    
    # كود ETA للفاتورة الإلكترونية
    eta_code = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name=_('كود مصلحة الضرائب')
    )
    
    class Meta:
        verbose_name = _('فئة ضريبية')
        verbose_name_plural = _('الفئات الضريبية')
        ordering = ['name']
    
    def __str__(self):
        if self.is_exempt:
            return f"{self.name} (معفى)"
        return f"{self.name} ({self.rate}%)"


class TaxInvoice(models.Model):
    """الفواتير الضريبية"""
    
    INVOICE_TYPE_CHOICES = [
        ('sales', _('فاتورة مبيعات')),
        ('sales_return', _('مرتجع مبيعات')),
        ('purchase', _('فاتورة مشتريات')),
        ('purchase_return', _('مرتجع مشتريات')),
    ]
    
    TAX_TYPE_CHOICES = [
        ('taxable', _('خاضع للضريبة')),
        ('exempt', _('معفى')),
        ('zero_rated', _('صفري')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('pending', _('في انتظار الإرسال')),
        ('submitted', _('تم الإرسال')),
        ('accepted', _('مقبولة')),
        ('rejected', _('مرفوضة')),
        ('cancelled', _('ملغاة')),
    ]
    
    # رقم الفاتورة
    invoice_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name=_('رقم الفاتورة')
    )
    internal_id = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name=_('الرقم الداخلي')
    )
    
    # نوع الفاتورة
    invoice_type = models.CharField(
        max_length=20, 
        choices=INVOICE_TYPE_CHOICES,
        verbose_name=_('نوع الفاتورة')
    )
    tax_type = models.CharField(
        max_length=20, 
        choices=TAX_TYPE_CHOICES,
        default='taxable',
        verbose_name=_('نوع الضريبة')
    )
    
    # التاريخ
    invoice_date = models.DateField(verbose_name=_('تاريخ الفاتورة'))
    due_date = models.DateField(null=True, blank=True, verbose_name=_('تاريخ الاستحقاق'))
    
    # العميل/المورد
    partner_name = models.CharField(max_length=200, verbose_name=_('اسم العميل/المورد'))
    partner_tax_id = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name=_('الرقم الضريبي للعميل/المورد')
    )
    partner_address = models.TextField(blank=True, verbose_name=_('العنوان'))
    
    # المبالغ
    subtotal = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name=_('الإجمالي قبل الضريبة')
    )
    discount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_('الخصم')
    )
    tax_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name=_('قيمة الضريبة')
    )
    total = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name=_('الإجمالي شامل الضريبة')
    )
    
    # نسبة الضريبة المطبقة
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=Decimal('14.00'),
        verbose_name=_('نسبة الضريبة %')
    )
    
    # الحالة
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_('الحالة')
    )
    
    # الفاتورة الإلكترونية
    uuid = models.CharField(max_length=100, blank=True, verbose_name=_('UUID'))
    submission_id = models.CharField(max_length=100, blank=True, verbose_name=_('رقم الإرسال'))
    long_id = models.CharField(max_length=200, blank=True, verbose_name=_('Long ID'))
    hash_key = models.CharField(max_length=500, blank=True, verbose_name=_('Hash Key'))
    qr_code = models.TextField(blank=True, verbose_name=_('QR Code'))
    
    # الربط بالفواتير الأصلية
    related_invoice = models.ForeignKey(
        'sales.Invoice', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='tax_invoices',
        verbose_name=_('فاتورة المبيعات')
    )
    related_purchase = models.ForeignKey(
        'purchases.PurchaseBill', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='tax_invoices',
        verbose_name=_('فاتورة المشتريات')
    )
    
    # ملاحظات
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    rejection_reason = models.TextField(blank=True, verbose_name=_('سبب الرفض'))
    
    # التتبع
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_tax_invoices',
        verbose_name=_('أنشئت بواسطة')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاريخ الإرسال'))
    
    class Meta:
        verbose_name = _('فاتورة ضريبية')
        verbose_name_plural = _('الفواتير الضريبية')
        ordering = ['-invoice_date', '-id']
        indexes = [
            models.Index(fields=['invoice_type', 'status']),
            models.Index(fields=['invoice_date']),
            models.Index(fields=['partner_tax_id']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.partner_name}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # توليد رقم فاتورة تلقائي
            prefix = {
                'sales': 'TAX-S',
                'sales_return': 'TAX-SR',
                'purchase': 'TAX-P',
                'purchase_return': 'TAX-PR',
            }.get(self.invoice_type, 'TAX')
            
            year_month = timezone.now().strftime('%Y%m')
            last = TaxInvoice.objects.filter(
                invoice_number__startswith=f'{prefix}-{year_month}'
            ).order_by('-id').first()
            
            if last:
                try:
                    seq = int(last.invoice_number.split('-')[-1]) + 1
                except:
                    seq = 1
            else:
                seq = 1
            
            self.invoice_number = f'{prefix}-{year_month}-{seq:05d}'
        
        super().save(*args, **kwargs)
    
    @property
    def is_sales(self):
        return self.invoice_type in ['sales', 'sales_return']
    
    @property
    def is_purchase(self):
        return self.invoice_type in ['purchase', 'purchase_return']
    
    @property
    def is_return(self):
        return self.invoice_type in ['sales_return', 'purchase_return']
    
    @property
    def tax_direction(self):
        """اتجاه الضريبة: مستحقة علينا أو لنا"""
        if self.invoice_type == 'sales':
            return 'output'  # ضريبة مخرجات (مستحقة علينا للضرائب)
        elif self.invoice_type == 'sales_return':
            return 'output_credit'  # تخفيض ضريبة مخرجات
        elif self.invoice_type == 'purchase':
            return 'input'  # ضريبة مدخلات (لنا عند الضرائب)
        elif self.invoice_type == 'purchase_return':
            return 'input_debit'  # تخفيض ضريبة مدخلات
        return 'unknown'


class TaxInvoiceLine(models.Model):
    """بنود الفاتورة الضريبية"""
    
    invoice = models.ForeignKey(
        TaxInvoice, 
        on_delete=models.CASCADE, 
        related_name='lines',
        verbose_name=_('الفاتورة')
    )
    
    # المنتج/الخدمة
    item_code = models.CharField(max_length=50, blank=True, verbose_name=_('كود الصنف'))
    item_name = models.CharField(max_length=200, verbose_name=_('اسم الصنف'))
    item_description = models.TextField(blank=True, verbose_name=_('الوصف'))
    
    # فئة الضريبة
    tax_category = models.ForeignKey(
        TaxCategory, 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_('فئة الضريبة')
    )
    
    # الكميات والأسعار
    quantity = models.DecimalField(max_digits=15, decimal_places=3, verbose_name=_('الكمية'))
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('سعر الوحدة'))
    discount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_('الخصم')
    )
    
    # الضريبة
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        verbose_name=_('نسبة الضريبة %')
    )
    tax_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name=_('قيمة الضريبة')
    )
    
    # الإجمالي
    line_total = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name=_('إجمالي البند')
    )
    
    # كود ETA
    eta_item_code = models.CharField(max_length=50, blank=True, verbose_name=_('كود ETA'))
    
    class Meta:
        verbose_name = _('بند فاتورة ضريبية')
        verbose_name_plural = _('بنود الفاتورة الضريبية')
    
    def __str__(self):
        return f"{self.item_name} - {self.quantity}"
    
    def save(self, *args, **kwargs):
        # حساب الإجمالي
        subtotal = (self.quantity * self.unit_price) - self.discount
        self.tax_amount = (subtotal * self.tax_rate) / 100
        self.line_total = subtotal + self.tax_amount
        super().save(*args, **kwargs)


class TaxPeriod(models.Model):
    """الفترات الضريبية"""
    
    PERIOD_TYPE_CHOICES = [
        ('monthly', _('شهري')),
        ('quarterly', _('ربع سنوي')),
        ('annually', _('سنوي')),
    ]
    
    STATUS_CHOICES = [
        ('open', _('مفتوحة')),
        ('closed', _('مغلقة')),
        ('filed', _('تم تقديم الإقرار')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_('اسم الفترة'))
    period_type = models.CharField(
        max_length=20, 
        choices=PERIOD_TYPE_CHOICES,
        default='monthly',
        verbose_name=_('نوع الفترة')
    )
    start_date = models.DateField(verbose_name=_('تاريخ البداية'))
    end_date = models.DateField(verbose_name=_('تاريخ النهاية'))
    due_date = models.DateField(verbose_name=_('تاريخ استحقاق الإقرار'))
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='open',
        verbose_name=_('الحالة')
    )
    
    # الإجماليات
    total_output_tax = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_('إجمالي ضريبة المخرجات')
    )
    total_input_tax = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_('إجمالي ضريبة المدخلات')
    )
    net_tax = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_('صافي الضريبة'),
        help_text=_('موجب = مستحق علينا، سالب = لنا')
    )
    
    # الإقرار
    filed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاريخ تقديم الإقرار'))
    filed_by = models.ForeignKey(
        User, 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_('قُدم بواسطة')
    )
    reference_number = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name=_('رقم مرجع الإقرار')
    )
    
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('فترة ضريبية')
        verbose_name_plural = _('الفترات الضريبية')
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name
    
    def calculate_taxes(self):
        """حساب الضرائب للفترة"""
        invoices = TaxInvoice.objects.filter(
            invoice_date__gte=self.start_date,
            invoice_date__lte=self.end_date,
            status__in=['submitted', 'accepted']
        )
        
        # ضريبة المخرجات (المبيعات)
        sales = invoices.filter(invoice_type='sales').aggregate(
            total=Sum('tax_amount')
        )['total'] or Decimal('0')
        
        sales_returns = invoices.filter(invoice_type='sales_return').aggregate(
            total=Sum('tax_amount')
        )['total'] or Decimal('0')
        
        self.total_output_tax = sales - sales_returns
        
        # ضريبة المدخلات (المشتريات)
        purchases = invoices.filter(invoice_type='purchase').aggregate(
            total=Sum('tax_amount')
        )['total'] or Decimal('0')
        
        purchase_returns = invoices.filter(invoice_type='purchase_return').aggregate(
            total=Sum('tax_amount')
        )['total'] or Decimal('0')
        
        self.total_input_tax = purchases - purchase_returns
        
        # صافي الضريبة
        self.net_tax = self.total_output_tax - self.total_input_tax
        
        self.save(update_fields=['total_output_tax', 'total_input_tax', 'net_tax'])
        return self.net_tax


class TaxPayment(models.Model):
    """سداد الضرائب"""
    
    PAYMENT_TYPE_CHOICES = [
        ('vat', _('ضريبة قيمة مضافة')),
        ('income', _('ضريبة دخل')),
        ('withholding', _('ضريبة خصم')),
        ('other', _('أخرى')),
    ]
    
    period = models.ForeignKey(
        TaxPeriod, 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payments',
        verbose_name=_('الفترة الضريبية')
    )
    
    payment_type = models.CharField(
        max_length=20, 
        choices=PAYMENT_TYPE_CHOICES,
        default='vat',
        verbose_name=_('نوع الضريبة')
    )
    
    payment_date = models.DateField(verbose_name=_('تاريخ السداد'))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('المبلغ'))
    
    reference_number = models.CharField(max_length=50, blank=True, verbose_name=_('رقم إيصال السداد'))
    bank_name = models.CharField(max_length=100, blank=True, verbose_name=_('البنك'))
    
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name=_('أنشئ بواسطة')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('سداد ضريبة')
        verbose_name_plural = _('سداد الضرائب')
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"سداد {self.amount} بتاريخ {self.payment_date}"


class TaxExemption(models.Model):
    """الإعفاءات الضريبية"""
    
    name = models.CharField(max_length=200, verbose_name=_('اسم الإعفاء'))
    description = models.TextField(blank=True, verbose_name=_('الوصف'))
    
    # نوع الإعفاء
    exemption_type = models.CharField(
        max_length=50,
        choices=[
            ('product', _('منتج معفى')),
            ('customer', _('عميل معفى')),
            ('transaction', _('معاملة معفاة')),
            ('sector', _('قطاع معفى')),
        ],
        verbose_name=_('نوع الإعفاء')
    )
    
    # مرجع قانوني
    legal_reference = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name=_('المرجع القانوني'),
        help_text=_('رقم المادة أو القرار')
    )
    
    start_date = models.DateField(verbose_name=_('تاريخ البداية'))
    end_date = models.DateField(null=True, blank=True, verbose_name=_('تاريخ الانتهاء'))
    
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('إعفاء ضريبي')
        verbose_name_plural = _('الإعفاءات الضريبية')
    
    def __str__(self):
        return self.name
