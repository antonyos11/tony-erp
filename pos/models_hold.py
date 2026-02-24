# -*- coding: utf-8 -*-
"""
نماذج الطلبات المعلقة والمنتجات المفضلة
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count

User = get_user_model()


class HeldOrder(models.Model):
    """الطلب المعلق - لحفظ الطلب مؤقتاً"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='held_orders',
        verbose_name=_('المستخدم')
    )
    customer_name = models.CharField(
        _('اسم العميل'), 
        max_length=100, 
        blank=True
    )
    customer_phone = models.CharField(
        _('هاتف العميل'), 
        max_length=20, 
        blank=True
    )
    note = models.TextField(
        _('ملاحظة'), 
        blank=True
    )
    items_json = models.JSONField(
        _('بنود الطلب'),
        help_text=_('JSON يحتوي على المنتجات والكميات والأسعار')
    )
    total = models.DecimalField(
        _('الإجمالي'),
        max_digits=12, 
        decimal_places=2, 
        default=0
    )
    created_at = models.DateTimeField(
        _('تاريخ الإنشاء'),
        auto_now_add=True
    )
    location = models.ForeignKey(
        'inventory.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('الموقع')
    )

    class Meta:
        verbose_name = _('طلب معلق')
        verbose_name_plural = _('الطلبات المعلقة')
        ordering = ['-created_at']

    def __str__(self):
        return f"Hold #{self.id} - {self.customer_name or 'عميل نقدي'}"

    @property
    def items_count(self):
        """عدد المنتجات في الطلب"""
        if not self.items_json:
            return 0
        return sum(item.get('qty', 0) for item in self.items_json)


class FavoriteProduct(models.Model):
    """المنتج المفضل لكل مستخدم"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_products',
        verbose_name=_('المستخدم')
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name=_('المنتج')
    )
    added_at = models.DateTimeField(
        _('تاريخ الإضافة'),
        auto_now_add=True
    )

    class Meta:
        verbose_name = _('منتج مفضل')
        verbose_name_plural = _('المنتجات المفضلة')
        unique_together = ['user', 'product']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.product.name} - {self.user.username}"


class QuickPriceButton(models.Model):
    """أزرار المبالغ السريعة للدفع"""
    amount = models.DecimalField(
        _('المبلغ'),
        max_digits=12,
        decimal_places=2
    )
    label = models.CharField(
        _('التسمية'),
        max_length=20,
        blank=True
    )
    order = models.IntegerField(
        _('الترتيب'),
        default=0
    )
    is_active = models.BooleanField(
        _('نشط'),
        default=True
    )

    class Meta:
        verbose_name = _('زر مبلغ سريع')
        verbose_name_plural = _('أزرار المبالغ السريعة')
        ordering = ['order', 'amount']

    def __str__(self):
        return self.label or f"{self.amount}"


def get_top_selling_products(user=None, days=7, limit=10):
    """
    جلب المنتجات الأكثر مبيعاً
    """
    from .models import POSOrderLine, POSOrder
    from datetime import timedelta
    
    date_from = timezone.now() - timedelta(days=days)
    
    qs = POSOrderLine.objects.filter(
        order__status='paid',
        order__created_at__gte=date_from
    )
    
    if user:
        qs = qs.filter(order__session__user=user)
    
    return qs.values('product_id', 'product__name').annotate(
        total_qty=Sum('quantity'),
        times_sold=Count('id')
    ).order_by('-total_qty')[:limit]


def get_recent_products(user, limit=10):
    """
    جلب آخر المنتجات المباعة بواسطة المستخدم
    """
    from .models import POSOrderLine
    
    return POSOrderLine.objects.filter(
        order__session__user=user,
        order__status='paid'
    ).select_related('product').order_by('-order__created_at').values_list(
        'product_id', flat=True
    ).distinct()[:limit]
