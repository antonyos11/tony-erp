"""
نظام قوائم الأسعار ومقاسات المنتجات
Price Lists & Product Variants System

يشمل:
- مقاسات المنتجات (طول × عرض)
- نظام التكلفة المتقدم (مباشرة وغير مباشرة)
- قوائم أسعار متعددة (جملة، قطاعي، موزعين)
- دعم الضريبة
- تصدير PDF و Excel
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ============ نظام الأحجام والمقاسات ============

class ProductSize(models.Model):
    """مقاسات المنتجات - مثل 90×190، 100×200، إلخ"""
    
    name = models.CharField('اسم المقاس', max_length=50, help_text='مثال: 90×190')
    width = models.PositiveIntegerField('العرض (سم)', validators=[MinValueValidator(1)])
    length = models.PositiveIntegerField('الطول (سم)', validators=[MinValueValidator(1)])
    height = models.PositiveIntegerField('الارتفاع (سم)', null=True, blank=True)
    
    # معامل السعر - لحساب السعر التلقائي
    price_multiplier = models.DecimalField(
        'معامل السعر',
        max_digits=6,
        decimal_places=3,
        default=Decimal('1.000'),
        help_text='يُضرب في السعر الأساسي'
    )
    
    # معامل التكلفة - لحساب التكلفة التلقائية
    cost_multiplier = models.DecimalField(
        'معامل التكلفة',
        max_digits=6,
        decimal_places=3,
        default=Decimal('1.000'),
        help_text='يُضرب في التكلفة الأساسية'
    )
    
    # ترتيب العرض
    sort_order = models.PositiveIntegerField('ترتيب العرض', default=0)
    is_active = models.BooleanField('نشط', default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'مقاس'
        verbose_name_plural = 'المقاسات'
        ordering = ['sort_order', 'width', 'length']
        unique_together = ['width', 'length', 'height']
    
    def __str__(self):
        if self.height:
            return f"{self.width}×{self.length}×{self.height}"
        return f"{self.width}×{self.length}"
    
    @property
    def area(self):
        """المساحة بالمتر المربع"""
        return (self.width * self.length) / 10000
    
    @property
    def volume(self):
        """الحجم بالمتر المكعب (إذا كان الارتفاع موجود)"""
        if self.height:
            return (self.width * self.length * self.height) / 1000000
        return None
    
    def save(self, *args, **kwargs):
        if not self.name:
            if self.height:
                self.name = f"{self.width}×{self.length}×{self.height}"
            else:
                self.name = f"{self.width}×{self.length}"
        super().save(*args, **kwargs)


class ProductFamily(models.Model):
    """عائلة المنتجات - مجموعة منتجات لها نفس المقاسات والأسعار"""
    
    code = models.CharField('الكود', max_length=20, unique=True, blank=True)
    name = models.CharField('اسم العائلة', max_length=200)
    name_en = models.CharField('الاسم بالإنجليزية', max_length=200, blank=True)
    description = models.TextField('الوصف', blank=True)
    
    # الفئة - مرتبط بفئات المخزون
    category = models.ForeignKey(
        'inventory.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الفئة',
        related_name='product_families'
    )
    
    # ربط بمنتج أساسي في المخزون (اختياري)
    base_product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='المنتج الأساسي في المخزون',
        related_name='price_list_families',
        help_text='المنتج المرتبط في نظام المخزون (اختياري)'
    )
    
    # صورة العائلة
    image = models.ImageField('صورة', upload_to='product_families/', blank=True, null=True)
    
    # السعر الأساسي (لأصغر مقاس)
    base_price = models.DecimalField(
        'السعر الأساسي',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        help_text='سعر أصغر مقاس'
    )
    
    # التكلفة الأساسية (لأصغر مقاس)
    base_cost = models.DecimalField(
        'التكلفة الأساسية',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        help_text='تكلفة أصغر مقاس'
    )
    
    # المقاسات المتاحة لهذه العائلة
    available_sizes = models.ManyToManyField(
        ProductSize,
        blank=True,
        verbose_name='المقاسات المتاحة',
        related_name='product_families'
    )
    
    # ارتفاع المنتج الافتراضي (لعرضه في قائمة الأسعار)
    default_height = models.PositiveIntegerField(
        'الارتفاع الافتراضي (سم)',
        default=30,
        help_text='ارتفاع المنتج بالسنتيمتر - يظهر في رأس الجدول'
    )
    
    is_active = models.BooleanField('نشط', default=True)
    show_in_price_list = models.BooleanField('إظهار في قائمة الأسعار', default=True)
    sort_order = models.PositiveIntegerField('ترتيب العرض', default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'عائلة منتجات'
        verbose_name_plural = 'عائلات المنتجات'
        ordering = ['sort_order', 'name']
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_unique_code(cls):
        """توليد كود فريد تلقائياً"""
        import uuid
        from datetime import datetime
        
        # محاولة إنشاء كود بناءً على التاريخ والرقم التسلسلي
        today = datetime.now()
        prefix = f"FAM{today.strftime('%y%m')}"
        
        # البحث عن آخر كود بنفس البادئة
        last_family = cls.objects.filter(code__startswith=prefix).order_by('-code').first()
        
        if last_family:
            try:
                # استخراج الرقم من الكود الأخير
                last_num = int(last_family.code.replace(prefix, ''))
                new_num = last_num + 1
            except (ValueError, TypeError):
                new_num = 1
        else:
            new_num = 1
        
        new_code = f"{prefix}{new_num:04d}"
        
        # التأكد من أن الكود فريد
        while cls.objects.filter(code=new_code).exists():
            new_num += 1
            new_code = f"{prefix}{new_num:04d}"
        
        return new_code
    
    def __str__(self):
        return self.name
    
    def get_price_for_size(self, size: ProductSize, price_list=None) -> Decimal:
        """حساب السعر لمقاس معين"""
        # البحث عن سعر مخصص أولاً
        variant_price = ProductVariantPrice.objects.filter(
            family=self,
            size=size,
            price_list=price_list
        ).first()
        
        if variant_price and variant_price.custom_price:
            return variant_price.custom_price
        
        # حساب السعر بالمعامل
        return self.base_price * size.price_multiplier
    
    def get_cost_for_size(self, size: ProductSize) -> Decimal:
        """حساب التكلفة لمقاس معين"""
        # البحث عن تكلفة مخصصة
        variant = ProductVariant.objects.filter(family=self, size=size).first()
        if variant and variant.custom_cost:
            return variant.custom_cost
        
        return self.base_cost * size.cost_multiplier


class ProductVariant(models.Model):
    """نسخة المنتج لكل مقاس - ربط العائلة بالمقاس"""
    
    family = models.ForeignKey(
        ProductFamily,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='عائلة المنتج'
    )
    size = models.ForeignKey(
        ProductSize,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='المقاس'
    )
    
    # ربط بالمنتج الفعلي في المخزون (اختياري)
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='price_variant',
        verbose_name='المنتج المرتبط'
    )
    
    # كود فريد للنسخة
    sku = models.CharField('SKU', max_length=50, unique=True, blank=True)
    barcode = models.CharField('الباركود', max_length=50, unique=True, blank=True, null=True)
    
    # تكلفة مخصصة (تتجاوز الحساب التلقائي)
    custom_cost = models.DecimalField(
        'تكلفة مخصصة',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='اتركه فارغاً لاستخدام الحساب التلقائي'
    )
    
    # تفاصيل التكلفة المحسوبة
    calculated_cost = models.DecimalField(
        'التكلفة المحسوبة',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        editable=False
    )
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'نسخة منتج'
        verbose_name_plural = 'نسخ المنتجات'
        unique_together = ['family', 'size']
        ordering = ['family', 'size__sort_order']
    
    def __str__(self):
        return f"{self.family.name} - {self.size}"
    
    @property
    def effective_cost(self):
        """التكلفة الفعلية"""
        if self.custom_cost:
            return self.custom_cost
        return self.calculated_cost or self.family.get_cost_for_size(self.size)
    
    def save(self, *args, **kwargs):
        # توليد SKU تلقائي
        if not self.sku:
            self.sku = f"{self.family.code}-{self.size.width}x{self.size.length}"
            if self.size.height:
                self.sku += f"x{self.size.height}"
        
        # حساب التكلفة
        if not self.custom_cost:
            self.calculated_cost = self.family.get_cost_for_size(self.size)
        
        super().save(*args, **kwargs)
    
    def sync_to_inventory(self, price_list=None):
        """
        مزامنة هذه النسخة مع منتج في المخزون
        - إذا كان المنتج موجود، يتم تحديثه
        - إذا لم يكن موجود، يتم إنشاؤه
        """
        from inventory.models import Product
        
        # الحصول على السعر من قائمة الأسعار
        if price_list:
            price = self.family.get_price_for_size(self.size, price_list)
        else:
            price = self.family.get_price_for_size(self.size)
        
        cost = self.effective_cost
        
        if self.product:
            # تحديث المنتج الموجود
            self.product.price = price
            self.product.cost = cost
            self.product.width = self.size.width
            self.product.length = self.size.length
            self.product.height = self.size.height or self.family.default_height
            self.product.save(update_fields=['price', 'cost', 'width', 'length', 'height'])
            return self.product
        else:
            # إنشاء منتج جديد أو البحث عنه بالـ SKU
            product, created = Product.objects.get_or_create(
                sku=self.sku,
                defaults={
                    'name': f"{self.family.name} {self.size}",
                    'price': price,
                    'cost': cost,
                    'category': self.family.category,
                    'product_type': 'finished',
                    'width': self.size.width,
                    'length': self.size.length,
                    'height': self.size.height or self.family.default_height,
                }
            )
            
            if not created:
                # تحديث المنتج الموجود
                product.price = price
                product.cost = cost
                product.width = self.size.width
                product.length = self.size.length
                product.height = self.size.height or self.family.default_height
                product.save(update_fields=['price', 'cost', 'width', 'length', 'height'])
            
            # ربط المنتج بالنسخة
            self.product = product
            self.save(update_fields=['product'])
            
            return product
    
    @classmethod
    def sync_all_to_inventory(cls, price_list=None):
        """مزامنة جميع النسخ مع المخزون"""
        synced = 0
        errors = []
        
        for variant in cls.objects.filter(is_active=True):
            try:
                variant.sync_to_inventory(price_list)
                synced += 1
            except Exception as e:
                errors.append(f"{variant}: {str(e)}")
        
        return {'synced': synced, 'errors': errors}


# ============ نظام التكلفة المتقدم ============

class CostCategory(models.Model):
    """فئات التكاليف"""
    
    COST_TYPE_CHOICES = [
        ('direct_material', 'مواد مباشرة'),
        ('direct_labor', 'عمالة مباشرة'),
        ('manufacturing_overhead', 'تكاليف تصنيع غير مباشرة'),
        ('selling_expense', 'مصاريف بيع'),
        ('admin_expense', 'مصاريف إدارية'),
        ('shipping', 'شحن ونقل'),
        ('packaging', 'تغليف'),
        ('other', 'أخرى'),
    ]
    
    name = models.CharField('اسم الفئة', max_length=100)
    cost_type = models.CharField('نوع التكلفة', max_length=30, choices=COST_TYPE_CHOICES)
    description = models.TextField('الوصف', blank=True)
    
    # هل هي تكلفة مباشرة أم غير مباشرة
    is_direct = models.BooleanField('تكلفة مباشرة', default=True)
    
    # طريقة التوزيع للتكاليف غير المباشرة
    ALLOCATION_METHOD_CHOICES = [
        ('per_unit', 'لكل وحدة'),
        ('per_area', 'حسب المساحة'),
        ('per_weight', 'حسب الوزن'),
        ('percentage_of_material', 'نسبة من المواد'),
        ('percentage_of_labor', 'نسبة من العمالة'),
        ('fixed', 'ثابتة'),
    ]
    allocation_method = models.CharField(
        'طريقة التوزيع',
        max_length=30,
        choices=ALLOCATION_METHOD_CHOICES,
        default='per_unit'
    )
    
    # معدل التكلفة الافتراضي
    default_rate = models.DecimalField(
        'المعدل الافتراضي',
        max_digits=12,
        decimal_places=4,
        default=Decimal('0')
    )
    
    is_active = models.BooleanField('نشط', default=True)
    sort_order = models.PositiveIntegerField('ترتيب', default=0)
    
    class Meta:
        verbose_name = 'فئة تكلفة'
        verbose_name_plural = 'فئات التكاليف'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_cost_type_display()})"


class VariantCostBreakdown(models.Model):
    """تفصيل تكاليف نسخة المنتج"""
    
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='cost_breakdown',
        verbose_name='نسخة المنتج'
    )
    cost_category = models.ForeignKey(
        CostCategory,
        on_delete=models.CASCADE,
        verbose_name='فئة التكلفة'
    )
    
    description = models.CharField('الوصف', max_length=200, blank=True)
    amount = models.DecimalField('المبلغ', max_digits=12, decimal_places=4)
    
    # مرجع للمادة إذا كانت تكلفة مواد
    material = models.ForeignKey(
        'inventory.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='المادة'
    )
    quantity = models.DecimalField('الكمية', max_digits=12, decimal_places=4, default=Decimal('1'))
    unit_cost = models.DecimalField('تكلفة الوحدة', max_digits=12, decimal_places=4, default=Decimal('0'))
    
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تفصيل تكلفة'
        verbose_name_plural = 'تفاصيل التكاليف'
        ordering = ['cost_category__sort_order']
    
    def __str__(self):
        return f"{self.variant} - {self.cost_category}: {self.amount}"
    
    def save(self, *args, **kwargs):
        if self.quantity and self.unit_cost:
            self.amount = self.quantity * self.unit_cost
        super().save(*args, **kwargs)


class OverheadCostSetting(models.Model):
    """إعدادات التكاليف غير المباشرة"""
    
    name = models.CharField('الاسم', max_length=100)
    cost_category = models.ForeignKey(
        CostCategory,
        on_delete=models.CASCADE,
        verbose_name='فئة التكلفة'
    )
    
    # طريقة الحساب
    CALCULATION_METHOD_CHOICES = [
        ('fixed_per_unit', 'مبلغ ثابت لكل وحدة'),
        ('percentage_of_direct', 'نسبة من التكاليف المباشرة'),
        ('percentage_of_material', 'نسبة من تكلفة المواد'),
        ('per_square_meter', 'لكل متر مربع'),
        ('per_labor_hour', 'لكل ساعة عمل'),
    ]
    calculation_method = models.CharField(
        'طريقة الحساب',
        max_length=30,
        choices=CALCULATION_METHOD_CHOICES
    )
    
    rate = models.DecimalField('المعدل', max_digits=12, decimal_places=4)
    
    # يطبق على عائلات معينة أو الكل
    applies_to_families = models.ManyToManyField(
        ProductFamily,
        blank=True,
        verbose_name='يطبق على العائلات',
        help_text='اتركه فارغاً للتطبيق على الكل'
    )
    
    is_active = models.BooleanField('نشط', default=True)
    
    class Meta:
        verbose_name = 'إعداد تكلفة غير مباشرة'
        verbose_name_plural = 'إعدادات التكاليف غير المباشرة'
    
    def __str__(self):
        return f"{self.name}: {self.rate}"


# ============ نظام قوائم الأسعار ============

class PriceList(models.Model):
    """قوائم الأسعار - جملة، قطاعي، موزعين"""
    
    PRICE_LIST_TYPE_CHOICES = [
        ('retail', 'قطاعي'),
        ('wholesale', 'جملة'),
        ('distributor', 'موزعين'),
        ('vip', 'عملاء VIP'),
        ('cost', 'التكلفة'),
        ('custom', 'مخصص'),
    ]
    
    code = models.CharField('الكود', max_length=20, unique=True)
    name = models.CharField('اسم القائمة', max_length=100)
    name_en = models.CharField('الاسم بالإنجليزية', max_length=100, blank=True)
    list_type = models.CharField('نوع القائمة', max_length=20, choices=PRICE_LIST_TYPE_CHOICES)
    description = models.TextField('الوصف', blank=True)
    
    # الخصم أو الزيادة على السعر الأساسي
    discount_percentage = models.DecimalField(
        'نسبة الخصم %',
        max_digits=5,
        decimal_places=2,
        default=Decimal('0'),
        help_text='نسبة سالبة للزيادة'
    )
    
    # هل تشمل الضريبة
    includes_tax = models.BooleanField('شامل الضريبة', default=False)
    tax_rate = models.DecimalField(
        'نسبة الضريبة %',
        max_digits=5,
        decimal_places=2,
        default=Decimal('15.00'),
        help_text='نسبة ضريبة القيمة المضافة'
    )
    
    # العملة
    currency = models.CharField('العملة', max_length=3, default='EGP')
    
    # الصلاحية
    valid_from = models.DateField('صالح من', null=True, blank=True)
    valid_until = models.DateField('صالح حتى', null=True, blank=True)
    
    # الحد الأدنى للطلب
    min_order_amount = models.DecimalField(
        'الحد الأدنى للطلب',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    
    is_active = models.BooleanField('نشط', default=True)
    is_default = models.BooleanField('افتراضي', default=False)
    
    # شعار القائمة
    logo = models.ImageField('الشعار', upload_to='price_lists/', blank=True, null=True)
    header_text = models.TextField('نص الترويسة', blank=True)
    footer_text = models.TextField('نص التذييل', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'قائمة أسعار'
        verbose_name_plural = 'قوائم الأسعار'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_list_type_display()})"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            PriceList.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    def apply_discount(self, price: Decimal) -> Decimal:
        """تطبيق الخصم على السعر"""
        if self.discount_percentage:
            return price * (1 - self.discount_percentage / 100)
        return price
    
    def apply_tax(self, price: Decimal) -> Decimal:
        """إضافة الضريبة للسعر"""
        if self.includes_tax:
            return price
        return price * (1 + self.tax_rate / 100)
    
    def remove_tax(self, price_with_tax: Decimal) -> Decimal:
        """إزالة الضريبة من السعر"""
        if not self.includes_tax:
            return price_with_tax
        return price_with_tax / (1 + self.tax_rate / 100)


class ProductVariantPrice(models.Model):
    """أسعار نسخ المنتجات في قوائم الأسعار المختلفة"""
    
    family = models.ForeignKey(
        ProductFamily,
        on_delete=models.CASCADE,
        related_name='variant_prices',
        verbose_name='عائلة المنتج'
    )
    size = models.ForeignKey(
        ProductSize,
        on_delete=models.CASCADE,
        related_name='variant_prices',
        verbose_name='المقاس'
    )
    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name='قائمة الأسعار'
    )
    
    # السعر المخصص (يتجاوز الحساب التلقائي)
    custom_price = models.DecimalField(
        'سعر مخصص',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='اتركه فارغاً لاستخدام الحساب التلقائي'
    )
    
    # السعر المحسوب (للعرض والتقارير)
    calculated_price = models.DecimalField(
        'السعر المحسوب',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        editable=False
    )
    
    # السعر النهائي (بعد الضريبة إذا كانت مطبقة)
    final_price = models.DecimalField(
        'السعر النهائي',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        editable=False
    )
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'سعر نسخة منتج'
        verbose_name_plural = 'أسعار نسخ المنتجات'
        unique_together = ['family', 'size', 'price_list']
        ordering = ['family', 'size__sort_order']
    
    def __str__(self):
        return f"{self.family.name} {self.size} - {self.price_list.name}: {self.effective_price}"
    
    @property
    def effective_price(self):
        """السعر الفعلي"""
        if self.custom_price:
            return self.custom_price
        return self.calculated_price
    
    def calculate_prices(self):
        """حساب السعر بناءً على السعر الأساسي والخصومات"""
        base_price = self.family.base_price * self.size.price_multiplier
        self.calculated_price = self.price_list.apply_discount(base_price)
        self.final_price = self.price_list.apply_tax(self.effective_price)
    
    def save(self, *args, **kwargs):
        self.calculate_prices()
        super().save(*args, **kwargs)


# ============ تصدير قوائم الأسعار ============

class PriceListExport(models.Model):
    """سجل تصدير قوائم الأسعار"""
    
    EXPORT_FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
    ]
    
    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.CASCADE,
        related_name='exports',
        verbose_name='قائمة الأسعار'
    )
    
    format = models.CharField('الصيغة', max_length=10, choices=EXPORT_FORMAT_CHOICES)
    file = models.FileField('الملف', upload_to='price_list_exports/')
    
    # خيارات التصدير
    include_cost = models.BooleanField('تضمين التكلفة', default=False)
    include_margin = models.BooleanField('تضمين الهامش', default=False)
    include_tax_breakdown = models.BooleanField('تفصيل الضريبة', default=True)
    
    # العائلات المصدرة (فارغ = كل العائلات)
    families = models.ManyToManyField(
        ProductFamily,
        blank=True,
        verbose_name='العائلات المصدرة'
    )
    
    generated_at = models.DateTimeField('تاريخ التصدير', auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'تصدير قائمة أسعار'
        verbose_name_plural = 'تصديرات قوائم الأسعار'
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.price_list.name} - {self.format.upper()} - {self.generated_at}"


# ============ إعدادات قائمة الأسعار ============

class PriceListSettings(models.Model):
    """إعدادات عامة لنظام قوائم الأسعار"""
    
    # ربط مع بيانات الشركة الرئيسية
    use_company_data = models.BooleanField(
        'استخدام بيانات الشركة',
        default=True,
        help_text='عند التفعيل، يتم استخدام بيانات الشركة من الإعدادات الرئيسية'
    )
    
    # بيانات مخصصة (تُستخدم فقط إذا use_company_data=False)
    company_name = models.CharField('اسم الشركة', max_length=200, blank=True)
    company_name_en = models.CharField('اسم الشركة بالإنجليزية', max_length=200, blank=True)
    logo = models.ImageField('الشعار', upload_to='price_list_settings/', blank=True, null=True)
    
    # معلومات التواصل المخصصة
    phone = models.CharField('الهاتف', max_length=50, blank=True)
    email = models.EmailField('البريد الإلكتروني', blank=True)
    website = models.URLField('الموقع الإلكتروني', blank=True)
    address = models.TextField('العنوان', blank=True)
    
    # إعدادات الضريبة
    default_tax_rate = models.DecimalField(
        'نسبة الضريبة الافتراضية',
        max_digits=5,
        decimal_places=2,
        default=Decimal('15.00')
    )
    tax_registration_number = models.CharField('الرقم الضريبي', max_length=50, blank=True)
    
    # نص قائمة الأسعار
    price_list_header = models.TextField('ترويسة قائمة الأسعار', blank=True)
    price_list_footer = models.TextField('تذييل قائمة الأسعار', blank=True)
    price_validity_text = models.CharField(
        'نص صلاحية الأسعار',
        max_length=200,
        default='الأسعار صالحة من تاريخ الإصدار'
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'إعدادات قائمة الأسعار'
        verbose_name_plural = 'إعدادات قوائم الأسعار'
    
    def __str__(self):
        return 'إعدادات قائمة الأسعار'
    
    @classmethod
    def get_settings(cls):
        """الحصول على الإعدادات أو إنشاء افتراضية"""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
    
    def get_company_name(self):
        """الحصول على اسم الشركة"""
        if self.use_company_data:
            from core.models import Company
            company = Company.objects.first()
            return company.name if company else self.company_name
        return self.company_name
    
    def get_company_logo(self):
        """الحصول على شعار الشركة"""
        if self.use_company_data:
            from core.models import Company
            company = Company.objects.first()
            if company and company.logo:
                return company.logo
        return self.logo
    
    def get_company_phone(self):
        """الحصول على هاتف الشركة"""
        if self.use_company_data:
            from core.models import Company
            company = Company.objects.first()
            if company:
                return company.phone or company.mobile
        return self.phone
    
    def get_company_email(self):
        """الحصول على بريد الشركة"""
        if self.use_company_data:
            from core.models import Company
            company = Company.objects.first()
            return company.email if company else self.email
        return self.email
    
    def get_company_website(self):
        """الحصول على موقع الشركة"""
        if self.use_company_data:
            from core.models import Company
            company = Company.objects.first()
            return company.website if company else self.website
        return self.website
    
    def get_company_address(self):
        """الحصول على عنوان الشركة"""
        if self.use_company_data:
            from core.models import Company
            company = Company.objects.first()
            return company.address if company else self.address
        return self.address
    
    def get_tax_id(self):
        """الحصول على الرقم الضريبي"""
        if self.use_company_data:
            from core.models import Company
            company = Company.objects.first()
            if company and company.tax_id:
                return company.tax_id
        return self.tax_registration_number
    
    def get_whatsapp(self):
        """الحصول على رقم الواتساب"""
        if self.use_company_data:
            from core.models import Company
            company = Company.objects.first()
            return company.whatsapp if company else ''
        return ''
    
    def get_all_company_data(self):
        """الحصول على جميع بيانات الشركة"""
        return {
            'name': self.get_company_name(),
            'name_en': self.company_name_en,
            'logo': self.get_company_logo(),
            'phone': self.get_company_phone(),
            'email': self.get_company_email(),
            'website': self.get_company_website(),
            'address': self.get_company_address(),
            'tax_id': self.get_tax_id(),
            'whatsapp': self.get_whatsapp(),
            'tax_rate': self.default_tax_rate,
            'header': self.price_list_header,
            'footer': self.price_list_footer,
            'validity_text': self.price_validity_text,
        }
