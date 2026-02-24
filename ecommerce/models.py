"""
نماذج المتجر الإلكتروني - Ecommerce Models
متكامل مع نظام المخزون والمبيعات
"""
from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
# from fernet_fields import EncryptedCharField (Disabled due to missing dependency)

User = get_user_model()


class EcommerceSettings(models.Model):
    """إعدادات المتجر الإلكتروني"""
    store_name = models.CharField(max_length=200, verbose_name=_("اسم المتجر"))
    store_logo = models.ImageField(upload_to='ecommerce/logo/', blank=True, null=True, verbose_name=_("شعار المتجر"))
    store_description = models.TextField(blank=True, verbose_name=_("وصف المتجر"))
    currency = models.CharField(max_length=10, default='EGP', verbose_name=_("العملة"))  # Changed to Egypt
    
    # Egypt Tax Settings (Added January 2026)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('14.00'),
                                   verbose_name=_("نسبة ضريبة القيمة المضافة"),
                                   help_text=_("ضريبة القيمة المضافة المصرية (14%)"))
    tax_registration_number = models.CharField(max_length=50, blank=True,
                                               verbose_name=_("رقم التسجيل الضريبي"),
                                               help_text=_("رقم التسجيل الضريبي للشركة"))
    
    # إعدادات العرض
    products_per_page = models.PositiveIntegerField(default=12, verbose_name=_("المنتجات في الصفحة"))
    show_out_of_stock = models.BooleanField(default=True, verbose_name=_("عرض المنتجات غير المتوفرة"))
    enable_reviews = models.BooleanField(default=True, verbose_name=_("تفعيل التقييمات"))
    enable_wishlist = models.BooleanField(default=True, verbose_name=_("تفعيل قائمة الأمنيات"))
    
    # إعدادات الشحن
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("حد الشحن المجاني"))
    default_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("تكلفة الشحن الافتراضية"))
    
    # معلومات التواصل
    contact_email = models.EmailField(blank=True, verbose_name=_("البريد الإلكتروني"))
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name=_("رقم الهاتف"))
    whatsapp_number = models.CharField(max_length=20, blank=True, verbose_name=_("رقم الواتساب"))
    
    # بالت الألوان
    primary_color = models.CharField(max_length=7, default='#0ea5e9', verbose_name=_("اللون الأساسي"))
    secondary_color = models.CharField(max_length=7, default='#64748b', verbose_name=_("اللون الثانوي"))
    accent_color = models.CharField(max_length=7, default='#f59e0b', verbose_name=_("لون التمييز"))
    background_color = models.CharField(max_length=7, default='#ffffff', verbose_name=_("لون الخلفية"))
    text_color = models.CharField(max_length=7, default='#1e293b', verbose_name=_("لون النص"))
    header_bg_color = models.CharField(max_length=7, default='#1e293b', verbose_name=_("لون خلفية الهيدر"))
    header_text_color = models.CharField(max_length=7, default='#ffffff', verbose_name=_("لون نص الهيدر"))
    footer_bg_color = models.CharField(max_length=7, default='#111827', verbose_name=_("لون خلفية الفوتر"))
    footer_text_color = models.CharField(max_length=7, default='#9ca3af', verbose_name=_("لون نص الفوتر"))
    button_color = models.CharField(max_length=7, default='#0ea5e9', verbose_name=_("لون الأزرار"))
    button_text_color = models.CharField(max_length=7, default='#ffffff', verbose_name=_("لون نص الأزرار"))
    sale_badge_color = models.CharField(max_length=7, default='#ef4444', verbose_name=_("لون شارة التخفيض"))
    
    is_active = models.BooleanField(default=True, verbose_name=_("المتجر مفعل"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("إعدادات المتجر")
        verbose_name_plural = _("إعدادات المتجر")
    
    def __str__(self):
        return self.store_name or "إعدادات المتجر"
    
    @classmethod
    def get_settings(cls):
        """الحصول على إعدادات المتجر مع معالجة أفضل للأخطاء"""
        try:
            settings, created = cls.objects.get_or_create(
                pk=1, 
                defaults={
                    'store_name': 'المتجر الإلكتروني',
                    'currency': 'EGP',  # Changed to Egypt
                    'vat_rate': Decimal('14.00'),  # Egypt VAT rate
                    'products_per_page': 12,
                }
            )
            return settings
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting EcommerceSettings: {str(e)}", exc_info=True)
            # إرجاع كائن افتراضي بدلاً من None
            return cls(
                pk=1,
                store_name='المتجر الإلكتروني',
                currency='EGP',
                vat_rate=Decimal('14.00'),
                products_per_page=12,
            )


class ProductCategory(models.Model):
    """فئات المنتجات للمتجر"""
    name = models.CharField(max_length=100, verbose_name=_("اسم الفئة"))
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True, verbose_name=_("الرابط"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    image = models.ImageField(upload_to='ecommerce/categories/', blank=True, null=True, verbose_name=_("الصورة"))
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                               related_name='children', verbose_name=_("الفئة الأب"))
    is_active = models.BooleanField(default=True, verbose_name=_("مفعلة"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("الترتيب"), help_text=_("ترتيب الفئة في القوائم"))
    
    # ربط مع فئة المخزون
    inventory_category = models.ForeignKey(
        'inventory.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecommerce_categories',
        verbose_name=_("فئة المخزون المرتبطة"),
        help_text=_("ربط هذه الفئة بفئة من المخزون لمزامنة المنتجات تلقائياً")
    )
    
    class Meta:
        verbose_name = _("فئة المنتج")
        verbose_name_plural = _("فئات المنتجات")
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    def sync_products_from_inventory(self):
        """مزامنة المنتجات من فئة المخزون المرتبطة"""
        if not self.inventory_category:
            return 0
        
        from inventory.models import Product
        count = 0
        products = Product.objects.filter(
            category=self.inventory_category,
            show_in_store=True
        )
        
        for product in products:
            online_product, created = OnlineProduct.objects.get_or_create(
                inventory_item=product,
                defaults={
                    'category': self,
                    'is_active': True,
                    'is_new': product.is_new,
                }
            )
            if not created and online_product.category != self:
                online_product.category = self
                online_product.save(update_fields=['category'])
            if created:
                count += 1
        return count


class Brand(models.Model):
    """العلامات التجارية الموثوقة"""
    name = models.CharField(max_length=100, verbose_name=_("اسم العلامة التجارية"))
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True, verbose_name=_("الرابط"))
    logo = models.ImageField(upload_to='ecommerce/brands/', blank=True, null=True, verbose_name=_("الشعار"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    website = models.URLField(blank=True, verbose_name=_("الموقع الإلكتروني"))
    is_featured = models.BooleanField(default=False, verbose_name=_("عرض في الصفحة الرئيسية"))
    is_active = models.BooleanField(default=True, verbose_name=_("مفعلة"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("علامة تجارية")
        verbose_name_plural = _("العلامات التجارية")
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_featured(cls):
        """جلب العلامات التجارية المميزة للعرض في الصفحة الرئيسية"""
        return cls.objects.filter(is_active=True, is_featured=True).order_by('sort_order')


class OnlineProduct(models.Model):
    """المنتجات المعروضة في المتجر الإلكتروني - مربوطة بالمخزون"""
    # ربط بالمخزون
    inventory_item = models.OneToOneField(
        'inventory.Product', 
        on_delete=models.CASCADE, 
        related_name='online_product',
        verbose_name=_("المنتج في المخزون"),
        null=True,
        blank=True
    )
    
    # بيانات العرض
    display_name = models.CharField(max_length=200, blank=True, verbose_name=_("اسم العرض"))
    slug = models.SlugField(max_length=200, unique=True, allow_unicode=True, blank=True, verbose_name=_("الرابط"))
    short_description = models.CharField(max_length=500, blank=True, verbose_name=_("وصف قصير"))
    full_description = models.TextField(blank=True, verbose_name=_("الوصف الكامل"))
    
    # الفئات والعلامات التجارية
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='online_products', verbose_name=_("الفئة"))
    brand = models.ForeignKey('Brand', on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='online_products', verbose_name=_("العلامة التجارية"))
    
    # الصور
    main_image = models.ImageField(upload_to='ecommerce/products/', blank=True, null=True, verbose_name=_("الصورة الرئيسية"))
    
    # السعر (يمكن تخصيصه أو استخدام سعر المخزون)
    custom_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("سعر مخصص"))
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("سعر المقارنة"), help_text=_("السعر الأصلي قبل الخصم للمقارنة"))
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("سعر الخصم"))
    discount_start = models.DateTimeField(null=True, blank=True, verbose_name=_("بداية الخصم"))
    discount_end = models.DateTimeField(null=True, blank=True, verbose_name=_("نهاية الخصم"))
    
    # الحالة
    is_featured = models.BooleanField(default=False, verbose_name=_("منتج مميز"))
    is_active = models.BooleanField(default=True, verbose_name=_("معروض"))
    is_new = models.BooleanField(default=False, verbose_name=_("جديد"))
    
    # الإحصائيات
    views_count = models.PositiveIntegerField(default=0, verbose_name=_("عدد المشاهدات"))
    sales_count = models.PositiveIntegerField(default=0, verbose_name=_("عدد المبيعات"))
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True, verbose_name=_("عنوان SEO"))
    meta_description = models.CharField(max_length=300, blank=True, verbose_name=_("وصف SEO"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("منتج إلكتروني")
        verbose_name_plural = _("المنتجات الإلكترونية")
        ordering = ['-is_featured', '-created_at']
    
    def __str__(self):
        return self.display_name or (self.inventory_item.name if self.inventory_item_id else str(self.pk))
    
    @property
    def name(self):
        if self.display_name:
            return self.display_name
        if self.inventory_item_id:
            return self.inventory_item.name
        return ''

    @name.setter
    def name(self, value):
        self.display_name = value
    
    @property
    def price(self):
        """السعر الفعلي"""
        now = timezone.now()
        if self.discount_price and self.discount_start and self.discount_end:
            if self.discount_start <= now <= self.discount_end:
                return self.discount_price
        if self.custom_price:
            return self.custom_price
        if self.inventory_item_id:
            return getattr(self.inventory_item, 'effective_price', None) or self.inventory_item.price
        return self.custom_price

    @price.setter
    def price(self, value):
        self.custom_price = value
    
    @property
    def original_price(self):
        """السعر الأصلي"""
        if self.custom_price:
            return self.custom_price
        if self.inventory_item_id:
            return self.inventory_item.price
        return None
    
    @property
    def stock(self):
        """الكمية المتوفرة"""
        if hasattr(self, '_stock_cache'):
            return self._stock_cache
        if self.inventory_item_id:
            return self.inventory_item.current_stock
        return 0

    @stock.setter
    def stock(self, value):
        self._stock_cache = value
    
    @property
    def is_in_stock(self):
        """هل المنتج متوفر"""
        return self.stock > 0
    
    @property
    def has_discount(self):
        """هل يوجد خصم حالي"""
        now = timezone.now()
        if self.discount_price and self.discount_start and self.discount_end:
            return self.discount_start <= now <= self.discount_end
        return False
    
    @property
    def discount_percentage(self):
        """نسبة الخصم"""
        if self.has_discount and self.original_price:
            return int(((self.original_price - self.discount_price) / self.original_price) * 100)
        return 0
    
    @property
    def image(self):
        """الصورة الرئيسية - للتوافق مع القوالب"""
        return self.main_image

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('ecommerce:product_detail', args=[str(self.id)])
    
    def save(self, *args, **kwargs):
        # توليد slug تلقائياً إذا لم يكن موجوداً
        if not self.slug and self.display_name:
            from django.utils.text import slugify
            self.slug = slugify(self.display_name, allow_unicode=True)
        elif not self.slug:
            # استخدام اسم المنتج من المخزون
            from django.utils.text import slugify
            self.slug = slugify(self.inventory_item.name if self.inventory_item_id else str(self.id), allow_unicode=True)
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    """صور إضافية للمنتج"""
    product = models.ForeignKey(OnlineProduct, on_delete=models.CASCADE, related_name='images', verbose_name=_("المنتج"))
    image = models.ImageField(upload_to='ecommerce/products/', verbose_name=_("الصورة"))
    alt_text = models.CharField(max_length=200, blank=True, verbose_name=_("النص البديل"))
    is_primary = models.BooleanField(default=False, verbose_name=_("صورة رئيسية"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("الترتيب"))
    
    class Meta:
        verbose_name = _("صورة المنتج")
        verbose_name_plural = _("صور المنتجات")
        ordering = ['sort_order']


class Cart(models.Model):
    """سلة التسوق"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, 
                            related_name='ecommerce_carts', verbose_name=_("المستخدم"))
    session_key = models.CharField(max_length=100, blank=True, verbose_name=_("مفتاح الجلسة"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("سلة التسوق")
        verbose_name_plural = _("سلات التسوق")
    
    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def items_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """عناصر سلة التسوق"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name=_("السلة"))
    product = models.ForeignKey(OnlineProduct, on_delete=models.CASCADE, verbose_name=_("المنتج"))
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("الكمية"))
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("عنصر السلة")
        verbose_name_plural = _("عناصر السلة")
        unique_together = ['cart', 'product']
    
    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    """طلبات المتجر الإلكتروني - مربوطة بفواتير المبيعات"""
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('confirmed', _('مؤكد')),
        ('processing', _('قيد المعالجة')),
        ('shipped', _('تم الشحن')),
        ('delivered', _('تم التسليم')),
        ('cancelled', _('ملغي')),
        ('refunded', _('مسترجع')),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', _('في انتظار الدفع')),
        ('paid', _('مدفوع')),
        ('failed', _('فشل الدفع')),
        ('refunded', _('مسترجع')),
    ]
    
    order_number = models.CharField(max_length=50, unique=True, verbose_name=_("رقم الطلب"))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='ecommerce_orders', verbose_name=_("المستخدم"))
    
    # ربط بالعميل في النظام
    customer = models.ForeignKey('partners.Customer', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='online_orders', verbose_name=_("العميل"))
    
    # ربط بفاتورة المبيعات
    invoice = models.OneToOneField('sales.Invoice', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='online_order', verbose_name=_("الفاتورة"))
    
    # بيانات الطلب
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_("حالة الطلب"))
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name=_("حالة الدفع"))
    
    # Payment Gateway Integration (Egypt - Added January 2026)
    payment_method = models.ForeignKey('PaymentGateway', on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='orders', verbose_name=_("طريقة الدفع"))
    payment_gateway_transaction_id = models.CharField(max_length=200, blank=True, 
                                                      verbose_name=_("رقم المعاملة"))
    payment_gateway_reference = models.CharField(max_length=200, blank=True,
                                                  verbose_name=_("الرقم المرجعي"))
    payment_gateway_callback_data = models.JSONField(default=dict, blank=True,
                                                      verbose_name=_("بيانات Callback"))
    payment_completed_at = models.DateTimeField(null=True, blank=True,
                                                verbose_name=_("تاريخ إتمام الدفع"))
    payment_gateway_fees = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'),
                                               verbose_name=_("رسوم بوابة الدفع"))
    
    # بيانات العميل
    customer_name = models.CharField(max_length=200, verbose_name=_("اسم العميل"))
    customer_email = models.EmailField(blank=True, verbose_name=_("البريد الإلكتروني"))
    customer_phone = models.CharField(max_length=20, verbose_name=_("رقم الهاتف"))
    
    # عنوان الشحن
    shipping_address = models.TextField(verbose_name=_("عنوان الشحن"))
    shipping_city = models.CharField(max_length=100, verbose_name=_("المدينة"))
    shipping_country = models.CharField(max_length=100, default='مصر', verbose_name=_("الدولة"))  # Changed default to Egypt
    
    # المبالغ
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_("المجموع الفرعي"))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("تكلفة الشحن"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("الخصم"))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("الضريبة"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_("الإجمالي"))
    
    # ملاحظات
    customer_notes = models.TextField(blank=True, verbose_name=_("ملاحظات العميل"))
    admin_notes = models.TextField(blank=True, verbose_name=_("ملاحظات الإدارة"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("طلب إلكتروني")
        verbose_name_plural = _("الطلبات الإلكترونية")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"طلب #{self.order_number}"
    
    @staticmethod
    def generate_order_number():
        """Generate unique order number"""
        import uuid
        return f"ORD-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def mark_as_paid(self, transaction_id, reference='', callback_data=None):
        """Mark order as paid (called by payment gateway webhooks)"""
        self.payment_status = 'paid'
        self.payment_gateway_transaction_id = transaction_id
        self.payment_gateway_reference = reference
        if callback_data:
            self.payment_gateway_callback_data = callback_data
        self.payment_completed_at = timezone.now()
        self.save()
        
        # Update order status
        if self.status == 'pending':
            self.status = 'confirmed'
            self.save()


class OrderItem(models.Model):
    """عناصر الطلب"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name=_("الطلب"))
    product = models.ForeignKey(OnlineProduct, on_delete=models.SET_NULL, null=True, verbose_name=_("المنتج"))
    product_name = models.CharField(max_length=200, verbose_name=_("اسم المنتج"))
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("الكمية"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("سعر الوحدة"))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("المجموع الفرعي"))
    
    class Meta:
        verbose_name = _("عنصر الطلب")
        verbose_name_plural = _("عناصر الطلب")


class Wishlist(models.Model):
    """قائمة الأمنيات"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ecommerce_wishlists', verbose_name=_("المستخدم"))
    product = models.ForeignKey(OnlineProduct, on_delete=models.CASCADE, verbose_name=_("المنتج"))
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("قائمة الأمنيات")
        verbose_name_plural = _("قوائم الأمنيات")
        unique_together = ['user', 'product']


class ProductReview(models.Model):
    """تقييمات المنتجات"""
    product = models.ForeignKey(OnlineProduct, on_delete=models.CASCADE, related_name='reviews', verbose_name=_("المنتج"))
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("المستخدم"))
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)], verbose_name=_("التقييم"))
    comment = models.TextField(blank=True, verbose_name=_("التعليق"))
    is_approved = models.BooleanField(default=False, verbose_name=_("موافق عليه"))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("تقييم المنتج")
        verbose_name_plural = _("تقييمات المنتجات")
        unique_together = ['product', 'user']


class Coupon(models.Model):
    """كوبونات الخصم"""
    code = models.CharField(max_length=50, unique=True, verbose_name=_("كود الكوبون"))
    discount_type = models.CharField(max_length=10, choices=[
        ('percentage', _('نسبة مئوية')),
        ('fixed', _('مبلغ ثابت')),
    ], verbose_name=_("نوع الخصم"))
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("قيمة الخصم"))
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("الحد الأدنى للطلب"))
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("الحد الأقصى للخصم"))
    usage_limit = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("حد الاستخدام"))
    used_count = models.PositiveIntegerField(default=0, verbose_name=_("عدد مرات الاستخدام"))
    valid_from = models.DateTimeField(verbose_name=_("صالح من"))
    valid_to = models.DateTimeField(verbose_name=_("صالح حتى"))
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    
    class Meta:
        verbose_name = _("كوبون")
        verbose_name_plural = _("الكوبونات")
    
    def __str__(self):
        return self.code
    
    def is_valid(self):
        """التحقق من صلاحية الكوبون"""
        try:
            now = timezone.now()
            
            if not self.is_active:
                return False
            
            # التحقق من التاريخ
            if now < self.valid_from or now > self.valid_to:
                return False
            
            # التحقق من حد الاستخدام
            if self.usage_limit and self.used_count >= self.usage_limit:
                return False
            
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in Coupon.is_valid: {str(e)}", exc_info=True)
            return False


class PaymentGateway(models.Model):
    """بوابات الدفع الإلكتروني"""
    GATEWAY_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('tap', 'Tap Payments'),
        ('moyasar', 'Moyasar'),
        ('paytabs', 'PayTabs'),
        ('hyperpay', 'HyperPay'),
        ('myfatoorah', 'MyFatoorah'),
        ('payfort', 'PayFort'),
        ('telr', 'Telr'),
        # Egypt Payment Gateways (Added January 2026)
        ('paymob_card', 'Paymob - البطاقات'),
        ('paymob_wallet', 'Paymob - محافظ موبايل'),
        ('paymob_valu', 'Paymob - تقسيط ValU'),
        ('paymob_souhoola', 'Paymob - تقسيط سهولة'),
        ('fawry', 'فوري Fawry'),
        ('instapay', 'InstaPay'),
        # Traditional methods
        ('cod', _('الدفع عند الاستلام')),
        ('bank_transfer', _('تحويل بنكي')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_("اسم البوابة"))
    gateway_type = models.CharField(max_length=50, choices=GATEWAY_CHOICES, unique=True, verbose_name=_("نوع البوابة"))
    
    # بيانات الاتصال - مشفرة بـ Fernet (January 2026) - Downgraded to CharField due to missing lib
    api_key = models.CharField(max_length=500, blank=True, verbose_name=_("API Key"))
    api_secret = models.CharField(max_length=500, blank=True, verbose_name=_("API Secret"))
    merchant_id = models.CharField(max_length=200, blank=True, verbose_name=_("معرف التاجر"))
    
    # إعدادات إضافية (JSON)
    extra_settings = models.JSONField(default=dict, blank=True, verbose_name=_("إعدادات إضافية"))
    
    # وضع الاختبار
    is_sandbox = models.BooleanField(default=True, verbose_name=_("وضع الاختبار"))
    sandbox_api_key = models.CharField(max_length=500, blank=True, verbose_name=_("API Key للاختبار"))
    sandbox_api_secret = models.CharField(max_length=500, blank=True, verbose_name=_("API Secret للاختبار"))
    
    # الحالة والترتيب
    is_active = models.BooleanField(default=False, verbose_name=_("مفعلة"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    
    # الأيقونة والوصف
    icon = models.ImageField(upload_to='ecommerce/payment_gateways/', blank=True, null=True, verbose_name=_("الأيقونة"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("بوابة الدفع")
        verbose_name_plural = _("بوابات الدفع")
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    def get_active_credentials(self):
        """الحصول على بيانات الاتصال النشطة"""
        if self.is_sandbox:
            return {
                'api_key': self.sandbox_api_key,
                'api_secret': self.sandbox_api_secret,
                'merchant_id': self.merchant_id,
            }
        return {
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'merchant_id': self.merchant_id,
        }


class ShippingCompany(models.Model):
    """شركات الشحن"""
    COMPANY_CHOICES = [
        ('aramex', 'Aramex'),
        ('dhl', 'DHL'),
        ('fedex', 'FedEx'),
        ('smsa', 'SMSA Express'),
        ('saudi_post', _('البريد السعودي')),
        ('zajil', 'Zajil Express'),
        ('naqel', 'Naqel Express'),
        ('imile', 'iMile'),
        ('jnt', 'J&T Express'),
        ('custom', _('شركة مخصصة')),
    ]
    
    CALCULATION_CHOICES = [
        ('flat', _('سعر ثابت')),
        ('weight', _('حسب الوزن')),
        ('price', _('حسب قيمة الطلب')),
        ('api', _('من API الشركة')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_("اسم الشركة"))
    company_type = models.CharField(max_length=50, choices=COMPANY_CHOICES, verbose_name=_("نوع الشركة"))
    
    # بيانات الاتصال - مشفرة بـ Fernet (January 2026) - Downgraded to CharField due to missing lib
    api_key = models.CharField(max_length=500, blank=True, verbose_name=_("API Key"))
    api_secret = models.CharField(max_length=500, blank=True, verbose_name=_("API Secret"))
    account_number = models.CharField(max_length=100, blank=True, verbose_name=_("رقم الحساب"))
    
    # إعدادات الشحن
    calculation_type = models.CharField(max_length=20, choices=CALCULATION_CHOICES, default='flat', verbose_name=_("طريقة الحساب"))
    flat_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("السعر الثابت"))
    weight_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("سعر الكيلو"))
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("حد الشحن المجاني"))
    
    # المناطق المتاحة
    available_countries = models.JSONField(default=list, blank=True, verbose_name=_("الدول المتاحة"))
    available_cities = models.JSONField(default=list, blank=True, verbose_name=_("المدن المتاحة"))
    
    # إعدادات إضافية
    extra_settings = models.JSONField(default=dict, blank=True, verbose_name=_("إعدادات إضافية"))
    is_sandbox = models.BooleanField(default=True, verbose_name=_("وضع الاختبار"))
    
    # الحالة
    is_active = models.BooleanField(default=False, verbose_name=_("مفعلة"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    
    # الأيقونة والوصف
    icon = models.ImageField(upload_to='ecommerce/shipping_companies/', blank=True, null=True, verbose_name=_("الأيقونة"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    tracking_url = models.URLField(blank=True, verbose_name=_("رابط التتبع"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("شركة الشحن")
        verbose_name_plural = _("شركات الشحن")
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    def calculate_shipping(self, order_total, weight=0):
        """حساب تكلفة الشحن"""
        if self.free_shipping_threshold and order_total >= self.free_shipping_threshold:
            return Decimal('0')
        
        if self.calculation_type == 'flat':
            return self.flat_rate
        elif self.calculation_type == 'weight':
            return self.weight_rate * Decimal(str(weight))
        elif self.calculation_type == 'price':
            # يمكن تخصيص نسبة من قيمة الطلب
            return order_total * Decimal('0.05')  # 5% من قيمة الطلب
        return self.flat_rate


class SocialMediaIntegration(models.Model):
    """تكامل مع مواقع التواصل الاجتماعي"""
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter / X'),
        ('tiktok', 'TikTok'),
        ('snapchat', 'Snapchat'),
        ('youtube', 'YouTube'),
        ('linkedin', 'LinkedIn'),
        ('whatsapp', 'WhatsApp Business'),
        ('telegram', 'Telegram'),
        ('pinterest', 'Pinterest'),
    ]
    
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, unique=True, verbose_name=_("المنصة"))
    
    # روابط الحسابات
    profile_url = models.URLField(blank=True, verbose_name=_("رابط الحساب"))
    username = models.CharField(max_length=100, blank=True, verbose_name=_("اسم المستخدم"))
    
    # بيانات API للتكامل
    app_id = models.CharField(max_length=200, blank=True, verbose_name=_("App ID"))
    app_secret = models.CharField(max_length=500, blank=True, verbose_name=_("App Secret"))
    access_token = models.TextField(blank=True, verbose_name=_("Access Token"))
    
    # Facebook Pixel / تتبع
    pixel_id = models.CharField(max_length=100, blank=True, verbose_name=_("Pixel ID"))
    
    # إعدادات إضافية
    extra_settings = models.JSONField(default=dict, blank=True, verbose_name=_("إعدادات إضافية"))
    
    # تفعيل المشاركة
    enable_sharing = models.BooleanField(default=True, verbose_name=_("تفعيل المشاركة"))
    enable_login = models.BooleanField(default=False, verbose_name=_("تفعيل تسجيل الدخول"))
    enable_tracking = models.BooleanField(default=False, verbose_name=_("تفعيل التتبع"))
    
    # عرض في الموقع
    show_in_header = models.BooleanField(default=True, verbose_name=_("عرض في الهيدر"))
    show_in_footer = models.BooleanField(default=True, verbose_name=_("عرض في الفوتر"))
    
    is_active = models.BooleanField(default=False, verbose_name=_("مفعل"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("تكامل التواصل الاجتماعي")
        verbose_name_plural = _("تكاملات التواصل الاجتماعي")
        ordering = ['sort_order', 'platform']
    
    def __str__(self):
        return self.get_platform_display()
    
    @property
    def icon_class(self):
        """إرجاع class الأيقونة"""
        icons = {
            'facebook': 'fab fa-facebook-f',
            'instagram': 'fab fa-instagram',
            'twitter': 'fab fa-x-twitter',
            'tiktok': 'fab fa-tiktok',
            'snapchat': 'fab fa-snapchat-ghost',
            'youtube': 'fab fa-youtube',
            'linkedin': 'fab fa-linkedin-in',
            'whatsapp': 'fab fa-whatsapp',
            'telegram': 'fab fa-telegram',
            'pinterest': 'fab fa-pinterest-p',
        }
        return icons.get(self.platform, 'fas fa-share-alt')


class StorePageContent(models.Model):
    """محتوى صفحات المتجر (الرئيسية، من نحن، إلخ)"""
    PAGE_CHOICES = [
        ('home', _('الصفحة الرئيسية')),
        ('about', _('من نحن')),
        ('contact', _('اتصل بنا')),
        ('faq', _('الأسئلة الشائعة')),
        ('privacy', _('سياسة الخصوصية')),
        ('terms', _('الشروط والأحكام')),
        ('shipping', _('سياسة الشحن')),
        ('returns', _('سياسة الإرجاع')),
    ]
    
    page = models.CharField(max_length=50, choices=PAGE_CHOICES, unique=True, verbose_name=_("الصفحة"))
    title = models.CharField(max_length=200, verbose_name=_("العنوان"))
    content = models.TextField(verbose_name=_("المحتوى"))
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True, verbose_name=_("عنوان SEO"))
    meta_description = models.CharField(max_length=300, blank=True, verbose_name=_("وصف SEO"))
    
    is_active = models.BooleanField(default=True, verbose_name=_("مفعلة"))
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("محتوى الصفحة")
        verbose_name_plural = _("محتويات الصفحات")
    
    def __str__(self):
        return self.get_page_display()


class Customer(models.Model):
    """ملف العميل في المتجر الإلكتروني"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile', verbose_name=_("المستخدم"))
    
    # الربط مع نظام المبيعات
    partner_customer = models.OneToOneField(
        'partners.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecommerce_profile',
        verbose_name=_("ملف العميل في المبيعات"),
        help_text=_("ربط العميل بنظام المبيعات لإنشاء الفواتير تلقائياً")
    )
    
    # البيانات الشخصية
    phone = models.CharField(max_length=20, blank=True, verbose_name=_("رقم الهاتف"))
    avatar = models.ImageField(upload_to='ecommerce/customers/', blank=True, null=True, verbose_name=_("الصورة الشخصية"))
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_("تاريخ الميلاد"))
    gender = models.CharField(max_length=10, choices=[
        ('male', _('ذكر')),
        ('female', _('أنثى')),
    ], blank=True, verbose_name=_("الجنس"))
    
    # العنوان الافتراضي
    default_address = models.TextField(blank=True, verbose_name=_("العنوان الافتراضي"))
    city = models.CharField(max_length=100, blank=True, verbose_name=_("المدينة"))
    country = models.CharField(max_length=100, default='مصر', verbose_name=_("الدولة"))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_("الرمز البريدي"))
    
    # الإحصائيات
    total_orders = models.PositiveIntegerField(default=0, verbose_name=_("إجمالي الطلبات"))
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_("إجمالي المشتريات"))
    
    # التفضيلات
    newsletter_subscribed = models.BooleanField(default=True, verbose_name=_("مشترك في النشرة البريدية"))
    sms_notifications = models.BooleanField(default=True, verbose_name=_("إشعارات SMS"))
    
    # التحقق
    email_verified = models.BooleanField(default=False, verbose_name=_("البريد موثق"))
    phone_verified = models.BooleanField(default=False, verbose_name=_("الهاتف موثق"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("عميل")
        verbose_name_plural = _("العملاء")
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username
    
    @property
    def name(self):
        return self.user.get_full_name() or self.user.username
    
    @property
    def email(self):
        return self.user.email


class CustomerAddress(models.Model):
    """عناوين العميل"""
    ADDRESS_TYPES = [
        ('home', _('المنزل')),
        ('work', _('العمل')),
        ('other', _('آخر')),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses', verbose_name=_("العميل"))
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES, default='home', verbose_name=_("نوع العنوان"))
    
    full_name = models.CharField(max_length=200, verbose_name=_("الاسم الكامل"))
    phone = models.CharField(max_length=20, verbose_name=_("رقم الهاتف"))
    address_line1 = models.CharField(max_length=300, verbose_name=_("العنوان - السطر 1"))
    address_line2 = models.CharField(max_length=300, blank=True, verbose_name=_("العنوان - السطر 2"))
    city = models.CharField(max_length=100, verbose_name=_("المدينة"))
    state = models.CharField(max_length=100, blank=True, verbose_name=_("المنطقة"))
    country = models.CharField(max_length=100, default='مصر', verbose_name=_("الدولة"))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_("الرمز البريدي"))
    
    is_default = models.BooleanField(default=False, verbose_name=_("العنوان الافتراضي"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("عنوان العميل")
        verbose_name_plural = _("عناوين العملاء")
    
    def __str__(self):
        return f"{self.full_name} - {self.city}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            # إلغاء العنوان الافتراضي السابق
            CustomerAddress.objects.filter(customer=self.customer, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class SocialAccount(models.Model):
    """الحسابات الاجتماعية المرتبطة"""
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter / X'),
        ('apple', 'Apple'),
        ('github', 'GitHub'),
        ('microsoft', 'Microsoft'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='social_accounts', verbose_name=_("العميل"))
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, verbose_name=_("المزود"))
    
    # بيانات الحساب
    provider_user_id = models.CharField(max_length=255, verbose_name=_("معرف المستخدم لدى المزود"))
    email = models.EmailField(blank=True, verbose_name=_("البريد الإلكتروني"))
    name = models.CharField(max_length=255, blank=True, verbose_name=_("الاسم"))
    picture_url = models.URLField(blank=True, verbose_name=_("رابط الصورة"))
    
    # التوكنات
    access_token = models.TextField(blank=True, verbose_name=_("Access Token"))
    refresh_token = models.TextField(blank=True, verbose_name=_("Refresh Token"))
    token_expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_("انتهاء التوكن"))
    
    # البيانات الخام
    raw_data = models.JSONField(default=dict, blank=True, verbose_name=_("البيانات الخام"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("حساب اجتماعي")
        verbose_name_plural = _("الحسابات الاجتماعية")
        unique_together = ['provider', 'provider_user_id']
    
    def __str__(self):
        return f"{self.get_provider_display()} - {self.email or self.name}"


class SocialAuthProvider(models.Model):
    """إعدادات مزودي تسجيل الدخول الاجتماعي"""
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter / X'),
        ('apple', 'Apple'),
        ('github', 'GitHub'),
        ('microsoft', 'Microsoft'),
    ]
    
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True, verbose_name=_("المزود"))
    name = models.CharField(max_length=100, verbose_name=_("الاسم المعروض"))
    
    # بيانات OAuth
    client_id = models.CharField(max_length=500, verbose_name=_("Client ID"))
    client_secret = models.CharField(max_length=500, verbose_name=_("Client Secret"))
    
    # URLs (معظمها مملوءة تلقائياً)
    auth_url = models.URLField(blank=True, verbose_name=_("Authorization URL"))
    token_url = models.URLField(blank=True, verbose_name=_("Token URL"))
    userinfo_url = models.URLField(blank=True, verbose_name=_("User Info URL"))
    
    # Scopes
    scopes = models.CharField(max_length=500, default='email profile', verbose_name=_("Scopes"))
    
    # إعدادات إضافية
    extra_params = models.JSONField(default=dict, blank=True, verbose_name=_("معاملات إضافية"))
    
    # الأيقونة واللون
    icon_class = models.CharField(max_length=100, blank=True, verbose_name=_("CSS Class للأيقونة"))
    button_color = models.CharField(max_length=20, blank=True, verbose_name=_("لون الزر"))
    
    is_active = models.BooleanField(default=False, verbose_name=_("مفعل"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("مزود تسجيل الدخول")
        verbose_name_plural = _("مزودي تسجيل الدخول")
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    def get_oauth_config(self):
        """الحصول على إعدادات OAuth الكاملة"""
        configs = {
            'google': {
                'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'token_url': 'https://oauth2.googleapis.com/token',
                'userinfo_url': 'https://www.googleapis.com/oauth2/v3/userinfo',
                'scopes': 'openid email profile',
                'icon_class': 'fab fa-google',
                'button_color': '#DB4437',
            },
            'facebook': {
                'auth_url': 'https://www.facebook.com/v18.0/dialog/oauth',
                'token_url': 'https://graph.facebook.com/v18.0/oauth/access_token',
                'userinfo_url': 'https://graph.facebook.com/me?fields=id,name,email,picture',
                'scopes': 'email public_profile',
                'icon_class': 'fab fa-facebook-f',
                'button_color': '#1877F2',
            },
            'twitter': {
                'auth_url': 'https://twitter.com/i/oauth2/authorize',
                'token_url': 'https://api.twitter.com/2/oauth2/token',
                'userinfo_url': 'https://api.twitter.com/2/users/me',
                'scopes': 'users.read tweet.read',
                'icon_class': 'fab fa-x-twitter',
                'button_color': '#000000',
            },
            'apple': {
                'auth_url': 'https://appleid.apple.com/auth/authorize',
                'token_url': 'https://appleid.apple.com/auth/token',
                'userinfo_url': '',
                'scopes': 'name email',
                'icon_class': 'fab fa-apple',
                'button_color': '#000000',
            },
            'github': {
                'auth_url': 'https://github.com/login/oauth/authorize',
                'token_url': 'https://github.com/login/oauth/access_token',
                'userinfo_url': 'https://api.github.com/user',
                'scopes': 'read:user user:email',
                'icon_class': 'fab fa-github',
                'button_color': '#333333',
            },
            'microsoft': {
                'auth_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                'token_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                'userinfo_url': 'https://graph.microsoft.com/v1.0/me',
                'scopes': 'openid email profile User.Read',
                'icon_class': 'fab fa-microsoft',
                'button_color': '#00A4EF',
            },
        }
        
        config = configs.get(self.provider, {})
        return {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'auth_url': self.auth_url or config.get('auth_url', ''),
            'token_url': self.token_url or config.get('token_url', ''),
            'userinfo_url': self.userinfo_url or config.get('userinfo_url', ''),
            'scopes': self.scopes or config.get('scopes', ''),
            'icon_class': self.icon_class or config.get('icon_class', ''),
            'button_color': self.button_color or config.get('button_color', ''),
        }
    
    def save(self, *args, **kwargs):
        # ملء القيم الافتراضية
        config = self.get_oauth_config()
        if not self.auth_url:
            self.auth_url = config.get('auth_url', '')
        if not self.token_url:
            self.token_url = config.get('token_url', '')
        if not self.userinfo_url:
            self.userinfo_url = config.get('userinfo_url', '')
        if not self.scopes:
            self.scopes = config.get('scopes', 'email profile')
        if not self.icon_class:
            self.icon_class = config.get('icon_class', '')
        if not self.button_color:
            self.button_color = config.get('button_color', '')
        super().save(*args, **kwargs)


class PasswordResetToken(models.Model):
    """توكنات إعادة تعيين كلمة المرور"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='password_reset_tokens', verbose_name=_("العميل"))
    token = models.CharField(max_length=100, unique=True, verbose_name=_("التوكن"))
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name=_("تنتهي في"))
    used = models.BooleanField(default=False, verbose_name=_("مستخدم"))
    
    class Meta:
        verbose_name = _("توكن إعادة تعيين كلمة المرور")
        verbose_name_plural = _("توكنات إعادة تعيين كلمة المرور")
    
    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at


class EmailVerificationToken(models.Model):
    """توكنات تأكيد البريد الإلكتروني"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='email_verification_tokens', verbose_name=_("العميل"))
    token = models.CharField(max_length=100, unique=True, verbose_name=_("التوكن"))
    email = models.EmailField(verbose_name=_("البريد الإلكتروني"))
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name=_("تنتهي في"))
    used = models.BooleanField(default=False, verbose_name=_("مستخدم"))
    
    class Meta:
        verbose_name = _("توكن تأكيد البريد")
        verbose_name_plural = _("توكنات تأكيد البريد")
    
    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at


class StoreBanner(models.Model):
    """بانرات المتجر"""
    POSITION_CHOICES = [
        ('home_slider', _('السلايدر الرئيسي')),
        ('home_top', _('أعلى الصفحة الرئيسية')),
        ('home_middle', _('وسط الصفحة الرئيسية')),
        ('sidebar', _('الشريط الجانبي')),
        ('category_top', _('أعلى صفحة الفئات')),
        ('product_top', _('أعلى صفحة المنتج')),
    ]
    
    title = models.CharField(max_length=200, verbose_name=_("العنوان"))
    subtitle = models.CharField(max_length=300, blank=True, verbose_name=_("العنوان الفرعي"))
    image = models.ImageField(upload_to='ecommerce/banners/', verbose_name=_("الصورة"))
    image_mobile = models.ImageField(upload_to='ecommerce/banners/', blank=True, null=True, verbose_name=_("صورة الموبايل"))
    
    link_url = models.URLField(blank=True, verbose_name=_("رابط البانر"))
    button_text = models.CharField(max_length=50, blank=True, verbose_name=_("نص الزر"))
    
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default='home_slider', verbose_name=_("الموضع"))
    
    # جدولة العرض
    start_date = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ البداية"))
    end_date = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ النهاية"))
    
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("ترتيب العرض"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("بانر")
        verbose_name_plural = _("البانرات")
        ordering = ['position', 'sort_order']
    
    def __str__(self):
        return self.title
    
    def is_visible(self):
        """هل البانر يظهر الآن"""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

# ==================== إعدادات الهيدر ====================

class HeaderSettings(models.Model):
    """إعدادات رأس المتجر (الهيدر)"""
    # الشعار
    logo = models.ImageField(upload_to='ecommerce/header/', blank=True, null=True, verbose_name=_("الشعار"))
    logo_alt_text = models.CharField(max_length=100, blank=True, verbose_name=_("النص البديل للشعار"))
    favicon = models.ImageField(upload_to='ecommerce/header/', blank=True, null=True, verbose_name=_("أيقونة الموقع"))
    
    # النصوص
    top_bar_text = models.CharField(max_length=500, blank=True, verbose_name=_("نص الشريط العلوي"))
    top_bar_enabled = models.BooleanField(default=True, verbose_name=_("إظهار الشريط العلوي"))
    
    # الألوان
    header_bg_color = models.CharField(max_length=20, default='#1a2538', verbose_name=_("لون خلفية الهيدر"))
    header_text_color = models.CharField(max_length=20, default='#ffffff', verbose_name=_("لون نص الهيدر"))
    top_bar_bg_color = models.CharField(max_length=20, default='#2c3e50', verbose_name=_("لون خلفية الشريط العلوي"))
    
    # إعدادات العرض
    show_search = models.BooleanField(default=True, verbose_name=_("إظهار البحث"))
    show_cart = models.BooleanField(default=True, verbose_name=_("إظهار السلة"))
    show_wishlist = models.BooleanField(default=True, verbose_name=_("إظهار المفضلة"))
    show_account = models.BooleanField(default=True, verbose_name=_("إظهار الحساب"))
    show_language = models.BooleanField(default=False, verbose_name=_("إظهار تبديل اللغة"))
    
    # القائمة الثابتة
    sticky_header = models.BooleanField(default=True, verbose_name=_("هيدر ثابت عند التمرير"))
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("إعدادات الهيدر")
        verbose_name_plural = _("إعدادات الهيدر")
    
    def __str__(self):
        return "إعدادات الهيدر"
    
    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


# ==================== إعدادات الفوتر ====================

class FooterSettings(models.Model):
    """إعدادات ذيل المتجر (الفوتر)"""
    # الشعار والوصف
    footer_logo = models.ImageField(upload_to='ecommerce/footer/', blank=True, null=True, verbose_name=_("شعار الفوتر"))
    footer_description = models.TextField(blank=True, verbose_name=_("وصف الفوتر"))
    
    # الألوان
    footer_bg_color = models.CharField(max_length=20, default='#1a2538', verbose_name=_("لون خلفية الفوتر"))
    footer_text_color = models.CharField(max_length=20, default='#ffffff', verbose_name=_("لون نص الفوتر"))
    
    # حقوق النشر
    copyright_text = models.CharField(max_length=300, blank=True, verbose_name=_("نص حقوق النشر"))
    
    # إعدادات العرض
    show_newsletter = models.BooleanField(default=True, verbose_name=_("إظهار النشرة البريدية"))
    show_social_links = models.BooleanField(default=True, verbose_name=_("إظهار روابط التواصل"))
    show_payment_icons = models.BooleanField(default=True, verbose_name=_("إظهار أيقونات الدفع"))
    show_app_links = models.BooleanField(default=False, verbose_name=_("إظهار روابط التطبيق"))
    
    # روابط التطبيق
    app_store_link = models.URLField(blank=True, verbose_name=_("رابط App Store"))
    play_store_link = models.URLField(blank=True, verbose_name=_("رابط Play Store"))
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("إعدادات الفوتر")
        verbose_name_plural = _("إعدادات الفوتر")
    
    def __str__(self):
        return "إعدادات الفوتر"
    
    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


# ==================== روابط الهيدر ====================

class HeaderLink(models.Model):
    """روابط القائمة الرئيسية في الهيدر"""
    title = models.CharField(max_length=100, verbose_name=_("العنوان"))
    url = models.CharField(max_length=500, verbose_name=_("الرابط"))
    icon = models.CharField(max_length=50, blank=True, verbose_name=_("أيقونة FontAwesome"))
    
    # الفتح في نافذة جديدة
    open_new_tab = models.BooleanField(default=False, verbose_name=_("فتح في نافذة جديدة"))
    
    # الترتيب والحالة
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("الترتيب"))
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    
    # رابط فرعي
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                               related_name='children', verbose_name=_("الرابط الأب"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("رابط الهيدر")
        verbose_name_plural = _("روابط الهيدر")
        ordering = ['sort_order']
    
    def __str__(self):
        return self.title


# ==================== روابط الفوتر ====================

class FooterColumn(models.Model):
    """أعمدة الفوتر"""
    title = models.CharField(max_length=100, verbose_name=_("عنوان العمود"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("الترتيب"))
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    
    class Meta:
        verbose_name = _("عمود الفوتر")
        verbose_name_plural = _("أعمدة الفوتر")
        ordering = ['sort_order']
    
    def __str__(self):
        return self.title


class FooterLink(models.Model):
    """روابط الفوتر"""
    column = models.ForeignKey(FooterColumn, on_delete=models.CASCADE, related_name='links', verbose_name=_("العمود"))
    title = models.CharField(max_length=100, verbose_name=_("العنوان"))
    url = models.CharField(max_length=500, verbose_name=_("الرابط"))
    open_new_tab = models.BooleanField(default=False, verbose_name=_("فتح في نافذة جديدة"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("الترتيب"))
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    
    class Meta:
        verbose_name = _("رابط الفوتر")
        verbose_name_plural = _("روابط الفوتر")
        ordering = ['sort_order']
    
    def __str__(self):
        return self.title


# ==================== النشرة البريدية ====================

class NewsletterSubscriber(models.Model):
    """مشتركي النشرة البريدية"""
    email = models.EmailField(unique=True, verbose_name=_("البريد الإلكتروني"))
    name = models.CharField(max_length=100, blank=True, verbose_name=_("الاسم"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    subscribed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الاشتراك"))
    unsubscribed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ إلغاء الاشتراك"))
    
    # مصدر الاشتراك
    source = models.CharField(max_length=50, default='website', verbose_name=_("المصدر"))
    
    class Meta:
        verbose_name = _("مشترك النشرة")
        verbose_name_plural = _("مشتركي النشرة")
        ordering = ['-subscribed_at']
    
    def __str__(self):
        return self.email


class NewsletterCampaign(models.Model):
    """حملات النشرة البريدية"""
    STATUS_CHOICES = [
        ('draft', _('مسودة')),
        ('scheduled', _('مجدولة')),
        ('sending', _('قيد الإرسال')),
        ('sent', _('تم الإرسال')),
        ('cancelled', _('ملغاة')),
    ]
    
    subject = models.CharField(max_length=200, verbose_name=_("عنوان الرسالة"))
    content = models.TextField(verbose_name=_("محتوى الرسالة"))
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name=_("الحالة"))
    
    # الإحصائيات
    total_recipients = models.PositiveIntegerField(default=0, verbose_name=_("عدد المستلمين"))
    sent_count = models.PositiveIntegerField(default=0, verbose_name=_("تم الإرسال"))
    opened_count = models.PositiveIntegerField(default=0, verbose_name=_("تم الفتح"))
    clicked_count = models.PositiveIntegerField(default=0, verbose_name=_("تم النقر"))
    
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name=_("موعد الإرسال"))
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الإرسال"))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("حملة النشرة")
        verbose_name_plural = _("حملات النشرة")
        ordering = ['-created_at']
    
    def __str__(self):
        return self.subject


# ==================== العروض السريعة ====================

class FlashSale(models.Model):
    """العروض السريعة"""
    name = models.CharField(max_length=200, verbose_name=_("اسم العرض"))
    description = models.TextField(blank=True, verbose_name=_("الوصف"))
    
    # فترة العرض
    start_date = models.DateTimeField(verbose_name=_("تاريخ البداية"))
    end_date = models.DateTimeField(verbose_name=_("تاريخ النهاية"))
    
    # الخصم
    discount_type = models.CharField(max_length=20, choices=[
        ('percentage', _('نسبة مئوية')),
        ('fixed', _('مبلغ ثابت')),
    ], default='percentage', verbose_name=_("نوع الخصم"))
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("قيمة الخصم"))
    
    # البانر
    banner = models.ImageField(upload_to='ecommerce/flash_sales/', blank=True, null=True, verbose_name=_("البانر"))
    
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    show_countdown = models.BooleanField(default=True, verbose_name=_("إظهار العد التنازلي"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("عرض سريع")
        verbose_name_plural = _("العروض السريعة")
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name
    
    @property
    def is_running(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date


class FlashSaleProduct(models.Model):
    """منتجات العرض السريع"""
    flash_sale = models.ForeignKey(FlashSale, on_delete=models.CASCADE, related_name='products', verbose_name=_("العرض"))
    product = models.ForeignKey(OnlineProduct, on_delete=models.CASCADE, verbose_name=_("المنتج"))
    
    # سعر مخصص للعرض (اختياري)
    custom_sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("سعر العرض"))
    
    # حد الكمية
    quantity_limit = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("حد الكمية"))
    sold_count = models.PositiveIntegerField(default=0, verbose_name=_("الكمية المباعة"))
    
    class Meta:
        verbose_name = _("منتج العرض")
        verbose_name_plural = _("منتجات العرض")
        unique_together = ['flash_sale', 'product']


# ==================== أقسام الصفحة الرئيسية ====================

class HomepageSection(models.Model):
    """أقسام الصفحة الرئيسية"""
    SECTION_TYPES = [
        ('featured_products', _('منتجات مميزة')),
        ('new_arrivals', _('وصل حديثاً')),
        ('best_sellers', _('الأكثر مبيعاً')),
        ('on_sale', _('عروض وخصومات')),
        ('category_products', _('منتجات فئة محددة')),
        ('custom_products', _('منتجات مخصصة')),
        ('banner', _('بانر')),
        ('categories_grid', _('شبكة الفئات')),
        ('brands', _('العلامات التجارية')),
        ('testimonials', _('آراء العملاء')),
        ('custom_html', _('HTML مخصص')),
    ]
    
    DISPLAY_STYLES = [
        ('grid', _('شبكة')),
        ('slider', _('سلايدر')),
        ('carousel', _('كاروسيل')),
        ('list', _('قائمة')),
    ]
    
    title = models.CharField(max_length=200, verbose_name=_("العنوان"))
    subtitle = models.CharField(max_length=300, blank=True, verbose_name=_("العنوان الفرعي"))
    
    section_type = models.CharField(max_length=50, choices=SECTION_TYPES, verbose_name=_("نوع القسم"))
    display_style = models.CharField(max_length=20, choices=DISPLAY_STYLES, default='grid', verbose_name=_("نمط العرض"))
    
    # للفئة المحددة
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=_("الفئة"))
    
    # عدد المنتجات
    products_count = models.PositiveIntegerField(default=8, verbose_name=_("عدد المنتجات"))
    
    # HTML مخصص
    custom_html = models.TextField(blank=True, verbose_name=_("HTML مخصص"))
    
    # الترتيب والحالة
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("الترتيب"))
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    
    # رابط "عرض الكل"
    show_view_all = models.BooleanField(default=True, verbose_name=_("إظهار رابط عرض الكل"))
    view_all_url = models.CharField(max_length=500, blank=True, verbose_name=_("رابط عرض الكل"))
    
    # الخلفية
    bg_color = models.CharField(max_length=20, blank=True, verbose_name=_("لون الخلفية"))
    bg_image = models.ImageField(upload_to='ecommerce/sections/', blank=True, null=True, verbose_name=_("صورة الخلفية"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("قسم الصفحة الرئيسية")
        verbose_name_plural = _("أقسام الصفحة الرئيسية")
        ordering = ['sort_order']
    
    def __str__(self):
        return self.title


class HomepageSectionProduct(models.Model):
    """منتجات مخصصة لقسم معين"""
    section = models.ForeignKey(HomepageSection, on_delete=models.CASCADE, related_name='custom_products', verbose_name=_("القسم"))
    product = models.ForeignKey(OnlineProduct, on_delete=models.CASCADE, verbose_name=_("المنتج"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("الترتيب"))
    
    class Meta:
        verbose_name = _("منتج القسم")
        verbose_name_plural = _("منتجات القسم")
        ordering = ['sort_order']
        unique_together = ['section', 'product']


# ==================== فئات الشريط الجانبي ====================

class SidebarCategory(models.Model):
    """الفئات المعروضة في الشريط الجانبي"""
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, verbose_name=_("الفئة"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("الترتيب"))
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    show_icon = models.BooleanField(default=True, verbose_name=_("إظهار الأيقونة"))
    custom_icon = models.CharField(max_length=50, blank=True, verbose_name=_("أيقونة مخصصة"))
    
    class Meta:
        verbose_name = _("فئة الشريط الجانبي")
        verbose_name_plural = _("فئات الشريط الجانبي")
        ordering = ['sort_order']
    
    def __str__(self):
        return self.category.name


# ==================== تكاليف الشحن حسب المنطقة ====================

class ShippingZone(models.Model):
    """مناطق الشحن"""
    name = models.CharField(max_length=100, verbose_name=_("اسم المنطقة"))
    countries = models.JSONField(default=list, verbose_name=_("الدول"))
    cities = models.JSONField(default=list, blank=True, verbose_name=_("المدن"))
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    
    class Meta:
        verbose_name = _("منطقة الشحن")
        verbose_name_plural = _("مناطق الشحن")
    
    def __str__(self):
        return self.name


class ShippingRate(models.Model):
    """أسعار الشحن"""
    zone = models.ForeignKey(ShippingZone, on_delete=models.CASCADE, related_name='rates', verbose_name=_("المنطقة"))
    company = models.ForeignKey(ShippingCompany, on_delete=models.CASCADE, verbose_name=_("شركة الشحن"))
    
    # نوع السعر
    rate_type = models.CharField(max_length=20, choices=[
        ('flat', _('ثابت')),
        ('weight', _('حسب الوزن')),
        ('price', _('حسب قيمة الطلب')),
    ], default='flat', verbose_name=_("نوع السعر"))
    
    # الأسعار
    flat_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("السعر الثابت"))
    weight_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'), verbose_name=_("سعر الكيلو"))
    min_order_free = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("الحد الأدنى للشحن المجاني"))
    
    # وقت التوصيل
    delivery_time_min = models.PositiveIntegerField(default=1, verbose_name=_("أقل وقت توصيل (أيام)"))
    delivery_time_max = models.PositiveIntegerField(default=3, verbose_name=_("أقصى وقت توصيل (أيام)"))
    
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    
    class Meta:
        verbose_name = _("سعر الشحن")
        verbose_name_plural = _("أسعار الشحن")
        unique_together = ['zone', 'company']
    
    def __str__(self):
        return f"{self.zone.name} - {self.company.name}"


# =====================================================
# نظام الضمان - Warranty System
# =====================================================

import uuid
import qrcode
from io import BytesIO
from django.core.files import File


class ProductWarranty(models.Model):
    """سياسات الضمان للمنتجات"""
    DURATION_UNIT_CHOICES = [
        ('days', _('أيام')),
        ('months', _('أشهر')),
        ('years', _('سنوات')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_("اسم الضمان"))
    description = models.TextField(blank=True, verbose_name=_("وصف الضمان"))
    
    # مدة الضمان
    duration = models.PositiveIntegerField(default=12, verbose_name=_("مدة الضمان"))
    duration_unit = models.CharField(max_length=10, choices=DURATION_UNIT_CHOICES, default='months', verbose_name=_("وحدة المدة"))
    
    # شروط الضمان
    terms_and_conditions = models.TextField(blank=True, verbose_name=_("الشروط والأحكام"))
    coverage = models.TextField(blank=True, verbose_name=_("ما يغطيه الضمان"))
    exclusions = models.TextField(blank=True, verbose_name=_("ما لا يغطيه الضمان"))
    
    # الإعدادات
    is_active = models.BooleanField(default=True, verbose_name=_("مفعل"))
    requires_registration = models.BooleanField(default=True, verbose_name=_("يتطلب تسجيل"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("سياسة الضمان")
        verbose_name_plural = _("سياسات الضمان")
    
    def __str__(self):
        return f"{self.name} ({self.duration} {self.get_duration_unit_display()})"
    
    def get_expiry_date(self, start_date):
        """حساب تاريخ انتهاء الضمان"""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        if self.duration_unit == 'days':
            return start_date + timedelta(days=self.duration)
        elif self.duration_unit == 'months':
            return start_date + relativedelta(months=self.duration)
        elif self.duration_unit == 'years':
            return start_date + relativedelta(years=self.duration)
        return start_date


class WarrantyCard(models.Model):
    """بطاقات الضمان - يتم إنشاؤها مع كل عملية بيع"""
    STATUS_CHOICES = [
        ('pending', _('في انتظار التفعيل')),
        ('active', _('مفعل')),
        ('expired', _('منتهي')),
        ('claimed', _('تم المطالبة')),
        ('void', _('ملغي')),
    ]
    
    # رمز فريد للضمان
    warranty_code = models.CharField(max_length=50, unique=True, verbose_name=_("رمز الضمان"))
    qr_code = models.ImageField(upload_to='ecommerce/warranty/qr/', blank=True, null=True, verbose_name=_("كود QR"))
    
    # ربط بالمنتج والضمان
    product = models.ForeignKey(OnlineProduct, on_delete=models.CASCADE, related_name='warranty_cards', 
                                null=True, blank=True, verbose_name=_("المنتج الإلكتروني"))
    inventory_product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, 
                                          related_name='warranty_cards', null=True, blank=True, 
                                          verbose_name=_("منتج المخزون"))
    warranty_policy = models.ForeignKey(ProductWarranty, on_delete=models.SET_NULL, null=True, 
                                        related_name='cards', verbose_name=_("سياسة الضمان"))
    
    # ربط بالفاتورة
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, 
                             related_name='warranty_cards', verbose_name=_("طلب المتجر"))
    sales_invoice = models.ForeignKey('sales.Invoice', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='warranty_cards', verbose_name=_("فاتورة المبيعات"))
    
    # معلومات البيع
    serial_number = models.CharField(max_length=100, blank=True, verbose_name=_("الرقم التسلسلي للمنتج"))
    purchase_date = models.DateField(verbose_name=_("تاريخ الشراء"))
    
    # معلومات الضمان
    warranty_start_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ بدء الضمان"))
    warranty_end_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ انتهاء الضمان"))
    
    # الحالة
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_("الحالة"))
    
    # معلومات التفعيل
    activated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ التفعيل"))
    activated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='activated_warranties', verbose_name=_("فُعِّل بواسطة"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("بطاقة ضمان")
        verbose_name_plural = _("بطاقات الضمان")
        ordering = ['-created_at']
    
    def __str__(self):
        product_name = self.product.name if self.product else (self.inventory_product.name if self.inventory_product else "منتج")
        return f"ضمان {product_name} - {self.warranty_code}"
    
    def save(self, *args, **kwargs):
        # إنشاء رمز الضمان إذا لم يكن موجوداً
        if not self.warranty_code:
            self.warranty_code = self.generate_warranty_code()
        
        # حساب تاريخ الانتهاء إذا تم تفعيل الضمان
        if self.status == 'active' and self.warranty_start_date and self.warranty_policy:
            self.warranty_end_date = self.warranty_policy.get_expiry_date(self.warranty_start_date)
        
        super().save(*args, **kwargs)
        
        # إنشاء QR code بعد الحفظ إذا لم يكن موجوداً
        if not self.qr_code:
            self.generate_qr_code()
    
    @staticmethod
    def generate_warranty_code():
        """إنشاء رمز ضمان فريد"""
        import random
        import string
        prefix = 'WRN'
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        timestamp = timezone.now().strftime('%y%m')
        return f"{prefix}-{timestamp}-{random_part}"
    
    def generate_qr_code(self):
        """إنشاء كود QR للضمان"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            # البيانات في QR code
            qr_data = f"WARRANTY:{self.warranty_code}"
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            self.qr_code.save(f'warranty_{self.warranty_code}.png', File(buffer), save=True)
        except Exception as e:
            print(f"Error generating QR code: {e}")
    
    @property
    def is_valid(self):
        """التحقق من صلاحية الضمان"""
        if self.status != 'active':
            return False
        if self.warranty_end_date:
            return timezone.now().date() <= self.warranty_end_date
        return False
    
    @property
    def days_remaining(self):
        """الأيام المتبقية"""
        if self.is_valid and self.warranty_end_date:
            return (self.warranty_end_date - timezone.now().date()).days
        return 0


class WarrantyRegistration(models.Model):
    """تسجيل تفعيل الضمان من العميل"""
    STATUS_CHOICES = [
        ('pending', _('في انتظار المراجعة')),
        ('approved', _('موافق عليه')),
        ('rejected', _('مرفوض')),
    ]
    
    warranty_card = models.ForeignKey(WarrantyCard, on_delete=models.CASCADE, null=True, blank=True,
                                      related_name='registrations', verbose_name=_("بطاقة الضمان"))
    
    # معلومات العميل
    customer_name = models.CharField(max_length=200, verbose_name=_("اسم العميل"))
    customer_email = models.EmailField(verbose_name=_("البريد الإلكتروني"))
    customer_phone = models.CharField(max_length=20, verbose_name=_("رقم الهاتف"))
    customer_address = models.TextField(blank=True, verbose_name=_("العنوان"))
    
    # المستخدم المسجل (اختياري)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='warranty_registrations', verbose_name=_("المستخدم"))
    
    # معلومات التسجيل
    warranty_code_entered = models.CharField(max_length=50, verbose_name=_("رمز الضمان المدخل"))
    invoice_number = models.CharField(max_length=100, blank=True, verbose_name=_("رقم الفاتورة"))
    invoice_image = models.ImageField(upload_to='ecommerce/warranty/invoices/', verbose_name=_("صورة الفاتورة"))
    purchase_date = models.DateField(verbose_name=_("تاريخ الشراء"))
    
    # معلومات المنتج
    product_serial = models.CharField(max_length=100, blank=True, verbose_name=_("الرقم التسلسلي"))
    product_image = models.ImageField(upload_to='ecommerce/warranty/products/', blank=True, null=True, 
                                       verbose_name=_("صورة المنتج"))
    
    # الحالة
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_("الحالة"))
    review_notes = models.TextField(blank=True, verbose_name=_("ملاحظات المراجعة"))
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='warranty_reviews', verbose_name=_("راجعه"))
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ المراجعة"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("تسجيل ضمان")
        verbose_name_plural = _("تسجيلات الضمان")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"تسجيل ضمان - {self.customer_name} - {self.warranty_code_entered}"
    
    def approve(self, user):
        """الموافقة على تسجيل الضمان وربطه بنظام ERP"""
        self.status = 'approved'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save()
        
        # تفعيل بطاقة الضمان
        if self.warranty_card:
            self.warranty_card.status = 'active'
            self.warranty_card.warranty_start_date = self.purchase_date
            self.warranty_card.activated_at = timezone.now()
            self.warranty_card.activated_by = user
            self.warranty_card.save()
        
        # ✅ ربط العميل بنظام CRM
        try:
            from crm.models import Customer as CRMCustomer
            crm_customer = CRMCustomer.objects.filter(
                Q(phone=self.customer_phone) | Q(email=self.customer_email)
            ).first()
            if not crm_customer:
                import random, string
                code = 'WRN-' + ''.join(random.choices(string.digits, k=6))
                name_parts = (self.customer_name or '').split(' ', 1)
                crm_customer = CRMCustomer.objects.create(
                    customer_code=code,
                    first_name=name_parts[0] if name_parts else self.customer_name,
                    last_name=name_parts[1] if len(name_parts) > 1 else '',
                    phone=self.customer_phone or '',
                    email=self.customer_email or '',
                    address_line1=self.customer_address or '',
                )
        except Exception:
            crm_customer = None
        
        # ✅ إنشاء سجل ضمان في ERP warranty_management
        if self.warranty_card and crm_customer:
            try:
                from warranty_management.models import (
                    Warranty as ERPWarranty,
                    WarrantyPolicy as ERPWarrantyPolicy,
                )
                from dateutil.relativedelta import relativedelta
                
                inv_product = self.warranty_card.inventory_product
                if inv_product:
                    # البحث عن/إنشاء سياسة ERP
                    erp_policy = ERPWarrantyPolicy.objects.filter(
                        product=inv_product, is_active=True
                    ).first()
                    
                    if not erp_policy:
                        wp = self.warranty_card.warranty_policy
                        erp_policy = ERPWarrantyPolicy.objects.create(
                            name=wp.name if wp else f'ضمان {inv_product.name}',
                            product=inv_product,
                            duration_months=wp.duration if wp else 12,
                            coverage_type='full',
                            terms_conditions=wp.terms_and_conditions if wp else 'ضمان شامل',
                            is_active=True,
                        )
                    
                    start = self.purchase_date
                    end = start + relativedelta(months=erp_policy.duration_months)
                    
                    # تجنب التكرار
                    if not ERPWarranty.objects.filter(
                        warranty_number=self.warranty_card.warranty_code
                    ).exists():
                        ERPWarranty.objects.create(
                            warranty_number=self.warranty_card.warranty_code,
                            policy=erp_policy,
                            customer=crm_customer,
                            product=inv_product,
                            serial_number=self.warranty_card.serial_number or self.product_serial or '',
                            start_date=start,
                            end_date=end,
                            status='active',
                        )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not sync warranty to ERP: {e}")
    
    def reject(self, user, notes=''):
        """رفض تسجيل الضمان"""
        self.status = 'rejected'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()


class WarrantyClaim(models.Model):
    """مطالبات الضمان - عندما يريد العميل استخدام الضمان"""
    STATUS_CHOICES = [
        ('submitted', _('مقدم')),
        ('under_review', _('قيد المراجعة')),
        ('approved', _('موافق عليه')),
        ('in_repair', _('قيد الإصلاح')),
        ('replaced', _('تم الاستبدال')),
        ('completed', _('مكتمل')),
        ('rejected', _('مرفوض')),
    ]
    
    CLAIM_TYPE_CHOICES = [
        ('repair', _('إصلاح')),
        ('replacement', _('استبدال')),
        ('refund', _('استرداد')),
    ]
    
    warranty_card = models.ForeignKey(WarrantyCard, on_delete=models.CASCADE, 
                                      related_name='claims', verbose_name=_("بطاقة الضمان"))
    
    # معلومات المطالبة
    claim_type = models.CharField(max_length=20, choices=CLAIM_TYPE_CHOICES, default='repair', 
                                  verbose_name=_("نوع المطالبة"))
    issue_description = models.TextField(verbose_name=_("وصف المشكلة"))
    issue_images = models.ImageField(upload_to='ecommerce/warranty/claims/', blank=True, null=True,
                                     verbose_name=_("صور المشكلة"))
    
    # معلومات الاتصال
    contact_name = models.CharField(max_length=200, verbose_name=_("اسم جهة الاتصال"))
    contact_phone = models.CharField(max_length=20, verbose_name=_("رقم الهاتف"))
    contact_email = models.EmailField(blank=True, verbose_name=_("البريد الإلكتروني"))
    pickup_address = models.TextField(blank=True, verbose_name=_("عنوان الاستلام"))
    
    # الحالة
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted', verbose_name=_("الحالة"))
    
    # تتبع المعالجة
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_claims', verbose_name=_("مُسند إلى"))
    resolution_notes = models.TextField(blank=True, verbose_name=_("ملاحظات الحل"))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ الحل"))
    
    # التواريخ
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ التقديم"))
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("مطالبة ضمان")
        verbose_name_plural = _("مطالبات الضمان")
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"مطالبة {self.get_claim_type_display()} - {self.warranty_card.warranty_code}"


class WarrantyClaimImage(models.Model):
    """صور إضافية لمطالبات الضمان"""
    claim = models.ForeignKey(WarrantyClaim, on_delete=models.CASCADE, related_name='additional_images',
                             verbose_name=_("المطالبة"))
    image = models.ImageField(upload_to='ecommerce/warranty/claims/', verbose_name=_("الصورة"))
    description = models.CharField(max_length=200, blank=True, verbose_name=_("وصف"))
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("صورة مطالبة")
        verbose_name_plural = _("صور المطالبات")