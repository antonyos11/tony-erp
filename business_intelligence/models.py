"""
نظام الذكاء الاصطناعي والبيانات الضخمة
Business Intelligence and Advanced Analytics
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class Dashboard(models.Model):
    """لوحات المعلومات التفاعلية"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('الاسم'), max_length=200)
    description = models.TextField(_('الوصف'), blank=True)
    
    # الخصائص
    is_public = models.BooleanField(_('عام'), default=False)
    is_default = models.BooleanField(_('افتراضي'), default=False)
    
    # الملكية والصلاحيات
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='dashboards')
    allowed_users = models.ManyToManyField('auth.User', blank=True, related_name='accessible_dashboards')
    
    # الإعدادات
    layout = models.CharField(_('التخطيط'), max_length=50,
                            choices=[('grid', _('شبكة')), ('flex', _('مرن')), ('custom', _('مخصص'))])
    theme = models.CharField(_('المظهر'), max_length=50,
                           choices=[('light', _('فاتح')), ('dark', _('غامق')), ('auto', _('تلقائي'))])
    
    # التحديث التلقائي
    auto_refresh = models.BooleanField(_('تحديث تلقائي'), default=True)
    refresh_interval = models.IntegerField(_('فترة التحديث (ثوان)'), default=300)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('لوحة معلومات')
        verbose_name_plural = _('لوحات المعلومات')
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name


class Widget(models.Model):
    """الأدوات على لوحات المعلومات"""
    
    WIDGET_TYPE_CHOICES = [
        ('kpi', _('مؤشر أداء رئيسي')),
        ('chart', _('رسم بياني')),
        ('table', _('جدول')),
        ('gauge', _('مقياس')),
        ('map', _('خريطة')),
        ('timeline', _('خط زمني')),
        ('heatmap', _('خريطة حرارية')),
        ('custom', _('مخصص')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='widgets')
    
    title = models.CharField(_('العنوان'), max_length=200)
    widget_type = models.CharField(_('نوع الأداة'), max_length=50, choices=WIDGET_TYPE_CHOICES)
    
    # البيانات
    data_source = models.CharField(_('مصدر البيانات'), max_length=200)
    query = models.TextField(_('الاستعلام'), blank=True)
    
    # العرض
    position_x = models.IntegerField(_('موقع X'))
    position_y = models.IntegerField(_('موقع Y'))
    width = models.IntegerField(_('العرض'))
    height = models.IntegerField(_('الارتفاع'))
    
    # الإعدادات
    settings = models.JSONField(_('الإعدادات'), default=dict, blank=True)
    
    # التحديث
    refresh_interval = models.IntegerField(_('فترة التحديث'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('أداة')
        verbose_name_plural = _('الأدوات')
        ordering = ['position_y', 'position_x']
    
    def __str__(self):
        return f"{self.dashboard.name} - {self.title}"


class Forecast(models.Model):
    """التنبؤات بالذكاء الاصطناعي"""
    
    FORECAST_TYPE_CHOICES = [
        ('revenue', _('الإيرادات')),
        ('demand', _('الطلب')),
        ('churn', _('معدل الفقدان')),
        ('inventory', _('المخزون')),
        ('customer_value', _('قيمة العميل')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    forecast_type = models.CharField(_('نوع التنبؤ'), max_length=50, choices=FORECAST_TYPE_CHOICES)
    
    # الفترة
    period_start = models.DateField(_('بداية الفترة'))
    period_end = models.DateField(_('نهاية الفترة'))
    
    # التنبؤات
    predicted_value = models.DecimalField(_('القيمة المتنبأ بها'), max_digits=15, decimal_places=2)
    confidence_level = models.DecimalField(_('مستوى الثقة %'), max_digits=5, decimal_places=2)
    lower_bound = models.DecimalField(_('الحد الأدنى'), max_digits=15, decimal_places=2)
    upper_bound = models.DecimalField(_('الحد الأقصى'), max_digits=15, decimal_places=2)
    
    # النتائج الفعلية
    actual_value = models.DecimalField(_('القيمة الفعلية'), max_digits=15, decimal_places=2, null=True, blank=True)
    accuracy = models.DecimalField(_('الدقة %'), max_digits=5, decimal_places=2, null=True, blank=True)
    
    # تفاصيل النموذج
    model_used = models.CharField(_('النموذج المستخدم'), max_length=100)
    training_data_points = models.IntegerField(_('نقاط البيانات المستخدمة'))
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('تنبؤ')
        verbose_name_plural = _('التنبؤات')
        ordering = ['-period_end']
        indexes = [
            models.Index(fields=['forecast_type']),
            models.Index(fields=['period_end']),
        ]
    
    def __str__(self):
        return f"{self.get_forecast_type_display()} - {self.period_end}"


class PredictiveAnalysis(models.Model):
    """التحليلات التنبؤية"""
    
    ANALYSIS_TYPE_CHOICES = [
        ('customer_segmentation', _('تقسيم العملاء')),
        ('churn_risk', _('خطر فقدان العميل')),
        ('next_best_action', _('أفضل إجراء تالي')),
        ('lifetime_value', _('القيمة مدى الحياة')),
        ('anomaly', _('كشف الشذوذ')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis_type = models.CharField(_('نوع التحليل'), max_length=50, choices=ANALYSIS_TYPE_CHOICES)
    
    # البيانات
    entity_type = models.CharField(_('نوع الكيان'), max_length=100)
    entity_id = models.CharField(_('رقم الكيان'), max_length=100)
    
    # النتائج
    score = models.DecimalField(_('الدرجة'), max_digits=5, decimal_places=2)
    segment = models.CharField(_('القطاع'), max_length=100, blank=True)
    recommendation = models.TextField(_('التوصية'))
    
    # الأنماط المكتشفة
    patterns = models.JSONField(_('الأنماط'), default=dict)
    
    analysis_date = models.DateField(_('تاريخ التحليل'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('تحليل تنبؤي')
        verbose_name_plural = _('التحليلات التنبؤية')
        ordering = ['-analysis_date']
    
    def __str__(self):
        return f"{self.get_analysis_type_display()} - {self.entity_type}"


class Report(models.Model):
    """التقارير المتقدمة"""
    
    REPORT_TYPE_CHOICES = [
        ('sales', _('المبيعات')),
        ('financial', _('مالي')),
        ('operational', _('تشغيلي')),
        ('customer', _('العملاء')),
        ('inventory', _('المخزون')),
        ('custom', _('مخصص')),
    ]
    
    FREQUENCY_CHOICES = [
        ('daily', _('يومي')),
        ('weekly', _('أسبوعي')),
        ('monthly', _('شهري')),
        ('quarterly', _('ربع سنوي')),
        ('annual', _('سنوي')),
        ('on_demand', _('عند الطلب')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('الاسم'), max_length=200)
    report_type = models.CharField(_('نوع التقرير'), max_length=50, choices=REPORT_TYPE_CHOICES)
    
    # الإعدادات
    frequency = models.CharField(_('التكرار'), max_length=20, choices=FREQUENCY_CHOICES)
    schedule = models.CharField(_('الجدولة'), max_length=100, blank=True,
                               help_text='مثل: 0 9 * * 1 (كل يوم اثنين الساعة 9 صباحاً)')
    
    # المستقبلون
    recipients = models.ManyToManyField('auth.User', blank=True, related_name='reports')
    recipient_emails = models.TextField(_('عناوين بريد إضافية'), blank=True)
    
    # الملفات
    last_report_file = models.FileField(_('آخر تقرير'), upload_to='reports/', blank=True)
    last_generated = models.DateTimeField(_('آخر توليد'), null=True, blank=True)
    
    # الخصائص
    is_active = models.BooleanField(_('نشط'), default=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('تقرير')
        verbose_name_plural = _('التقارير')
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
