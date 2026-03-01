"""
نماذج تطبيق الخزينة والبنوك — RITA ERP
"""
from django.db import models
from apps.core.models import AuditMixin


class BankAccount(AuditMixin):
    """حساب بنكي"""
    name = models.CharField(max_length=255, verbose_name="اسم البنك")
    account_number = models.CharField(max_length=50, verbose_name="رقم الحساب")
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.PROTECT,
        related_name='bank_accounts', verbose_name="الفرع",
    )
    account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        related_name='bank_account_links', verbose_name="الحساب المحاسبي",
    )
    current_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="الرصيد الحالي",
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "حساب بنكي"
        verbose_name_plural = "الحسابات البنكية"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} — {self.account_number}"


class CashBox(AuditMixin):
    """خزنة نقدية"""
    name = models.CharField(max_length=255, verbose_name="اسم الخزنة")
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.PROTECT,
        related_name='cash_boxes', verbose_name="الفرع",
    )
    account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT,
        related_name='cash_box_links', verbose_name="الحساب المحاسبي",
    )
    current_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="الرصيد الحالي",
    )
    responsible = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cash_boxes', verbose_name="المسؤول",
    )

    class Meta:
        verbose_name = "خزنة"
        verbose_name_plural = "الخزائن"
        ordering = ['name']

    def __str__(self):
        return self.name


class Check(AuditMixin):
    """شيك (وارد أو صادر)"""
    CHECK_TYPES = [
        ('incoming', 'وارد'),
        ('outgoing', 'صادر'),
    ]
    CHECK_STATUSES = [
        ('pending',   'في الانتظار'),
        ('deposited', 'مودع'),
        ('cleared',   'تم التحصيل'),
        ('bounced',   'مرتجع'),
        ('cancelled', 'ملغي'),
    ]

    check_number = models.CharField(max_length=50, verbose_name="رقم الشيك")
    check_type = models.CharField(max_length=10, choices=CHECK_TYPES, verbose_name="النوع")
    status = models.CharField(
        max_length=20, choices=CHECK_STATUSES, default='pending', verbose_name="الحالة",
    )
    bank = models.ForeignKey(
        BankAccount, on_delete=models.PROTECT, null=True, blank=True,
        related_name='checks', verbose_name="البنك",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="المبلغ")
    issue_date = models.DateField(verbose_name="تاريخ الإصدار")
    due_date = models.DateField(verbose_name="تاريخ الاستحقاق")
    partner_name = models.CharField(max_length=255, verbose_name="اسم الطرف")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    journal_entry = models.ForeignKey(
        'accounts.JournalEntry', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='checks',
    )

    class Meta:
        verbose_name = "شيك"
        verbose_name_plural = "الشيكات"
        ordering = ['-due_date']

    def __str__(self):
        return f"شيك {self.check_number} — {self.partner_name} ({self.amount})"


class MoneyTransfer(AuditMixin):
    """تحويل مالي بين بنوك أو خزائن"""
    ACCOUNT_TYPE_CHOICES = [
        ('cash', 'خزنة'),
        ('bank', 'بنك'),
    ]

    from_account_type = models.CharField(
        max_length=20, choices=ACCOUNT_TYPE_CHOICES, verbose_name="نوع المصدر",
    )
    from_cash = models.ForeignKey(
        CashBox, on_delete=models.PROTECT, null=True, blank=True,
        related_name='transfers_out', verbose_name="الخزنة المصدر",
    )
    from_bank = models.ForeignKey(
        BankAccount, on_delete=models.PROTECT, null=True, blank=True,
        related_name='transfers_out', verbose_name="البنك المصدر",
    )
    to_account_type = models.CharField(
        max_length=20, choices=ACCOUNT_TYPE_CHOICES, verbose_name="نوع الوجهة",
    )
    to_cash = models.ForeignKey(
        CashBox, on_delete=models.PROTECT, null=True, blank=True,
        related_name='transfers_in', verbose_name="الخزنة الوجهة",
    )
    to_bank = models.ForeignKey(
        BankAccount, on_delete=models.PROTECT, null=True, blank=True,
        related_name='transfers_in', verbose_name="البنك الوجهة",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="المبلغ")
    date = models.DateTimeField(verbose_name="التاريخ")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    journal_entry = models.ForeignKey(
        'accounts.JournalEntry', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='money_transfers',
    )

    class Meta:
        verbose_name = "تحويل مالي"
        verbose_name_plural = "التحويلات المالية"
        ordering = ['-date']

    def __str__(self):
        return f"تحويل {self.amount} بتاريخ {self.date:%Y-%m-%d}"
