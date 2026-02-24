"""
نماذج إدارة المشاريع
Projects Management Models
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class ProjectType(models.Model):
    """أنواع المشاريع"""
    name = models.CharField('اسم النوع', max_length=100)
    code = models.CharField('الكود', max_length=20, unique=True)
    description = models.TextField('الوصف', blank=True)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'نوع مشروع'
        verbose_name_plural = 'أنواع المشاريع'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProjectCategory(models.Model):
    """تصنيفات المشاريع"""
    name = models.CharField('اسم التصنيف', max_length=100)
    code = models.CharField('الكود', max_length=20, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name='التصنيف الأب')
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'تصنيف مشروع'
        verbose_name_plural = 'تصنيفات المشاريع'
        ordering = ['name']

    def __str__(self):
        return self.name


class Project(models.Model):
    """المشاريع"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('planning', 'تخطيط'),
        ('in_progress', 'قيد التنفيذ'),
        ('on_hold', 'معلق'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]
    
    name = models.CharField('اسم المشروع', max_length=200)
    code = models.CharField('كود المشروع', max_length=50, unique=True)
    description = models.TextField('الوصف', blank=True)
    project_type = models.ForeignKey(ProjectType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='نوع المشروع')
    category = models.ForeignKey(ProjectCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='التصنيف')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    start_date = models.DateField('تاريخ البداية', null=True, blank=True)
    end_date = models.DateField('تاريخ النهاية', null=True, blank=True)
    actual_start = models.DateField('البداية الفعلية', null=True, blank=True)
    actual_end = models.DateField('النهاية الفعلية', null=True, blank=True)
    
    budget = models.DecimalField('الميزانية', max_digits=15, decimal_places=2, default=Decimal('0'))
    actual_cost = models.DecimalField('التكلفة الفعلية', max_digits=15, decimal_places=2, default=Decimal('0'))
    
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_projects', verbose_name='مدير المشروع')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_projects', verbose_name='أنشأ بواسطة')
    
    client_name = models.CharField('اسم العميل', max_length=200, blank=True)
    client_contact = models.CharField('جهة اتصال العميل', max_length=200, blank=True)
    progress = models.PositiveIntegerField('نسبة الإنجاز', default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'مشروع'
        verbose_name_plural = 'المشاريع'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.name}"


class ProjectAdjustment(models.Model):
    """تعديلات المشاريع"""
    ADJUSTMENT_TYPES = [
        ('budget', 'تعديل ميزانية'),
        ('schedule', 'تعديل جدول'),
        ('scope', 'تعديل نطاق'),
        ('other', 'أخرى'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='adjustments', verbose_name='المشروع')
    adjustment_type = models.CharField('نوع التعديل', max_length=20, choices=ADJUSTMENT_TYPES)
    description = models.TextField('الوصف')
    old_value = models.TextField('القيمة القديمة', blank=True)
    new_value = models.TextField('القيمة الجديدة', blank=True)
    reason = models.TextField('السبب')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='اعتمد بواسطة')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='project_adjustments', verbose_name='أنشأ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'تعديل مشروع'
        verbose_name_plural = 'تعديلات المشاريع'
        ordering = ['-created_at']

    def __str__(self):
        return f"تعديل {self.project.code} - {self.get_adjustment_type_display()}"


class BOQItem(models.Model):
    """بنود جدول الكميات"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='boq_items', verbose_name='المشروع')
    item_code = models.CharField('كود البند', max_length=50)
    description = models.TextField('الوصف')
    unit = models.CharField('الوحدة', max_length=20)
    quantity = models.DecimalField('الكمية', max_digits=15, decimal_places=3)
    unit_price = models.DecimalField('سعر الوحدة', max_digits=15, decimal_places=2)
    total_price = models.DecimalField('الإجمالي', max_digits=15, decimal_places=2, editable=False, default=Decimal('0'))
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'بند كميات'
        verbose_name_plural = 'جدول الكميات'
        ordering = ['item_code']

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_code} - {self.description[:50]}"


class Contractor(models.Model):
    """المقاولين"""
    name = models.CharField('اسم المقاول', max_length=200)
    code = models.CharField('الكود', max_length=50, unique=True)
    specialty = models.CharField('التخصص', max_length=100, blank=True)
    phone = models.CharField('الهاتف', max_length=50, blank=True)
    email = models.EmailField('البريد الإلكتروني', blank=True)
    address = models.TextField('العنوان', blank=True)
    tax_number = models.CharField('الرقم الضريبي', max_length=50, blank=True)
    rating = models.PositiveIntegerField('التقييم', default=0)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'مقاول'
        verbose_name_plural = 'المقاولين'
        ordering = ['name']

    def __str__(self):
        return self.name


class ContractorContract(models.Model):
    """عقود المقاولين"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('completed', 'مكتمل'),
        ('terminated', 'منتهي'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='contractor_contracts', verbose_name='المشروع')
    contractor = models.ForeignKey(Contractor, on_delete=models.CASCADE, related_name='contracts', verbose_name='المقاول')
    contract_number = models.CharField('رقم العقد', max_length=50, unique=True)
    description = models.TextField('وصف العقد')
    amount = models.DecimalField('قيمة العقد', max_digits=15, decimal_places=2)
    start_date = models.DateField('تاريخ البداية')
    end_date = models.DateField('تاريخ النهاية')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'عقد مقاول'
        verbose_name_plural = 'عقود المقاولين'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.contract_number} - {self.contractor.name}"


class ProjectLabour(models.Model):
    """العمالة"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='labour', verbose_name='المشروع')
    name = models.CharField('اسم العامل', max_length=100)
    job_title = models.CharField('المسمى الوظيفي', max_length=100)
    daily_rate = models.DecimalField('الأجر اليومي', max_digits=10, decimal_places=2)
    phone = models.CharField('الهاتف', max_length=50, blank=True)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'عامل'
        verbose_name_plural = 'العمالة'
        ordering = ['name']

    def __str__(self):
        return self.name


class LabourAttendance(models.Model):
    """حضور العمالة"""
    labour = models.ForeignKey(ProjectLabour, on_delete=models.CASCADE, related_name='attendance', verbose_name='العامل')
    date = models.DateField('التاريخ')
    hours_worked = models.DecimalField('ساعات العمل', max_digits=5, decimal_places=2)
    overtime_hours = models.DecimalField('ساعات إضافية', max_digits=5, decimal_places=2, default=Decimal('0'))
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'حضور عامل'
        verbose_name_plural = 'سجل الحضور'
        ordering = ['-date']
        unique_together = ['labour', 'date']

    def __str__(self):
        return f"{self.labour.name} - {self.date}"


class ProjectExpense(models.Model):
    """مصروفات المشروع"""
    EXPENSE_TYPES = [
        ('material', 'مواد'),
        ('labour', 'عمالة'),
        ('equipment', 'معدات'),
        ('transport', 'نقل'),
        ('other', 'أخرى'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expenses', verbose_name='المشروع')
    expense_type = models.CharField('نوع المصروف', max_length=20, choices=EXPENSE_TYPES)
    description = models.TextField('الوصف')
    amount = models.DecimalField('المبلغ', max_digits=15, decimal_places=2)
    date = models.DateField('التاريخ')
    paid_to = models.CharField('مدفوع إلى', max_length=200, blank=True)
    receipt_number = models.CharField('رقم الإيصال', max_length=50, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='أنشأ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'مصروف مشروع'
        verbose_name_plural = 'مصروفات المشاريع'
        ordering = ['-date']

    def __str__(self):
        return f"{self.project.code} - {self.get_expense_type_display()} - {self.amount}"


class ProjectInvoice(models.Model):
    """فواتير المشروع"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('sent', 'مرسلة'),
        ('paid', 'مدفوعة'),
        ('overdue', 'متأخرة'),
        ('cancelled', 'ملغاة'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invoices', verbose_name='المشروع')
    invoice_number = models.CharField('رقم الفاتورة', max_length=50, unique=True)
    amount = models.DecimalField('المبلغ', max_digits=15, decimal_places=2)
    description = models.TextField('الوصف')
    date = models.DateField('التاريخ')
    due_date = models.DateField('تاريخ الاستحقاق')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='أنشأ بواسطة')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'فاتورة مشروع'
        verbose_name_plural = 'فواتير المشاريع'
        ordering = ['-date']

    def __str__(self):
        return f"{self.invoice_number} - {self.project.code}"
