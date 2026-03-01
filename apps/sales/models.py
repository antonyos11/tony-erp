"""
نماذج تطبيق المبيعات — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class PriceList(AuditMixin):
    """قائمة الأسعار"""
    PRICE_TYPE_CHOICES = [
        ('retail', 'تجزئة'),
        ('wholesale', 'جملة'),
        ('franchise', 'توكيل'),
        ('distributor', 'موزع'),
        ('online', 'أونلاين'),
    ]

    name = models.CharField(max_length=200, verbose_name='الاسم')
    price_type = models.CharField(max_length=20, choices=PRICE_TYPE_CHOICES, verbose_name='نوع السعر')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الخصم %')
    is_active = models.BooleanField(default=True, verbose_name='نشطة')

    class Meta:
        verbose_name = 'قائمة أسعار'
        verbose_name_plural = 'قوائم الأسعار'
        ordering = ['name']

    def __str__(self):
        return self.name


class PriceListItem(models.Model):
    """سطر قائمة الأسعار"""
    price_list = models.ForeignKey(
        'PriceList', on_delete=models.CASCADE,
        related_name='items', verbose_name='قائمة الأسعار',
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.CASCADE,
        related_name='price_list_items', verbose_name='المنتج',
    )
    price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='السعر')

    class Meta:
        verbose_name = 'سطر قائمة أسعار'
        verbose_name_plural = 'أسطر قوائم الأسعار'
        unique_together = [['price_list', 'product']]

    def __str__(self):
        return f'{self.price_list} - {self.product}: {self.price}'


class Customer(AuditMixin):
    """العملاء"""
    CUSTOMER_TYPE_CHOICES = [
        ('retail', 'تجزئة'),
        ('wholesale', 'جملة'),
        ('franchise', 'توكيل'),
        ('distributor', 'موزع'),
        ('online', 'أونلاين'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='الكود')
    name = models.CharField(max_length=300, verbose_name='الاسم')
    customer_type = models.CharField(
        max_length=20, choices=CUSTOMER_TYPE_CHOICES,
        default='retail', verbose_name='نوع العميل',
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='الهاتف')
    phone2 = models.CharField(max_length=20, blank=True, verbose_name='هاتف 2')
    address = models.TextField(blank=True, verbose_name='العنوان')
    governorate = models.CharField(max_length=100, blank=True, verbose_name='المحافظة')
    tax_number = models.CharField(max_length=50, blank=True, verbose_name='الرقم الضريبي')
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='حد الائتمان')
    price_list = models.ForeignKey(
        'PriceList', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='customers', verbose_name='قائمة الأسعار',
    )
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='customers', verbose_name='الفرع',
    )
    account = models.ForeignKey(
        'accounts.Account', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='customers', verbose_name='الحساب المحاسبي',
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'عميل'
        verbose_name_plural = 'العملاء'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class SalesInvoice(AuditMixin):
    """فاتورة المبيعات"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكدة'),
        ('delivered', 'مسلمة'),
        ('paid', 'مدفوعة'),
        ('partial_paid', 'مدفوعة جزئياً'),
        ('cancelled', 'ملغية'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'نقداً'),
        ('installment', 'تقسيط'),
        ('visa', 'فيزا'),
        ('bank_transfer', 'تحويل بنكي'),
        ('check', 'شيك'),
        ('mixed', 'مختلط'),
    ]
    SALE_CHANNEL_CHOICES = [
        ('branch', 'فرع'),
        ('online', 'أونلاين'),
        ('phone', 'هاتف'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, verbose_name='رقم الفاتورة')
    date = models.DateTimeField(verbose_name='التاريخ')
    customer = models.ForeignKey(
        'Customer', on_delete=models.PROTECT,
        related_name='invoices', verbose_name='العميل',
    )
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.PROTECT,
        related_name='sales_invoices', verbose_name='الفرع',
    )
    warehouse = models.ForeignKey(
        'core.Warehouse', on_delete=models.PROTECT,
        related_name='sales_invoices', verbose_name='المخزن',
    )
    salesperson = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_invoices', verbose_name='البائع',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='الحالة')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash', verbose_name='طريقة الدفع')
    sale_channel = models.CharField(max_length=20, choices=SALE_CHANNEL_CHOICES, default='branch', verbose_name='قناة البيع')
    price_list = models.ForeignKey(
        'PriceList', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices', verbose_name='قائمة الأسعار',
    )
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الإجمالي قبل الخصم')
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='مبلغ الخصم')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الخصم %')
    taxable_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='المبلغ الخاضع للضريبة')
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='مبلغ الضريبة')
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الإجمالي')
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='المبلغ المدفوع')
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='المبلغ المتبقي')
    is_taxable = models.BooleanField(default=True, verbose_name='خاضعة للضريبة')
    delivery_required = models.BooleanField(default=False, verbose_name='يستلزم توصيل')
    delivery_address = models.TextField(blank=True, verbose_name='عنوان التوصيل')
    delivery_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='رسوم التوصيل')
    journal_entry = models.ForeignKey(
        'accounts.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_invoices', verbose_name='القيد',
    )
    notes = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'فاتورة مبيعات'
        verbose_name_plural = 'فواتير المبيعات'
        ordering = ['-date', '-invoice_number']

    def __str__(self):
        return f'{self.invoice_number} - {self.customer}'


class SalesInvoiceLine(models.Model):
    """سطر فاتورة المبيعات"""
    invoice = models.ForeignKey(
        'SalesInvoice', on_delete=models.CASCADE,
        related_name='lines', verbose_name='الفاتورة',
    )
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.PROTECT,
        related_name='invoice_lines', verbose_name='المنتج',
    )
    quantity = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='الكمية')
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='سعر الوحدة')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نسبة الخصم %')
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='مبلغ الخصم')
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الإجمالي')
    cost_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='سعر التكلفة')
    profit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الربح')
    custom_width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='العرض المخصص')
    custom_length = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='الطول المخصص')
    notes = models.CharField(max_length=500, blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'سطر فاتورة'
        verbose_name_plural = 'أسطر الفواتير'

    def __str__(self):
        return f'{self.product} x{self.quantity} @ {self.unit_price}'


class SalesReturn(AuditMixin):
    """مرتجع المبيعات"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('approved', 'معتمد'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]

    return_number = models.CharField(max_length=50, unique=True, verbose_name='رقم المرتجع')
    date = models.DateTimeField(verbose_name='التاريخ')
    original_invoice = models.ForeignKey(
        'SalesInvoice', on_delete=models.PROTECT,
        related_name='returns', verbose_name='الفاتورة الأصلية',
    )
    customer = models.ForeignKey(
        'Customer', on_delete=models.PROTECT,
        related_name='returns', verbose_name='العميل',
    )
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.PROTECT,
        related_name='sales_returns', verbose_name='الفرع',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='الحالة')
    reason = models.TextField(verbose_name='سبب الإرجاع')
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='الإجمالي')
    journal_entry = models.ForeignKey(
        'accounts.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sales_returns', verbose_name='القيد',
    )

    class Meta:
        verbose_name = 'مرتجع مبيعات'
        verbose_name_plural = 'مرتجعات المبيعات'
        ordering = ['-date']

    def __str__(self):
        return f'{self.return_number} - {self.customer}'

