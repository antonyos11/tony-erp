from django.db import models
from django.conf import settings

class QualityStandard(models.Model):
    """Quality standards definition"""
    name = models.CharField('اسم المعيار', max_length=200)
    code = models.CharField('الكود', max_length=50, unique=True)
    description = models.TextField('الوصف', blank=True)
    category = models.CharField('الفئة', max_length=100)
    min_value = models.DecimalField('القيمة الدنيا', max_digits=10, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField('القيمة القصوى', max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField('وحدة القياس', max_length=50, blank=True)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_standards')

    class Meta:
        verbose_name = 'معيار جودة'
        verbose_name_plural = 'معايير الجودة'

    def __str__(self):
        return f"{self.code} - {self.name}"

class InspectionType(models.Model):
    """Types of quality inspections"""
    name = models.CharField('اسم نوع الفحص', max_length=200)
    code = models.CharField('الكود', max_length=50, unique=True)
    description = models.TextField('الوصف', blank=True)
    standards = models.ManyToManyField(QualityStandard, related_name='inspection_types', blank=True)
    is_active = models.BooleanField('نشط', default=True)

    class Meta:
        verbose_name = 'نوع فحص'
        verbose_name_plural = 'أنواع الفحص'

    def __str__(self):
        return self.name

class QualityInspection(models.Model):
    """Quality inspection records"""
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'جاري الفحص'),
        ('passed', 'ناجح'),
        ('failed', 'فاشل'),
        ('conditional', 'مقبول بشروط'),
    ]
    
    code = models.CharField('رقم الفحص', max_length=50, unique=True)
    inspection_type = models.ForeignKey(InspectionType, on_delete=models.PROTECT, verbose_name='نوع الفحص')
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, verbose_name='المنتج', null=True, blank=True)
    batch_number = models.CharField('رقم الدفعة', max_length=100, blank=True)
    inspection_date = models.DateTimeField('تاريخ الفحص')
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='inspections', verbose_name='المفتش')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    overall_score = models.DecimalField('الدرجة الإجمالية', max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)

    class Meta:
        verbose_name = 'فحص جودة'
        verbose_name_plural = 'فحوصات الجودة'
        ordering = ['-inspection_date']

    def __str__(self):
        return f"{self.code} - {self.inspection_type}"

class InspectionResult(models.Model):
    """Individual inspection results"""
    inspection = models.ForeignKey(QualityInspection, on_delete=models.CASCADE, related_name='results')
    standard = models.ForeignKey(QualityStandard, on_delete=models.PROTECT, verbose_name='المعيار')
    measured_value = models.DecimalField('القيمة المقاسة', max_digits=10, decimal_places=2, null=True, blank=True)
    is_passed = models.BooleanField('ناجح', default=False)
    notes = models.TextField('ملاحظات', blank=True)

    class Meta:
        verbose_name = 'نتيجة فحص'
        verbose_name_plural = 'نتائج الفحص'

class QualityIssue(models.Model):
    """Quality issues and defects tracking"""
    SEVERITY_CHOICES = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('critical', 'حرجة'),
    ]
    STATUS_CHOICES = [
        ('open', 'مفتوح'),
        ('investigating', 'قيد التحقيق'),
        ('resolved', 'تم الحل'),
        ('closed', 'مغلق'),
    ]
    
    code = models.CharField('رقم المشكلة', max_length=50, unique=True)
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف')
    inspection = models.ForeignKey(QualityInspection, on_delete=models.SET_NULL, null=True, blank=True, related_name='issues')
    product = models.ForeignKey('inventory.Product', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المنتج')
    severity = models.CharField('الخطورة', max_length=20, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='open')
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reported_issues')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_issues')
    root_cause = models.TextField('السبب الجذري', blank=True)
    corrective_action = models.TextField('الإجراء التصحيحي', blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    resolved_at = models.DateTimeField('تاريخ الحل', null=True, blank=True)

    class Meta:
        verbose_name = 'مشكلة جودة'
        verbose_name_plural = 'مشاكل الجودة'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.title}"
