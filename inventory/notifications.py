# -*- coding: utf-8 -*-
"""
نظام إشعارات تغيير الأسعار - Price Change Notifications
========================================================
إشعارات ذكية عند تغير أسعار المواد الخام وتأثيرها على المنتجات

الميزات:
- إشعارات فورية عند تغير السعر
- إشعارات بالتأثير على المنتجات
- إشعارات بالتأثير على هامش الربح
- دعم قنوات متعددة (Dashboard, Email, WebSocket)
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PriceChangeNotification(models.Model):
    """
    إشعارات تغيير الأسعار
    """
    
    NOTIFICATION_TYPES = [
        ('price_increase', _('زيادة سعر')),
        ('price_decrease', _('انخفاض سعر')),
        ('new_price', _('سعر جديد')),
        ('cost_impact', _('تأثير على التكلفة')),
        ('margin_alert', _('تنبيه هامش الربح')),
        ('bulk_update', _('تحديث جماعي')),
    ]
    
    SEVERITY_LEVELS = [
        ('info', _('معلومة')),
        ('warning', _('تحذير')),
        ('critical', _('حرج')),
    ]
    
    STATUS_CHOICES = [
        ('unread', _('غير مقروء')),
        ('read', _('مقروء')),
        ('dismissed', _('تم تجاهله')),
        ('actioned', _('تم اتخاذ إجراء')),
    ]
    
    id = models.AutoField(primary_key=True)
    
    # نوع الإشعار
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        verbose_name=_('نوع الإشعار')
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='info',
        verbose_name=_('الأهمية')
    )
    
    # العنوان والرسالة
    title = models.CharField(
        max_length=255,
        verbose_name=_('العنوان')
    )
    message = models.TextField(
        verbose_name=_('الرسالة')
    )
    
    # البيانات المرتبطة
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_notifications',
        verbose_name=_('المنتج')
    )
    supplier = models.ForeignKey(
        'partners.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('المورد')
    )
    price_history = models.ForeignKey(
        'inventory.MaterialPriceHistory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('سجل السعر')
    )
    
    # تفاصيل التغيير
    old_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_('القيمة القديمة')
    )
    new_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_('القيمة الجديدة')
    )
    change_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('نسبة التغيير')
    )
    
    # عدد المنتجات المتأثرة
    affected_products_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('عدد المنتجات المتأثرة')
    )
    
    # بيانات إضافية (JSON)
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('بيانات إضافية')
    )
    
    # الحالة والمستلم
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='unread',
        verbose_name=_('الحالة')
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_notifications',
        verbose_name=_('المستلم')
    )
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('إشعار تغيير السعر')
        verbose_name_plural = _('إشعارات تغييرات الأسعار')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        self.status = 'read'
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at'])
    
    @classmethod
    def create_price_change_notification(
        cls,
        product,
        supplier,
        old_price,
        new_price,
        price_history=None,
        affected_products=None,
        recipients=None
    ):
        """
        إنشاء إشعار تغيير السعر
        
        Args:
            product: المادة الخام
            supplier: المورد
            old_price: السعر القديم
            new_price: السعر الجديد
            price_history: سجل التغيير
            affected_products: قائمة المنتجات المتأثرة
            recipients: قائمة المستخدمين لإرسال الإشعار لهم
        """
        from django.contrib.auth.models import User
        
        # حساب التغيير
        price_change = new_price - old_price
        if old_price and old_price > 0:
            change_pct = (price_change / old_price * 100)
        else:
            change_pct = Decimal('100') if new_price > 0 else Decimal('0')
        
        # تحديد نوع الإشعار والأهمية
        if old_price == 0 or old_price is None:
            notification_type = 'new_price'
            severity = 'info'
            title = f"سعر جديد: {product.name}"
        elif price_change > 0:
            notification_type = 'price_increase'
            severity = 'warning' if change_pct > 10 else 'info'
            if change_pct > 25:
                severity = 'critical'
            title = f"ارتفاع سعر: {product.name} (+{change_pct:.1f}%)"
        else:
            notification_type = 'price_decrease'
            severity = 'info'
            title = f"انخفاض سعر: {product.name} ({change_pct:.1f}%)"
        
        # بناء الرسالة
        message_parts = [
            f"تم تغيير سعر '{product.name}' من المورد '{supplier.name}':",
            f"السعر القديم: {old_price:.2f}",
            f"السعر الجديد: {new_price:.2f}",
            f"التغيير: {price_change:.2f} ({change_pct:.1f}%)",
        ]
        
        affected_count = 0
        if affected_products:
            affected_count = len(affected_products)
            message_parts.append(f"المنتجات المتأثرة: {affected_count}")
        
        message = "\n".join(message_parts)
        
        # تحديد المستلمين
        if recipients is None:
            # إرسال للمشرفين افتراضياً
            recipients = User.objects.filter(is_staff=True, is_active=True)
        
        # إنشاء الإشعارات
        notifications = []
        for user in recipients:
            notification = cls.objects.create(
                notification_type=notification_type,
                severity=severity,
                title=title,
                message=message,
                product=product,
                supplier=supplier,
                price_history=price_history,
                old_value=old_price,
                new_value=new_price,
                change_percentage=change_pct,
                affected_products_count=affected_count,
                extra_data={
                    'affected_products': [
                        {'id': p['product_id'], 'name': p['product_name']}
                        for p in (affected_products or [])[:10]
                    ]
                },
                recipient=user,
            )
            notifications.append(notification)
        
        # إرسال إشعار WebSocket
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    'price_updates',
                    {
                        'type': 'price_change_notification',
                        'notification': {
                            'type': notification_type,
                            'severity': severity,
                            'title': title,
                            'product_id': product.id,
                            'product_name': product.name,
                            'old_price': float(old_price or 0),
                            'new_price': float(new_price),
                            'change_percentage': float(change_pct),
                            'affected_count': affected_count,
                        }
                    }
                )
        except Exception as e:
            logger.warning(f"Could not send WebSocket notification: {e}")
        
        return notifications
    
    @classmethod
    def create_margin_alert(
        cls,
        product,
        old_margin,
        new_margin,
        triggered_by=None,
        recipients=None
    ):
        """
        إنشاء تنبيه انخفاض هامش الربح
        """
        from django.contrib.auth.models import User
        
        margin_change = new_margin - old_margin
        
        # تحديد الأهمية
        if new_margin < 10:
            severity = 'critical'
        elif new_margin < 20:
            severity = 'warning'
        else:
            severity = 'info'
        
        title = f"تنبيه هامش الربح: {product.name}"
        message = f"""
هامش الربح لمنتج '{product.name}' تغير:
- الهامش السابق: {old_margin:.1f}%
- الهامش الحالي: {new_margin:.1f}%
- التغيير: {margin_change:.1f}%

{'⚠️ تحذير: هامش الربح منخفض جداً!' if new_margin < 15 else ''}
        """.strip()
        
        if recipients is None:
            recipients = User.objects.filter(is_staff=True, is_active=True)
        
        notifications = []
        for user in recipients:
            notification = cls.objects.create(
                notification_type='margin_alert',
                severity=severity,
                title=title,
                message=message,
                product=product,
                old_value=Decimal(str(old_margin)),
                new_value=Decimal(str(new_margin)),
                change_percentage=Decimal(str(margin_change)),
                recipient=user,
            )
            notifications.append(notification)
        
        return notifications


class NotificationPreference(models.Model):
    """
    تفضيلات الإشعارات لكل مستخدم
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='inventory_notification_preferences',
        verbose_name=_('المستخدم')
    )
    
    # إشعارات تغير الأسعار
    receive_price_increase = models.BooleanField(
        default=True,
        verbose_name=_('إشعارات ارتفاع الأسعار')
    )
    receive_price_decrease = models.BooleanField(
        default=True,
        verbose_name=_('إشعارات انخفاض الأسعار')
    )
    
    # الحد الأدنى للتغيير للإشعار
    min_change_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        verbose_name=_('الحد الأدنى لنسبة التغيير %'),
        help_text=_('لن يتم إرسال إشعار إذا كان التغيير أقل من هذه النسبة')
    )
    
    # إشعارات هامش الربح
    receive_margin_alerts = models.BooleanField(
        default=True,
        verbose_name=_('تنبيهات هامش الربح')
    )
    min_margin_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('15.00'),
        verbose_name=_('الحد الأدنى لهامش الربح %'),
        help_text=_('إرسال تنبيه إذا انخفض الهامش عن هذه النسبة')
    )
    
    # قنوات الإشعار
    notify_dashboard = models.BooleanField(
        default=True,
        verbose_name=_('إشعارات لوحة التحكم')
    )
    notify_email = models.BooleanField(
        default=False,
        verbose_name=_('إشعارات البريد الإلكتروني')
    )
    notify_websocket = models.BooleanField(
        default=True,
        verbose_name=_('إشعارات فورية')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('تفضيلات الإشعارات')
        verbose_name_plural = _('تفضيلات الإشعارات')
    
    def __str__(self):
        return f"تفضيلات إشعارات: {self.user.username}"


def send_price_change_notifications(
    product,
    supplier,
    old_price,
    new_price,
    price_history=None,
    affected_products=None
):
    """
    إرسال إشعارات تغيير السعر
    دالة مساعدة للاستخدام من أي مكان
    """
    from django.contrib.auth.models import User
    
    # جلب المستخدمين المؤهلين
    try:
        preferences = NotificationPreference.objects.filter(
            receive_price_increase=True if new_price > old_price else True,
            receive_price_decrease=True if new_price < old_price else True,
        ).select_related('user')
        
        # تصفية حسب الحد الأدنى للتغيير
        if old_price and old_price > 0:
            change_pct = abs((new_price - old_price) / old_price * 100)
            preferences = [p for p in preferences if change_pct >= float(p.min_change_percentage)]
        
        recipients = [p.user for p in preferences]
        
        if not recipients:
            # إذا لم يوجد مستخدمين بتفضيلات، نرسل للمشرفين
            recipients = list(User.objects.filter(is_staff=True, is_active=True))
        
    except Exception:
        # fallback: إرسال للمشرفين
        recipients = list(User.objects.filter(is_staff=True, is_active=True))
    
    return PriceChangeNotification.create_price_change_notification(
        product=product,
        supplier=supplier,
        old_price=old_price,
        new_price=new_price,
        price_history=price_history,
        affected_products=affected_products,
        recipients=recipients
    )
