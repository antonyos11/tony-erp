# -*- coding: utf-8 -*-
"""
نماذج تاريخ الأسعار - لتتبع جميع تغييرات أسعار المواد الخام
=====================================================
يحتفظ بسجل كامل لكل تغيير في السعر مع:
- السعر القديم والجديد
- نسبة التغيير
- المستخدم الذي قام بالتغيير
- سبب التغيير
- تأثير التغيير على المنتجات
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal


class MaterialPriceHistory(models.Model):
    """
    سجل تاريخ أسعار المواد الخام
    يحتفظ بكل تغيير في السعر للرجوع إليه لاحقاً
    """
    
    CHANGE_TYPES = [
        ('manual', _('تغيير يدوي')),
        ('supplier_update', _('تحديث من المورد')),
        ('bulk_update', _('تحديث جماعي')),
        ('import', _('استيراد من ملف')),
        ('api', _('تحديث عبر API')),
        ('system', _('تحديث تلقائي من النظام')),
    ]
    
    CHANGE_REASONS = [
        ('market_change', _('تغير أسعار السوق')),
        ('currency_fluctuation', _('تذبذب العملة')),
        ('supplier_negotiation', _('تفاوض مع المورد')),
        ('new_contract', _('عقد جديد')),
        ('seasonal', _('تغير موسمي')),
        ('shortage', _('نقص في المعروض')),
        ('correction', _('تصحيح خطأ')),
        ('other', _('سبب آخر')),
    ]
    
    id = models.AutoField(primary_key=True)
    
    # المادة الخام
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='material_price_history',
        verbose_name=_('المادة الخام')
    )
    
    # المورد (اختياري - قد يكون تغيير في السعر الأساسي)
    supplier = models.ForeignKey(
        'partners.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='price_changes',
        verbose_name=_('المورد')
    )
    
    # سجل سعر المورد المرتبط (اختياري)
    supplier_price = models.ForeignKey(
        'inventory.SupplierProductPrice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history',
        verbose_name=_('سعر المورد')
    )
    
    # الأسعار
    old_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        verbose_name=_('السعر القديم')
    )
    new_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        verbose_name=_('السعر الجديد')
    )
    
    # حساب التغيير
    price_change = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('0'),
        verbose_name=_('قيمة التغيير'),
        help_text=_('السعر الجديد - السعر القديم')
    )
    change_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name=_('نسبة التغيير %')
    )
    
    # الوحدة والعملة
    unit = models.CharField(
        max_length=20,
        default='unit',
        verbose_name=_('الوحدة')
    )
    currency = models.CharField(
        max_length=3,
        default='EGP',
        verbose_name=_('العملة')
    )
    
    # نوع وسبب التغيير
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPES,
        default='manual',
        verbose_name=_('نوع التغيير')
    )
    change_reason = models.CharField(
        max_length=30,
        choices=CHANGE_REASONS,
        default='market_change',
        verbose_name=_('سبب التغيير')
    )
    
    # ملاحظات إضافية
    notes = models.TextField(
        blank=True,
        verbose_name=_('ملاحظات')
    )
    
    # المستخدم والتاريخ
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('تم التغيير بواسطة')
    )
    changed_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('تاريخ التغيير')
    )
    
    # تاريخ سريان السعر الجديد
    effective_date = models.DateField(
        default=timezone.now,
        verbose_name=_('تاريخ السريان')
    )
    
    # حقول التتبع
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('سجل تغيير السعر')
        verbose_name_plural = _('سجل تغييرات الأسعار')
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['product', '-changed_at']),
            models.Index(fields=['supplier', '-changed_at']),
            models.Index(fields=['-changed_at']),
            models.Index(fields=['change_type']),
        ]
    
    def __str__(self):
        direction = '↑' if self.price_change > 0 else '↓' if self.price_change < 0 else '='
        return f"{self.product.name}: {self.old_price} → {self.new_price} {direction} ({self.change_percentage}%)"
    
    def save(self, *args, **kwargs):
        # حساب قيمة التغيير
        self.price_change = self.new_price - self.old_price
        
        # حساب نسبة التغيير
        if self.old_price and self.old_price > 0:
            self.change_percentage = ((self.new_price - self.old_price) / self.old_price * 100).quantize(Decimal('0.01'))
        else:
            self.change_percentage = Decimal('100.00') if self.new_price > 0 else Decimal('0')
        
        super().save(*args, **kwargs)
    
    @property
    def is_increase(self):
        """هل السعر زاد؟"""
        return self.price_change > 0
    
    @property
    def is_decrease(self):
        """هل السعر نقص؟"""
        return self.price_change < 0
    
    @property
    def change_direction(self):
        """اتجاه التغيير"""
        if self.price_change > 0:
            return 'increase'
        elif self.price_change < 0:
            return 'decrease'
        return 'unchanged'


class ProductCostHistory(models.Model):
    """
    سجل تاريخ تكاليف المنتجات التامة
    يتتبع كيف تتأثر تكلفة المنتج بتغير أسعار المواد الخام
    """
    
    id = models.AutoField(primary_key=True)
    
    # المنتج التام
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='cost_history',
        verbose_name=_('المنتج')
    )
    
    # قائمة المواد المستخدمة
    bom = models.ForeignKey(
        'production.BillOfMaterials',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('قائمة المواد')
    )
    
    # التكاليف
    old_material_cost = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('0'),
        verbose_name=_('تكلفة المواد القديمة')
    )
    new_material_cost = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('0'),
        verbose_name=_('تكلفة المواد الجديدة')
    )
    
    old_total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('0'),
        verbose_name=_('التكلفة الإجمالية القديمة')
    )
    new_total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('0'),
        verbose_name=_('التكلفة الإجمالية الجديدة')
    )
    
    # التغيير
    cost_change = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('0'),
        verbose_name=_('قيمة تغير التكلفة')
    )
    change_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name=_('نسبة تغير التكلفة %')
    )
    
    # السبب (ربط بتغيير سعر المادة الخام)
    triggered_by = models.ForeignKey(
        MaterialPriceHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='affected_products',
        verbose_name=_('ناتج عن تغيير')
    )
    
    # المستخدم والتاريخ
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('تم التغيير بواسطة')
    )
    changed_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('تاريخ التغيير')
    )
    
    notes = models.TextField(blank=True, verbose_name=_('ملاحظات'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('سجل تغيير تكلفة المنتج')
        verbose_name_plural = _('سجل تغييرات تكاليف المنتجات')
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['product', '-changed_at']),
            models.Index(fields=['-changed_at']),
        ]
    
    def __str__(self):
        return f"{self.product.name}: {self.old_total_cost} → {self.new_total_cost}"
    
    def save(self, *args, **kwargs):
        # حساب التغيير
        self.cost_change = self.new_total_cost - self.old_total_cost
        
        if self.old_total_cost and self.old_total_cost > 0:
            self.change_percentage = ((self.new_total_cost - self.old_total_cost) / self.old_total_cost * 100).quantize(Decimal('0.01'))
        else:
            self.change_percentage = Decimal('0')
        
        super().save(*args, **kwargs)


class PriceChangeImpact(models.Model):
    """
    تحليل تأثير تغيير سعر مادة خام على المنتجات والأرباح
    """
    
    id = models.AutoField(primary_key=True)
    
    # تغيير السعر المرتبط
    price_change = models.ForeignKey(
        MaterialPriceHistory,
        on_delete=models.CASCADE,
        related_name='impacts',
        verbose_name=_('تغيير السعر')
    )
    
    # المنتج المتأثر
    affected_product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='price_impacts',
        verbose_name=_('المنتج المتأثر')
    )
    
    # الكمية المستخدمة في المنتج
    quantity_used = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0'),
        verbose_name=_('الكمية المستخدمة')
    )
    
    # التأثير على تكلفة الوحدة
    unit_cost_impact = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('0'),
        verbose_name=_('تأثير على تكلفة الوحدة')
    )
    
    # التأثير على هامش الربح
    old_profit_margin = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name=_('هامش الربح القديم %')
    )
    new_profit_margin = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name=_('هامش الربح الجديد %')
    )
    
    # التأثير على المخزون الحالي
    current_stock = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0'),
        verbose_name=_('المخزون الحالي')
    )
    stock_value_impact = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('0'),
        verbose_name=_('تأثير على قيمة المخزون')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('تأثير تغيير السعر')
        verbose_name_plural = _('تأثيرات تغييرات الأسعار')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"تأثير على {self.affected_product.name}: {self.unit_cost_impact}"
