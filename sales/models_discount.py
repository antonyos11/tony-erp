"""
نماذج إشعارات الخصم للعملاء - Customer Discount Notes (Debit Notes)
====================================================================
إشعار مدين (خصم مسموح به): يُستخدم لمنح العميل خصم على حسابه

أنواع الخصم المسموح به:
- خصم وفاء عميل
- خصم تجاري خاص  
- تعويض تأخير
- خصم سداد مبكر
"""

from django.db import models, transaction
from django.db.models import Sum, F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from decimal import Decimal
from partners.models import Customer
from core.sequence_utils import next_sequence


class CustomerDiscountNote(models.Model):
    """
    إشعار خصم مسموح به (إشعار مدين) - Debit Note
    يُستخدم لتسجيل الخصومات المُعطاة للعملاء
    """
    
    DISCOUNT_REASONS = [
        ('loyalty', _('خصم وفاء عميل')),
        ('trade', _('خصم تجاري خاص')),
        ('delay_compensation', _('تعويض تأخير')),
        ('early_payment', _('خصم سداد مبكر')),
        ('other', _('سبب آخر')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('posted', _('مرحّل')),
        ('cancelled', _('ملغى')),
    ]
    
    # رقم الإشعار
    number = models.CharField(
        _('رقم الإشعار المدين'),
        max_length=50,
        unique=True,
        blank=True
    )
    
    # العميل
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='discount_notes',
        verbose_name=_('العميل')
    )
    
    # ربط بفاتورة (اختياري) - إما خصم عام أو على فاتورة محددة
    invoice = models.ForeignKey(
        'Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='discount_notes',
        verbose_name=_('الفاتورة المرتبطة')
    )
    
    # التاريخ
    date = models.DateField(_('التاريخ'), default=timezone.now)
    
    # قيمة الخصم
    amount = models.DecimalField(
        _('قيمة الخصم'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    
    # نوع القيمة: مبلغ ثابت أو نسبة
    is_percentage = models.BooleanField(
        _('نسبة مئوية'),
        default=False,
        help_text=_('إذا كان نعم، سيتم احتساب النسبة من الفاتورة المرتبطة')
    )
    percentage_value = models.DecimalField(
        _('النسبة المئوية'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0'),
        help_text=_('النسبة من 0 إلى 100')
    )
    
    # سبب الخصم
    reason = models.CharField(
        _('سبب الخصم'),
        max_length=30,
        choices=DISCOUNT_REASONS,
        default='loyalty'
    )
    
    # ملاحظات إضافية
    notes = models.TextField(_('ملاحظات إضافية'), blank=True)
    
    # الحالة
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    # القيد المحاسبي
    journal_entry = models.ForeignKey(
        'accounting.JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_discount_notes',
        verbose_name=_('القيد المحاسبي')
    )
    
    # بيانات التدقيق
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_customer_discount_notes',
        verbose_name=_('أنشأه')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    posted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_customer_discount_notes',
        verbose_name=_('رحّله')
    )
    posted_at = models.DateTimeField(_('تاريخ الترحيل'), null=True, blank=True)
    
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_customer_discount_notes',
        verbose_name=_('ألغاه')
    )
    cancelled_at = models.DateTimeField(_('تاريخ الإلغاء'), null=True, blank=True)
    cancellation_reason = models.TextField(_('سبب الإلغاء'), blank=True)
    
    class Meta:
        ordering = ['-date', '-id']
        verbose_name = _('إشعار خصم مسموح به')
        verbose_name_plural = _('إشعارات الخصم المسموح بها')
        permissions = [
            ('can_post_customer_discount', _('يمكنه ترحيل إشعار خصم العميل')),
            ('can_cancel_customer_discount', _('يمكنه إلغاء إشعار خصم العميل')),
        ]
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['customer', '-date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.customer.name} - {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from django.db import IntegrityError
            import time
            
            now = timezone.now()
            prefix = f"CN-{now.strftime('%Y%m')}"  # CN = Credit Note (للعميل هو credit)
            
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    seq = next_sequence(f'CUST_DISCOUNT_{now.strftime("%Y%m")}')
                    self.number = f"{prefix}-{str(seq).zfill(4)}"
                    super().save(*args, **kwargs)
                    return
                except IntegrityError as e:
                    if 'UNIQUE constraint failed' in str(e) or 'unique' in str(e).lower():
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    raise
            
            self.number = f"{prefix}-{int(now.timestamp())}"
        
        super().save(*args, **kwargs)
    
    @property
    def calculated_amount(self):
        """حساب قيمة الخصم الفعلية"""
        if self.is_percentage and self.invoice:
            return (self.invoice.total * self.percentage_value) / Decimal('100')
        return self.amount
    
    @property
    def is_editable(self):
        """هل يمكن تعديل الإشعار؟"""
        return self.status == 'draft'
    
    def post(self, user=None):
        """ترحيل الإشعار وإنشاء القيد المحاسبي"""
        if self.status != 'draft':
            return None
        
        from accounting.services import post_customer_discount_journal
        
        with transaction.atomic():
            je = post_customer_discount_journal(self, user=user)
            if je and je.is_posted:
                self.status = 'posted'
                self.posted_by = user
                self.posted_at = timezone.now()
                self.journal_entry = je
                self.save(update_fields=['status', 'posted_by', 'posted_at', 'journal_entry'])
                
                # تحديث رصيد العميل إذا كانت مرتبطة بفاتورة
                if self.invoice:
                    # خصم المبلغ من المستحق على الفاتورة
                    self.invoice.discount = F('discount') + self.calculated_amount
                    self.invoice.save(update_fields=['discount'])
                    self.invoice.refresh_from_db()
                
                return je
        return None
    
    def cancel(self, user=None, reason=''):
        """إلغاء الإشعار"""
        if self.status not in ['draft', 'posted']:
            return False
        
        with transaction.atomic():
            # إذا كان مرحّل، نلغي القيد أيضاً
            if self.status == 'posted' and self.journal_entry:
                # إنشاء قيد عكسي أو إلغاء القيد
                from accounting.journal_service import JournalService
                JournalService.reverse(self.journal_entry, user=user)
                
                # إرجاع الخصم للفاتورة إذا كانت مرتبطة
                if self.invoice:
                    self.invoice.discount = F('discount') - self.calculated_amount
                    self.invoice.save(update_fields=['discount'])
                    self.invoice.refresh_from_db()
            
            self.status = 'cancelled'
            self.cancelled_by = user
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.save(update_fields=['status', 'cancelled_by', 'cancelled_at', 'cancellation_reason'])
            
            return True
    
    @classmethod
    def get_customer_balance_impact(cls, customer_id):
        """حساب إجمالي تأثير الخصومات على رصيد العميل"""
        total = cls.objects.filter(
            customer_id=customer_id,
            status='posted'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        return total
