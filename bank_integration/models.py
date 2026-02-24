"""
نماذج التكامل البنكي
Bank Integration Models
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class BankAccount(models.Model):
    """حساب بنكي متكامل"""
    
    STATUS_CHOICES = [
        ('active', _('نشط')),
        ('inactive', _('غير نشط')),
        ('suspended', _('معلق')),
    ]
    
    ACCOUNT_TYPE_CHOICES = [
        ('checking', _('حساب جاري')),
        ('savings', _('حساب توفير')),
        ('business', _('حساب تجاري')),
        ('investment', _('حساب استثماري')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_name = models.CharField(_('اسم البنك'), max_length=200)
    account_number = models.CharField(_('رقم الحساب'), max_length=50, unique=True)
    account_holder = models.CharField(_('صاحب الحساب'), max_length=200)
    account_type = models.CharField(_('نوع الحساب'), max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    currency = models.CharField(_('العملة'), max_length=3, default='EGP')
    current_balance = models.DecimalField(_('الرصيد الحالي'), max_digits=15, decimal_places=2, default=0)
    iban = models.CharField(_('IBAN'), max_length=50, unique=True)
    swift_code = models.CharField(_('SWIFT Code'), max_length=20, blank=True)
    bank_code = models.CharField(_('رمز البنك'), max_length=10, blank=True)
    branch_code = models.CharField(_('رمز الفرع'), max_length=10, blank=True)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='active')
    
    # بيانات الاتصال
    api_key = models.CharField(_('مفتاح API'), max_length=255, blank=True)
    api_secret = models.CharField(_('سر API'), max_length=255, blank=True)
    webhook_url = models.URLField(_('URL Webhook'), blank=True)
    
    # معلومات التكامل
    last_sync = models.DateTimeField(_('آخر مزامنة'), null=True, blank=True)
    sync_enabled = models.BooleanField(_('تفعيل المزامنة'), default=True)
    auto_reconcile = models.BooleanField(_('مطابقة تلقائية'), default=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('حساب بنكي')
        verbose_name_plural = _('الحسابات البنكية')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"
    
    def sync_transactions(self):
        """مزامنة العمليات من البنك"""
        from .services import bank_sync_service
        return bank_sync_service.sync_account_transactions(self)
    
    def reconcile_transactions(self):
        """مطابقة العمليات تلقائياً"""
        from .services import reconciliation_service
        return reconciliation_service.auto_reconcile(self)


class BankTransaction(models.Model):
    """عملية بنكية مسجلة"""
    
    TYPE_CHOICES = [
        ('debit', _('خصم')),
        ('credit', _('إيداع')),
        ('transfer', _('تحويل')),
        ('fee', _('رسوم')),
        ('interest', _('فائدة')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('completed', _('مكتملة')),
        ('failed', _('فشلت')),
        ('reconciled', _('متطابقة')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_date = models.DateField(_('تاريخ العملية'))
    value_date = models.DateField(_('تاريخ القيمة'), null=True, blank=True)
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    transaction_type = models.CharField(_('نوع العملية'), max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(_('الوصف'))
    reference_number = models.CharField(_('رقم المرجع'), max_length=100, unique=True)
    bank_reference = models.CharField(_('مرجع البنك'), max_length=100, blank=True)
    
    counterparty_name = models.CharField(_('اسم الطرف الآخر'), max_length=200, blank=True)
    counterparty_account = models.CharField(_('حساب الطرف الآخر'), max_length=50, blank=True)
    
    # تفاصيل المطابقة
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    matched_invoice = models.ForeignKey('sales.Invoice', on_delete=models.SET_NULL, 
                                       null=True, blank=True, related_name='bank_transactions')
    matched_payment = models.ForeignKey('payments.PaymentTransaction', on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='bank_transaction')
    matching_score = models.DecimalField(_('درجة المطابقة'), max_digits=5, decimal_places=2, default=0)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الاستقبال'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('عملية بنكية')
        verbose_name_plural = _('العمليات البنكية')
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['account', 'transaction_date']),
            models.Index(fields=['status']),
            models.Index(fields=['reference_number']),
        ]
        unique_together = ['account', 'reference_number']
    
    def __str__(self):
        return f"{self.account} - {self.amount} - {self.transaction_date}"
    
    def mark_reconciled(self):
        """وضع علامة على العملية كمتطابقة"""
        self.status = 'reconciled'
        self.save()


class BankReconciliation(models.Model):
    """سجل المطابقة البنكية"""
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('in_progress', _('قيد المطابقة')),
        ('completed', _('مكتملة')),
        ('rejected', _('مرفوضة')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='reconciliations')
    statement_date = models.DateField(_('تاريخ كشف الحساب'))
    statement_balance = models.DecimalField(_('رصيد كشف الحساب'), max_digits=15, decimal_places=2)
    system_balance = models.DecimalField(_('رصيد النظام'), max_digits=15, decimal_places=2)
    difference = models.DecimalField(_('الفرق'), max_digits=15, decimal_places=2, default=0)
    
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='draft')
    reconciled_transactions = models.ManyToManyField(BankTransaction, related_name='reconciliations', blank=True)
    unreconciled_transactions = models.ManyToManyField(BankTransaction, related_name='unreconciled_in', blank=True)
    
    reconciled_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    reconciled_at = models.DateTimeField(_('تاريخ المطابقة'), null=True, blank=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('مطابقة بنكية')
        verbose_name_plural = _('المطابقات البنكية')
        ordering = ['-statement_date']
        indexes = [
            models.Index(fields=['account', 'statement_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"المطابقة - {self.account} - {self.statement_date}"
    
    def calculate_difference(self):
        """حساب الفرق"""
        self.difference = self.statement_balance - self.system_balance
        self.save()
    
    def get_variance_ratio(self):
        """نسبة التباين"""
        if self.system_balance == 0:
            return 0
        return abs(self.difference / self.system_balance) * 100


class BankTransactionMapping(models.Model):
    """ربط بين عملية بنكية وقيد محاسبي"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_transaction = models.OneToOneField(BankTransaction, on_delete=models.CASCADE, related_name='mapping')
    journal_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.CASCADE, related_name='bank_mappings')
    matching_confidence = models.DecimalField(_('درجة الثقة'), max_digits=5, decimal_places=2)
    auto_matched = models.BooleanField(_('مطابقة تلقائية'), default=False)
    created_at = models.DateTimeField(_('تاريخ الربط'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('ربط عملية بنكية')
        verbose_name_plural = _('روابط العمليات البنكية')
    
    def __str__(self):
        return f"ربط - {self.bank_transaction.reference_number}"


class BankFee(models.Model):
    """رسوم بنكية"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='fees')
    fee_type = models.CharField(_('نوع الرسم'), max_length=100)
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=2)
    fee_date = models.DateField(_('تاريخ الرسم'))
    frequency = models.CharField(_('التكرار'), max_length=20, 
                                choices=[('monthly', _('شهري')), ('quarterly', _('ربع سنوي')), 
                                        ('yearly', _('سنوي')), ('per_transaction', _('لكل عملية'))])
    description = models.TextField(_('الوصف'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('رسم بنكي')
        verbose_name_plural = _('الرسوم البنكية')
        ordering = ['-fee_date']
    
    def __str__(self):
        return f"{self.account} - {self.fee_type} - {self.amount}"
