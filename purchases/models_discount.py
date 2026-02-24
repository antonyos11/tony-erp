"""
نماذج إشعارات الخصم من الموردين - Supplier Discount Notes (Credit Notes)
=========================================================================
إشعار دائن (خصم مكتسب): يُستخدم لتسجيل الخصومات المُكتسبة من الموردين

أنواع الخصم المكتسب:
- خصم تعجيل دفع
- خصم كمية / تاريخ
- تسوية بضاعة تالفة
- فرق أسعار
"""

from django.db import models, transaction
from django.db.models import Sum, F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from decimal import Decimal
from partners.models import Supplier
from core.sequence_utils import next_sequence


class SupplierDiscountNote(models.Model):
    """
    إشعار خصم مكتسب (إشعار دائن) - Credit Note from Supplier
    يُستخدم لتسجيل الخصومات المُكتسبة من الموردين
    """
    
    DISCOUNT_REASONS = [
        ('early_payment', _('خصم تعجيل دفع')),
        ('quantity', _('خصم كمية / تاريخ')),
        ('damaged_goods', _('تسوية بضاعة تالفة')),
        ('price_diff', _('فرق أسعار')),
        ('other', _('سبب آخر')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('posted', _('مرحّل')),
        ('cancelled', _('ملغى')),
    ]
    
    # رقم الإشعار
    number = models.CharField(
        _('رقم الإشعار الدائن'),
        max_length=50,
        unique=True,
        blank=True
    )
    
    # رقم إشعار المورد الخارجي
    supplier_note_number = models.CharField(
        _('رقم إشعار المورد'),
        max_length=100,
        blank=True,
        help_text=_('رقم الإشعار الصادر من المورد')
    )
    
    # المورد
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='discount_notes',
        verbose_name=_('المورد')
    )
    
    # ربط بفاتورة شراء (اختياري)
    bill = models.ForeignKey(
        'PurchaseBill',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='discount_notes',
        verbose_name=_('فاتورة الشراء المرتبطة')
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
        default='early_payment'
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
        related_name='supplier_discount_notes',
        verbose_name=_('القيد المحاسبي')
    )
    
    # بيانات التدقيق
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_supplier_discount_notes',
        verbose_name=_('أنشأه')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    posted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_supplier_discount_notes',
        verbose_name=_('رحّله')
    )
    posted_at = models.DateTimeField(_('تاريخ الترحيل'), null=True, blank=True)
    
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_supplier_discount_notes',
        verbose_name=_('ألغاه')
    )
    cancelled_at = models.DateTimeField(_('تاريخ الإلغاء'), null=True, blank=True)
    cancellation_reason = models.TextField(_('سبب الإلغاء'), blank=True)
    
    class Meta:
        ordering = ['-date', '-id']
        verbose_name = _('إشعار خصم مكتسب')
        verbose_name_plural = _('إشعارات الخصم المكتسبة')
        permissions = [
            ('can_post_supplier_discount', _('يمكنه ترحيل إشعار خصم المورد')),
            ('can_cancel_supplier_discount', _('يمكنه إلغاء إشعار خصم المورد')),
        ]
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['supplier', '-date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.number} - {self.supplier.name} - {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            from django.db import IntegrityError
            import time
            
            now = timezone.now()
            prefix = f"DN-{now.strftime('%Y%m')}"  # DN = Debit Note (للمورد هو debit)
            
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    seq = next_sequence(f'SUPP_DISCOUNT_{now.strftime("%Y%m")}')
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
        if self.is_percentage and self.bill:
            return (self.bill.total * self.percentage_value) / Decimal('100')
        return self.amount
    
    @property
    def is_editable(self):
        """هل يمكن تعديل الإشعار؟"""
        return self.status == 'draft'
    
    def post(self, user=None):
        """ترحيل الإشعار وإنشاء القيد المحاسبي"""
        if self.status != 'draft':
            return None
        
        from accounting.services import post_supplier_discount_journal
        
        with transaction.atomic():
            je = post_supplier_discount_journal(self, user=user)
            if je and je.is_posted:
                self.status = 'posted'
                self.posted_by = user
                self.posted_at = timezone.now()
                self.journal_entry = je
                self.save(update_fields=['status', 'posted_by', 'posted_at', 'journal_entry'])
                
                # تحديث رصيد المورد إذا كانت مرتبطة بفاتورة
                if self.bill:
                    # خصم المبلغ من المستحق للمورد
                    self.bill.discount = F('discount') + self.calculated_amount
                    self.bill.save(update_fields=['discount'])
                    self.bill.refresh_from_db()
                
                return je
        return None
    
    def cancel(self, user=None, reason=''):
        """إلغاء الإشعار"""
        if self.status not in ['draft', 'posted']:
            return False
        
        with transaction.atomic():
            # إذا كان مرحّل، نلغي القيد أيضاً
            if self.status == 'posted' and self.journal_entry:
                from accounting.journal_service import JournalService
                JournalService.reverse(self.journal_entry, user=user)
                
                # إرجاع الخصم للفاتورة إذا كانت مرتبطة
                if self.bill:
                    self.bill.discount = F('discount') - self.calculated_amount
                    self.bill.save(update_fields=['discount'])
                    self.bill.refresh_from_db()
            
            self.status = 'cancelled'
            self.cancelled_by = user
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.save(update_fields=['status', 'cancelled_by', 'cancelled_at', 'cancellation_reason'])
            
            return True
    
    @classmethod
    def get_supplier_balance_impact(cls, supplier_id):
        """حساب إجمالي تأثير الخصومات على رصيد المورد"""
        total = cls.objects.filter(
            supplier_id=supplier_id,
            status='posted'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        return total
