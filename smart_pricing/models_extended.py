"""
Extended Smart Pricing Models
نماذج التسعير الذكي المتقدمة

يشمل:
- تحليل المنافسين
- تسعير موسمي
- تاريخ الأسعار
- أهداف التسعير
- استراتيجيات التسعير الذكي
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone


class Competitor(models.Model):
    """المنافسين"""
    
    name = models.CharField('اسم المنافس', max_length=200)
    website = models.URLField('الموقع الإلكتروني', blank=True)
    logo = models.ImageField('الشعار', upload_to='competitors/', blank=True, null=True)
    
    # التصنيف
    COMPETITOR_TYPE_CHOICES = [
        ('direct', 'منافس مباشر'),
        ('indirect', 'منافس غير مباشر'),
        ('potential', 'منافس محتمل'),
    ]
    competitor_type = models.CharField('نوع المنافس', max_length=20, choices=COMPETITOR_TYPE_CHOICES, default='direct')
    
    # التقييم
    market_share = models.DecimalField('الحصة السوقية %', max_digits=5, decimal_places=2, default=0)
    quality_rating = models.IntegerField('تقييم الجودة', validators=[MinValueValidator(1), MaxValueValidator(10)], default=5)
    price_level = models.CharField('مستوى السعر', max_length=20, choices=[
        ('very_low', 'منخفض جداً'),
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'مرتفع'),
        ('premium', 'فاخر'),
    ], default='medium')
    
    # معلومات إضافية
    strengths = models.TextField('نقاط القوة', blank=True)
    weaknesses = models.TextField('نقاط الضعف', blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'منافس'
        verbose_name_plural = 'المنافسين'
        ordering = ['-market_share']
    
    def __str__(self):
        return self.name


class CompetitorPrice(models.Model):
    """أسعار المنافسين"""
    
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='prices', verbose_name='المنافس')
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, verbose_name='المنتج', null=True, blank=True)
    product_name = models.CharField('اسم المنتج', max_length=200)
    product_category = models.CharField('فئة المنتج', max_length=100, blank=True)
    
    price = models.DecimalField('السعر', max_digits=12, decimal_places=2)
    currency = models.CharField('العملة', max_length=3, default='EGP')
    
    # المصدر
    SOURCE_CHOICES = [
        ('website', 'الموقع الإلكتروني'),
        ('store', 'المتجر'),
        ('catalog', 'الكتالوج'),
        ('quote', 'عرض سعر'),
        ('customer', 'من العميل'),
        ('market_research', 'بحث سوقي'),
    ]
    source = models.CharField('المصدر', max_length=20, choices=SOURCE_CHOICES, default='website')
    source_url = models.URLField('رابط المصدر', blank=True)
    
    recorded_at = models.DateTimeField('تاريخ التسجيل', default=timezone.now)
    valid_until = models.DateField('صالح حتى', null=True, blank=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='مسجل بواسطة')
    
    class Meta:
        verbose_name = 'سعر منافس'
        verbose_name_plural = 'أسعار المنافسين'
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.competitor.name} - {self.product_name}: {self.price}"


class PricingStrategy(models.Model):
    """استراتيجيات التسعير"""
    
    STRATEGY_TYPE_CHOICES = [
        ('penetration', 'اختراق السوق'),
        ('skimming', 'القشط'),
        ('competitive', 'تنافسي'),
        ('value_based', 'على أساس القيمة'),
        ('cost_plus', 'التكلفة + هامش'),
        ('dynamic', 'ديناميكي'),
        ('psychological', 'نفسي'),
        ('bundle', 'حزمة'),
        ('freemium', 'مجاني + مدفوع'),
        ('premium', 'فاخر'),
    ]
    
    name = models.CharField('اسم الاستراتيجية', max_length=200)
    strategy_type = models.CharField('نوع الاستراتيجية', max_length=20, choices=STRATEGY_TYPE_CHOICES)
    description = models.TextField('الوصف', blank=True)
    
    # النطاق
    applies_to_category = models.CharField('فئة المنتجات', max_length=100, blank=True)
    applies_to_customer_segment = models.CharField('شريحة العملاء', max_length=100, blank=True)
    
    # المعاملات
    base_margin = models.DecimalField('الهامش الأساسي %', max_digits=5, decimal_places=2, default=25)
    min_margin = models.DecimalField('الحد الأدنى للهامش %', max_digits=5, decimal_places=2, default=10)
    max_margin = models.DecimalField('الحد الأقصى للهامش %', max_digits=5, decimal_places=2, default=50)
    
    # التعديلات
    competitor_adjustment = models.DecimalField('تعديل المنافسة %', max_digits=5, decimal_places=2, default=0,
                                                 help_text='نسبة أقل/أعلى من سعر المنافس')
    demand_sensitivity = models.DecimalField('حساسية الطلب', max_digits=5, decimal_places=2, default=1.0,
                                              validators=[MinValueValidator(0), MaxValueValidator(2)])
    
    # الفترة
    start_date = models.DateField('تاريخ البدء', null=True, blank=True)
    end_date = models.DateField('تاريخ الانتهاء', null=True, blank=True)
    
    is_active = models.BooleanField('نشط', default=True)
    priority = models.IntegerField('الأولوية', default=0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'استراتيجية تسعير'
        verbose_name_plural = 'استراتيجيات التسعير'
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_strategy_type_display()})"


class SeasonalPricing(models.Model):
    """التسعير الموسمي"""
    
    SEASON_CHOICES = [
        ('ramadan', 'رمضان'),
        ('eid_fitr', 'عيد الفطر'),
        ('eid_adha', 'عيد الأضحى'),
        ('national_day', 'اليوم الوطني'),
        ('black_friday', 'الجمعة البيضاء'),
        ('year_end', 'نهاية السنة'),
        ('summer', 'الصيف'),
        ('winter', 'الشتاء'),
        ('back_to_school', 'العودة للمدارس'),
        ('custom', 'مخصص'),
    ]
    
    name = models.CharField('اسم الموسم', max_length=200)
    season_type = models.CharField('نوع الموسم', max_length=20, choices=SEASON_CHOICES, default='custom')
    
    # الفترة
    start_date = models.DateField('تاريخ البدء')
    end_date = models.DateField('تاريخ الانتهاء')
    
    # التعديلات
    ADJUSTMENT_TYPE_CHOICES = [
        ('percentage', 'نسبة مئوية'),
        ('fixed', 'مبلغ ثابت'),
    ]
    adjustment_type = models.CharField('نوع التعديل', max_length=20, choices=ADJUSTMENT_TYPE_CHOICES, default='percentage')
    adjustment_value = models.DecimalField('قيمة التعديل', max_digits=10, decimal_places=2, default=0)
    
    # النطاق
    applies_to_all = models.BooleanField('ينطبق على الجميع', default=True)
    product_categories = models.TextField('فئات المنتجات', blank=True, help_text='فئات مفصولة بفواصل')
    
    # التفعيل
    is_active = models.BooleanField('نشط', default=True)
    auto_activate = models.BooleanField('تفعيل تلقائي', default=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تسعير موسمي'
        verbose_name_plural = 'التسعير الموسمي'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    def is_currently_active(self):
        """هل الموسم نشط حالياً"""
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date


class PriceHistory(models.Model):
    """تاريخ الأسعار"""
    
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='smart_price_history', verbose_name='المنتج')
    
    old_price = models.DecimalField('السعر القديم', max_digits=12, decimal_places=2)
    new_price = models.DecimalField('السعر الجديد', max_digits=12, decimal_places=2)
    
    old_cost = models.DecimalField('التكلفة القديمة', max_digits=12, decimal_places=2, null=True, blank=True)
    new_cost = models.DecimalField('التكلفة الجديدة', max_digits=12, decimal_places=2, null=True, blank=True)
    
    # سبب التغيير
    REASON_CHOICES = [
        ('cost_change', 'تغيير التكلفة'),
        ('market_adjustment', 'تعديل سوقي'),
        ('competitor_response', 'استجابة للمنافسة'),
        ('seasonal', 'موسمي'),
        ('promotion', 'عرض ترويجي'),
        ('demand_change', 'تغيير الطلب'),
        ('ai_recommendation', 'توصية الذكاء الاصطناعي'),
        ('manual', 'يدوي'),
    ]
    reason = models.CharField('سبب التغيير', max_length=30, choices=REASON_CHOICES, default='manual')
    reason_details = models.TextField('تفاصيل السبب', blank=True)
    
    # التأثير
    price_change_percentage = models.DecimalField('نسبة التغيير %', max_digits=8, decimal_places=2, default=0)
    
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='تم التغيير بواسطة')
    changed_at = models.DateTimeField('تاريخ التغيير', default=timezone.now)
    
    # الموافقة
    requires_approval = models.BooleanField('يحتاج موافقة', default=False)
    approved = models.BooleanField('موافق عليه', default=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='approved_price_changes', verbose_name='موافق عليه بواسطة')
    approved_at = models.DateTimeField('تاريخ الموافقة', null=True, blank=True)
    
    class Meta:
        verbose_name = 'تاريخ سعر'
        verbose_name_plural = 'تاريخ الأسعار'
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.product.name}: {self.old_price} → {self.new_price}"
    
    def save(self, *args, **kwargs):
        if self.old_price and self.old_price > 0:
            self.price_change_percentage = ((self.new_price - self.old_price) / self.old_price) * 100
        super().save(*args, **kwargs)


class PricingGoal(models.Model):
    """أهداف التسعير"""
    
    GOAL_TYPE_CHOICES = [
        ('revenue', 'الإيرادات'),
        ('profit', 'الأرباح'),
        ('margin', 'الهامش'),
        ('market_share', 'الحصة السوقية'),
        ('volume', 'حجم المبيعات'),
        ('customer_acquisition', 'اكتساب العملاء'),
    ]
    
    name = models.CharField('اسم الهدف', max_length=200)
    goal_type = models.CharField('نوع الهدف', max_length=30, choices=GOAL_TYPE_CHOICES)
    description = models.TextField('الوصف', blank=True)
    
    # الفترة
    period_start = models.DateField('بداية الفترة')
    period_end = models.DateField('نهاية الفترة')
    
    # الهدف
    target_value = models.DecimalField('القيمة المستهدفة', max_digits=15, decimal_places=2)
    current_value = models.DecimalField('القيمة الحالية', max_digits=15, decimal_places=2, default=0)
    
    # النطاق
    product_category = models.CharField('فئة المنتج', max_length=100, blank=True)
    
    # الحالة
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('achieved', 'تم تحقيقه'),
        ('missed', 'لم يتحقق'),
        ('cancelled', 'ملغي'),
    ]
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='active')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'هدف تسعير'
        verbose_name_plural = 'أهداف التسعير'
        ordering = ['-period_start']
    
    def __str__(self):
        return f"{self.name} - {self.get_goal_type_display()}"
    
    def progress_percentage(self):
        """نسبة التقدم"""
        if self.target_value > 0:
            return min(100, (self.current_value / self.target_value) * 100)
        return 0


class PriceAlert(models.Model):
    """تنبيهات الأسعار"""
    
    ALERT_TYPE_CHOICES = [
        ('competitor_price_drop', 'انخفاض سعر منافس'),
        ('competitor_price_increase', 'ارتفاع سعر منافس'),
        ('margin_below_threshold', 'الهامش أقل من الحد'),
        ('cost_increase', 'ارتفاع التكلفة'),
        ('high_demand', 'طلب مرتفع'),
        ('low_demand', 'طلب منخفض'),
        ('price_recommendation', 'توصية سعرية'),
        ('goal_at_risk', 'هدف في خطر'),
    ]
    
    alert_type = models.CharField('نوع التنبيه', max_length=30, choices=ALERT_TYPE_CHOICES)
    title = models.CharField('العنوان', max_length=200)
    message = models.TextField('الرسالة')
    
    # المرجع
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, null=True, blank=True, verbose_name='المنتج')
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, null=True, blank=True, verbose_name='المنافس')
    
    # البيانات الإضافية
    data = models.JSONField('بيانات إضافية', default=dict, blank=True)
    
    # التوصية
    recommended_action = models.TextField('الإجراء الموصى به', blank=True)
    recommended_price = models.DecimalField('السعر الموصى به', max_digits=12, decimal_places=2, null=True, blank=True)
    
    # الأولوية
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    priority = models.CharField('الأولوية', max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # الحالة
    is_read = models.BooleanField('مقروء', default=False)
    is_actioned = models.BooleanField('تم اتخاذ إجراء', default=False)
    actioned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='بواسطة')
    actioned_at = models.DateTimeField('تاريخ الإجراء', null=True, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    expires_at = models.DateTimeField('ينتهي في', null=True, blank=True)
    
    class Meta:
        verbose_name = 'تنبيه سعر'
        verbose_name_plural = 'تنبيهات الأسعار'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_alert_type_display()}: {self.title}"


class PricingSimulation(models.Model):
    """محاكاة التسعير"""
    
    name = models.CharField('اسم المحاكاة', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    # سيناريو المحاكاة
    SCENARIO_CHOICES = [
        ('price_increase', 'زيادة الأسعار'),
        ('price_decrease', 'تخفيض الأسعار'),
        ('competitor_response', 'رد فعل المنافس'),
        ('market_change', 'تغيير السوق'),
        ('cost_change', 'تغيير التكلفة'),
        ('promotion', 'حملة ترويجية'),
    ]
    scenario_type = models.CharField('نوع السيناريو', max_length=30, choices=SCENARIO_CHOICES)
    
    # المعاملات
    price_change_percentage = models.DecimalField('نسبة تغيير السعر %', max_digits=8, decimal_places=2, default=0)
    demand_elasticity = models.DecimalField('مرونة الطلب', max_digits=5, decimal_places=2, default=1.0)
    
    # النتائج المتوقعة
    expected_revenue_change = models.DecimalField('التغير المتوقع في الإيرادات %', max_digits=8, decimal_places=2, default=0)
    expected_volume_change = models.DecimalField('التغير المتوقع في الحجم %', max_digits=8, decimal_places=2, default=0)
    expected_profit_change = models.DecimalField('التغير المتوقع في الأرباح %', max_digits=8, decimal_places=2, default=0)
    
    # البيانات
    input_data = models.JSONField('بيانات الإدخال', default=dict, blank=True)
    results = models.JSONField('النتائج', default=dict, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='أنشئ بواسطة')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'محاكاة تسعير'
        verbose_name_plural = 'محاكاة التسعير'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class ProductPricingProfile(models.Model):
    """ملف تسعير المنتج"""
    
    product = models.OneToOneField('inventory.Product', on_delete=models.CASCADE, 
                                    related_name='pricing_profile', verbose_name='المنتج')
    
    # استراتيجية التسعير
    pricing_strategy = models.ForeignKey(PricingStrategy, on_delete=models.SET_NULL, 
                                          null=True, blank=True, verbose_name='استراتيجية التسعير')
    pricing_rule = models.ForeignKey('smart_pricing.PricingRule', on_delete=models.SET_NULL,
                                      null=True, blank=True, verbose_name='قاعدة التسعير')
    
    # التسعير الأساسي
    base_cost = models.DecimalField('التكلفة الأساسية', max_digits=12, decimal_places=2, default=0)
    target_margin = models.DecimalField('الهامش المستهدف %', max_digits=5, decimal_places=2, default=25)
    min_price = models.DecimalField('الحد الأدنى للسعر', max_digits=12, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField('الحد الأقصى للسعر', max_digits=12, decimal_places=2, null=True, blank=True)
    
    # التسعير الذكي
    enable_dynamic_pricing = models.BooleanField('تفعيل التسعير الديناميكي', default=False)
    enable_competitor_tracking = models.BooleanField('تتبع أسعار المنافسين', default=False)
    enable_demand_based_pricing = models.BooleanField('التسعير حسب الطلب', default=False)
    
    # معاملات AI
    ai_price_adjustment_limit = models.DecimalField('حد تعديل AI %', max_digits=5, decimal_places=2, default=10,
                                                     help_text='الحد الأقصى لتغيير السعر تلقائياً')
    last_ai_recommendation = models.DecimalField('آخر توصية AI', max_digits=12, decimal_places=2, null=True, blank=True)
    last_ai_recommendation_date = models.DateTimeField('تاريخ آخر توصية', null=True, blank=True)
    
    # الإحصائيات
    average_margin = models.DecimalField('متوسط الهامش الفعلي %', max_digits=5, decimal_places=2, default=0)
    price_changes_count = models.IntegerField('عدد تغييرات السعر', default=0)
    
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'ملف تسعير منتج'
        verbose_name_plural = 'ملفات تسعير المنتجات'
    
    def __str__(self):
        return f"تسعير: {self.product.name}"


class BundlePricing(models.Model):
    """تسعير الحزم"""
    
    name = models.CharField('اسم الحزمة', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    # المنتجات
    products = models.ManyToManyField('inventory.Product', through='BundlePricingItem', 
                                       related_name='bundles', verbose_name='المنتجات')
    
    # التسعير
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'نسبة مئوية'),
        ('fixed', 'مبلغ ثابت'),
        ('fixed_price', 'سعر ثابت للحزمة'),
    ]
    discount_type = models.CharField('نوع الخصم', max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField('قيمة الخصم', max_digits=12, decimal_places=2, default=0)
    
    total_original_price = models.DecimalField('السعر الأصلي الإجمالي', max_digits=12, decimal_places=2, default=0)
    bundle_price = models.DecimalField('سعر الحزمة', max_digits=12, decimal_places=2, default=0)
    savings = models.DecimalField('التوفير', max_digits=12, decimal_places=2, default=0)
    
    # الفترة
    start_date = models.DateField('تاريخ البدء', null=True, blank=True)
    end_date = models.DateField('تاريخ الانتهاء', null=True, blank=True)
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تسعير حزمة'
        verbose_name_plural = 'تسعير الحزم'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def calculate_prices(self):
        """حساب أسعار الحزمة"""
        items = self.items.select_related('product')
        self.total_original_price = sum(item.product.price * item.quantity for item in items)
        
        if self.discount_type == 'percentage':
            self.bundle_price = self.total_original_price * (1 - self.discount_value / 100)
        elif self.discount_type == 'fixed':
            self.bundle_price = self.total_original_price - self.discount_value
        elif self.discount_type == 'fixed_price':
            self.bundle_price = self.discount_value
        
        self.savings = self.total_original_price - self.bundle_price
        self.save()


class BundlePricingItem(models.Model):
    """عناصر الحزمة"""
    
    bundle = models.ForeignKey(BundlePricing, on_delete=models.CASCADE, related_name='items', verbose_name='الحزمة')
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, verbose_name='المنتج')
    quantity = models.IntegerField('الكمية', default=1, validators=[MinValueValidator(1)])
    
    class Meta:
        verbose_name = 'عنصر حزمة'
        verbose_name_plural = 'عناصر الحزم'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
