from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
from partners.models import Customer

User = get_user_model()


class InstallmentPlan(models.Model):
    """خطة التقسيط"""
    
    STATUS_CHOICES = [
        ('active', _('نشط')),
        ('completed', _('مكتمل')),
        ('defaulted', _('متعثر')),
        ('cancelled', _('ملغي')),
    ]
    
    order = models.ForeignKey(
        'pos.POSOrder', 
        on_delete=models.CASCADE, 
        related_name='installment_plans',
        verbose_name=_('الطلب')
    )
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='installment_plans',
        verbose_name=_('العميل')
    )
    
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name=_('المبلغ الإجمالي')
    )
    down_payment = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_('الدفعة المقدمة')
    )
    remaining_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name=_('المبلغ المتبقي للتقسيط')
    )
    
    number_of_installments = models.PositiveIntegerField(
        verbose_name=_('عدد الأقساط')
    )
    installment_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name=_('قيمة القسط')
    )
    
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_('نسبة الفائدة %')
    )
    
    start_date = models.DateField(
        verbose_name=_('تاريخ البداية')
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='active',
        verbose_name=_('الحالة')
    )
    
    # معلومات إضافية عن العميل
    customer_phone = models.CharField(
        max_length=20, 
        verbose_name=_('رقم الموبايل')
    )
    customer_phone2 = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('رقم موبايل إضافي')
    )
    customer_address = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_('العنوان')
    )
    customer_national_id = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('الرقم القومي')
    )
    guarantor_name = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name=_('اسم الضامن')
    )
    guarantor_phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('رقم موبايل الضامن')
    )
    guarantor_national_id = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('الرقم القومي للضامن')
    )
    
    notes = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_('ملاحظات')
    )
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_installment_plans',
        verbose_name=_('أنشأ بواسطة')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('تاريخ الإنشاء')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('تاريخ التحديث')
    )
    
    class Meta:
        verbose_name = _('خطة تقسيط')
        verbose_name_plural = _('خطط التقسيط')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"تقسيط #{self.id} - {self.customer.name}"
    
    @property
    def paid_amount(self):
        """المبلغ المدفوع"""
        return self.installments.filter(is_paid=True).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
    
    @property
    def remaining_to_pay(self):
        """المبلغ المتبقي للسداد"""
        return self.remaining_amount - self.paid_amount
    
    @property
    def paid_installments_count(self):
        """عدد الأقساط المدفوعة"""
        return self.installments.filter(is_paid=True).count()
    
    @property
    def overdue_installments(self):
        """الأقساط المتأخرة"""
        return self.installments.filter(
            is_paid=False, 
            due_date__lt=timezone.now().date()
        )
    
    @property
    def next_installment(self):
        """القسط التالي"""
        return self.installments.filter(is_paid=False).order_by('due_date').first()
    
    def generate_installments(self):
        """إنشاء الأقساط"""
        from dateutil.relativedelta import relativedelta
        
        # حذف الأقساط القديمة إن وجدت
        self.installments.all().delete()
        
        current_date = self.start_date
        for i in range(self.number_of_installments):
            Installment.objects.create(
                plan=self,
                installment_number=i + 1,
                amount=self.installment_amount,
                due_date=current_date
            )
            current_date = current_date + relativedelta(months=1)
    
    def check_status(self):
        """تحديث حالة الخطة"""
        if self.paid_installments_count >= self.number_of_installments:
            self.status = 'completed'
        elif self.overdue_installments.count() >= 3:
            self.status = 'defaulted'
        self.save(update_fields=['status'])


class Installment(models.Model):
    """القسط الفردي"""
    
    plan = models.ForeignKey(
        InstallmentPlan, 
        on_delete=models.CASCADE, 
        related_name='installments',
        verbose_name=_('خطة التقسيط')
    )
    
    installment_number = models.PositiveIntegerField(
        verbose_name=_('رقم القسط')
    )
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name=_('قيمة القسط')
    )
    due_date = models.DateField(
        verbose_name=_('تاريخ الاستحقاق')
    )
    
    is_paid = models.BooleanField(
        default=False,
        verbose_name=_('مدفوع')
    )
    paid_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name=_('تاريخ الدفع')
    )
    paid_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name=_('المبلغ المدفوع')
    )
    
    late_fee = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name=_('غرامة التأخير')
    )
    
    payment_method = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('طريقة الدفع')
    )
    receipt_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('رقم الإيصال')
    )
    
    paid_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='paid_installments',
        verbose_name=_('استلم بواسطة')
    )
    
    notes = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_('ملاحظات')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('تاريخ الإنشاء')
    )
    
    class Meta:
        verbose_name = _('قسط')
        verbose_name_plural = _('الأقساط')
        ordering = ['due_date']
        unique_together = ['plan', 'installment_number']
    
    def __str__(self):
        return f"قسط {self.installment_number} - {self.plan}"
    
    @property
    def is_overdue(self):
        """هل القسط متأخر؟"""
        return not self.is_paid and self.due_date < timezone.now().date()
    
    @property
    def days_overdue(self):
        """عدد أيام التأخير"""
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0
    
    def mark_as_paid(self, user=None, amount=None, payment_method=None, receipt_number=None):
        """تسجيل دفع القسط"""
        self.is_paid = True
        self.paid_date = timezone.now().date()
        self.paid_amount = amount or self.amount
        self.paid_by = user
        self.payment_method = payment_method
        self.receipt_number = receipt_number
        self.save()
        
        # تحديث حالة الخطة
        self.plan.check_status()
