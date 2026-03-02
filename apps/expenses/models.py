"""
نماذج بيانات تطبيق المصروفات — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class ExpenseCategory(AuditMixin):
    """تصنيفات المصروفات"""
    name = models.CharField(max_length=255, verbose_name="اسم التصنيف")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='children', verbose_name="التصنيف الأب")
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT,
                                verbose_name="الحساب المحاسبي")
    budget_monthly = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                         verbose_name="الميزانية الشهرية")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "تصنيف مصروف"
        verbose_name_plural = "تصنيفات المصروفات"

    def __str__(self):
        return self.name


class Expense(AuditMixin):
    """مصروف"""
    EXPENSE_STATUSES = [
        ('draft', 'مسودة'),
        ('pending', 'في انتظار الاعتماد'),
        ('approved', 'معتمد'),
        ('paid', 'مدفوع'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي'),
    ]
    PAYMENT_METHODS = [
        ('cash', 'نقدي'),
        ('bank', 'تحويل بنكي'),
        ('check', 'شيك'),
        ('credit_card', 'بطاقة ائتمان'),
    ]

    expense_number = models.CharField(max_length=50, unique=True, verbose_name="رقم المصروف")
    date = models.DateField(verbose_name="التاريخ")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, verbose_name="التصنيف")
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")
    department = models.ForeignKey('hr.Department', on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="القسم")
    description = models.TextField(verbose_name="الوصف")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="المبلغ")
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="الضريبة")
    total = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="الإجمالي")
    is_taxable = models.BooleanField(default=False, verbose_name="خاضع للضريبة")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash',
                                      verbose_name="طريقة الدفع")
    status = models.CharField(max_length=20, choices=EXPENSE_STATUSES, default='draft',
                              verbose_name="الحالة")

    # مرفقات
    receipt_image = models.ImageField(upload_to='expenses/receipts/', null=True, blank=True,
                                      verbose_name="صورة الإيصال")

    # الاعتماد
    approved_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_expenses', verbose_name="اعتمده")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الاعتماد")
    rejection_reason = models.TextField(blank=True, verbose_name="سبب الرفض")

    # الربط المحاسبي
    journal_entry = models.ForeignKey('accounts.JournalEntry', on_delete=models.SET_NULL,
                                      null=True, blank=True, verbose_name="القيد")
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="المورد")

    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name = "مصروف"
        verbose_name_plural = "المصروفات"
        ordering = ['-date']

    def __str__(self):
        return f"{self.expense_number} - {self.description[:50]}"


class RecurringExpense(AuditMixin):
    """مصروفات دورية (إيجار، كهرباء، إنترنت، إلخ)"""
    FREQUENCY_CHOICES = [
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('annual', 'سنوي'),
    ]

    name = models.CharField(max_length=255, verbose_name="اسم المصروف")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, verbose_name="التصنيف")
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="المبلغ")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly',
                                 verbose_name="التكرار")
    start_date = models.DateField(verbose_name="تاريخ البداية")
    end_date = models.DateField(null=True, blank=True, verbose_name="تاريخ النهاية")
    next_due_date = models.DateField(verbose_name="تاريخ الاستحقاق القادم")
    auto_approve = models.BooleanField(default=False, verbose_name="اعتماد تلقائي")
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="المورد")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "مصروف دوري"
        verbose_name_plural = "المصروفات الدورية"

    def __str__(self):
        return self.name


class PaymentVoucher(AuditMixin):
    """سند صرف"""
    VOUCHER_STATUSES = [
        ('draft', 'مسودة'),
        ('approved', 'معتمد'),
        ('paid', 'مصروف'),
        ('cancelled', 'ملغي'),
    ]

    voucher_number = models.CharField(max_length=50, unique=True, verbose_name="رقم سند الصرف")
    date = models.DateField(verbose_name="التاريخ")
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")

    # المستفيد
    beneficiary_type = models.CharField(max_length=20, choices=[
        ('supplier', 'مورد'),
        ('employee', 'موظف'),
        ('customer', 'عميل'),
        ('other', 'أخرى'),
    ], verbose_name="نوع المستفيد")
    supplier = models.ForeignKey('partners.Supplier', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="المورد")
    employee = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="الموظف")
    customer = models.ForeignKey('sales.Customer', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="العميل")
    beneficiary_name = models.CharField(max_length=255, blank=True, verbose_name="اسم المستفيد")

    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="المبلغ")
    amount_in_words = models.CharField(max_length=500, blank=True, verbose_name="المبلغ كتابةً")
    description = models.TextField(verbose_name="البيان")

    payment_method = models.CharField(max_length=20, choices=[
        ('cash', 'نقدي'),
        ('bank', 'تحويل بنكي'),
        ('check', 'شيك'),
    ], default='cash', verbose_name="طريقة الدفع")

    # الحسابات
    debit_account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT,
                                      related_name='payment_voucher_debits', verbose_name="الحساب المدين")
    credit_account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT,
                                       related_name='payment_voucher_credits', verbose_name="الحساب الدائن")

    status = models.CharField(max_length=20, choices=VOUCHER_STATUSES, default='draft',
                              verbose_name="الحالة")
    approved_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_payment_vouchers', verbose_name="اعتمده")
    journal_entry = models.ForeignKey('accounts.JournalEntry', on_delete=models.SET_NULL,
                                      null=True, blank=True)
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name = "سند صرف"
        verbose_name_plural = "سندات الصرف"
        ordering = ['-date']

    def __str__(self):
        return f"{self.voucher_number} - {self.description[:50]}"


class ReceiptVoucher(AuditMixin):
    """سند قبض"""
    VOUCHER_STATUSES = [
        ('draft', 'مسودة'),
        ('approved', 'معتمد'),
        ('received', 'مقبوض'),
        ('cancelled', 'ملغي'),
    ]

    voucher_number = models.CharField(max_length=50, unique=True, verbose_name="رقم سند القبض")
    date = models.DateField(verbose_name="التاريخ")
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")

    # المُحصّل منه
    payer_type = models.CharField(max_length=20, choices=[
        ('customer', 'عميل'),
        ('other', 'أخرى'),
    ], verbose_name="نوع الدافع")
    customer = models.ForeignKey('sales.Customer', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="العميل")
    payer_name = models.CharField(max_length=255, blank=True, verbose_name="اسم الدافع")

    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="المبلغ")
    amount_in_words = models.CharField(max_length=500, blank=True, verbose_name="المبلغ كتابةً")
    description = models.TextField(verbose_name="البيان")

    payment_method = models.CharField(max_length=20, choices=[
        ('cash', 'نقدي'),
        ('bank', 'تحويل بنكي'),
        ('check', 'شيك'),
    ], default='cash', verbose_name="طريقة الدفع")

    # الحسابات
    debit_account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT,
                                      related_name='receipt_voucher_debits', verbose_name="الحساب المدين")
    credit_account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT,
                                       related_name='receipt_voucher_credits', verbose_name="الحساب الدائن")

    # ربط بفاتورة (اختياري)
    invoice = models.ForeignKey('sales.SalesInvoice', on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name="الفاتورة")

    status = models.CharField(max_length=20, choices=VOUCHER_STATUSES, default='draft',
                              verbose_name="الحالة")
    approved_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_receipt_vouchers', verbose_name="اعتمده")
    journal_entry = models.ForeignKey('accounts.JournalEntry', on_delete=models.SET_NULL,
                                      null=True, blank=True)
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name = "سند قبض"
        verbose_name_plural = "سندات القبض"
        ordering = ['-date']

    def __str__(self):
        return f"{self.voucher_number} - {self.description[:50]}"


class PettyCash(AuditMixin):
    """عهدة نثرية"""
    name = models.CharField(max_length=255, verbose_name="اسم العهدة")
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name="الفرع")
    custodian = models.ForeignKey('core.User', on_delete=models.PROTECT, verbose_name="أمين العهدة")
    limit_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="الحد الأقصى")
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                          verbose_name="الرصيد الحالي")
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT,
                                verbose_name="الحساب المحاسبي")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "عهدة نثرية"
        verbose_name_plural = "العهد النثرية"

    def __str__(self):
        return self.name


class PettyCashTransaction(AuditMixin):
    """حركة على العهدة النثرية"""
    petty_cash = models.ForeignKey(PettyCash, on_delete=models.CASCADE, related_name='transactions',
                                   verbose_name="العهدة")
    date = models.DateField(verbose_name="التاريخ")
    transaction_type = models.CharField(max_length=10, choices=[('in', 'إيداع'), ('out', 'صرف')],
                                        verbose_name="النوع")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="المبلغ")
    description = models.TextField(verbose_name="البيان")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="التصنيف")
    receipt_image = models.ImageField(upload_to='petty_cash/', null=True, blank=True,
                                      verbose_name="صورة الإيصال")
    journal_entry = models.ForeignKey('accounts.JournalEntry', on_delete=models.SET_NULL,
                                      null=True, blank=True)

    class Meta:
        verbose_name = "حركة عهدة"
        verbose_name_plural = "حركات العهدة"
        ordering = ['-date']

    def __str__(self):
        return f"{self.petty_cash.name} - {self.get_transaction_type_display()} - {self.amount}"
