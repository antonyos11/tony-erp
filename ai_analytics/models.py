"""
نماذج تحليلات الذكاء الاصطناعي
AI Analytics Models
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class PredictionModel(models.Model):
    """نموذج التنبؤ"""
    
    MODEL_TYPES = [
        ('sales_forecast', 'توقع المبيعات'),
        ('demand_prediction', 'توقع الطلب'),
        ('churn_prediction', 'توقع فقدان العملاء'),
        ('price_optimization', 'تحسين الأسعار'),
        ('inventory_optimization', 'تحسين المخزون'),
        ('customer_segmentation', 'تقسيم العملاء'),
        ('anomaly_detection', 'كشف الشذوذ'),
    ]
    
    name = models.CharField('الاسم', max_length=200)
    description = models.TextField('الوصف', blank=True)
    model_type = models.CharField('نوع النموذج', max_length=30, choices=MODEL_TYPES)
    
    # الإعدادات
    config = models.JSONField('الإعدادات', default=dict)
    parameters = models.JSONField('المعلمات', default=dict)
    
    # التدريب
    is_trained = models.BooleanField('مدرب', default=False)
    last_trained = models.DateTimeField('آخر تدريب', null=True, blank=True)
    training_accuracy = models.FloatField('دقة التدريب', null=True, blank=True)
    
    # الحالة
    is_active = models.BooleanField('نشط', default=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'نموذج تنبؤ'
        verbose_name_plural = 'نماذج التنبؤ'
    
    def __str__(self):
        return self.name


class Prediction(models.Model):
    """التنبؤ"""
    
    uuid = models.UUIDField('المعرف الفريد', default=uuid.uuid4, unique=True)
    model = models.ForeignKey(
        PredictionModel,
        on_delete=models.CASCADE,
        related_name='predictions',
        verbose_name='النموذج'
    )
    
    # البيانات المدخلة
    input_data = models.JSONField('البيانات المدخلة', default=dict)
    
    # النتائج
    prediction_value = models.JSONField('قيمة التنبؤ', default=dict)
    confidence = models.FloatField('الثقة %', default=0)
    
    # التحليل
    analysis = models.TextField('التحليل', blank=True)
    recommendations = models.JSONField('التوصيات', default=list)
    
    # الدقة الفعلية (للتحقق لاحقاً)
    actual_value = models.JSONField('القيمة الفعلية', null=True, blank=True)
    accuracy = models.FloatField('الدقة الفعلية', null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تنبؤ'
        verbose_name_plural = 'التنبؤات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.model.name} - {self.created_at}"


class AIInsight(models.Model):
    """رؤى الذكاء الاصطناعي"""
    
    INSIGHT_TYPES = [
        ('trend', 'اتجاه'),
        ('anomaly', 'شذوذ'),
        ('opportunity', 'فرصة'),
        ('risk', 'مخاطرة'),
        ('recommendation', 'توصية'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('critical', 'حرج'),
    ]
    
    title = models.CharField('العنوان', max_length=300)
    description = models.TextField('الوصف')
    insight_type = models.CharField('نوع الرؤية', max_length=20, choices=INSIGHT_TYPES)
    priority = models.CharField('الأولوية', max_length=20, choices=PRIORITY_LEVELS, default='medium')
    
    # البيانات
    data = models.JSONField('البيانات', default=dict)
    metrics = models.JSONField('المقاييس', default=dict)
    
    # الإجراءات المقترحة
    suggested_actions = models.JSONField('الإجراءات المقترحة', default=list)
    
    # التأثير
    estimated_impact = models.CharField('التأثير المتوقع', max_length=200, blank=True)
    
    # الحالة
    is_read = models.BooleanField('مقروء', default=False)
    is_actioned = models.BooleanField('تم اتخاذ إجراء', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    expires_at = models.DateTimeField('تنتهي في', null=True, blank=True)
    
    class Meta:
        verbose_name = 'رؤية ذكية'
        verbose_name_plural = 'الرؤى الذكية'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class DataAnalysis(models.Model):
    """تحليل البيانات"""
    
    ANALYSIS_TYPES = [
        ('descriptive', 'وصفي'),
        ('diagnostic', 'تشخيصي'),
        ('predictive', 'تنبؤي'),
        ('prescriptive', 'توصيفي'),
    ]
    
    title = models.CharField('العنوان', max_length=200)
    analysis_type = models.CharField('نوع التحليل', max_length=20, choices=ANALYSIS_TYPES)
    
    # مصدر البيانات
    data_source = models.CharField('مصدر البيانات', max_length=200)
    query_params = models.JSONField('معلمات الاستعلام', default=dict)
    date_range = models.JSONField('نطاق التاريخ', default=dict)
    
    # النتائج
    results = models.JSONField('النتائج', default=dict)
    summary = models.TextField('الملخص', blank=True)
    
    # الرسوم البيانية
    charts_config = models.JSONField('تكوين الرسوم', default=list)
    
    # الذكاء الاصطناعي
    ai_insights = models.TextField('رؤى AI', blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تحليل بيانات'
        verbose_name_plural = 'تحليلات البيانات'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
