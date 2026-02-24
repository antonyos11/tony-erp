from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class CustomerSegment(models.Model):
    """شريحة العملاء"""
    SEGMENT_TYPES = [
        ('demographic', 'ديموغرافي'),
        ('behavioral', 'سلوكي'),
        ('geographic', 'جغرافي'),
        ('psychographic', 'نفسي'),
        ('value_based', 'حسب القيمة'),
    ]
    
    name = models.CharField('اسم الشريحة', max_length=200)
    segment_type = models.CharField('نوع الشريحة', max_length=30, choices=SEGMENT_TYPES)
    description = models.TextField('الوصف', blank=True)
    
    # معايير التقسيم
    criteria = models.JSONField('معايير التقسيم', default=dict, help_text='معايير اختيار العملاء')
    
    # الإحصائيات
    customer_count = models.IntegerField('عدد العملاء', default=0)
    total_revenue = models.DecimalField('إجمالي الإيرادات', max_digits=15, decimal_places=2, default=0)
    average_order_value = models.DecimalField('متوسط قيمة الطلب', max_digits=15, decimal_places=2, default=0)
    
    is_active = models.BooleanField('نشط', default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='customer_segments')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'شريحة عملاء'
        verbose_name_plural = 'شرائح العملاء'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.customer_count} عميل)"


class Campaign(models.Model):
    """الحملة التسويقية"""
    CAMPAIGN_TYPES = [
        ('awareness', 'توعية'),
        ('lead_generation', 'جذب عملاء محتملين'),
        ('conversion', 'تحويل'),
        ('retention', 'احتفاظ'),
        ('loyalty', 'ولاء'),
        ('seasonal', 'موسمية'),
        ('product_launch', 'إطلاق منتج'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('scheduled', 'مجدولة'),
        ('active', 'نشطة'),
        ('paused', 'متوقفة مؤقتاً'),
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغاة'),
    ]
    
    CHANNELS = [
        ('email', 'بريد إلكتروني'),
        ('sms', 'رسائل نصية'),
        ('whatsapp', 'واتساب'),
        ('social_media', 'وسائل التواصل'),
        ('website', 'الموقع الإلكتروني'),
        ('mobile_app', 'تطبيق الموبايل'),
        ('direct_mail', 'بريد مباشر'),
        ('phone_call', 'اتصال هاتفي'),
    ]
    
    name = models.CharField('اسم الحملة', max_length=200)
    campaign_type = models.CharField('نوع الحملة', max_length=30, choices=CAMPAIGN_TYPES)
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # التوقيت
    start_date = models.DateTimeField('تاريخ البداية')
    end_date = models.DateTimeField('تاريخ النهاية')
    
    # الجمهور المستهدف
    target_segments = models.ManyToManyField(CustomerSegment, verbose_name='الشرائح المستهدفة', related_name='campaigns')
    target_audience_size = models.IntegerField('حجم الجمهور المستهدف', default=0)
    
    # القنوات
    channels = models.JSONField('قنوات التسويق', default=list, help_text='قائمة القنوات المستخدمة')
    
    # الميزانية
    budget = models.DecimalField('الميزانية', max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    actual_cost = models.DecimalField('التكلفة الفعلية', max_digits=15, decimal_places=2, default=0)
    
    # الأهداف
    goal_description = models.TextField('وصف الأهداف')
    target_conversions = models.IntegerField('التحويلات المستهدفة', default=0)
    target_revenue = models.DecimalField('الإيراد المستهدف', max_digits=15, decimal_places=2, default=0)
    
    # النتائج
    total_sent = models.IntegerField('إجمالي الرسائل المرسلة', default=0)
    total_delivered = models.IntegerField('إجمالي الرسائل المستلمة', default=0)
    total_opened = models.IntegerField('إجمالي مرات الفتح', default=0)
    total_clicked = models.IntegerField('إجمالي النقرات', default=0)
    total_conversions = models.IntegerField('إجمالي التحويلات', default=0)
    total_revenue = models.DecimalField('إجمالي الإيرادات', max_digits=15, decimal_places=2, default=0)
    
    # المحتوى
    message_template = models.TextField('قالب الرسالة', blank=True)
    landing_page_url = models.URLField('رابط الصفحة المقصودة', blank=True)
    offer_details = models.TextField('تفاصيل العرض', blank=True)
    
    # التحليلات
    roi = models.DecimalField('العائد على الاستثمار (ROI) %', max_digits=10, decimal_places=2, default=0)
    cost_per_conversion = models.DecimalField('تكلفة التحويل', max_digits=15, decimal_places=2, default=0)
    conversion_rate = models.DecimalField('معدل التحويل %', max_digits=5, decimal_places=2, default=0)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='campaigns_created')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns_approved')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'حملة تسويقية'
        verbose_name_plural = 'الحملات التسويقية'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['campaign_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def calculate_metrics(self):
        """حساب مقاييس الأداء"""
        if self.total_sent > 0:
            self.conversion_rate = (self.total_conversions / self.total_sent) * 100
        
        if self.total_conversions > 0 and self.actual_cost > 0:
            self.cost_per_conversion = self.actual_cost / self.total_conversions
        
        if self.actual_cost > 0:
            profit = self.total_revenue - self.actual_cost
            self.roi = (profit / self.actual_cost) * 100
        
        self.save()


class CampaignMessage(models.Model):
    """رسالة الحملة"""
    MESSAGE_TYPES = [
        ('email', 'بريد إلكتروني'),
        ('sms', 'رسالة نصية'),
        ('whatsapp', 'واتساب'),
        ('push_notification', 'إشعار'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'معلق'),
        ('sent', 'مرسل'),
        ('delivered', 'مستلم'),
        ('opened', 'مفتوح'),
        ('clicked', 'تم النقر'),
        ('converted', 'تم التحويل'),
        ('bounced', 'فشل'),
        ('unsubscribed', 'إلغاء اشتراك'),
    ]
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='messages', verbose_name='الحملة')
    customer = models.ForeignKey('crm.Customer', on_delete=models.CASCADE, related_name='campaign_messages', verbose_name='العميل')
    
    message_type = models.CharField('نوع الرسالة', max_length=30, choices=MESSAGE_TYPES)
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    subject = models.CharField('الموضوع', max_length=200, blank=True)
    content = models.TextField('المحتوى')
    
    sent_at = models.DateTimeField('تاريخ الإرسال', null=True, blank=True)
    delivered_at = models.DateTimeField('تاريخ الاستلام', null=True, blank=True)
    opened_at = models.DateTimeField('تاريخ الفتح', null=True, blank=True)
    clicked_at = models.DateTimeField('تاريخ النقر', null=True, blank=True)
    converted_at = models.DateTimeField('تاريخ التحويل', null=True, blank=True)
    
    conversion_value = models.DecimalField('قيمة التحويل', max_digits=15, decimal_places=2, default=0)
    
    # معلومات إضافية
    metadata = models.JSONField('بيانات إضافية', default=dict, blank=True)
    error_message = models.TextField('رسالة الخطأ', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'رسالة حملة'
        verbose_name_plural = 'رسائل الحملات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['customer']),
            models.Index(fields=['message_type']),
        ]
    
    def __str__(self):
        return f"{self.campaign.name} - {self.customer.name}"


class ABTest(models.Model):
    """اختبار A/B"""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='ab_tests', verbose_name='الحملة')
    
    name = models.CharField('اسم الاختبار', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    # النسخة A
    variant_a_name = models.CharField('اسم النسخة A', max_length=100, default='النسخة A')
    variant_a_content = models.TextField('محتوى النسخة A')
    variant_a_sent = models.IntegerField('مرسل A', default=0)
    variant_a_conversions = models.IntegerField('تحويلات A', default=0)
    variant_a_conversion_rate = models.DecimalField('معدل التحويل A %', max_digits=5, decimal_places=2, default=0)
    
    # النسخة B
    variant_b_name = models.CharField('اسم النسخة B', max_length=100, default='النسخة B')
    variant_b_content = models.TextField('محتوى النسخة B')
    variant_b_sent = models.IntegerField('مرسل B', default=0)
    variant_b_conversions = models.IntegerField('تحويلات B', default=0)
    variant_b_conversion_rate = models.DecimalField('معدل التحويل B %', max_digits=5, decimal_places=2, default=0)
    
    # النتيجة
    winner = models.CharField('الفائز', max_length=1, choices=[('A', 'A'), ('B', 'B'), ('N', 'لا فرق')], blank=True)
    confidence_level = models.DecimalField('مستوى الثقة %', max_digits=5, decimal_places=2, default=0)
    
    is_active = models.BooleanField('نشط', default=True)
    is_completed = models.BooleanField('مكتمل', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'اختبار A/B'
        verbose_name_plural = 'اختبارات A/B'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.campaign.name}"
    
    def calculate_winner(self):
        """حساب النسخة الفائزة"""
        if self.variant_a_sent > 0:
            self.variant_a_conversion_rate = (self.variant_a_conversions / self.variant_a_sent) * 100
        
        if self.variant_b_sent > 0:
            self.variant_b_conversion_rate = (self.variant_b_conversions / self.variant_b_sent) * 100
        
        # تحديد الفائز (بسيط - يمكن تحسينه بإحصائيات أفضل)
        diff = abs(self.variant_a_conversion_rate - self.variant_b_conversion_rate)
        
        if diff < 1:
            self.winner = 'N'
            self.confidence_level = Decimal('50')
        elif self.variant_a_conversion_rate > self.variant_b_conversion_rate:
            self.winner = 'A'
            self.confidence_level = min(Decimal('95'), Decimal('50') + diff * 5)
        else:
            self.winner = 'B'
            self.confidence_level = min(Decimal('95'), Decimal('50') + diff * 5)
        
        self.save()


class CampaignROI(models.Model):
    """تحليل العائد على الاستثمار للحملة"""
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name='roi_analysis', verbose_name='الحملة')
    
    # التكاليف التفصيلية
    creative_cost = models.DecimalField('تكلفة التصميم', max_digits=15, decimal_places=2, default=0)
    platform_cost = models.DecimalField('تكلفة المنصة', max_digits=15, decimal_places=2, default=0)
    media_cost = models.DecimalField('تكلفة الإعلان', max_digits=15, decimal_places=2, default=0)
    staff_cost = models.DecimalField('تكلفة الموظفين', max_digits=15, decimal_places=2, default=0)
    other_costs = models.DecimalField('تكاليف أخرى', max_digits=15, decimal_places=2, default=0)
    
    # الإيرادات
    direct_revenue = models.DecimalField('الإيراد المباشر', max_digits=15, decimal_places=2, default=0)
    indirect_revenue = models.DecimalField('الإيراد غير المباشر', max_digits=15, decimal_places=2, default=0)
    
    # التحليل
    total_cost = models.DecimalField('إجمالي التكلفة', max_digits=15, decimal_places=2, default=0)
    total_revenue = models.DecimalField('إجمالي الإيراد', max_digits=15, decimal_places=2, default=0)
    net_profit = models.DecimalField('صافي الربح', max_digits=15, decimal_places=2, default=0)
    roi_percentage = models.DecimalField('العائد على الاستثمار %', max_digits=10, decimal_places=2, default=0)
    
    # مقاييس إضافية
    customer_acquisition_cost = models.DecimalField('تكلفة اكتساب العميل (CAC)', max_digits=15, decimal_places=2, default=0)
    customer_lifetime_value = models.DecimalField('قيمة العميل مدى الحياة (CLV)', max_digits=15, decimal_places=2, default=0)
    payback_period_days = models.IntegerField('فترة استرداد التكلفة (أيام)', default=0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تحليل ROI للحملة'
        verbose_name_plural = 'تحليلات ROI للحملات'
    
    def __str__(self):
        return f"ROI: {self.campaign.name}"
    
    def calculate_roi(self):
        """حساب ROI"""
        self.total_cost = (
            self.creative_cost + self.platform_cost + self.media_cost + 
            self.staff_cost + self.other_costs
        )
        
        self.total_revenue = self.direct_revenue + self.indirect_revenue
        self.net_profit = self.total_revenue - self.total_cost
        
        if self.total_cost > 0:
            self.roi_percentage = (self.net_profit / self.total_cost) * 100
        
        # تكلفة اكتساب العميل
        if self.campaign.total_conversions > 0:
            self.customer_acquisition_cost = self.total_cost / self.campaign.total_conversions
        
        self.save()
