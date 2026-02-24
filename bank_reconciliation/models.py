"""
نماذج مطابقة البنوك
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class BankStatement(models.Model):
    """كشف حساب بنكي مستورد"""
    STATUS_CHOICES = [
        ('pending', 'معلق'),
        ('in_progress', 'قيد المطابقة'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغى'),
    ]
    
    bank_account = models.ForeignKey('accounting.Bank', on_delete=models.PROTECT,
                                    related_name='statements', verbose_name='الحساب البنكي')
    statement_date = models.DateField('تاريخ الكشف')
    start_date = models.DateField('من تاريخ')
    end_date = models.DateField('إلى تاريخ')
    
    opening_balance = models.DecimalField('الرصيد الافتتاحي', max_digits=15, decimal_places=2)
    closing_balance = models.DecimalField('الرصيد الختامي', max_digits=15, decimal_places=2)
    
    file = models.FileField('ملف الكشف', upload_to='bank_statements/', blank=True)
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    imported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                   related_name='imported_statements', verbose_name='مستورد بواسطة')
    imported_at = models.DateTimeField('تاريخ الاستيراد', auto_now_add=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    class Meta:
        verbose_name = 'كشف حساب بنكي'
        verbose_name_plural = 'كشوف الحسابات البنكية'
        ordering = ['-statement_date']
    
    def __str__(self):
        return f"{self.bank_account} - {self.statement_date}"
    
    def get_matched_count(self):
        return self.transactions.filter(is_matched=True).count()
    
    def get_unmatched_count(self):
        return self.transactions.filter(is_matched=False).count()


class BankStatementLine(models.Model):
    """سطر في كشف الحساب البنكي"""
    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE,
                                 related_name='transactions', verbose_name='الكشف')
    
    transaction_date = models.DateField('تاريخ العملية')
    value_date = models.DateField('تاريخ القيمة', null=True, blank=True)
    reference = models.CharField('المرجع', max_length=100, blank=True)
    description = models.TextField('الوصف')
    
    debit = models.DecimalField('مدين', max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField('دائن', max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField('الرصيد', max_digits=15, decimal_places=2, null=True, blank=True)
    
    is_matched = models.BooleanField('مطابق', default=False)
    matched_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='matched_bank_lines',
                                     verbose_name='القيد المطابق')
    matched_at = models.DateTimeField('تاريخ المطابقة', null=True, blank=True)
    matched_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='matched_bank_lines', verbose_name='طابق بواسطة')
    
    class Meta:
        verbose_name = 'سطر كشف بنكي'
        verbose_name_plural = 'سطور كشوف البنك'
        ordering = ['transaction_date', 'id']
    
    def __str__(self):
        return f"{self.transaction_date} - {self.description[:50]}"
    
    @property
    def amount(self):
        return self.credit - self.debit


class Reconciliation(models.Model):
    """جلسة مطابقة"""
    STATUS_CHOICES = [
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتملة'),
        ('approved', 'معتمدة'),
    ]
    
    bank_account = models.ForeignKey('accounting.Bank', on_delete=models.PROTECT,
                                    related_name='reconciliations', verbose_name='الحساب البنكي')
    reconciliation_date = models.DateField('تاريخ المطابقة')
    
    book_balance = models.DecimalField('رصيد الدفاتر', max_digits=15, decimal_places=2)
    bank_balance = models.DecimalField('رصيد البنك', max_digits=15, decimal_places=2)
    
    adjusted_book_balance = models.DecimalField('رصيد الدفاتر المعدل', max_digits=15, decimal_places=2, null=True)
    adjusted_bank_balance = models.DecimalField('رصيد البنك المعدل', max_digits=15, decimal_places=2, null=True)
    
    difference = models.DecimalField('الفرق', max_digits=15, decimal_places=2, default=0)
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='in_progress')
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_reconciliations',
                                  verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_reconciliations', verbose_name='اعتمد بواسطة')
    approved_at = models.DateTimeField('تاريخ الاعتماد', null=True, blank=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    class Meta:
        verbose_name = 'مطابقة بنكية'
        verbose_name_plural = 'المطابقات البنكية'
        ordering = ['-reconciliation_date']
    
    def __str__(self):
        return f"{self.bank_account} - {self.reconciliation_date}"


class ReconciliationItem(models.Model):
    """بند مطابقة"""
    TYPE_CHOICES = [
        ('outstanding_check', 'شيك صادر لم يُصرف'),
        ('deposit_in_transit', 'إيداع في الطريق'),
        ('bank_charge', 'عمولة بنكية'),
        ('bank_interest', 'فوائد بنكية'),
        ('error_correction', 'تصحيح خطأ'),
        ('other', 'أخرى'),
    ]
    
    reconciliation = models.ForeignKey(Reconciliation, on_delete=models.CASCADE,
                                      related_name='items', verbose_name='المطابقة')
    item_type = models.CharField('النوع', max_length=30, choices=TYPE_CHOICES)
    description = models.CharField('الوصف', max_length=300)
    reference = models.CharField('المرجع', max_length=100, blank=True)
    date = models.DateField('التاريخ')
    amount = models.DecimalField('المبلغ', max_digits=15, decimal_places=2)
    
    affects_book = models.BooleanField('يؤثر على الدفاتر', default=False)
    affects_bank = models.BooleanField('يؤثر على البنك', default=True)
    
    adjustment_entry = models.ForeignKey('accounting.JournalEntry', on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='reconciliation_adjustments',
                                        verbose_name='قيد التسوية')
    
    class Meta:
        verbose_name = 'بند مطابقة'
        verbose_name_plural = 'بنود المطابقة'
    
    def __str__(self):
        return f"{self.get_item_type_display()} - {self.amount}"
