from django.db import models
from decimal import Decimal


class UtilityMeter(models.Model):
    """عداد المرافق"""
    meter_number = models.CharField('رقم العداد', max_length=100, unique=True)
    utility_type = models.CharField('نوع المرفق', max_length=20, choices=[
        ('electricity', 'كهرباء'), ('water', 'مياه'), ('gas', 'غاز'), ('other', 'أخرى')
    ])
    location = models.CharField('الموقع', max_length=200)
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='utility_meters')
    
    installation_date = models.DateField('تاريخ التركيب')
    is_active = models.BooleanField('نشط', default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'عداد مرافق'
        verbose_name_plural = 'عدادات المرافق'
    
    def __str__(self):
        return f"{self.meter_number} - {self.get_utility_type_display()}"


class UtilityReading(models.Model):
    """قراءة العداد"""
    meter = models.ForeignKey(UtilityMeter, on_delete=models.CASCADE, related_name='readings')
    reading_date = models.DateField('تاريخ القراءة')
    current_reading = models.DecimalField('القراءة الحالية', max_digits=12, decimal_places=2)
    previous_reading = models.DecimalField('القراءة السابقة', max_digits=12, decimal_places=2, default=0)
    consumption = models.DecimalField('الاستهلاك', max_digits=12, decimal_places=2, default=0)
    
    unit_price = models.DecimalField('سعر الوحدة', max_digits=10, decimal_places=2)
    total_cost = models.DecimalField('التكلفة الإجمالية', max_digits=15, decimal_places=2, default=0)
    
    notes = models.TextField('ملاحظات', blank=True)
    recorded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'قراءة عداد'
        verbose_name_plural = 'قراءات العدادات'
        ordering = ['-reading_date']
    
    def __str__(self):
        return f"{self.meter.meter_number} - {self.reading_date}"
    
    def calculate_consumption(self):
        """حساب الاستهلاك"""
        self.consumption = self.current_reading - self.previous_reading
        self.total_cost = self.consumption * self.unit_price
        self.save()


class EnergyConsumptionAnalysis(models.Model):
    """تحليل استهلاك الطاقة"""
    meter = models.ForeignKey(UtilityMeter, on_delete=models.CASCADE, related_name='analyses')
    period_start = models.DateField('بداية الفترة')
    period_end = models.DateField('نهاية الفترة')
    
    total_consumption = models.DecimalField('إجمالي الاستهلاك', max_digits=15, decimal_places=2, default=0)
    total_cost = models.DecimalField('إجمالي التكلفة', max_digits=15, decimal_places=2, default=0)
    average_daily_consumption = models.DecimalField('متوسط الاستهلاك اليومي', max_digits=12, decimal_places=2, default=0)
    
    # المقارنة
    previous_period_consumption = models.DecimalField('استهلاك الفترة السابقة', max_digits=15, decimal_places=2, default=0)
    consumption_variance = models.DecimalField('انحراف الاستهلاك', max_digits=15, decimal_places=2, default=0)
    variance_percentage = models.DecimalField('نسبة الانحراف %', max_digits=5, decimal_places=2, default=0)
    
    # التوصيات
    efficiency_score = models.IntegerField('نقاط الكفاءة', default=50, help_text='من 0 إلى 100')
    recommendations = models.TextField('التوصيات', blank=True)
    savings_potential = models.DecimalField('إمكانية التوفير', max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'تحليل استهلاك الطاقة'
        verbose_name_plural = 'تحليلات استهلاك الطاقة'
        ordering = ['-period_end']
    
    def __str__(self):
        return f"{self.meter.meter_number} - {self.period_start} إلى {self.period_end}"


class EnergyAlert(models.Model):
    """تنبيه استهلاك"""
    meter = models.ForeignKey(UtilityMeter, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField('نوع التنبيه', max_length=20, choices=[
        ('high_consumption', 'استهلاك عالي'), ('spike', 'قفزة في الاستهلاك'),
        ('budget_exceeded', 'تجاوز الميزانية'), ('anomaly', 'استهلاك شاذ')
    ])
    severity = models.CharField('الخطورة', max_length=20, choices=[
        ('low', 'منخفضة'), ('medium', 'متوسطة'), ('high', 'عالية'), ('critical', 'حرجة')
    ], default='medium')
    
    message = models.TextField('الرسالة')
    threshold_value = models.DecimalField('القيمة الحدية', max_digits=12, decimal_places=2)
    actual_value = models.DecimalField('القيمة الفعلية', max_digits=12, decimal_places=2)
    
    is_resolved = models.BooleanField('تم الحل', default=False)
    resolved_at = models.DateTimeField('تاريخ الحل', null=True, blank=True)
    resolution_notes = models.TextField('ملاحظات الحل', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'تنبيه استهلاك'
        verbose_name_plural = 'تنبيهات الاستهلاك'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.meter.meter_number}"
