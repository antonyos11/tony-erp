"""
AI-Powered Smart Pricing System
نظام التسعير الذكي بالذكاء الاصطناعي

يسعر المنتجات المخصصة بشكل آلي ودقيق حسب:
- الشكل والتصميم
- الكمية المطلوبة
- المقاس والأبعاد
- المواد الخام
- تكلفة العمالة
- هامش الربح
"""

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from inventory.models import Product
from production.models import ProductionWorkCenter


class PricingRule(models.Model):
    """قواعد التسعير الذكي"""
    
    PRICING_METHOD_CHOICES = [
        ('fixed', 'سعر ثابت'),
        ('cost_plus', 'التكلفة + الهامش'),
        ('market_based', 'حسب السوق'),
        ('ai_dynamic', 'ذكاء اصطناعي ديناميكي'),
    ]
    
    name = models.CharField('اسم القاعدة', max_length=200)
    product_category = models.CharField('فئة المنتج', max_length=100, blank=True)
    method = models.CharField('طريقة التسعير', max_length=20, choices=PRICING_METHOD_CHOICES, default='cost_plus')
    
    # معاملات التسعير
    base_cost_multiplier = models.DecimalField('معامل التكلفة الأساسية', max_digits=5, decimal_places=2, default=Decimal('1.0'))
    quantity_discount_threshold = models.IntegerField('حد الخصم الكمي', default=100)
    quantity_discount_rate = models.DecimalField('نسبة الخصم الكمي %', max_digits=5, decimal_places=2, default=Decimal('5.0'))
    
    # هامش الربح
    min_profit_margin = models.DecimalField('هامش الربح الأدنى %', max_digits=5, decimal_places=2, default=Decimal('15.0'))
    target_profit_margin = models.DecimalField('هامش الربح المستهدف %', max_digits=5, decimal_places=2, default=Decimal('25.0'))
    max_profit_margin = models.DecimalField('هامش الربح الأقصى %', max_digits=5, decimal_places=2, default=Decimal('50.0'))
    
    # معاملات الحجم
    size_multiplier_small = models.DecimalField('معامل المقاس الصغير', max_digits=5, decimal_places=2, default=Decimal('0.8'))
    size_multiplier_medium = models.DecimalField('معامل المقاس المتوسط', max_digits=5, decimal_places=2, default=Decimal('1.0'))
    size_multiplier_large = models.DecimalField('معامل المقاس الكبير', max_digits=5, decimal_places=2, default=Decimal('1.3'))
    size_multiplier_xlarge = models.DecimalField('معامل المقاس الضخم', max_digits=5, decimal_places=2, default=Decimal('1.6'))
    
    # معاملات التعقيد
    complexity_simple = models.DecimalField('معامل التصميم البسيط', max_digits=5, decimal_places=2, default=Decimal('1.0'))
    complexity_medium = models.DecimalField('معامل التصميم المتوسط', max_digits=5, decimal_places=2, default=Decimal('1.2'))
    complexity_complex = models.DecimalField('معامل التصميم المعقد', max_digits=5, decimal_places=2, default=Decimal('1.5'))
    
    # AI Parameters
    use_ai_pricing = models.BooleanField('استخدام الذكاء الاصطناعي', default=False)
    ai_model_version = models.CharField('إصدار نموذج AI', max_length=50, blank=True)
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'قاعدة تسعير'
        verbose_name_plural = 'قواعد التسعير'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class SmartQuote(models.Model):
    """عرض سعر ذكي آلي"""
    
    SIZE_CHOICES = [
        ('small', 'صغير'),
        ('medium', 'متوسط'),
        ('large', 'كبير'),
        ('xlarge', 'ضخم'),
    ]
    
    COMPLEXITY_CHOICES = [
        ('simple', 'بسيط'),
        ('medium', 'متوسط'),
        ('complex', 'معقد'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('calculating', 'جاري الحساب'),
        ('ready', 'جاهز'),
        ('sent', 'مرسل'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
    ]
    
    quote_number = models.CharField('رقم العرض', max_length=50, unique=True)
    customer = models.ForeignKey('crm.Customer', on_delete=models.PROTECT, verbose_name='العميل')
    
    # مواصفات المنتج
    product_name = models.CharField('اسم المنتج', max_length=200)
    description = models.TextField('الوصف', blank=True)
    quantity = models.IntegerField('الكمية', validators=[MinValueValidator(1)])
    size = models.CharField('المقاس', max_length=20, choices=SIZE_CHOICES)
    complexity = models.CharField('التعقيد', max_length=20, choices=COMPLEXITY_CHOICES)
    
    # الأبعاد (اختياري)
    width = models.DecimalField('العرض (سم)', max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField('الطول (سم)', max_digits=10, decimal_places=2, null=True, blank=True)
    depth = models.DecimalField('العمق (سم)', max_digits=10, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField('الوزن (كجم)', max_digits=10, decimal_places=2, null=True, blank=True)
    
    # التسعير
    pricing_rule = models.ForeignKey(PricingRule, on_delete=models.SET_NULL, null=True, verbose_name='قاعدة التسعير')
    
    raw_material_cost = models.DecimalField('تكلفة المواد الخام', max_digits=12, decimal_places=2, default=Decimal('0'))
    labor_cost = models.DecimalField('تكلفة العمالة', max_digits=12, decimal_places=2, default=Decimal('0'))
    overhead_cost = models.DecimalField('التكاليف الإضافية', max_digits=12, decimal_places=2, default=Decimal('0'))
    total_cost = models.DecimalField('التكلفة الإجمالية', max_digits=12, decimal_places=2, default=Decimal('0'))
    
    profit_margin = models.DecimalField('هامش الربح %', max_digits=5, decimal_places=2, default=Decimal('25.0'))
    unit_price = models.DecimalField('سعر الوحدة', max_digits=12, decimal_places=2, default=Decimal('0'))
    total_price = models.DecimalField('السعر الإجمالي', max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # خصومات
    quantity_discount = models.DecimalField('خصم الكمية %', max_digits=5, decimal_places=2, default=Decimal('0'))
    final_price = models.DecimalField('السعر النهائي', max_digits=12, decimal_places=2, default=Decimal('0'))
    
    # AI Details
    ai_calculated = models.BooleanField('محسوب بالذكاء الاصطناعي', default=False)
    ai_confidence_score = models.DecimalField('درجة الثقة AI', max_digits=5, decimal_places=2, null=True, blank=True)
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    valid_until = models.DateField('صالح حتى', null=True, blank=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='created_quotes')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'عرض سعر ذكي'
        verbose_name_plural = 'عروض أسعار ذكية'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.quote_number} - {self.customer.name}"
    
    def calculate_price(self):
        """حساب السعر التلقائي"""
        if not self.pricing_rule:
            return False
        
        rule = self.pricing_rule
        
        # 1. حساب التكلفة الأساسية (يمكن تحسينها بالـ AI)
        if self.raw_material_cost == 0:
            # تقدير تلقائي بناءً على المواصفات
            base_cost = Decimal('100.0')  # قيمة افتراضية
            
            # معامل الحجم
            size_multiplier = {
                'small': rule.size_multiplier_small,
                'medium': rule.size_multiplier_medium,
                'large': rule.size_multiplier_large,
                'xlarge': rule.size_multiplier_xlarge,
            }.get(self.size, Decimal('1.0'))
            
            # معامل التعقيد
            complexity_multiplier = {
                'simple': rule.complexity_simple,
                'medium': rule.complexity_medium,
                'complex': rule.complexity_complex,
            }.get(self.complexity, Decimal('1.0'))
            
            self.raw_material_cost = base_cost * size_multiplier * complexity_multiplier
        
        # 2. حساب تكلفة العمالة
        if self.labor_cost == 0:
            self.labor_cost = self.raw_material_cost * Decimal('0.3')  # 30% من المواد
        
        # 3. التكاليف الإضافية
        if self.overhead_cost == 0:
            self.overhead_cost = (self.raw_material_cost + self.labor_cost) * Decimal('0.15')  # 15%
        
        # 4. التكلفة الإجمالية
        self.total_cost = self.raw_material_cost + self.labor_cost + self.overhead_cost
        
        # 5. هامش الربح
        self.profit_margin = rule.target_profit_margin
        
        # 6. سعر الوحدة
        self.unit_price = self.total_cost * (1 + self.profit_margin / 100)
        
        # 7. السعر الإجمالي
        self.total_price = self.unit_price * self.quantity
        
        # 8. خصم الكمية
        if self.quantity >= rule.quantity_discount_threshold:
            self.quantity_discount = rule.quantity_discount_rate
        else:
            self.quantity_discount = Decimal('0')
        
        # 9. السعر النهائي
        discount_amount = self.total_price * (self.quantity_discount / 100)
        self.final_price = self.total_price - discount_amount
        
        self.status = 'ready'
        self.save()
        
        return True


class ProductionLineRecommendation(models.Model):
    """ترشيح خط الإنتاج الأنسب بالذكاء الاصطناعي"""
    
    smart_quote = models.ForeignKey(SmartQuote, on_delete=models.CASCADE, related_name='recommendations')
    work_center = models.ForeignKey('production.ProductionWorkCenter', on_delete=models.CASCADE, verbose_name='خط الإنتاج')
    
    # معايير التقييم
    estimated_cost = models.DecimalField('التكلفة المتوقعة', max_digits=12, decimal_places=2)
    estimated_time = models.DecimalField('الوقت المتوقع (ساعات)', max_digits=8, decimal_places=2)
    capacity_match = models.DecimalField('مطابقة السعة %', max_digits=5, decimal_places=2)
    quality_score = models.DecimalField('درجة الجودة', max_digits=5, decimal_places=2)
    
    # الترشيح
    recommendation_score = models.DecimalField('درجة الترشيح', max_digits=5, decimal_places=2)
    is_recommended = models.BooleanField('مُرشح', default=False)
    
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'ترشيح خط إنتاج'
        verbose_name_plural = 'ترشيحات خطوط الإنتاج'
        ordering = ['-recommendation_score']
    
    def __str__(self):
        return f"{self.work_center.name} - Score: {self.recommendation_score}"


class AutoMaterialRelease(models.Model):
    """صرف المواد الخام الآلي من المستودع"""
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('approved', 'موافق عليه'),
        ('released', 'تم الصرف'),
        ('cancelled', 'ملغي'),
    ]
    
    production_order = models.ForeignKey('production.ProductionOrder', on_delete=models.CASCADE, verbose_name='أمر الإنتاج')
    release_number = models.CharField('رقم أمر الصرف', max_length=50, unique=True)
    
    warehouse = models.ForeignKey('inventory.Location', on_delete=models.PROTECT, verbose_name='الموقع/المستودع')
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    auto_generated = models.BooleanField('تم الإنشاء تلقائياً', default=True)
    
    released_at = models.DateTimeField('تاريخ الصرف', null=True, blank=True)
    released_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='released_materials')
    
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'أمر صرف مواد آلي'
        verbose_name_plural = 'أوامر صرف المواد الآلية'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.release_number} - {self.production_order}"


class MaterialReleaseItem(models.Model):
    """مواد أمر الصرف"""
    
    release = models.ForeignKey(AutoMaterialRelease, on_delete=models.CASCADE, related_name='items')
    material = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, verbose_name='المادة')
    
    required_quantity = models.DecimalField('الكمية المطلوبة', max_digits=12, decimal_places=3)
    released_quantity = models.DecimalField('الكمية المصروفة', max_digits=12, decimal_places=3, default=Decimal('0'))
    
    unit_cost = models.DecimalField('تكلفة الوحدة', max_digits=12, decimal_places=2, default=Decimal('0'))
    total_cost = models.DecimalField('التكلفة الإجمالية', max_digits=12, decimal_places=2, default=Decimal('0'))
    
    class Meta:
        verbose_name = 'مادة أمر صرف'
        verbose_name_plural = 'مواد أوامر الصرف'
    
    def __str__(self):
        return f"{self.material.name} - {self.required_quantity}"
