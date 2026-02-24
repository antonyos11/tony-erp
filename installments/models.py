"""
نظام التقسيط الذكي - Smart Installments System
نظام متكامل لإدارة التقسيط للمبيعات مع دعم الضامنين والتنبيهات
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import timedelta
import uuid


class InstallmentPlan(models.Model):
    """خطط التقسيط المتاحة"""
    id = models.AutoField(primary_key=True)
    
    name = models.CharField(_('اسم الخطة'), max_length=100)
    description = models.TextField(_('الوصف'), blank=True)
    
    # مدة التقسيط
    duration_months = models.PositiveIntegerField(
        _('المدة بالأشهر'),
        validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    
    # نسبة الفائدة السنوية
    annual_interest_rate = models.DecimalField(
        _('نسبة الفائدة السنوية %'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # المصاريف الإدارية
    admin_fee_type = models.CharField(
        _('نوع المصاريف الإدارية'),
        max_length=20,
        choices=[
            ('fixed', 'مبلغ ثابت'),
            ('percentage', 'نسبة مئوية'),
        ],
        default='percentage'
    )
    admin_fee_value = models.DecimalField(
        _('قيمة المصاريف الإدارية'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # الحد الأدنى للمقدم
    min_down_payment_percentage = models.DecimalField(
        _('الحد الأدنى للمقدم %'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    
    # الحد الأدنى والأقصى للمبلغ
    min_amount = models.DecimalField(
        _('الحد الأدنى للمبلغ'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('500.00')
    )
    max_amount = models.DecimalField(
        _('الحد الأقصى للمبلغ'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # رسوم التأخير
    late_fee_type = models.CharField(
        _('نوع رسوم التأخير'),
        max_length=20,
        choices=[
            ('fixed', 'مبلغ ثابت'),
            ('percentage', 'نسبة من القسط'),
            ('daily', 'رسم يومي'),
        ],
        default='percentage'
    )
    late_fee_value = models.DecimalField(
        _('قيمة رسوم التأخير'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('5.00')
    )
    grace_period_days = models.PositiveIntegerField(
        _('فترة السماح (أيام)'),
        default=3
    )
    
    # هل يتطلب ضامن
    requires_guarantor = models.BooleanField(
        _('يتطلب ضامن'),
        default=False
    )
    min_guarantors = models.PositiveIntegerField(
        _('الحد الأدنى للضامنين'),
        default=1
    )
    
    # الحالة
    is_active = models.BooleanField(_('نشط'), default=True)
    
    # الطوابع الزمنية
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_smart_installment_plans',
        verbose_name=_('أنشئ بواسطة')
    )
    
    class Meta:
        verbose_name = _('خطة تقسيط')
        verbose_name_plural = _('خطط التقسيط')
        ordering = ['duration_months']
    
    def __str__(self):
        return f"{self.name} ({self.duration_months} شهر)"
    
    def calculate_monthly_payment(self, principal_amount: Decimal, down_payment: Decimal = Decimal('0')) -> dict:
        """حساب القسط الشهري والتفاصيل"""
        financed_amount = principal_amount - down_payment
        
        # حساب المصاريف الإدارية
        if self.admin_fee_type == 'fixed':
            admin_fee = self.admin_fee_value
        else:
            admin_fee = financed_amount * (self.admin_fee_value / Decimal('100'))
        
        # حساب الفائدة
        if self.annual_interest_rate > 0:
            monthly_rate = self.annual_interest_rate / Decimal('12') / Decimal('100')
            # صيغة القسط الشهري مع الفائدة المركبة
            n = self.duration_months
            if monthly_rate > 0:
                monthly_payment = financed_amount * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
            else:
                monthly_payment = financed_amount / n
            total_interest = (monthly_payment * n) - financed_amount
        else:
            monthly_payment = financed_amount / self.duration_months
            total_interest = Decimal('0')
        
        total_amount = financed_amount + total_interest + admin_fee
        
        return {
            'principal_amount': principal_amount,
            'down_payment': down_payment,
            'financed_amount': financed_amount,
            'admin_fee': admin_fee.quantize(Decimal('0.01')),
            'total_interest': total_interest.quantize(Decimal('0.01')),
            'monthly_payment': monthly_payment.quantize(Decimal('0.01')),
            'total_amount': total_amount.quantize(Decimal('0.01')),
            'duration_months': self.duration_months,
        }


class InstallmentContract(models.Model):
    """عقد التقسيط"""
    id = models.AutoField(primary_key=True)
    
    CONTRACT_STATUS = [
        ('draft', 'مسودة'),
        ('pending_approval', 'في انتظار الموافقة'),
        ('approved', 'معتمد'),
        ('active', 'نشط'),
        ('completed', 'مكتمل'),
        ('defaulted', 'متعثر'),
        ('cancelled', 'ملغي'),
        ('legal', 'تحت إجراء قانوني'),
    ]
    
    # رقم العقد الفريد
    contract_number = models.CharField(
        _('رقم العقد'),
        max_length=50,
        unique=True,
        editable=False
    )
    
    # UUID للوصول العام
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # العميل
    customer = models.ForeignKey(
        'partners.Customer',
        on_delete=models.PROTECT,
        related_name='installment_contracts',
        verbose_name=_('العميل')
    )
    
    # خطة التقسيط
    plan = models.ForeignKey(
        InstallmentPlan,
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name=_('خطة التقسيط')
    )
    
    # الفاتورة المرتبطة
    invoice = models.OneToOneField(
        'sales.Invoice',
        on_delete=models.PROTECT,
        related_name='installment_contract',
        verbose_name=_('الفاتورة'),
        null=True,
        blank=True
    )
    
    # الفرع/المعرض
    showroom = models.ForeignKey(
        'showrooms.Showroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installment_contracts',
        verbose_name=_('الفرع/المعرض')
    )
    
    # المبالغ
    principal_amount = models.DecimalField(
        _('المبلغ الأصلي'),
        max_digits=15,
        decimal_places=2
    )
    down_payment = models.DecimalField(
        _('المقدم'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    financed_amount = models.DecimalField(
        _('المبلغ الممول'),
        max_digits=15,
        decimal_places=2
    )
    admin_fee = models.DecimalField(
        _('المصاريف الإدارية'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    total_interest = models.DecimalField(
        _('إجمالي الفوائد'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    monthly_payment = models.DecimalField(
        _('القسط الشهري'),
        max_digits=15,
        decimal_places=2
    )
    total_amount = models.DecimalField(
        _('الإجمالي النهائي'),
        max_digits=15,
        decimal_places=2
    )
    
    # التواريخ
    contract_date = models.DateField(_('تاريخ العقد'), default=timezone.localdate)
    start_date = models.DateField(_('تاريخ بداية الأقساط'))
    end_date = models.DateField(_('تاريخ نهاية الأقساط'))
    
    # حالة العقد
    status = models.CharField(
        _('حالة العقد'),
        max_length=20,
        choices=CONTRACT_STATUS,
        default='draft'
    )
    
    # بيانات إضافية
    national_id = models.CharField(_('رقم الهوية'), max_length=20, blank=True)
    national_id_image = models.ImageField(
        _('صورة الهوية'),
        upload_to='installments/ids/',
        blank=True
    )
    address = models.TextField(_('العنوان'), blank=True)
    phone = models.CharField(_('رقم الهاتف'), max_length=20, blank=True)
    alternative_phone = models.CharField(_('رقم هاتف بديل'), max_length=20, blank=True)
    work_address = models.TextField(_('عنوان العمل'), blank=True)
    work_phone = models.CharField(_('هاتف العمل'), max_length=20, blank=True)
    
    # ملاحظات
    notes = models.TextField(_('ملاحظات'), blank=True)
    internal_notes = models.TextField(_('ملاحظات داخلية'), blank=True)
    
    # التوقيعات
    customer_signature = models.ImageField(
        _('توقيع العميل'),
        upload_to='installments/signatures/',
        blank=True
    )
    signed_contract = models.FileField(
        _('العقد الموقع'),
        upload_to='installments/contracts/',
        blank=True
    )
    
    # الطوابع الزمنية
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_installment_contracts',
        verbose_name=_('أنشئ بواسطة')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_installment_contracts',
        verbose_name=_('اعتمد بواسطة')
    )
    
    class Meta:
        verbose_name = _('عقد تقسيط')
        verbose_name_plural = _('عقود التقسيط')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contract_number']),
            models.Index(fields=['status']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.contract_number} - {self.customer}"
    
    def save(self, *args, **kwargs):
        if not self.contract_number:
            from core.sequence_utils import next_sequence
            now = timezone.now()
            prefix = f"INST-{now.strftime('%Y%m')}"
            seq = next_sequence(f'INSTALLMENT_{now.strftime("%Y%m")}')
            self.contract_number = f"{prefix}-{str(seq).zfill(5)}"
        
        # حساب المبلغ الممول
        self.financed_amount = self.principal_amount - self.down_payment
        
        # حساب تاريخ النهاية
        if self.start_date and self.plan:
            self.end_date = self.start_date + timedelta(days=self.plan.duration_months * 30)
        
        super().save(*args, **kwargs)
    
    def generate_installments(self):
        """توليد جدول الأقساط"""
        if self.installments.exists():
            raise ValueError("الأقساط موجودة بالفعل")
        
        installments = []
        current_date = self.start_date
        
        for i in range(1, self.plan.duration_months + 1):
            installment = Installment(
                contract=self,
                installment_number=i,
                due_date=current_date,
                amount=self.monthly_payment,
                status='pending'
            )
            installments.append(installment)
            
            # الانتقال للشهر التالي
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                try:
                    current_date = current_date.replace(month=current_date.month + 1)
                except ValueError:
                    # في حالة لا يوجد نفس اليوم في الشهر التالي
                    current_date = current_date.replace(month=current_date.month + 1, day=28)
        
        Installment.objects.bulk_create(installments)
        return installments
    
    @property
    def paid_amount(self):
        """إجمالي المبلغ المدفوع"""
        return self.installments.filter(
            status='paid'
        ).aggregate(total=models.Sum('paid_amount'))['total'] or Decimal('0')
    
    @property
    def remaining_amount(self):
        """المبلغ المتبقي"""
        return self.total_amount - self.down_payment - self.paid_amount
    
    @property
    def overdue_amount(self):
        """المبلغ المتأخر"""
        return self.installments.filter(
            status='overdue'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
    
    @property
    def overdue_count(self):
        """عدد الأقساط المتأخرة"""
        return self.installments.filter(status='overdue').count()
    
    @property
    def next_installment(self):
        """القسط القادم"""
        return self.installments.filter(
            status__in=['pending', 'overdue']
        ).order_by('due_date').first()
    
    @property
    def progress_percentage(self):
        """نسبة التقدم"""
        if self.total_amount == 0:
            return 0
        return round((self.paid_amount / self.total_amount) * 100, 1)


class Installment(models.Model):
    """قسط فردي"""
    id = models.AutoField(primary_key=True)
    
    INSTALLMENT_STATUS = [
        ('pending', 'معلق'),
        ('paid', 'مدفوع'),
        ('partially_paid', 'مدفوع جزئياً'),
        ('overdue', 'متأخر'),
        ('waived', 'معفى'),
    ]
    
    contract = models.ForeignKey(
        InstallmentContract,
        on_delete=models.CASCADE,
        related_name='installments',
        verbose_name=_('العقد')
    )
    
    installment_number = models.PositiveIntegerField(_('رقم القسط'))
    due_date = models.DateField(_('تاريخ الاستحقاق'))
    amount = models.DecimalField(_('مبلغ القسط'), max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField(
        _('المبلغ المدفوع'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    late_fee = models.DecimalField(
        _('رسوم التأخير'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=INSTALLMENT_STATUS,
        default='pending'
    )
    
    payment_date = models.DateField(_('تاريخ الدفع'), null=True, blank=True)
    payment_method = models.ForeignKey(
        'payments.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('طريقة الدفع')
    )
    payment_reference = models.CharField(
        _('مرجع الدفع'),
        max_length=100,
        blank=True
    )
    
    # ملاحظات
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    # عدد التذكيرات المرسلة
    reminder_count = models.PositiveIntegerField(_('عدد التذكيرات'), default=0)
    last_reminder_date = models.DateTimeField(_('تاريخ آخر تذكير'), null=True, blank=True)
    
    # الطوابع الزمنية
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('قسط')
        verbose_name_plural = _('الأقساط')
        ordering = ['due_date']
        unique_together = ['contract', 'installment_number']
        indexes = [
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.contract.contract_number} - قسط {self.installment_number}"
    
    @property
    def remaining_amount(self):
        """المبلغ المتبقي"""
        return self.amount - self.paid_amount + self.late_fee
    
    @property
    def is_overdue(self):
        """هل القسط متأخر؟"""
        if self.status == 'paid':
            return False
        grace_period = self.contract.plan.grace_period_days
        return self.due_date + timedelta(days=grace_period) < timezone.now().date()
    
    @property
    def days_overdue(self):
        """عدد أيام التأخير"""
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.due_date).days
    
    def calculate_late_fee(self):
        """حساب رسوم التأخير"""
        if not self.is_overdue:
            return Decimal('0')
        
        plan = self.contract.plan
        days = self.days_overdue
        
        if plan.late_fee_type == 'fixed':
            return plan.late_fee_value
        elif plan.late_fee_type == 'percentage':
            return (self.amount * plan.late_fee_value / Decimal('100')).quantize(Decimal('0.01'))
        elif plan.late_fee_type == 'daily':
            return (plan.late_fee_value * days).quantize(Decimal('0.01'))
        
        return Decimal('0')
    
    def pay(self, amount: Decimal, payment_method=None, payment_reference='', notes=''):
        """تسجيل دفعة على القسط"""
        from django.db import transaction
        
        with transaction.atomic():
            self.paid_amount += amount
            self.payment_date = timezone.now().date()
            self.payment_method = payment_method
            self.payment_reference = payment_reference
            
            if notes:
                self.notes = f"{self.notes}\n{notes}" if self.notes else notes
            
            # تحديد الحالة
            if self.paid_amount >= self.amount + self.late_fee:
                self.status = 'paid'
            elif self.paid_amount > 0:
                self.status = 'partially_paid'
            
            self.save()
            
            # تسجيل الدفعة
            InstallmentPayment.objects.create(
                installment=self,
                amount=amount,
                payment_method=payment_method,
                payment_reference=payment_reference,
                notes=notes
            )
            
            # تحديث حالة العقد إذا اكتمل السداد
            contract = self.contract
            if not contract.installments.exclude(status='paid').exists():
                contract.status = 'completed'
                contract.save()
            
            return True


class InstallmentPayment(models.Model):
    """سجل دفعات الأقساط"""
    id = models.AutoField(primary_key=True)
    
    installment = models.ForeignKey(
        Installment,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('القسط')
    )
    
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=2)
    payment_date = models.DateTimeField(_('تاريخ الدفع'), default=timezone.now)
    
    payment_method = models.ForeignKey(
        'payments.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('طريقة الدفع')
    )
    payment_reference = models.CharField(
        _('مرجع الدفع'),
        max_length=100,
        blank=True
    )
    
    receipt_number = models.CharField(
        _('رقم الإيصال'),
        max_length=50,
        unique=True,
        blank=True
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_installment_payments',
        verbose_name=_('استلمها')
    )
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('دفعة قسط')
        verbose_name_plural = _('دفعات الأقساط')
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"دفعة {self.amount} على {self.installment}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            from core.sequence_utils import next_sequence
            now = timezone.now()
            prefix = f"RCP-{now.strftime('%Y%m')}"
            seq = next_sequence(f'RECEIPT_{now.strftime("%Y%m")}')
            self.receipt_number = f"{prefix}-{str(seq).zfill(6)}"
        super().save(*args, **kwargs)


class Guarantor(models.Model):
    """الضامن/الكفيل"""
    id = models.AutoField(primary_key=True)
    
    contract = models.ForeignKey(
        InstallmentContract,
        on_delete=models.CASCADE,
        related_name='guarantors',
        verbose_name=_('العقد')
    )
    
    # البيانات الشخصية
    name = models.CharField(_('الاسم'), max_length=200)
    national_id = models.CharField(_('رقم الهوية'), max_length=20)
    national_id_image = models.ImageField(
        _('صورة الهوية'),
        upload_to='installments/guarantor_ids/',
        blank=True
    )
    
    # بيانات التواصل
    phone = models.CharField(_('رقم الهاتف'), max_length=20)
    alternative_phone = models.CharField(_('رقم هاتف بديل'), max_length=20, blank=True)
    address = models.TextField(_('العنوان'))
    
    # بيانات العمل
    job_title = models.CharField(_('الوظيفة'), max_length=100, blank=True)
    employer = models.CharField(_('جهة العمل'), max_length=200, blank=True)
    work_address = models.TextField(_('عنوان العمل'), blank=True)
    work_phone = models.CharField(_('هاتف العمل'), max_length=20, blank=True)
    monthly_income = models.DecimalField(
        _('الدخل الشهري'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # العلاقة بالعميل
    relationship = models.CharField(
        _('العلاقة بالعميل'),
        max_length=50,
        choices=[
            ('relative', 'قريب'),
            ('friend', 'صديق'),
            ('colleague', 'زميل عمل'),
            ('employer', 'صاحب عمل'),
            ('other', 'أخرى'),
        ],
        default='relative'
    )
    relationship_details = models.CharField(
        _('تفاصيل العلاقة'),
        max_length=100,
        blank=True
    )
    
    # التوقيع
    signature = models.ImageField(
        _('التوقيع'),
        upload_to='installments/guarantor_signatures/',
        blank=True
    )
    
    # ملاحظات
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    # الطوابع الزمنية
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('ضامن')
        verbose_name_plural = _('الضامنين')
    
    def __str__(self):
        return f"{self.name} - ضامن لـ {self.contract.contract_number}"


class InstallmentReminder(models.Model):
    """تذكيرات الأقساط"""
    id = models.AutoField(primary_key=True)
    
    REMINDER_TYPE = [
        ('upcoming', 'قبل الاستحقاق'),
        ('due', 'يوم الاستحقاق'),
        ('overdue', 'متأخر'),
    ]
    
    CHANNEL_CHOICES = [
        ('sms', 'رسالة SMS'),
        ('whatsapp', 'واتساب'),
        ('email', 'بريد إلكتروني'),
        ('push', 'إشعار تطبيق'),
        ('call', 'اتصال هاتفي'),
    ]
    
    installment = models.ForeignKey(
        Installment,
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name=_('القسط')
    )
    
    reminder_type = models.CharField(
        _('نوع التذكير'),
        max_length=20,
        choices=REMINDER_TYPE
    )
    
    channel = models.CharField(
        _('قناة الإرسال'),
        max_length=20,
        choices=CHANNEL_CHOICES
    )
    
    message = models.TextField(_('نص الرسالة'))
    
    sent_at = models.DateTimeField(_('تاريخ الإرسال'), auto_now_add=True)
    delivered = models.BooleanField(_('تم التوصيل'), default=False)
    read = models.BooleanField(_('تم القراءة'), default=False)
    
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_installment_reminders',
        verbose_name=_('أرسل بواسطة')
    )
    
    class Meta:
        verbose_name = _('تذكير قسط')
        verbose_name_plural = _('تذكيرات الأقساط')
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"تذكير {self.get_reminder_type_display()} - {self.installment}"


class InstallmentSettings(models.Model):
    """إعدادات نظام التقسيط"""
    id = models.AutoField(primary_key=True)
    
    # تذكيرات تلقائية
    auto_reminders_enabled = models.BooleanField(
        _('تفعيل التذكيرات التلقائية'),
        default=True
    )
    reminder_days_before = models.PositiveIntegerField(
        _('أيام قبل الاستحقاق للتذكير'),
        default=3
    )
    overdue_reminder_interval = models.PositiveIntegerField(
        _('الفترة بين تذكيرات التأخير (أيام)'),
        default=7
    )
    max_reminders_per_installment = models.PositiveIntegerField(
        _('الحد الأقصى لعدد التذكيرات لكل قسط'),
        default=5
    )
    
    # قنوات التذكير
    sms_enabled = models.BooleanField(_('SMS'), default=True)
    whatsapp_enabled = models.BooleanField(_('واتساب'), default=True)
    email_enabled = models.BooleanField(_('البريد الإلكتروني'), default=True)
    push_enabled = models.BooleanField(_('إشعارات التطبيق'), default=True)
    
    # قواعد التعثر
    default_after_days = models.PositiveIntegerField(
        _('يُعتبر متعثر بعد (أيام)'),
        default=90
    )
    
    # نصوص الرسائل
    upcoming_message_template = models.TextField(
        _('قالب رسالة قبل الاستحقاق'),
        default='عزيزي {customer_name}، نذكرك بأن القسط رقم {installment_number} بمبلغ {amount} يستحق بتاريخ {due_date}. العقد رقم: {contract_number}'
    )
    due_message_template = models.TextField(
        _('قالب رسالة يوم الاستحقاق'),
        default='عزيزي {customer_name}، اليوم يستحق القسط رقم {installment_number} بمبلغ {amount}. يرجى السداد لتجنب رسوم التأخير. العقد رقم: {contract_number}'
    )
    overdue_message_template = models.TextField(
        _('قالب رسالة التأخير'),
        default='عزيزي {customer_name}، القسط رقم {installment_number} متأخر بمبلغ {amount} منذ {days_overdue} يوم. رسوم التأخير: {late_fee}. يرجى السداد فوراً. العقد رقم: {contract_number}'
    )
    
    class Meta:
        verbose_name = _('إعدادات التقسيط')
        verbose_name_plural = _('إعدادات التقسيط')
    
    def save(self, *args, **kwargs):
        # ضمان وجود سجل واحد فقط
        self.__class__.objects.exclude(id=self.id).delete()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """الحصول على الإعدادات أو إنشاء افتراضية"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class EarlySettlement(models.Model):
    """طلبات التسوية المبكرة"""
    id = models.AutoField(primary_key=True)
    
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]
    
    contract = models.ForeignKey(
        InstallmentContract,
        on_delete=models.CASCADE,
        related_name='early_settlements',
        verbose_name=_('العقد')
    )
    
    # المبالغ
    remaining_principal = models.DecimalField(
        _('المبلغ الأصلي المتبقي'),
        max_digits=15,
        decimal_places=2
    )
    remaining_interest = models.DecimalField(
        _('الفوائد المتبقية'),
        max_digits=15,
        decimal_places=2
    )
    discount_percentage = models.DecimalField(
        _('نسبة الخصم %'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0')
    )
    discount_amount = models.DecimalField(
        _('مبلغ الخصم'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    settlement_amount = models.DecimalField(
        _('مبلغ التسوية النهائي'),
        max_digits=15,
        decimal_places=2
    )
    
    # التواريخ والحالة
    request_date = models.DateTimeField(_('تاريخ الطلب'), auto_now_add=True)
    settlement_date = models.DateField(_('تاريخ التسوية'), null=True, blank=True)
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # ملاحظات وسبب
    reason = models.TextField(_('سبب الطلب'), blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    rejection_reason = models.TextField(_('سبب الرفض'), blank=True)
    
    # المستخدمين
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_early_settlements',
        verbose_name=_('مقدم الطلب')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_early_settlements',
        verbose_name=_('الموافق')
    )
    
    class Meta:
        verbose_name = _('تسوية مبكرة')
        verbose_name_plural = _('التسويات المبكرة')
        ordering = ['-request_date']
    
    def __str__(self):
        return f"تسوية مبكرة - {self.contract.contract_number}"
    
    def calculate_settlement(self, discount_percent=Decimal('0')):
        """حساب مبلغ التسوية"""
        unpaid = self.contract.installments.filter(status__in=['pending', 'partially_paid', 'overdue'])
        self.remaining_principal = sum(i.amount - i.paid_amount for i in unpaid)
        self.remaining_interest = self.contract.total_interest * (
            unpaid.count() / self.contract.plan.duration_months
        ) if self.contract.plan.duration_months > 0 else Decimal('0')
        
        total = self.remaining_principal + self.remaining_interest
        self.discount_percentage = discount_percent
        self.discount_amount = (total * discount_percent / Decimal('100')).quantize(Decimal('0.01'))
        self.settlement_amount = total - self.discount_amount
        return self.settlement_amount


class ContractReschedule(models.Model):
    """إعادة جدولة العقد"""
    id = models.AutoField(primary_key=True)
    
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
        ('applied', 'مطبق'),
    ]
    
    contract = models.ForeignKey(
        InstallmentContract,
        on_delete=models.CASCADE,
        related_name='reschedules',
        verbose_name=_('العقد')
    )
    
    # التفاصيل الأصلية
    original_monthly_payment = models.DecimalField(
        _('القسط الشهري الأصلي'),
        max_digits=15,
        decimal_places=2
    )
    original_remaining_months = models.PositiveIntegerField(_('الأشهر المتبقية الأصلية'))
    original_remaining_amount = models.DecimalField(
        _('المبلغ المتبقي الأصلي'),
        max_digits=15,
        decimal_places=2
    )
    
    # التفاصيل الجديدة
    new_monthly_payment = models.DecimalField(
        _('القسط الشهري الجديد'),
        max_digits=15,
        decimal_places=2
    )
    new_duration_months = models.PositiveIntegerField(_('المدة الجديدة بالأشهر'))
    new_start_date = models.DateField(_('تاريخ البدء الجديد'))
    additional_interest = models.DecimalField(
        _('فوائد إضافية'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    
    # التواريخ والحالة
    request_date = models.DateTimeField(_('تاريخ الطلب'), auto_now_add=True)
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # السبب والملاحظات
    reason = models.TextField(_('سبب إعادة الجدولة'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    rejection_reason = models.TextField(_('سبب الرفض'), blank=True)
    
    # المستخدمين
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_reschedules',
        verbose_name=_('مقدم الطلب')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_reschedules',
        verbose_name=_('الموافق')
    )
    
    class Meta:
        verbose_name = _('إعادة جدولة')
        verbose_name_plural = _('إعادات الجدولة')
        ordering = ['-request_date']
    
    def __str__(self):
        return f"إعادة جدولة - {self.contract.contract_number}"
    
    def apply_reschedule(self):
        """تطبيق إعادة الجدولة"""
        from django.db import transaction
        
        with transaction.atomic():
            # حذف الأقساط غير المدفوعة
            self.contract.installments.filter(
                status__in=['pending', 'partially_paid', 'overdue']
            ).delete()
            
            # إنشاء أقساط جديدة
            current_date = self.new_start_date
            for i in range(1, self.new_duration_months + 1):
                Installment.objects.create(
                    contract=self.contract,
                    installment_number=self.contract.installments.count() + 1,
                    due_date=current_date,
                    amount=self.new_monthly_payment,
                    status='pending'
                )
                # الانتقال للشهر التالي
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    try:
                        current_date = current_date.replace(month=current_date.month + 1)
                    except ValueError:
                        current_date = current_date.replace(month=current_date.month + 1, day=28)
            
            # تحديث العقد
            self.contract.monthly_payment = self.new_monthly_payment
            self.contract.total_amount += self.additional_interest
            self.contract.save()
            
            self.status = 'applied'
            self.save()


class ContractTransfer(models.Model):
    """نقل ملكية العقد"""
    id = models.AutoField(primary_key=True)
    
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
        ('completed', 'مكتمل'),
    ]
    
    contract = models.ForeignKey(
        InstallmentContract,
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name=_('العقد')
    )
    
    # العميل الأصلي
    original_customer = models.ForeignKey(
        'partners.Customer',
        on_delete=models.PROTECT,
        related_name='transferred_from_contracts',
        verbose_name=_('العميل الأصلي')
    )
    
    # العميل الجديد
    new_customer = models.ForeignKey(
        'partners.Customer',
        on_delete=models.PROTECT,
        related_name='transferred_to_contracts',
        verbose_name=_('العميل الجديد')
    )
    
    # رسوم النقل
    transfer_fee = models.DecimalField(
        _('رسوم النقل'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    
    # التواريخ والحالة
    request_date = models.DateTimeField(_('تاريخ الطلب'), auto_now_add=True)
    transfer_date = models.DateField(_('تاريخ النقل'), null=True, blank=True)
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # المستندات
    transfer_document = models.FileField(
        _('مستند النقل'),
        upload_to='installments/transfers/',
        blank=True
    )
    
    # السبب والملاحظات
    reason = models.TextField(_('سبب النقل'), blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    # المستخدمين
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_contract_transfers',
        verbose_name=_('مقدم الطلب')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_contract_transfers',
        verbose_name=_('الموافق')
    )
    
    class Meta:
        verbose_name = _('نقل ملكية')
        verbose_name_plural = _('نقل الملكيات')
        ordering = ['-request_date']
    
    def __str__(self):
        return f"نقل {self.contract.contract_number} من {self.original_customer} إلى {self.new_customer}"
    
    def complete_transfer(self):
        """إتمام عملية النقل"""
        from django.db import transaction
        
        with transaction.atomic():
            self.contract.customer = self.new_customer
            self.contract.save()
            
            self.status = 'completed'
            self.transfer_date = timezone.now().date()
            self.save()


class CustomerCreditScore(models.Model):
    """تقييم ائتماني للعميل"""
    id = models.AutoField(primary_key=True)
    
    SCORE_LEVEL = [
        ('excellent', 'ممتاز'),
        ('good', 'جيد'),
        ('fair', 'مقبول'),
        ('poor', 'ضعيف'),
        ('bad', 'سيء'),
    ]
    
    customer = models.OneToOneField(
        'partners.Customer',
        on_delete=models.CASCADE,
        related_name='credit_score',
        verbose_name=_('العميل')
    )
    
    # النتيجة
    score = models.PositiveIntegerField(
        _('النتيجة'),
        default=500,
        validators=[MinValueValidator(0), MaxValueValidator(1000)]
    )
    level = models.CharField(
        _('المستوى'),
        max_length=20,
        choices=SCORE_LEVEL,
        default='fair'
    )
    
    # عوامل التقييم
    total_contracts = models.PositiveIntegerField(_('إجمالي العقود'), default=0)
    completed_contracts = models.PositiveIntegerField(_('العقود المكتملة'), default=0)
    defaulted_contracts = models.PositiveIntegerField(_('العقود المتعثرة'), default=0)
    on_time_payments = models.PositiveIntegerField(_('الدفعات في الموعد'), default=0)
    late_payments = models.PositiveIntegerField(_('الدفعات المتأخرة'), default=0)
    total_late_days = models.PositiveIntegerField(_('إجمالي أيام التأخير'), default=0)
    
    # الحدود
    max_credit_limit = models.DecimalField(
        _('الحد الائتماني الأقصى'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    available_credit = models.DecimalField(
        _('الائتمان المتاح'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    
    # آخر تحديث
    last_updated = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('تقييم ائتماني')
        verbose_name_plural = _('التقييمات الائتمانية')
    
    def __str__(self):
        return f"تقييم {self.customer.name}: {self.score} ({self.get_level_display()})"
    
    def calculate_score(self):
        """حساب النتيجة الائتمانية"""
        contracts = InstallmentContract.objects.filter(customer=self.customer)
        self.total_contracts = contracts.count()
        self.completed_contracts = contracts.filter(status='completed').count()
        self.defaulted_contracts = contracts.filter(status='defaulted').count()
        
        # حساب معدل السداد في الموعد
        all_payments = InstallmentPayment.objects.filter(
            installment__contract__customer=self.customer
        )
        on_time = 0
        late = 0
        total_late_days = 0
        
        for payment in all_payments:
            if payment.payment_date.date() <= payment.installment.due_date:
                on_time += 1
            else:
                late += 1
                total_late_days += (payment.payment_date.date() - payment.installment.due_date).days
        
        self.on_time_payments = on_time
        self.late_payments = late
        self.total_late_days = total_late_days
        
        # حساب النتيجة (من 0 إلى 1000)
        base_score = 500
        
        # مكافأة للعقود المكتملة
        if self.total_contracts > 0:
            completion_rate = self.completed_contracts / self.total_contracts
            base_score += int(completion_rate * 200)
        
        # خصم للعقود المتعثرة
        base_score -= self.defaulted_contracts * 100
        
        # مكافأة للسداد في الموعد
        total_payments = self.on_time_payments + self.late_payments
        if total_payments > 0:
            on_time_rate = self.on_time_payments / total_payments
            base_score += int(on_time_rate * 150)
        
        # خصم لأيام التأخير
        base_score -= min(self.total_late_days, 150)
        
        # ضمان النتيجة في النطاق المسموح
        self.score = max(0, min(1000, base_score))
        
        # تحديد المستوى
        if self.score >= 800:
            self.level = 'excellent'
        elif self.score >= 650:
            self.level = 'good'
        elif self.score >= 500:
            self.level = 'fair'
        elif self.score >= 350:
            self.level = 'poor'
        else:
            self.level = 'bad'
        
        # حساب الحد الائتماني
        self.max_credit_limit = Decimal(str(self.score * 100))
        
        # حساب الائتمان المتاح
        active_contracts = contracts.filter(status='active')
        used_credit = sum(c.remaining_amount for c in active_contracts)
        self.available_credit = max(Decimal('0'), self.max_credit_limit - used_credit)
        
        self.save()
        return self.score


class CollectionAction(models.Model):
    """إجراءات التحصيل"""
    id = models.AutoField(primary_key=True)
    
    ACTION_TYPE = [
        ('phone_call', 'اتصال هاتفي'),
        ('sms', 'رسالة SMS'),
        ('whatsapp', 'رسالة واتساب'),
        ('email', 'بريد إلكتروني'),
        ('visit', 'زيارة ميدانية'),
        ('legal_notice', 'إنذار قانوني'),
        ('legal_action', 'إجراء قانوني'),
        ('settlement_offer', 'عرض تسوية'),
        ('other', 'أخرى'),
    ]
    
    RESULT_CHOICES = [
        ('promise_to_pay', 'وعد بالسداد'),
        ('partial_payment', 'سداد جزئي'),
        ('full_payment', 'سداد كامل'),
        ('no_response', 'لا رد'),
        ('refused', 'رفض'),
        ('wrong_contact', 'بيانات اتصال خاطئة'),
        ('not_available', 'غير متاح'),
        ('dispute', 'نزاع'),
        ('other', 'أخرى'),
    ]
    
    installment = models.ForeignKey(
        Installment,
        on_delete=models.CASCADE,
        related_name='collection_actions',
        verbose_name=_('القسط')
    )
    
    action_type = models.CharField(
        _('نوع الإجراء'),
        max_length=20,
        choices=ACTION_TYPE
    )
    
    action_date = models.DateTimeField(_('تاريخ الإجراء'), default=timezone.now)
    
    result = models.CharField(
        _('النتيجة'),
        max_length=20,
        choices=RESULT_CHOICES,
        blank=True
    )
    
    # تفاصيل الوعد بالسداد
    promise_date = models.DateField(_('تاريخ الوعد'), null=True, blank=True)
    promise_amount = models.DecimalField(
        _('المبلغ الموعود'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='collection_actions',
        verbose_name=_('المنفذ')
    )
    
    # متابعة
    follow_up_date = models.DateField(_('تاريخ المتابعة'), null=True, blank=True)
    follow_up_done = models.BooleanField(_('تمت المتابعة'), default=False)
    
    class Meta:
        verbose_name = _('إجراء تحصيل')
        verbose_name_plural = _('إجراءات التحصيل')
        ordering = ['-action_date']
    
    def __str__(self):
        return f"{self.get_action_type_display()} - {self.installment}"


class InstallmentWaiver(models.Model):
    """إعفاء من القسط أو جزء منه"""
    id = models.AutoField(primary_key=True)
    
    WAIVER_TYPE = [
        ('late_fee', 'إعفاء من رسوم التأخير'),
        ('partial', 'إعفاء جزئي'),
        ('full', 'إعفاء كامل'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
    ]
    
    installment = models.ForeignKey(
        Installment,
        on_delete=models.CASCADE,
        related_name='waivers',
        verbose_name=_('القسط')
    )
    
    waiver_type = models.CharField(
        _('نوع الإعفاء'),
        max_length=20,
        choices=WAIVER_TYPE
    )
    
    waiver_amount = models.DecimalField(
        _('مبلغ الإعفاء'),
        max_digits=15,
        decimal_places=2
    )
    
    reason = models.TextField(_('سبب الإعفاء'))
    
    request_date = models.DateTimeField(_('تاريخ الطلب'), auto_now_add=True)
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_waivers',
        verbose_name=_('مقدم الطلب')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_waivers',
        verbose_name=_('الموافق')
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    rejection_reason = models.TextField(_('سبب الرفض'), blank=True)
    
    class Meta:
        verbose_name = _('إعفاء')
        verbose_name_plural = _('الإعفاءات')
        ordering = ['-request_date']
    
    def __str__(self):
        return f"{self.get_waiver_type_display()} - {self.installment}"
    
    def apply_waiver(self):
        """تطبيق الإعفاء"""
        if self.waiver_type == 'late_fee':
            self.installment.late_fee = Decimal('0')
        elif self.waiver_type == 'partial':
            self.installment.amount -= self.waiver_amount
        elif self.waiver_type == 'full':
            self.installment.status = 'waived'
            self.installment.paid_amount = self.installment.amount
        
        self.installment.save()
