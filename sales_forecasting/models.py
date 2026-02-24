from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class ForecastPeriod(models.Model):
    """فترة التنبؤ"""
    PERIOD_TYPES = [
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('yearly', 'سنوي'),
    ]
    
    name = models.CharField('الاسم', max_length=200)
    period_type = models.CharField('نوع الفترة', max_length=20, choices=PERIOD_TYPES)
    start_date = models.DateField('تاريخ البداية')
    end_date = models.DateField('تاريخ النهاية')
    is_active = models.BooleanField('نشط', default=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='forecast_periods')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'فترة تنبؤ'
        verbose_name_plural = 'فترات التنبؤ'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['period_type', 'start_date']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"


class SalesForecast(models.Model):
    """التنبؤ بالمبيعات"""
    FORECAST_METHODS = [
        ('moving_average', 'المتوسط المتحرك'),
        ('exponential_smoothing', 'التمهيد الأسي'),
        ('linear_regression', 'الانحدار الخطي'),
        ('seasonal', 'التحليل الموسمي'),
        ('ai_ml', 'الذكاء الاصطناعي'),
        ('manual', 'يدوي'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
    ]
    
    period = models.ForeignKey(ForecastPeriod, on_delete=models.CASCADE, related_name='forecasts', verbose_name='الفترة')
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='forecasts', verbose_name='المنتج')
    
    # التنبؤ
    forecasted_quantity = models.DecimalField('الكمية المتوقعة', max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    forecasted_revenue = models.DecimalField('الإيراد المتوقع', max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    confidence_level = models.DecimalField('مستوى الثقة %', max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # الأرقام الفعلية (بعد انتهاء الفترة)
    actual_quantity = models.DecimalField('الكمية الفعلية', max_digits=15, decimal_places=2, null=True, blank=True)
    actual_revenue = models.DecimalField('الإيراد الفعلي', max_digits=15, decimal_places=2, null=True, blank=True)
    
    # الانحراف
    variance_quantity = models.DecimalField('انحراف الكمية', max_digits=15, decimal_places=2, null=True, blank=True)
    variance_revenue = models.DecimalField('انحراف الإيراد', max_digits=15, decimal_places=2, null=True, blank=True)
    accuracy_percentage = models.DecimalField('نسبة الدقة %', max_digits=5, decimal_places=2, null=True, blank=True)
    
    # معلومات إضافية
    method = models.CharField('طريقة التنبؤ', max_length=50, choices=FORECAST_METHODS, default='moving_average')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField('ملاحظات', blank=True)
    
    # البيانات التاريخية المستخدمة
    historical_data = models.JSONField('البيانات التاريخية', default=dict, blank=True)
    seasonality_factors = models.JSONField('عوامل الموسمية', default=dict, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_forecasts')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_forecasts')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تنبؤ بالمبيعات'
        verbose_name_plural = 'التنبؤات بالمبيعات'
        unique_together = ['period', 'product']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['period', 'product']),
            models.Index(fields=['status']),
            models.Index(fields=['method']),
        ]
    
    def __str__(self):
        return f"تنبؤ {self.product.name} - {self.period.name}"
    
    def calculate_variance(self):
        """حساب الانحراف بعد معرفة الأرقام الفعلية"""
        if self.actual_quantity is not None:
            self.variance_quantity = self.actual_quantity - self.forecasted_quantity
            if self.forecasted_quantity > 0:
                accuracy = (1 - abs(self.variance_quantity) / self.forecasted_quantity) * 100
                self.accuracy_percentage = max(Decimal('0'), accuracy)
        
        if self.actual_revenue is not None:
            self.variance_revenue = self.actual_revenue - self.forecasted_revenue
        
        self.save()


class DemandPattern(models.Model):
    """نمط الطلب"""
    PATTERN_TYPES = [
        ('stable', 'مستقر'),
        ('growing', 'نامي'),
        ('declining', 'متراجع'),
        ('seasonal', 'موسمي'),
        ('volatile', 'متقلب'),
    ]
    
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='demand_patterns', verbose_name='المنتج')
    pattern_type = models.CharField('نوع النمط', max_length=20, choices=PATTERN_TYPES)
    
    # التحليل الإحصائي
    average_daily_demand = models.DecimalField('متوسط الطلب اليومي', max_digits=15, decimal_places=2)
    standard_deviation = models.DecimalField('الانحراف المعياري', max_digits=15, decimal_places=2)
    coefficient_of_variation = models.DecimalField('معامل التباين', max_digits=10, decimal_places=4)
    
    # الموسمية
    has_seasonality = models.BooleanField('له موسمية', default=False)
    peak_months = models.JSONField('أشهر الذروة', default=list, blank=True)
    low_months = models.JSONField('أشهر الهدوء', default=list, blank=True)
    seasonality_index = models.JSONField('مؤشر الموسمية', default=dict, blank=True)
    
    # الاتجاه
    trend_direction = models.CharField('اتجاه الطلب', max_length=20, choices=[
        ('up', 'تصاعدي'),
        ('down', 'تنازلي'),
        ('flat', 'ثابت'),
    ], default='flat')
    trend_percentage = models.DecimalField('نسبة الاتجاه الشهري %', max_digits=5, decimal_places=2, default=0)
    
    # فترة التحليل
    analysis_start_date = models.DateField('بداية فترة التحليل')
    analysis_end_date = models.DateField('نهاية فترة التحليل')
    data_points_count = models.IntegerField('عدد نقاط البيانات', default=0)
    
    # التوصيات
    recommended_reorder_point = models.DecimalField('نقطة إعادة الطلب الموصى بها', max_digits=15, decimal_places=2)
    recommended_safety_stock = models.DecimalField('المخزون الاحتياطي الموصى به', max_digits=15, decimal_places=2)
    recommended_order_quantity = models.DecimalField('كمية الطلب الموصى بها', max_digits=15, decimal_places=2)
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'نمط طلب'
        verbose_name_plural = 'أنماط الطلب'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['pattern_type']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.get_pattern_type_display()}"


class InventoryRecommendation(models.Model):
    """توصية المخزون"""
    RECOMMENDATION_TYPES = [
        ('stock_up', 'زيادة المخزون'),
        ('reduce_stock', 'تقليل المخزون'),
        ('maintain', 'الحفاظ على المستوى الحالي'),
        ('urgent_order', 'طلب عاجل'),
        ('slow_moving', 'بطيء الحركة - تقليل المخزون'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('critical', 'حرجة'),
    ]
    
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='inventory_recommendations', verbose_name='المنتج')
    recommendation_type = models.CharField('نوع التوصية', max_length=30, choices=RECOMMENDATION_TYPES)
    priority = models.CharField('الأولوية', max_length=20, choices=PRIORITY_LEVELS)
    
    # الأرقام الحالية
    current_stock = models.DecimalField('المخزون الحالي', max_digits=15, decimal_places=2)
    current_reorder_point = models.DecimalField('نقطة إعادة الطلب الحالية', max_digits=15, decimal_places=2)
    
    # التوصيات
    recommended_stock_level = models.DecimalField('مستوى المخزون الموصى به', max_digits=15, decimal_places=2)
    recommended_order_quantity = models.DecimalField('كمية الطلب الموصى بها', max_digits=15, decimal_places=2)
    estimated_stockout_date = models.DateField('تاريخ نفاذ المخزون المتوقع', null=True, blank=True)
    
    # المبررات
    reason = models.TextField('السبب')
    forecast_data = models.ForeignKey(SalesForecast, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='بيانات التنبؤ')
    demand_pattern = models.ForeignKey(DemandPattern, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='نمط الطلب')
    
    # الحالة
    status = models.CharField('الحالة', max_length=20, choices=[
        ('pending', 'معلق'),
        ('accepted', 'مقبول'),
        ('rejected', 'مرفوض'),
        ('implemented', 'تم التنفيذ'),
    ], default='pending')
    
    action_taken = models.TextField('الإجراء المتخذ', blank=True)
    action_date = models.DateTimeField('تاريخ الإجراء', null=True, blank=True)
    action_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_actions')
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'توصية مخزون'
        verbose_name_plural = 'توصيات المخزون'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['recommendation_type']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.get_recommendation_type_display()}"


class ForecastAccuracyMetrics(models.Model):
    """مقاييس دقة التنبؤ"""
    period = models.ForeignKey(ForecastPeriod, on_delete=models.CASCADE, related_name='accuracy_metrics', verbose_name='الفترة')
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, null=True, blank=True, verbose_name='المنتج')
    
    # المقاييس
    total_forecasts = models.IntegerField('إجمالي التنبؤات', default=0)
    accurate_forecasts = models.IntegerField('التنبؤات الدقيقة', default=0)
    overall_accuracy = models.DecimalField('الدقة الإجمالية %', max_digits=5, decimal_places=2)
    
    mean_absolute_error = models.DecimalField('متوسط الخطأ المطلق (MAE)', max_digits=15, decimal_places=2)
    mean_squared_error = models.DecimalField('متوسط مربع الخطأ (MSE)', max_digits=15, decimal_places=2)
    root_mean_squared_error = models.DecimalField('الجذر التربيعي لمتوسط مربع الخطأ (RMSE)', max_digits=15, decimal_places=2)
    mean_absolute_percentage_error = models.DecimalField('متوسط نسبة الخطأ المطلق (MAPE) %', max_digits=5, decimal_places=2)
    
    # بيانات إضافية
    best_method = models.CharField('أفضل طريقة', max_length=50, blank=True)
    worst_method = models.CharField('أسوأ طريقة', max_length=50, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'مقاييس دقة التنبؤ'
        verbose_name_plural = 'مقاييس دقة التنبؤ'
        unique_together = ['period', 'product']
        ordering = ['-created_at']
    
    def __str__(self):
        if self.product:
            return f"دقة {self.product.name} - {self.period.name}: {self.overall_accuracy}%"
        return f"دقة إجمالية - {self.period.name}: {self.overall_accuracy}%"
