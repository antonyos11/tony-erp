from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class Competitor(models.Model):
    """المنافس"""
    name = models.CharField('الاسم', max_length=200)
    website = models.URLField('الموقع الإلكتروني', blank=True)
    description = models.TextField('الوصف', blank=True)
    
    market_position = models.CharField('المركز السوقي', max_length=20, choices=[
        ('leader', 'رائد'), ('challenger', 'منافس قوي'), ('follower', 'تابع'), ('niche', 'متخصص')
    ], default='follower')
    
    estimated_market_share = models.DecimalField('الحصة السوقية المقدرة %', max_digits=5, 
                                                 decimal_places=2, default=0)
    estimated_revenue = models.DecimalField('الإيراد المقدر', max_digits=15, decimal_places=2, default=0)
    
    strengths = models.TextField('نقاط القوة', blank=True)
    weaknesses = models.TextField('نقاط الضعف', blank=True)
    opportunities = models.TextField('الفرص', blank=True)
    threats = models.TextField('التهديدات', blank=True)
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'منافس'
        verbose_name_plural = 'المنافسون'
        ordering = ['-estimated_market_share']
    
    def __str__(self):
        return self.name


class CompetitorProduct(models.Model):
    """منتج المنافس"""
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='products')
    our_product = models.ForeignKey('inventory.Product', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='competitor_equivalents')
    
    product_name = models.CharField('اسم المنتج', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    price = models.DecimalField('السعر', max_digits=10, decimal_places=2)
    our_price = models.DecimalField('سعرنا', max_digits=10, decimal_places=2, null=True, blank=True)
    price_difference = models.DecimalField('فرق السعر', max_digits=10, decimal_places=2, default=0)
    price_difference_percentage = models.DecimalField('فرق السعر %', max_digits=5, decimal_places=2, default=0)
    
    features = models.JSONField('المميزات', default=list)
    quality_rating = models.IntegerField('تقييم الجودة', default=3, help_text='من 1 إلى 5')
    
    last_price_update = models.DateField('آخر تحديث للسعر', auto_now=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'منتج منافس'
        verbose_name_plural = 'منتجات المنافسين'
        ordering = ['competitor', 'product_name']
    
    def __str__(self):
        return f"{self.competitor.name} - {self.product_name}"
    
    def calculate_price_difference(self):
        """حساب فرق السعر"""
        if self.our_price:
            self.price_difference = self.price - self.our_price
            if self.our_price > 0:
                self.price_difference_percentage = (self.price_difference / self.our_price) * 100
        self.save()


class MarketTrend(models.Model):
    """اتجاه السوق"""
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف')
    
    trend_type = models.CharField('نوع الاتجاه', max_length=30, choices=[
        ('pricing', 'تسعير'), ('technology', 'تقنية'), ('customer_preference', 'تفضيلات عملاء'),
        ('regulation', 'تنظيمات'), ('competition', 'منافسة'), ('economic', 'اقتصادي')
    ])
    
    impact_level = models.CharField('مستوى التأثير', max_length=20, choices=[
        ('low', 'منخفض'), ('medium', 'متوسط'), ('high', 'عالي'), ('critical', 'حرج')
    ], default='medium')
    
    trend_direction = models.CharField('اتجاه التطور', max_length=20, choices=[
        ('increasing', 'متزايد'), ('decreasing', 'متناقص'), ('stable', 'مستقر'), ('volatile', 'متقلب')
    ])
    
    identified_date = models.DateField('تاريخ الرصد', auto_now_add=True)
    relevance_start = models.DateField('بداية الصلاحية', null=True, blank=True)
    relevance_end = models.DateField('نهاية الصلاحية', null=True, blank=True)
    
    # التوصيات
    strategic_implications = models.TextField('الآثار الاستراتيجية', blank=True)
    recommended_actions = models.TextField('الإجراءات الموصى بها', blank=True)
    
    identified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'اتجاه سوق'
        verbose_name_plural = 'اتجاهات السوق'
        ordering = ['-identified_date']
    
    def __str__(self):
        return f"{self.title} - {self.get_impact_level_display()}"


class CompetitiveAnalysis(models.Model):
    """تحليل تنافسي"""
    title = models.CharField('العنوان', max_length=200)
    analysis_date = models.DateField('تاريخ التحليل', auto_now_add=True)
    period_start = models.DateField('بداية الفترة')
    period_end = models.DateField('نهاية الفترة')
    
    competitors_analyzed = models.ManyToManyField(Competitor, verbose_name='المنافسون المحللون')
    
    # النتائج
    key_findings = models.TextField('النتائج الرئيسية')
    market_positioning = models.TextField('المركز السوقي')
    competitive_advantages = models.TextField('المزايا التنافسية')
    competitive_disadvantages = models.TextField('العيوب التنافسية')
    
    # التوصيات
    strategic_recommendations = models.TextField('التوصيات الاستراتيجية')
    action_items = models.TextField('بنود العمل')
    
    prepared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='analyses_prepared')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='analyses_reviewed')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تحليل تنافسي'
        verbose_name_plural = 'التحليلات التنافسية'
        ordering = ['-analysis_date']
    
    def __str__(self):
        return f"{self.title} - {self.analysis_date}"
