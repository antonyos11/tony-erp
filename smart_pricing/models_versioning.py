"""
نظام إصدارات قوائم الأسعار
Price List Versioning System

يتيح:
1. حفظ تاريخ كل إصدار من قائمة الأسعار
2. تثبيت السعر للعميل عند الحجز
3. فترة سماح قبل تطبيق الأسعار الجديدة
4. أرشيف كامل للأسعار القديمة
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal


class PriceListVersion(models.Model):
    """
    إصدار قائمة أسعار
    كل مرة تتغير الأسعار، يتم إنشاء إصدار جديد
    """
    
    price_list = models.ForeignKey(
        'smart_pricing.PriceList',
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='قائمة الأسعار'
    )
    
    version_number = models.PositiveIntegerField('رقم الإصدار', default=1)
    version_name = models.CharField('اسم الإصدار', max_length=100, blank=True,
                                     help_text='مثال: أسعار يناير 2026')
    
    # تواريخ الإصدار
    effective_from = models.DateTimeField('ساري من', default=timezone.now,
                                          help_text='تاريخ بدء تطبيق هذا الإصدار')
    effective_until = models.DateTimeField('ساري حتى', null=True, blank=True,
                                           help_text='يُملأ تلقائياً عند إنشاء إصدار جديد')
    
    # فترة السماح
    grace_period_days = models.PositiveIntegerField(
        'فترة السماح (أيام)',
        default=0,
        help_text='عدد الأيام التي يمكن فيها استخدام السعر القديم بعد تاريخ البدء'
    )
    
    # حالة الإصدار
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('pending', 'في انتظار التفعيل'),
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('archived', 'مؤرشف'),
    ]
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # سبب التغيير
    change_reason = models.TextField('سبب التغيير', blank=True)
    
    # معلومات الإنشاء
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_price_versions',
        verbose_name='أنشئ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    # معلومات الاعتماد
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_price_versions',
        verbose_name='اعتُمد بواسطة'
    )
    approved_at = models.DateTimeField('تاريخ الاعتماد', null=True, blank=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    class Meta:
        verbose_name = 'إصدار قائمة أسعار'
        verbose_name_plural = 'إصدارات قوائم الأسعار'
        ordering = ['-version_number']
        unique_together = ['price_list', 'version_number']
    
    def __str__(self):
        return f"{self.price_list.name} - v{self.version_number}"
    
    @property
    def is_current(self):
        """هل هذا الإصدار هو الحالي؟"""
        now = timezone.now()
        if self.status != 'active':
            return False
        if self.effective_until and self.effective_until < now:
            return False
        return self.effective_from <= now
    
    @property
    def grace_period_end(self):
        """نهاية فترة السماح"""
        if self.grace_period_days:
            from datetime import timedelta
            return self.effective_from + timedelta(days=self.grace_period_days)
        return self.effective_from
    
    def is_in_grace_period(self):
        """هل نحن في فترة السماح؟"""
        if not self.grace_period_days:
            return False
        now = timezone.now()
        return self.effective_from <= now <= self.grace_period_end
    
    def activate(self, user=None):
        """تفعيل الإصدار وإنهاء الإصدار السابق"""
        from django.db import transaction
        
        with transaction.atomic():
            # إنهاء الإصدار السابق
            previous = PriceListVersion.objects.filter(
                price_list=self.price_list,
                status='active'
            ).exclude(pk=self.pk).first()
            
            if previous:
                previous.status = 'expired'
                previous.effective_until = timezone.now()
                previous.save()
            
            # تفعيل هذا الإصدار
            self.status = 'active'
            self.approved_by = user
            self.approved_at = timezone.now()
            self.save()
    
    def save(self, *args, **kwargs):
        # تحديد رقم الإصدار تلقائياً
        if not self.pk and not self.version_number:
            last_version = PriceListVersion.objects.filter(
                price_list=self.price_list
            ).order_by('-version_number').first()
            self.version_number = (last_version.version_number + 1) if last_version else 1
        
        # تحديد اسم الإصدار تلقائياً
        if not self.version_name:
            self.version_name = f"إصدار {self.version_number}"
        
        super().save(*args, **kwargs)


class VersionedPrice(models.Model):
    """
    أسعار الإصدار
    نسخة من الأسعار محفوظة مع كل إصدار
    """
    
    version = models.ForeignKey(
        PriceListVersion,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name='الإصدار'
    )
    
    family = models.ForeignKey(
        'smart_pricing.ProductFamily',
        on_delete=models.CASCADE,
        verbose_name='عائلة المنتج'
    )
    size = models.ForeignKey(
        'smart_pricing.ProductSize',
        on_delete=models.CASCADE,
        verbose_name='المقاس'
    )
    
    # الأسعار
    base_price = models.DecimalField('السعر الأساسي', max_digits=12, decimal_places=2)
    discounted_price = models.DecimalField('السعر بعد الخصم', max_digits=12, decimal_places=2)
    final_price = models.DecimalField('السعر النهائي (شامل الضريبة)', max_digits=12, decimal_places=2)
    
    # التكلفة (للمرجعية)
    cost = models.DecimalField('التكلفة', max_digits=12, decimal_places=2, default=Decimal('0'))
    margin_percentage = models.DecimalField('هامش الربح %', max_digits=5, decimal_places=2, default=Decimal('0'))
    
    class Meta:
        verbose_name = 'سعر إصدار'
        verbose_name_plural = 'أسعار الإصدارات'
        unique_together = ['version', 'family', 'size']
    
    def __str__(self):
        return f"{self.family.name} - {self.size} @ {self.final_price}"


class LockedPrice(models.Model):
    """
    سعر مثبت لعميل/طلب
    يحفظ السعر عند الحجز ولا يتأثر بتغيير القائمة
    """
    
    LOCK_TYPE_CHOICES = [
        ('order', 'أمر بيع'),
        ('quotation', 'عرض سعر'),
        ('contract', 'عقد'),
        ('manual', 'تثبيت يدوي'),
    ]
    
    lock_type = models.CharField('نوع التثبيت', max_length=20, choices=LOCK_TYPE_CHOICES)
    
    # العميل
    customer = models.ForeignKey(
        'partners.Customer',
        on_delete=models.CASCADE,
        related_name='locked_prices',
        verbose_name='العميل'
    )
    
    # المنتج
    family = models.ForeignKey(
        'smart_pricing.ProductFamily',
        on_delete=models.CASCADE,
        verbose_name='عائلة المنتج'
    )
    size = models.ForeignKey(
        'smart_pricing.ProductSize',
        on_delete=models.CASCADE,
        verbose_name='المقاس'
    )
    
    # قائمة الأسعار والإصدار
    price_list = models.ForeignKey(
        'smart_pricing.PriceList',
        on_delete=models.CASCADE,
        verbose_name='قائمة الأسعار'
    )
    price_version = models.ForeignKey(
        PriceListVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='إصدار القائمة'
    )
    
    # السعر المثبت
    locked_price = models.DecimalField('السعر المثبت', max_digits=12, decimal_places=2)
    locked_price_with_tax = models.DecimalField('السعر شامل الضريبة', max_digits=12, decimal_places=2)
    
    # الكمية المثبتة (اختياري)
    locked_quantity = models.PositiveIntegerField('الكمية المثبتة', null=True, blank=True,
                                                   help_text='اتركه فارغاً لتثبيت السعر لأي كمية')
    
    # المرجع (أمر البيع، عرض السعر، إلخ)
    reference_type = models.CharField('نوع المرجع', max_length=50, blank=True)
    reference_id = models.PositiveIntegerField('رقم المرجع', null=True, blank=True)
    reference_number = models.CharField('رقم المستند', max_length=50, blank=True)
    
    # الصلاحية
    valid_from = models.DateTimeField('صالح من', default=timezone.now)
    valid_until = models.DateTimeField('صالح حتى', null=True, blank=True,
                                        help_text='اتركه فارغاً للصلاحية الدائمة')
    
    # الحالة
    is_active = models.BooleanField('نشط', default=True)
    is_used = models.BooleanField('تم الاستخدام', default=False)
    used_at = models.DateTimeField('تاريخ الاستخدام', null=True, blank=True)
    
    # معلومات الإنشاء
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='أنشئ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    class Meta:
        verbose_name = 'سعر مثبت'
        verbose_name_plural = 'الأسعار المثبتة'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'is_active']),
            models.Index(fields=['family', 'size', 'is_active']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]
    
    def __str__(self):
        return f"{self.customer} - {self.family.name} {self.size} @ {self.locked_price}"
    
    @property
    def is_valid(self):
        """هل السعر المثبت لا يزال صالحاً؟"""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.valid_until and self.valid_until < now:
            return False
        return self.valid_from <= now
    
    def mark_as_used(self):
        """تعليم السعر كمستخدم"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
    
    @classmethod
    def get_locked_price(cls, customer, family, size, use_if_valid=True):
        """
        الحصول على السعر المثبت للعميل إن وجد
        
        Args:
            customer: العميل
            family: عائلة المنتج
            size: المقاس
            use_if_valid: استخدام السعر إذا كان صالحاً
            
        Returns:
            LockedPrice instance أو None
        """
        now = timezone.now()
        locked = cls.objects.filter(
            customer=customer,
            family=family,
            size=size,
            is_active=True,
            valid_from__lte=now
        ).filter(
            models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=now)
        ).order_by('-created_at').first()
        
        return locked
    
    @classmethod
    def lock_from_order(cls, sales_order, user=None):
        """
        تثبيت الأسعار من أمر بيع
        
        Args:
            sales_order: SalesOrder instance
            user: المستخدم الذي يقوم بالتثبيت
            
        Returns:
            قائمة بالأسعار المثبتة
        """
        from .models_price_list import ProductFamily, ProductSize, PriceList, ProductVariant
        
        locked_prices = []
        
        # الحصول على قائمة الأسعار الافتراضية
        price_list = PriceList.objects.filter(is_active=True, list_type='retail').first()
        current_version = PriceListVersion.objects.filter(
            price_list=price_list,
            status='active'
        ).first() if price_list else None
        
        for line in sales_order.lines.all():
            # البحث عن الـ variant
            variant = ProductVariant.objects.filter(
                product=line.product
            ).select_related('family', 'size').first()
            
            if not variant:
                continue
            
            locked = cls.objects.create(
                lock_type='order',
                customer=sales_order.customer,
                family=variant.family,
                size=variant.size,
                price_list=price_list,
                price_version=current_version,
                locked_price=line.price,
                locked_price_with_tax=line.price,  # يمكن حساب الضريبة
                locked_quantity=line.quantity,
                reference_type='SalesOrder',
                reference_id=sales_order.pk,
                reference_number=sales_order.number,
                created_by=user,
                notes=f'تثبيت تلقائي من أمر البيع {sales_order.number}'
            )
            locked_prices.append(locked)
        
        return locked_prices


class PriceChangeLog(models.Model):
    """
    سجل تغييرات الأسعار
    يحفظ كل تغيير في الأسعار للمراجعة
    """
    
    price_list = models.ForeignKey(
        'smart_pricing.PriceList',
        on_delete=models.CASCADE,
        related_name='change_logs',
        verbose_name='قائمة الأسعار'
    )
    
    version = models.ForeignKey(
        PriceListVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الإصدار'
    )
    
    family = models.ForeignKey(
        'smart_pricing.ProductFamily',
        on_delete=models.CASCADE,
        verbose_name='عائلة المنتج'
    )
    size = models.ForeignKey(
        'smart_pricing.ProductSize',
        on_delete=models.CASCADE,
        verbose_name='المقاس'
    )
    
    # السعر القديم والجديد
    old_price = models.DecimalField('السعر القديم', max_digits=12, decimal_places=2)
    new_price = models.DecimalField('السعر الجديد', max_digits=12, decimal_places=2)
    price_change = models.DecimalField('مقدار التغيير', max_digits=12, decimal_places=2)
    change_percentage = models.DecimalField('نسبة التغيير %', max_digits=8, decimal_places=2)
    
    # نوع التغيير
    CHANGE_TYPE_CHOICES = [
        ('increase', 'زيادة'),
        ('decrease', 'تخفيض'),
        ('new', 'سعر جديد'),
    ]
    change_type = models.CharField('نوع التغيير', max_length=20, choices=CHANGE_TYPE_CHOICES)
    
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='تم التغيير بواسطة'
    )
    changed_at = models.DateTimeField('تاريخ التغيير', auto_now_add=True)
    reason = models.TextField('السبب', blank=True)
    
    class Meta:
        verbose_name = 'سجل تغيير سعر'
        verbose_name_plural = 'سجل تغييرات الأسعار'
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.family.name} {self.size}: {self.old_price} → {self.new_price}"
    
    def save(self, *args, **kwargs):
        # حساب التغيير
        self.price_change = self.new_price - self.old_price
        if self.old_price and self.old_price != 0:
            self.change_percentage = (self.price_change / self.old_price) * 100
        else:
            self.change_percentage = Decimal('100') if self.new_price else Decimal('0')
        
        # تحديد نوع التغيير
        if self.old_price == 0:
            self.change_type = 'new'
        elif self.price_change > 0:
            self.change_type = 'increase'
        else:
            self.change_type = 'decrease'
        
        super().save(*args, **kwargs)
