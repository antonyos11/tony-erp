"""
نماذج تطبيق التوصيل — RITA ERP
"""
import uuid
from django.db import models
from apps.core.models import AuditMixin


class DeliveryZone(AuditMixin):
    """منطقة توصيل"""

    name                = models.CharField(max_length=255, verbose_name='المنطقة')
    governorate         = models.CharField(max_length=100, verbose_name='المحافظة')
    delivery_fee        = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='رسوم التوصيل')
    free_delivery_above = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='توصيل مجاني فوق')
    estimated_days      = models.IntegerField(default=1, verbose_name='أيام التوصيل المتوقعة')
    is_active           = models.BooleanField(default=True, verbose_name='نشطة')

    class Meta:
        verbose_name        = 'منطقة توصيل'
        verbose_name_plural = 'مناطق التوصيل'
        ordering            = ['governorate', 'name']

    def __str__(self):
        return f'{self.name} — {self.governorate}'

    def get_fee_for_order(self, order_total) -> 'Decimal':
        """حساب رسوم التوصيل بناءً على إجمالي الطلب."""
        from decimal import Decimal
        if self.free_delivery_above > 0 and order_total >= self.free_delivery_above:
            return Decimal('0.00')
        return self.delivery_fee


class DeliveryOrder(AuditMixin):
    """أمر توصيل"""

    DELIVERY_STATUSES = [
        ('pending',    'في الانتظار'),
        ('assigned',   'تم التعيين'),
        ('in_transit', 'جاري التوصيل'),
        ('delivered',  'تم التسليم'),
        ('returned',   'مرتجع'),
        ('cancelled',  'ملغي'),
    ]

    order_number     = models.CharField(max_length=50, unique=True, verbose_name='رقم التوصيل')
    invoice          = models.ForeignKey(
        'sales.SalesInvoice',
        on_delete=models.PROTECT,
        related_name='delivery_orders',
        verbose_name='الفاتورة',
    )
    zone             = models.ForeignKey(
        DeliveryZone,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
        verbose_name='المنطقة',
    )
    driver           = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='delivery_orders',
        verbose_name='السائق',
    )
    status           = models.CharField(max_length=20, choices=DELIVERY_STATUSES, default='pending', verbose_name='الحالة')
    delivery_date    = models.DateField(null=True, blank=True, verbose_name='تاريخ التوصيل')
    delivery_address = models.TextField(verbose_name='عنوان التوصيل')
    delivery_fee     = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='رسوم التوصيل')
    notes            = models.TextField(blank=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name        = 'أمر توصيل'
        verbose_name_plural = 'أوامر التوصيل'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.order_number} — {self.get_status_display()}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_order_number() -> str:
        from django.utils import timezone
        prefix = timezone.now().strftime('DEL%Y%m%d')
        count  = DeliveryOrder.objects.filter(
            order_number__startswith=prefix
        ).count() + 1
        return f'{prefix}{count:04d}'

    @property
    def is_active(self):
        return self.status not in ('delivered', 'returned', 'cancelled')
