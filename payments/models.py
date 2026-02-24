"""
نماذج نظام المدفوعات والقروض
"""
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from partners.models import Partner


class PaymentMethod(models.Model):
    """طرق الدفع"""
    PAYMENT_TYPES = [
        ('cash', 'نقدي'),
        ('bank_transfer', 'حوالة بنكية'),
        ('check', 'شيك'),
        ('credit_card', 'كارت ائتماني'),
        ('instapay', 'إنستا باي'),
        ('wallet', 'محفظة إلكترونية عامة'),
        # طرق إضافية شائعة
        ('vodafone_cash', 'فودافون كاش'),
        ('orange_cash', 'أورنج كاش'),
        ('etisalat_cash', 'اتصالات كاش'),
        ('stc_pay', 'STC Pay'),
        ('apple_pay', 'Apple Pay'),
        ('google_pay', 'Google Pay'),
        ('paypal', 'PayPal'),
        ('mada', 'مدى'),
        ('installment', 'قسط'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    name = models.CharField('اسم طريقة الدفع', max_length=100)
    type = models.CharField('نوع الدفع', max_length=20, choices=PAYMENT_TYPES)
    account_number = models.CharField('رقم الحساب', max_length=50, blank=True)
    bank_name = models.CharField('اسم البنك', max_length=100, blank=True)
    is_active = models.BooleanField('نشط', default=True)
    display_order = models.PositiveIntegerField('ترتيب العرض', default=100, help_text='رقم أصغر = يظهر أولاً')
    # ربط اختياري بحساب محاسبي لاستخدامه عند إنشاء قيود تلقائية للمدفوعات
    account = models.ForeignKey('accounting.Account', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='الحساب المحاسبي المرتبط', help_text='يُستخدم لإنشاء قيد استلام آلي (مدين نقدية/بنك) مقابل عميل عند تسجيل دفعة.')
    
    class Meta:
        verbose_name = 'طريقة دفع'
        verbose_name_plural = 'طرق الدفع'
    
    def __str__(self):
        return self.name


class Loan(models.Model):
    """القروض"""
    LOAN_TYPES = [
        ('personal', 'شخصي'),
        ('business', 'تجاري'),
        ('vehicle', 'سيارة'),
        ('property', 'عقار'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    LOAN_STATUS = [
        ('active', 'نشط'),
        ('completed', 'مكتمل'),
        ('defaulted', 'متعثر'),
        ('cancelled', 'ملغي'),
    ]
    
    loan_number = models.CharField('رقم القرض', max_length=20, unique=True)
    borrower = models.ForeignKey(Partner, on_delete=models.CASCADE, verbose_name='المقترض')
    loan_type = models.CharField('نوع القرض', max_length=20, choices=LOAN_TYPES)
    principal_amount = models.DecimalField('مبلغ القرض الأساسي', max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField('معدل الفائدة %', max_digits=5, decimal_places=2)
    duration_months = models.IntegerField('مدة القرض بالشهور')
    monthly_payment = models.DecimalField('القسط الشهري', max_digits=15, decimal_places=2)
    start_date = models.DateField('تاريخ بداية القرض')
    end_date = models.DateField('تاريخ نهاية القرض')
    status = models.CharField('حالة القرض', max_length=20, choices=LOAN_STATUS, default='active')
    notes = models.TextField('ملاحظات', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_loans', verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'قرض'
        verbose_name_plural = 'القروض'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.loan_number} - {self.borrower.name}"
    
    @property
    def total_amount(self):
        """إجمالي مبلغ القرض مع الفوائد"""
        return self.monthly_payment * self.duration_months
    
    @property
    def total_interest(self):
        """إجمالي الفوائد"""
        return self.total_amount - self.principal_amount
    
    @property
    def remaining_balance(self):
        """الرصيد المتبقي"""
        paid_installments = self.installments.filter(status='paid').aggregate(
            total=models.Sum('amount'))['total'] or Decimal('0')
        return self.total_amount - paid_installments


class LoanInstallment(models.Model):
    """أقساط القروض"""
    INSTALLMENT_STATUS = [
        ('pending', 'معلق'),
        ('paid', 'مدفوع'),
        ('overdue', 'متأخر'),
        ('partially_paid', 'مدفوع جزئياً'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='installments', verbose_name='القرض')
    installment_number = models.IntegerField('رقم القسط')
    due_date = models.DateField('تاريخ الاستحقاق')
    amount = models.DecimalField('مبلغ القسط', max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField('المبلغ المدفوع', max_digits=15, decimal_places=2, default=Decimal('0'))
    payment_date = models.DateField('تاريخ الدفع', null=True, blank=True)
    status = models.CharField('حالة القسط', max_length=20, choices=INSTALLMENT_STATUS, default='pending')
    late_fee = models.DecimalField('رسوم التأخير', max_digits=10, decimal_places=2, default=Decimal('0'))
    notes = models.TextField('ملاحظات', blank=True)
    
    class Meta:
        verbose_name = 'قسط'
        verbose_name_plural = 'الأقساط'
        ordering = ['due_date']
        unique_together = ['loan', 'installment_number']
    
    def __str__(self):
        return f"{self.loan.loan_number} - قسط {self.installment_number}"
    
    @property
    def is_overdue(self):
        """هل القسط متأخر؟"""
        return self.due_date < timezone.now().date() and self.status != 'paid'
    
    @property
    def remaining_amount(self):
        """المبلغ المتبقي"""
        return self.amount - self.paid_amount


class PaymentTransaction(models.Model):
    """معاملات الدفع"""
    TRANSACTION_TYPES = [
        ('payment', 'دفع'),
        ('refund', 'استرداد'),
        ('adjustment', 'تسوية'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    TRANSACTION_STATUS = [
        ('pending', 'معلق'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
        ('cancelled', 'ملغي'),
    ]
    
    transaction_number = models.CharField('رقم المعاملة', max_length=20, unique=True)
    transaction_type = models.CharField('نوع المعاملة', max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField('المبلغ', max_digits=15, decimal_places=2)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE, verbose_name='طريقة الدفع')
    reference_number = models.CharField('رقم المرجع', max_length=100, blank=True)
    description = models.TextField('الوصف', blank=True)
    status = models.CharField('حالة المعاملة', max_length=20, choices=TRANSACTION_STATUS, default='pending')
    processed_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='تم المعالجة بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    processed_at = models.DateTimeField('تاريخ المعالجة', null=True, blank=True)
    
    # ربط بالكيانات الأخرى (قسط، فاتورة، إلخ)
    installment = models.ForeignKey(LoanInstallment, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='القسط')
    
    class Meta:
        verbose_name = 'معاملة دفع'
        verbose_name_plural = 'معاملات الدفع'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_number} - {self.amount}"


class PaymentReminder(models.Model):
    """تذكيرات الدفع"""
    REMINDER_STATUS = [
        ('pending', 'معلق'),
        ('sent', 'تم الإرسال'),
        ('delivered', 'تم التسليم'),
        ('failed', 'فشل'),
    ]
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking
    
    installment = models.ForeignKey(LoanInstallment, on_delete=models.CASCADE, verbose_name='القسط')
    reminder_date = models.DateTimeField('تاريخ التذكير')
    message = models.TextField('نص الرسالة')
    status = models.CharField('حالة التذكير', max_length=20, choices=REMINDER_STATUS, default='pending')
    sent_at = models.DateTimeField('تاريخ الإرسال', null=True, blank=True)
    delivery_attempts = models.IntegerField('محاولات التسليم', default=0)
    
    class Meta:
        verbose_name = 'تذكير دفع'
        verbose_name_plural = 'تذكيرات الدفع'
        ordering = ['reminder_date']
    
    def __str__(self):
        return f"تذكير {self.installment} - {self.reminder_date}"