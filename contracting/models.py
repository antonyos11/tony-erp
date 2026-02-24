"""
Models for Contracting App - نماذج نظام المقاولات
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal


class ContractingProject(models.Model):
    """مشروع مقاولات"""
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('active', _('نشط')),
        ('on_hold', _('متوقف مؤقتاً')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
    ]
    
    name = models.CharField(_('اسم المشروع'), max_length=255)
    code = models.CharField(_('كود المشروع'), max_length=50, unique=True)
    description = models.TextField(_('الوصف'), blank=True)
    
    client_name = models.CharField(_('اسم العميل'), max_length=255)
    client_phone = models.CharField(_('هاتف العميل'), max_length=20, blank=True)
    client_email = models.EmailField(_('بريد العميل'), blank=True)
    client_address = models.TextField(_('عنوان العميل'), blank=True)
    
    location = models.CharField(_('موقع المشروع'), max_length=255, blank=True)
    
    start_date = models.DateField(_('تاريخ البدء'), null=True, blank=True)
    expected_end_date = models.DateField(_('تاريخ الانتهاء المتوقع'), null=True, blank=True)
    actual_end_date = models.DateField(_('تاريخ الانتهاء الفعلي'), null=True, blank=True)
    
    contract_value = models.DecimalField(_('قيمة العقد'), max_digits=15, decimal_places=2, default=Decimal('0'))
    budget = models.DecimalField(_('الميزانية'), max_digits=15, decimal_places=2, default=Decimal('0'))
    
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='draft')
    progress_percentage = models.PositiveIntegerField(_('نسبة الإنجاز'), default=0)
    
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='managed_contracting_projects',
        verbose_name=_('مدير المشروع')
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_contracting_projects',
        verbose_name=_('أنشئ بواسطة')
    )
    
    class Meta:
        verbose_name = _('مشروع مقاولات')
        verbose_name_plural = _('مشاريع المقاولات')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def total_expenses(self):
        """إجمالي المصروفات"""
        return self.expenses.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
    
    @property
    def total_receipts(self):
        """إجمالي المقبوضات"""
        return self.receipts.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
    
    @property
    def profit_loss(self):
        """الربح/الخسارة"""
        return self.total_receipts - self.total_expenses


class ContractingWorker(models.Model):
    """عامل في نظام المقاولات"""
    
    WORKER_TYPE_CHOICES = [
        ('daily', _('يومي')),
        ('monthly', _('شهري')),
        ('contract', _('عقد')),
    ]
    
    name = models.CharField(_('اسم العامل'), max_length=255)
    national_id = models.CharField(_('رقم الهوية'), max_length=20, unique=True)
    phone = models.CharField(_('رقم الهاتف'), max_length=20, blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    
    job_title = models.CharField(_('المسمى الوظيفي'), max_length=100)
    worker_type = models.CharField(_('نوع العامل'), max_length=20, choices=WORKER_TYPE_CHOICES, default='daily')
    daily_wage = models.DecimalField(_('الأجر اليومي'), max_digits=10, decimal_places=2, default=Decimal('0'))
    
    hire_date = models.DateField(_('تاريخ التعيين'), default=timezone.localdate)
    is_active = models.BooleanField(_('نشط'), default=True)
    
    current_project = models.ForeignKey(
        ContractingProject,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='workers',
        verbose_name=_('المشروع الحالي')
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('عامل')
        verbose_name_plural = _('العمال')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.job_title}"


class ContractingAttendance(models.Model):
    """سجل حضور وانصراف العمال"""
    
    STATUS_CHOICES = [
        ('present', _('حاضر')),
        ('absent', _('غائب')),
        ('late', _('متأخر')),
        ('half_day', _('نصف يوم')),
        ('vacation', _('إجازة')),
    ]
    
    worker = models.ForeignKey(
        ContractingWorker,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name=_('العامل')
    )
    project = models.ForeignKey(
        ContractingProject,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name=_('المشروع')
    )
    
    date = models.DateField(_('التاريخ'))
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='present')
    
    check_in = models.TimeField(_('وقت الحضور'), null=True, blank=True)
    check_out = models.TimeField(_('وقت الانصراف'), null=True, blank=True)
    
    hours_worked = models.DecimalField(_('ساعات العمل'), max_digits=5, decimal_places=2, default=Decimal('0'))
    overtime_hours = models.DecimalField(_('ساعات إضافية'), max_digits=5, decimal_places=2, default=Decimal('0'))
    
    daily_wage = models.DecimalField(_('الأجر اليومي'), max_digits=10, decimal_places=2, default=Decimal('0'))
    total_wage = models.DecimalField(_('إجمالي الأجر'), max_digits=10, decimal_places=2, default=Decimal('0'))
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('سجل بواسطة')
    )
    
    class Meta:
        verbose_name = _('سجل حضور')
        verbose_name_plural = _('سجلات الحضور')
        ordering = ['-date', 'worker__name']
        unique_together = ['worker', 'date']
    
    def __str__(self):
        return f"{self.worker.name} - {self.date}"
    
    def save(self, *args, **kwargs):
        if not self.daily_wage:
            self.daily_wage = self.worker.daily_wage
        if self.status == 'present':
            self.total_wage = self.daily_wage
        elif self.status == 'half_day':
            self.total_wage = self.daily_wage / 2
        else:
            self.total_wage = 0
        super().save(*args, **kwargs)


class ContractingMaterial(models.Model):
    """مادة في نظام المقاولات"""
    
    UNIT_CHOICES = [
        ('kg', _('كجم')),
        ('ton', _('طن')),
        ('m', _('متر')),
        ('m2', _('متر مربع')),
        ('m3', _('متر مكعب')),
        ('piece', _('قطعة')),
        ('bag', _('كيس')),
        ('roll', _('رول')),
        ('box', _('صندوق')),
        ('liter', _('لتر')),
    ]
    
    name = models.CharField(_('اسم المادة'), max_length=255)
    code = models.CharField(_('كود المادة'), max_length=50, unique=True)
    description = models.TextField(_('الوصف'), blank=True)
    
    unit = models.CharField(_('الوحدة'), max_length=20, choices=UNIT_CHOICES, default='piece')
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=12, decimal_places=2, default=Decimal('0'))
    
    current_stock = models.DecimalField(_('المخزون الحالي'), max_digits=12, decimal_places=3, default=Decimal('0'))
    min_stock = models.DecimalField(_('الحد الأدنى'), max_digits=12, decimal_places=3, default=Decimal('0'))
    
    is_active = models.BooleanField(_('نشط'), default=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('مادة')
        verbose_name_plural = _('المواد')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class ContractingEquipment(models.Model):
    """معدة في نظام المقاولات"""
    
    STATUS_CHOICES = [
        ('available', _('متاحة')),
        ('in_use', _('قيد الاستخدام')),
        ('maintenance', _('صيانة')),
        ('broken', _('معطلة')),
    ]
    
    name = models.CharField(_('اسم المعدة'), max_length=255)
    code = models.CharField(_('كود المعدة'), max_length=50, unique=True)
    description = models.TextField(_('الوصف'), blank=True)
    
    brand = models.CharField(_('الماركة'), max_length=100, blank=True)
    model = models.CharField(_('الموديل'), max_length=100, blank=True)
    serial_number = models.CharField(_('الرقم التسلسلي'), max_length=100, blank=True)
    
    purchase_date = models.DateField(_('تاريخ الشراء'), null=True, blank=True)
    purchase_price = models.DecimalField(_('سعر الشراء'), max_digits=12, decimal_places=2, default=Decimal('0'))
    
    daily_rental_rate = models.DecimalField(_('معدل الإيجار اليومي'), max_digits=10, decimal_places=2, default=Decimal('0'))
    
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='available')
    
    current_project = models.ForeignKey(
        ContractingProject,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='equipment',
        verbose_name=_('المشروع الحالي')
    )
    
    last_maintenance_date = models.DateField(_('آخر صيانة'), null=True, blank=True)
    next_maintenance_date = models.DateField(_('الصيانة القادمة'), null=True, blank=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('معدة')
        verbose_name_plural = _('المعدات')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class ContractingExpense(models.Model):
    """مصروف في نظام المقاولات"""
    
    EXPENSE_TYPE_CHOICES = [
        ('labor', _('أجور عمال')),
        ('materials', _('مواد')),
        ('equipment', _('معدات')),
        ('transport', _('نقل')),
        ('admin', _('إدارية')),
        ('other', _('أخرى')),
    ]
    
    project = models.ForeignKey(
        ContractingProject,
        on_delete=models.CASCADE,
        related_name='expenses',
        verbose_name=_('المشروع')
    )
    
    expense_type = models.CharField(_('نوع المصروف'), max_length=20, choices=EXPENSE_TYPE_CHOICES)
    description = models.CharField(_('الوصف'), max_length=255)
    
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    date = models.DateField(_('التاريخ'), default=timezone.localdate)
    
    reference_number = models.CharField(_('رقم المرجع'), max_length=50, blank=True)
    
    material = models.ForeignKey(
        ContractingMaterial,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='expenses',
        verbose_name=_('المادة')
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('أنشئ بواسطة')
    )
    
    class Meta:
        verbose_name = _('مصروف')
        verbose_name_plural = _('المصروفات')
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.project.code} - {self.description} - {self.amount}"


class ContractingReceipt(models.Model):
    """مقبوضات في نظام المقاولات"""
    
    RECEIPT_TYPE_CHOICES = [
        ('advance', _('دفعة مقدمة')),
        ('progress', _('دفعة تقدم')),
        ('final', _('دفعة نهائية')),
        ('retention', _('إفراج ضمان')),
        ('other', _('أخرى')),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', _('نقداً')),
        ('bank', _('تحويل بنكي')),
        ('check', _('شيك')),
        ('other', _('أخرى')),
    ]
    
    project = models.ForeignKey(
        ContractingProject,
        on_delete=models.CASCADE,
        related_name='receipts',
        verbose_name=_('المشروع')
    )
    
    receipt_type = models.CharField(_('نوع المقبوض'), max_length=20, choices=RECEIPT_TYPE_CHOICES)
    payment_method = models.CharField(_('طريقة الدفع'), max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    
    description = models.CharField(_('الوصف'), max_length=255)
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    date = models.DateField(_('التاريخ'), default=timezone.localdate)
    
    reference_number = models.CharField(_('رقم المرجع'), max_length=50, blank=True)
    check_number = models.CharField(_('رقم الشيك'), max_length=50, blank=True)
    bank_name = models.CharField(_('اسم البنك'), max_length=100, blank=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('أنشئ بواسطة')
    )
    
    class Meta:
        verbose_name = _('مقبوض')
        verbose_name_plural = _('المقبوضات')
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.project.code} - {self.description} - {self.amount}"


class ContractingContract(models.Model):
    """عقد مقاولات"""
    
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('pending', _('قيد الانتظار')),
        ('active', _('نشط')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
    ]
    
    project = models.ForeignKey(
        ContractingProject,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name=_('المشروع')
    )
    
    contract_number = models.CharField(_('رقم العقد'), max_length=50, unique=True)
    title = models.CharField(_('عنوان العقد'), max_length=255)
    description = models.TextField(_('الوصف'), blank=True)
    
    contractor_name = models.CharField(_('اسم المقاول'), max_length=255, blank=True)
    contractor_phone = models.CharField(_('هاتف المقاول'), max_length=20, blank=True)
    
    contract_value = models.DecimalField(_('قيمة العقد'), max_digits=15, decimal_places=2, default=Decimal('0'))
    advance_payment = models.DecimalField(_('الدفعة المقدمة'), max_digits=15, decimal_places=2, default=Decimal('0'))
    retention_percentage = models.DecimalField(_('نسبة الضمان'), max_digits=5, decimal_places=2, default=Decimal('10'))
    
    start_date = models.DateField(_('تاريخ البدء'), null=True, blank=True)
    end_date = models.DateField(_('تاريخ الانتهاء'), null=True, blank=True)
    
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    terms = models.TextField(_('شروط العقد'), blank=True)
    
    signed_date = models.DateField(_('تاريخ التوقيع'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('أنشئ بواسطة')
    )
    
    class Meta:
        verbose_name = _('عقد')
        verbose_name_plural = _('العقود')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.contract_number} - {self.title}"
