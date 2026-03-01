"""
نماذج تطبيق المحاسبة — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class FiscalYear(AuditMixin):
    """السنة المالية"""
    name = models.CharField(max_length=100, verbose_name='اسم السنة المالية')
    start_date = models.DateField(verbose_name='تاريخ البداية')
    end_date = models.DateField(verbose_name='تاريخ النهاية')
    is_closed = models.BooleanField(default=False, verbose_name='مغلقة')
    is_active = models.BooleanField(default=True, verbose_name='نشطة')

    class Meta:
        verbose_name = 'سنة مالية'
        verbose_name_plural = 'السنوات المالية'
        ordering = ['-start_date']

    def __str__(self):
        return self.name


class CostCenter(AuditMixin):
    """مركز التكلفة"""
    CENTER_TYPE_CHOICES = [
        ('branch', 'فرع'),
        ('product_line', 'خط إنتاج'),
        ('warehouse', 'مخزن'),
        ('department', 'قسم'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='الكود')
    name = models.CharField(max_length=200, verbose_name='الاسم')
    center_type = models.CharField(max_length=20, choices=CENTER_TYPE_CHOICES, verbose_name='نوع المركز')
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children', verbose_name='المركز الأب',
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'مركز تكلفة'
        verbose_name_plural = 'مراكز التكلفة'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class Account(AuditMixin):
    """دليل الحسابات"""
    ACCOUNT_TYPE_CHOICES = [
        ('asset', 'أصول'),
        ('liability', 'التزامات'),
        ('equity', 'حقوق ملكية'),
        ('revenue', 'إيرادات'),
        ('cogs', 'تكلفة المبيعات'),
        ('expense', 'مصروفات'),
    ]
    NATURE_CHOICES = [
        ('debit', 'مدين'),
        ('credit', 'دائن'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='كود الحساب')
    name = models.CharField(max_length=200, verbose_name='اسم الحساب')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, verbose_name='نوع الحساب')
    nature = models.CharField(max_length=10, choices=NATURE_CHOICES, verbose_name='طبيعة الحساب')
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children', verbose_name='الحساب الأب',
    )
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='accounts', verbose_name='الفرع',
    )
    cost_center = models.ForeignKey(
        'CostCenter', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='accounts', verbose_name='مركز التكلفة',
    )
    is_detail = models.BooleanField(default=True, verbose_name='حساب تفصيلي')
    is_system = models.BooleanField(default=False, verbose_name='حساب النظام')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'حساب'
        verbose_name_plural = 'الحسابات'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class JournalEntry(AuditMixin):
    """القيد اليومية"""
    SOURCE_CHOICES = [
        ('manual', 'يدوي'),
        ('purchase', 'مشتريات'),
        ('sale', 'مبيعات'),
        ('production', 'إنتاج'),
        ('stock_move', 'حركة مخزون'),
        ('payroll', 'رواتب'),
        ('expense', 'مصروفات'),
        ('adjustment', 'تسوية'),
    ]
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('pending', 'في الانتظار'),
        ('approved', 'معتمد'),
        ('posted', 'مرحّل'),
        ('cancelled', 'ملغي'),
    ]

    entry_number = models.CharField(max_length=50, unique=True, verbose_name='رقم القيد')
    date = models.DateField(verbose_name='التاريخ')
    fiscal_year = models.ForeignKey(
        'FiscalYear', on_delete=models.PROTECT,
        related_name='journal_entries', verbose_name='السنة المالية',
    )
    description = models.TextField(verbose_name='البيان')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual', verbose_name='المصدر')
    source_document = models.CharField(max_length=100, blank=True, verbose_name='المستند المصدر')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='الحالة')
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='journal_entries', verbose_name='الفرع',
    )
    approved_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_journal_entries', verbose_name='اعتمد بواسطة',
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الاعتماد')
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي المدين')
    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='إجمالي الدائن')

    class Meta:
        verbose_name = 'قيد يومية'
        verbose_name_plural = 'قيود اليومية'
        ordering = ['-date', '-entry_number']

    def __str__(self):
        return f'{self.entry_number} - {self.description}'


class JournalLine(models.Model):
    """سطر القيد اليومية"""
    PARTNER_TYPE_CHOICES = [
        ('customer', 'عميل'),
        ('supplier', 'مورد'),
        ('', 'لا يوجد'),
    ]

    entry = models.ForeignKey(
        'JournalEntry', on_delete=models.CASCADE,
        related_name='lines', verbose_name='القيد',
    )
    account = models.ForeignKey(
        'Account', on_delete=models.PROTECT,
        related_name='journal_lines', verbose_name='الحساب',
    )
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='مدين')
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='دائن')
    description = models.CharField(max_length=500, blank=True, verbose_name='البيان')
    cost_center = models.ForeignKey(
        'CostCenter', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='journal_lines', verbose_name='مركز التكلفة',
    )
    partner_type = models.CharField(max_length=20, blank=True, choices=PARTNER_TYPE_CHOICES, verbose_name='نوع الطرف')
    partner_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='معرف الطرف')

    class Meta:
        verbose_name = 'سطر قيد'
        verbose_name_plural = 'أسطر القيود'

    def __str__(self):
        return f'{self.account} | مدين: {self.debit} | دائن: {self.credit}'


class TaxTransaction(AuditMixin):
    """معاملة ضريبية"""
    TAX_TYPE_CHOICES = [
        ('input', 'ضريبة مدخلات'),
        ('output', 'ضريبة مخرجات'),
    ]

    tax_type = models.CharField(max_length=10, choices=TAX_TYPE_CHOICES, verbose_name='نوع الضريبة')
    date = models.DateField(verbose_name='التاريخ')
    amount_before_tax = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='المبلغ قبل الضريبة')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=14, verbose_name='نسبة الضريبة')
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='مبلغ الضريبة')
    journal_entry = models.ForeignKey(
        'JournalEntry', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tax_transactions', verbose_name='القيد',
    )
    is_taxable_purchase = models.BooleanField(default=False, verbose_name='مشتريات خاضعة للضريبة')
    is_taxable_sale = models.BooleanField(default=False, verbose_name='مبيعات خاضعة للضريبة')

    class Meta:
        verbose_name = 'معاملة ضريبية'
        verbose_name_plural = 'المعاملات الضريبية'
        ordering = ['-date']

    def __str__(self):
        return f'{self.get_tax_type_display()} - {self.tax_amount}'

