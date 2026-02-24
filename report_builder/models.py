"""
نماذج منشئ التقارير المرئي
Visual Report Builder Models
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
import uuid

User = get_user_model()


class DataSource(models.Model):
    """مصدر البيانات"""
    
    SOURCE_TYPES = [
        ('model', 'نموذج Django'),
        ('sql', 'استعلام SQL'),
        ('api', 'واجهة API'),
        ('file', 'ملف'),
    ]
    
    name = models.CharField('الاسم', max_length=200)
    description = models.TextField('الوصف', blank=True)
    source_type = models.CharField('نوع المصدر', max_length=20, choices=SOURCE_TYPES)
    
    # لنماذج Django
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='النموذج'
    )
    
    # للاستعلامات SQL
    sql_query = models.TextField('استعلام SQL', blank=True)
    
    # للـ API
    api_url = models.URLField('رابط API', blank=True)
    api_method = models.CharField('طريقة الطلب', max_length=10, default='GET')
    api_headers = models.JSONField('الرؤوس', default=dict)
    
    # للملفات
    file = models.FileField('الملف', upload_to='report_builder/sources/', blank=True)
    
    # الحقول المتاحة
    available_fields = models.JSONField('الحقول المتاحة', default=list)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'مصدر بيانات'
        verbose_name_plural = 'مصادر البيانات'
    
    def __str__(self):
        return self.name


class Report(models.Model):
    """التقرير"""
    
    REPORT_TYPES = [
        ('table', 'جدول'),
        ('chart', 'رسم بياني'),
        ('pivot', 'جدول محوري'),
        ('card', 'بطاقات'),
        ('mixed', 'مختلط'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('published', 'منشور'),
        ('archived', 'مؤرشف'),
    ]
    
    uuid = models.UUIDField('المعرف الفريد', default=uuid.uuid4, unique=True)
    name = models.CharField('اسم التقرير', max_length=200)
    description = models.TextField('الوصف', blank=True)
    report_type = models.CharField('نوع التقرير', max_length=20, choices=REPORT_TYPES, default='table')
    
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='مصدر البيانات'
    )
    
    # تكوين التقرير
    config = models.JSONField('التكوين', default=dict)
    
    # الفلاتر
    filters = models.JSONField('الفلاتر', default=list)
    
    # الترتيب
    sorting = models.JSONField('الترتيب', default=list)
    
    # التجميع
    grouping = models.JSONField('التجميع', default=list)
    
    # الأعمدة المحددة
    selected_columns = models.JSONField('الأعمدة', default=list)
    
    # حسابات مخصصة
    calculations = models.JSONField('الحسابات', default=list)
    
    # التنسيق
    styling = models.JSONField('التنسيق', default=dict)
    
    # إعدادات التصدير
    export_config = models.JSONField('إعدادات التصدير', default=dict)
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # المشاركة
    is_public = models.BooleanField('عام', default=False)
    shared_with = models.ManyToManyField(
        User,
        blank=True,
        related_name='shared_reports',
        verbose_name='مشارك مع'
    )
    
    # الجدولة
    is_scheduled = models.BooleanField('مجدول', default=False)
    schedule_config = models.JSONField('تكوين الجدول', default=dict)
    
    # الإحصائيات
    view_count = models.IntegerField('عدد المشاهدات', default=0)
    last_viewed = models.DateTimeField('آخر مشاهدة', null=True, blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='builder_created_reports',
        verbose_name='أنشئ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تقرير'
        verbose_name_plural = 'التقارير'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name


class ReportWidget(models.Model):
    """عنصر في التقرير"""
    
    WIDGET_TYPES = [
        ('table', 'جدول'),
        ('bar_chart', 'رسم أعمدة'),
        ('line_chart', 'رسم خطي'),
        ('pie_chart', 'رسم دائري'),
        ('area_chart', 'رسم مساحة'),
        ('donut_chart', 'رسم دونات'),
        ('card', 'بطاقة'),
        ('gauge', 'مقياس'),
        ('map', 'خريطة'),
        ('text', 'نص'),
        ('image', 'صورة'),
    ]
    
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='widgets',
        verbose_name='التقرير'
    )
    
    widget_type = models.CharField('نوع العنصر', max_length=20, choices=WIDGET_TYPES)
    title = models.CharField('العنوان', max_length=200, blank=True)
    
    # الموقع
    position_x = models.IntegerField('الموقع X', default=0)
    position_y = models.IntegerField('الموقع Y', default=0)
    width = models.IntegerField('العرض', default=6)
    height = models.IntegerField('الارتفاع', default=4)
    
    # التكوين
    config = models.JSONField('التكوين', default=dict)
    
    # البيانات
    data_config = models.JSONField('تكوين البيانات', default=dict)
    
    # التنسيق
    styling = models.JSONField('التنسيق', default=dict)
    
    order = models.IntegerField('الترتيب', default=0)
    is_visible = models.BooleanField('مرئي', default=True)
    
    class Meta:
        verbose_name = 'عنصر تقرير'
        verbose_name_plural = 'عناصر التقرير'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.get_widget_type_display()} - {self.report.name}"


class ReportTemplate(models.Model):
    """قالب التقرير"""
    
    name = models.CharField('الاسم', max_length=200)
    description = models.TextField('الوصف', blank=True)
    preview_image = models.ImageField('صورة المعاينة', upload_to='report_builder/templates/', blank=True)
    
    # التكوين
    config = models.JSONField('التكوين', default=dict)
    widgets_config = models.JSONField('تكوين العناصر', default=list)
    
    is_system = models.BooleanField('قالب نظام', default=False)
    is_active = models.BooleanField('نشط', default=True)
    
    category = models.CharField('الفئة', max_length=100, blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='أنشئ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'قالب تقرير'
        verbose_name_plural = 'قوالب التقارير'
    
    def __str__(self):
        return self.name


class ScheduledReport(models.Model):
    """التقارير المجدولة"""
    
    FREQUENCY_CHOICES = [
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('yearly', 'سنوي'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('html', 'HTML'),
    ]
    
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='التقرير'
    )
    
    frequency = models.CharField('التكرار', max_length=20, choices=FREQUENCY_CHOICES)
    day_of_week = models.IntegerField('يوم الأسبوع', null=True, blank=True)  # 0-6
    day_of_month = models.IntegerField('يوم الشهر', null=True, blank=True)  # 1-31
    time_of_day = models.TimeField('وقت التنفيذ')
    
    # التصدير
    export_format = models.CharField('صيغة التصدير', max_length=10, choices=FORMAT_CHOICES)
    
    # الإرسال
    send_email = models.BooleanField('إرسال بالبريد', default=True)
    email_recipients = models.JSONField('المستلمون', default=list)
    email_subject = models.CharField('موضوع البريد', max_length=200, blank=True)
    email_body = models.TextField('نص البريد', blank=True)
    
    # الحفظ
    save_to_storage = models.BooleanField('حفظ في التخزين', default=False)
    storage_path = models.CharField('مسار الحفظ', max_length=500, blank=True)
    
    is_active = models.BooleanField('نشط', default=True)
    last_run = models.DateTimeField('آخر تشغيل', null=True, blank=True)
    next_run = models.DateTimeField('التشغيل القادم', null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تقرير مجدول'
        verbose_name_plural = 'التقارير المجدولة'
    
    def __str__(self):
        return f"{self.report.name} - {self.get_frequency_display()}"


class ReportExecution(models.Model):
    """سجل تنفيذ التقارير"""
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('running', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
    ]
    
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='التقرير'
    )
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    parameters = models.JSONField('المعلمات', default=dict)
    result_file = models.FileField('ملف النتيجة', upload_to='report_builder/results/', blank=True)
    
    rows_count = models.IntegerField('عدد الصفوف', default=0)
    execution_time = models.FloatField('وقت التنفيذ (ثانية)', default=0)
    
    error_message = models.TextField('رسالة الخطأ', blank=True)
    
    executed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='builder_report_executions', verbose_name='نفذ بواسطة')
    started_at = models.DateTimeField('بدأ في', auto_now_add=True)
    completed_at = models.DateTimeField('اكتمل في', null=True, blank=True)
    
    class Meta:
        verbose_name = 'تنفيذ تقرير'
        verbose_name_plural = 'تنفيذات التقارير'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.report.name} - {self.started_at}"
