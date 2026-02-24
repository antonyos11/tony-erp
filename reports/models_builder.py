"""
نظام بناء التقارير المتقدم (Advanced Report Builder)
يوفر واجهة سحب وإسقاط لتصميم تقارير مخصصة
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import json


class ReportTemplate(models.Model):
    """قالب تقرير قابل لإعادة الاستخدام"""
    
    CATEGORY_CHOICES = [
        ('sales', 'المبيعات'),
        ('purchases', 'المشتريات'),
        ('inventory', 'المخزون'),
        ('accounting', 'المحاسبة'),
        ('hr', 'الموارد البشرية'),
        ('production', 'الإنتاج'),
        ('crm', 'إدارة العملاء'),
        ('custom', 'مخصص'),
    ]
    
    OUTPUT_FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('html', 'HTML'),
        ('json', 'JSON'),
    ]
    
    name = models.CharField('اسم القالب', max_length=200)
    description = models.TextField('الوصف', blank=True)
    category = models.CharField('الفئة', max_length=50, choices=CATEGORY_CHOICES)
    
    # المستخدم المنشئ
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_report_templates',
        verbose_name='المنشئ'
    )
    
    # الأذونات
    is_public = models.BooleanField('عام', default=False, help_text='متاح لجميع المستخدمين')
    allowed_users = models.ManyToManyField(
        User, 
        blank=True,
        related_name='allowed_report_templates',
        verbose_name='المستخدمون المسموح لهم'
    )
    allowed_groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name='allowed_report_templates',
        verbose_name='المجموعات المسموح لها'
    )
    
    # تكوين التقرير (JSON)
    data_source = models.CharField('مصدر البيانات', max_length=100, help_text='اسم الموديل أو View')
    fields_config = models.TextField('تكوين الحقول', help_text='JSON configuration')
    filters_config = models.TextField('تكوين الفلاتر', blank=True, default='[]')
    grouping_config = models.TextField('تكوين التجميع', blank=True, default='[]')
    sorting_config = models.TextField('تكوين الترتيب', blank=True, default='[]')
    
    # التنسيق والعرض
    layout = models.CharField('التخطيط', max_length=20, choices=[
        ('table', 'جدول'),
        ('cards', 'بطاقات'),
        ('chart', 'رسم بياني'),
        ('mixed', 'مختلط'),
    ], default='table')
    
    chart_type = models.CharField('نوع الرسم البياني', max_length=50, blank=True, choices=[
        ('bar', 'أعمدة'),
        ('line', 'خطي'),
        ('pie', 'دائري'),
        ('area', 'مساحة'),
        ('scatter', 'نقطي'),
    ])
    
    # الألوان والتنسيق
    theme = models.CharField('السمة', max_length=50, default='default')
    custom_css = models.TextField('CSS مخصص', blank=True)
    
    # صيغ الإخراج المدعومة
    supported_formats = models.CharField(
        'صيغ الإخراج',
        max_length=100,
        default='pdf,excel,csv',
        help_text='مفصولة بفاصلة'
    )
    
    # الجدولة
    is_scheduled = models.BooleanField('مجدول', default=False)
    schedule_frequency = models.CharField('تكرار الجدولة', max_length=20, blank=True, choices=[
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('yearly', 'سنوي'),
    ])
    schedule_time = models.TimeField('وقت التنفيذ', null=True, blank=True)
    schedule_recipients = models.TextField('المستلمون', blank=True, help_text='بريد إلكتروني، مفصول بفاصلة')
    
    # البيانات الوصفية
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    last_run_at = models.DateTimeField('آخر تشغيل', null=True, blank=True)
    run_count = models.IntegerField('عدد مرات التشغيل', default=0)
    
    class Meta:
        verbose_name = 'قالب تقرير'
        verbose_name_plural = 'قوالب التقارير'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_fields_config(self):
        """استرجاع تكوين الحقول كـ Python object"""
        try:
            return json.loads(self.fields_config)
        except:
            return []
    
    def get_filters_config(self):
        """استرجاع تكوين الفلاتر"""
        try:
            return json.loads(self.filters_config)
        except:
            return []
    
    def get_supported_formats_list(self):
        """قائمة صيغ الإخراج المدعومة"""
        return [f.strip() for f in self.supported_formats.split(',') if f.strip()]


class ReportExecution(models.Model):
    """سجل تنفيذ التقارير"""
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('running', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
        ('cancelled', 'ملغي'),
    ]
    
    template = models.ForeignKey(
        ReportTemplate, 
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='القالب'
    )
    
    executed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='المنفذ'
    )
    
    # معاملات التنفيذ
    parameters = models.TextField('المعاملات', blank=True, help_text='JSON parameters')
    
    # حالة التنفيذ
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField('بداية التنفيذ', null=True, blank=True)
    completed_at = models.DateTimeField('نهاية التنفيذ', null=True, blank=True)
    
    # النتائج
    output_format = models.CharField('صيغة الإخراج', max_length=20)
    output_file = models.FileField(
        'ملف الإخراج',
        upload_to='reports/output/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['pdf', 'xlsx', 'csv', 'html', 'json'])]
    )
    output_file_size = models.IntegerField('حجم الملف (بايت)', null=True, blank=True)
    
    # الإحصائيات
    rows_processed = models.IntegerField('عدد الصفوف', null=True, blank=True)
    execution_time = models.FloatField('وقت التنفيذ (ثواني)', null=True, blank=True)
    
    # الأخطاء
    error_message = models.TextField('رسالة الخطأ', blank=True)
    error_traceback = models.TextField('تتبع الخطأ', blank=True)
    
    # الجدولة
    is_scheduled = models.BooleanField('مجدول', default=False)
    scheduled_at = models.DateTimeField('موعد الجدولة', null=True, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تنفيذ تقرير'
        verbose_name_plural = 'تنفيذات التقارير'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template', '-created_at']),
            models.Index(fields=['executed_by', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['is_scheduled', 'scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.template.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_parameters(self):
        """استرجاع المعاملات كـ Python object"""
        try:
            return json.loads(self.parameters)
        except:
            return {}


class ReportField(models.Model):
    """حقل في التقرير"""
    
    FIELD_TYPE_CHOICES = [
        ('text', 'نص'),
        ('number', 'رقم'),
        ('date', 'تاريخ'),
        ('datetime', 'تاريخ ووقت'),
        ('boolean', 'منطقي'),
        ('choice', 'اختيار'),
        ('foreign_key', 'مرجع خارجي'),
        ('calculated', 'محسوب'),
    ]
    
    AGGREGATION_CHOICES = [
        ('none', 'بدون'),
        ('sum', 'مجموع'),
        ('avg', 'متوسط'),
        ('count', 'عدد'),
        ('min', 'أصغر قيمة'),
        ('max', 'أكبر قيمة'),
    ]
    
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='fields',
        verbose_name='القالب'
    )
    
    name = models.CharField('اسم الحقل', max_length=100)
    label = models.CharField('التسمية', max_length=200)
    field_type = models.CharField('نوع الحقل', max_length=20, choices=FIELD_TYPE_CHOICES)
    
    # المصدر
    source_field = models.CharField('حقل المصدر', max_length=200, help_text='اسم الحقل في الموديل')
    
    # الحسابات
    is_calculated = models.BooleanField('محسوب', default=False)
    calculation_formula = models.TextField('صيغة الحساب', blank=True)
    
    # التجميع
    aggregation = models.CharField('التجميع', max_length=20, choices=AGGREGATION_CHOICES, default='none')
    
    # العرض
    is_visible = models.BooleanField('ظاهر', default=True)
    display_order = models.IntegerField('ترتيب العرض', default=0)
    width = models.IntegerField('العرض (%)', null=True, blank=True)
    alignment = models.CharField('المحاذاة', max_length=10, choices=[
        ('left', 'يسار'),
        ('center', 'وسط'),
        ('right', 'يمين'),
    ], default='left')
    
    # التنسيق
    format_string = models.CharField('صيغة التنسيق', max_length=100, blank=True, help_text='مثال: {:.2f} للأرقام')
    prefix = models.CharField('بادئة', max_length=50, blank=True)
    suffix = models.CharField('لاحقة', max_length=50, blank=True)
    
    # التلوين الشرطي
    conditional_formatting = models.TextField('التنسيق الشرطي', blank=True, help_text='JSON rules')
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'حقل تقرير'
        verbose_name_plural = 'حقول التقارير'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.template.name} - {self.label}"


class ReportFilter(models.Model):
    """فلتر في التقرير"""
    
    OPERATOR_CHOICES = [
        ('equals', 'يساوي'),
        ('not_equals', 'لا يساوي'),
        ('greater_than', 'أكبر من'),
        ('greater_than_equal', 'أكبر من أو يساوي'),
        ('less_than', 'أصغر من'),
        ('less_than_equal', 'أصغر من أو يساوي'),
        ('contains', 'يحتوي'),
        ('not_contains', 'لا يحتوي'),
        ('starts_with', 'يبدأ بـ'),
        ('ends_with', 'ينتهي بـ'),
        ('in', 'ضمن'),
        ('not_in', 'ليس ضمن'),
        ('between', 'بين'),
        ('is_null', 'فارغ'),
        ('is_not_null', 'غير فارغ'),
    ]
    
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='filters',
        verbose_name='القالب'
    )
    
    field_name = models.CharField('اسم الحقل', max_length=200)
    operator = models.CharField('المشغل', max_length=30, choices=OPERATOR_CHOICES)
    value = models.TextField('القيمة', blank=True)
    
    # الفلاتر المتقدمة
    is_dynamic = models.BooleanField('ديناميكي', default=False, help_text='يتم تحديثه عند التنفيذ')
    dynamic_value_source = models.CharField('مصدر القيمة الديناميكية', max_length=100, blank=True)
    
    # المجموعات المنطقية
    group_id = models.IntegerField('معرف المجموعة', default=0)
    logical_operator = models.CharField('مشغل منطقي', max_length=5, choices=[
        ('AND', 'و'),
        ('OR', 'أو'),
    ], default='AND')
    
    display_order = models.IntegerField('ترتيب العرض', default=0)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'فلتر تقرير'
        verbose_name_plural = 'فلاتر التقارير'
        ordering = ['group_id', 'display_order']
    
    def __str__(self):
        return f"{self.template.name} - {self.field_name} {self.operator}"


class SavedReport(models.Model):
    """تقرير محفوظ (snapshot)"""
    
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='saved_reports',
        verbose_name='القالب'
    )
    
    execution = models.OneToOneField(
        ReportExecution,
        on_delete=models.CASCADE,
        related_name='saved_report',
        verbose_name='التنفيذ'
    )
    
    name = models.CharField('الاسم', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    # البيانات المحفوظة
    data_snapshot = models.TextField('البيانات', help_text='JSON snapshot')
    
    # المشاركة
    is_shared = models.BooleanField('مشارك', default=False)
    shared_with = models.ManyToManyField(
        User,
        blank=True,
        related_name='shared_saved_reports',
        verbose_name='مشارك مع'
    )
    
    # الأرشفة
    is_archived = models.BooleanField('مؤرشف', default=False)
    archived_at = models.DateTimeField('تاريخ الأرشفة', null=True, blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='المنشئ'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تقرير محفوظ'
        verbose_name_plural = 'تقارير محفوظة'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
