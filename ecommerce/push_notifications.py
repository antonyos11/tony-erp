"""
Push Notifications Service for E-commerce
==========================================
Order updates, abandoned cart, promotions
Week 2 Phase 1 - January 2026
"""

import json
import logging
from datetime import timedelta
from typing import Optional, Dict, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

try:
    from pywebpush import webpush, WebPushException
    WEBPUSH_AVAILABLE = True
except ImportError:
    WEBPUSH_AVAILABLE = False
    webpush = None
    WebPushException = Exception

logger = logging.getLogger(__name__)
User = get_user_model()


class PushSubscription(models.Model):
    """
    Store push notification subscriptions
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=40, blank=True, null=True)
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'ecommerce'
        db_table = 'ecommerce_push_subscription'
    
    def __str__(self):
        return f"Push subscription for {self.user or self.session_key}"


class PushNotificationLog(models.Model):
    """
    Log of sent push notifications
    """
    TYPES = [
        ('order_confirmed', 'تأكيد الطلب'),
        ('order_shipped', 'تم الشحن'),
        ('order_delivered', 'تم التوصيل'),
        ('abandoned_cart', 'سلة متروكة'),
        ('price_drop', 'انخفاض السعر'),
        ('back_in_stock', 'متوفر مجدداً'),
        ('promotion', 'عرض ترويجي'),
        ('flash_sale', 'تخفيضات سريعة'),
    ]
    
    subscription = models.ForeignKey(
        PushSubscription,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=50, choices=TYPES)
    title = models.CharField(max_length=200)
    body = models.TextField()
    data = models.JSONField(default=dict)
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered = models.BooleanField(default=False)
    clicked = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    
    class Meta:
        app_label = 'ecommerce'
        db_table = 'ecommerce_push_notification_log'
        ordering = ['-sent_at']


class PushNotificationService:
    """
    Service for sending push notifications
    """
    
    # Arabic notification templates
    TEMPLATES = {
        'order_confirmed': {
            'title': '✅ تم تأكيد طلبك!',
            'body': 'طلبك رقم {order_number} تم تأكيده بنجاح. سنقوم بإعداده للشحن قريباً.',
            'icon': '/static/ecommerce/icons/order-confirmed.png',
            'action_url': '/ecommerce/orders/{order_id}/'
        },
        'order_shipped': {
            'title': '🚚 طلبك في الطريق!',
            'body': 'تم شحن طلبك رقم {order_number}. رقم التتبع: {tracking_number}',
            'icon': '/static/ecommerce/icons/shipping.png',
            'action_url': '/ecommerce/orders/{order_id}/track/'
        },
        'order_delivered': {
            'title': '🎉 تم توصيل طلبك!',
            'body': 'تم توصيل طلبك رقم {order_number} بنجاح. شكراً لثقتك بنا!',
            'icon': '/static/ecommerce/icons/delivered.png',
            'action_url': '/ecommerce/orders/{order_id}/'
        },
        'abandoned_cart': {
            'title': '🛒 لا تنسى سلتك!',
            'body': 'لديك {item_count} منتجات في السلة بقيمة {cart_total} ج.م. أكمل طلبك الآن!',
            'icon': '/static/ecommerce/icons/cart.png',
            'action_url': '/ecommerce/cart/'
        },
        'price_drop': {
            'title': '💰 انخفض سعر منتج تتابعه!',
            'body': '{product_name} الآن بسعر {new_price} ج.م بدلاً من {old_price} ج.م',
            'icon': '/static/ecommerce/icons/price-drop.png',
            'action_url': '/ecommerce/product/{product_id}/'
        },
        'back_in_stock': {
            'title': '🔔 المنتج متوفر الآن!',
            'body': '{product_name} عاد للمخزون. اطلبه قبل نفاذ الكمية!',
            'icon': '/static/ecommerce/icons/in-stock.png',
            'action_url': '/ecommerce/product/{product_id}/'
        },
        'promotion': {
            'title': '🎁 عرض خاص لك!',
            'body': '{message}',
            'icon': '/static/ecommerce/icons/promotion.png',
            'action_url': '/ecommerce/{action_path}/'
        },
        'flash_sale': {
            'title': '⚡ تخفيضات سريعة!',
            'body': 'خصم يصل إلى {discount}% لفترة محدودة. لا تفوت الفرصة!',
            'icon': '/static/ecommerce/icons/flash-sale.png',
            'action_url': '/ecommerce/flash-sales/'
        }
    }
    
    def __init__(self):
        self.vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', None)
        self.vapid_public_key = getattr(settings, 'VAPID_PUBLIC_KEY', None)
        self.vapid_claims = {
            'sub': f"mailto:{getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@example.com')}"
        }
    
    def send_notification(
        self,
        subscription: PushSubscription,
        notification_type: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a push notification
        """
        if not WEBPUSH_AVAILABLE:
            logger.warning("pywebpush is not installed. Cannot send push notifications.")
            return False
        
        if not self.vapid_private_key:
            logger.warning("VAPID_PRIVATE_KEY not configured")
            return False
        
        data = data or {}
        template = self.TEMPLATES.get(notification_type)
        
        if not template:
            logger.error(f"Unknown notification type: {notification_type}")
            return False
        
        try:
            # Format template with data
            title = template['title'].format(**data)
            body = template['body'].format(**data)
            action_url = template['action_url'].format(**data)
            
            payload = {
                'title': title,
                'body': body,
                'icon': template['icon'],
                'badge': '/static/ecommerce/icons/badge.png',
                'dir': 'rtl',
                'lang': 'ar',
                'tag': notification_type,
                'requireInteraction': notification_type in ['order_confirmed', 'order_shipped'],
                'data': {
                    'url': action_url,
                    'type': notification_type,
                    **data
                },
                'actions': self._get_actions(notification_type)
            }
            
            # Send the notification
            webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': {
                        'p256dh': subscription.p256dh,
                        'auth': subscription.auth
                    }
                },
                data=json.dumps(payload),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims
            )
            
            # Log success
            PushNotificationLog.objects.create(
                subscription=subscription,
                notification_type=notification_type,
                title=title,
                body=body,
                data=data,
                delivered=True
            )
            
            logger.info(f"Push notification sent: {notification_type} to {subscription}")
            return True
            
        except WebPushException as e:
            # Handle subscription expiry
            if hasattr(e, 'response') and e.response and getattr(e.response, 'status_code', 0) in [404, 410]:
                subscription.is_active = False
                subscription.save()
                logger.info(f"Push subscription deactivated (expired): {subscription}")
            else:
                logger.error(f"WebPush error: {e}")
            
            PushNotificationLog.objects.create(
                subscription=subscription,
                notification_type=notification_type,
                title=template['title'],
                body=template['body'],
                data=data,
                delivered=False,
                error=str(e)
            )
            return False
        
        except Exception as e:
            logger.exception(f"Push notification error: {e}")
            return False
    
    def _get_actions(self, notification_type: str) -> list:
        """
        Get notification actions based on type
        """
        actions_map = {
            'order_confirmed': [
                {'action': 'view_order', 'title': 'عرض الطلب'},
                {'action': 'track_order', 'title': 'تتبع الطلب'}
            ],
            'order_shipped': [
                {'action': 'track_order', 'title': 'تتبع الشحنة'},
                {'action': 'contact_support', 'title': 'تواصل معنا'}
            ],
            'order_delivered': [
                {'action': 'view_order', 'title': 'عرض الطلب'},
                {'action': 'leave_review', 'title': 'أضف تقييم'}
            ],
            'abandoned_cart': [
                {'action': 'complete_order', 'title': 'أكمل الطلب'},
                {'action': 'view_cart', 'title': 'عرض السلة'}
            ],
            'price_drop': [
                {'action': 'buy_now', 'title': 'اشتري الآن'},
                {'action': 'view_product', 'title': 'عرض المنتج'}
            ],
            'back_in_stock': [
                {'action': 'add_to_cart', 'title': 'أضف للسلة'},
                {'action': 'view_product', 'title': 'عرض المنتج'}
            ],
            'flash_sale': [
                {'action': 'shop_now', 'title': 'تسوق الآن'},
                {'action': 'dismiss', 'title': 'لاحقاً'}
            ]
        }
        return actions_map.get(notification_type, [])
    
    def send_to_user(
        self,
        user,
        notification_type: str,
        data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Send notification to all user's subscriptions
        Returns number of successful sends
        """
        subscriptions = PushSubscription.objects.filter(
            user=user,
            is_active=True
        )
        
        success_count = 0
        for subscription in subscriptions:
            if self.send_notification(subscription, notification_type, data):
                success_count += 1
        
        return success_count
    
    def broadcast(
        self,
        notification_type: str,
        data: Optional[Dict[str, Any]] = None,
        user_filter: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Broadcast notification to multiple users
        """
        subscriptions = PushSubscription.objects.filter(is_active=True)
        
        if user_filter:
            subscriptions = subscriptions.filter(user__isnull=False)
            if 'user_ids' in user_filter:
                subscriptions = subscriptions.filter(user_id__in=user_filter['user_ids'])
        
        success_count = 0
        for subscription in subscriptions.iterator():
            if self.send_notification(subscription, notification_type, data):
                success_count += 1
        
        logger.info(f"Broadcast complete: {success_count} notifications sent")
        return success_count


# =============================================
# NOTIFICATION TRIGGERS
# =============================================

def send_order_confirmation(order):
    """
    Send push notification when order is confirmed
    """
    service = PushNotificationService()
    
    if order.user:
        service.send_to_user(
            user=order.user,
            notification_type='order_confirmed',
            data={
                'order_id': order.id,
                'order_number': order.order_number,
                'total': str(order.total)
            }
        )


def send_order_shipped(order, tracking_number: Optional[str] = None):
    """
    Send push notification when order is shipped
    """
    service = PushNotificationService()
    
    if order.user:
        service.send_to_user(
            user=order.user,
            notification_type='order_shipped',
            data={
                'order_id': order.id,
                'order_number': order.order_number,
                'tracking_number': tracking_number or 'غير متوفر'
            }
        )


def send_order_delivered(order):
    """
    Send push notification when order is delivered
    """
    service = PushNotificationService()
    
    if order.user:
        service.send_to_user(
            user=order.user,
            notification_type='order_delivered',
            data={
                'order_id': order.id,
                'order_number': order.order_number
            }
        )


def send_abandoned_cart_reminder(user, cart_data: Dict):
    """
    Send reminder for abandoned cart
    """
    service = PushNotificationService()
    
    service.send_to_user(
        user=user,
        notification_type='abandoned_cart',
        data={
            'item_count': cart_data.get('item_count', 0),
            'cart_total': cart_data.get('total', 0)
        }
    )


def send_price_drop_alert(user, product, old_price: float, new_price: float):
    """
    Send notification when a watched product's price drops
    """
    service = PushNotificationService()
    
    service.send_to_user(
        user=user,
        notification_type='price_drop',
        data={
            'product_id': product.id,
            'product_name': product.name,
            'old_price': str(old_price),
            'new_price': str(new_price)
        }
    )


def send_back_in_stock_alert(user, product):
    """
    Send notification when a product is back in stock
    """
    service = PushNotificationService()
    
    service.send_to_user(
        user=user,
        notification_type='back_in_stock',
        data={
            'product_id': product.id,
            'product_name': product.name
        }
    )


def send_flash_sale_notification(discount_percentage: int, user_ids: Optional[list] = None):
    """
    Broadcast flash sale notification
    """
    service = PushNotificationService()
    
    user_filter: Optional[Dict[str, Any]] = {'user_ids': user_ids} if user_ids else None
    
    service.broadcast(
        notification_type='flash_sale',
        data={'discount': discount_percentage},
        user_filter=user_filter
    )


# =============================================
# CELERY TASKS (if available)
# =============================================

try:
    from celery import shared_task
    
    @shared_task
    def check_abandoned_carts():
        """
        Check for abandoned carts and send reminders
        Runs every hour via Celery Beat
        """
        from .models import Cart
        
        # Carts not updated in the last 1-24 hours
        min_age = timezone.now() - timedelta(hours=24)
        max_age = timezone.now() - timedelta(hours=1)
        
        abandoned_carts = Cart.objects.filter(
            user__isnull=False,
            updated_at__gte=min_age,
            updated_at__lte=max_age
        ).select_related('user')
        
        for cart in abandoned_carts:
            items = cart.items.all()
            if items.exists():
                total = sum(item.product.price * item.quantity for item in items)
                send_abandoned_cart_reminder(
                    user=cart.user,
                    cart_data={
                        'item_count': items.count(),
                        'total': float(total)
                    }
                )
        
        return f"Checked {abandoned_carts.count()} abandoned carts"
    
    @shared_task
    def send_push_notification_task(subscription_id: int, notification_type: str, data: Dict):
        """
        Async task to send push notification
        """
        try:
            subscription = PushSubscription.objects.get(id=subscription_id, is_active=True)
            service = PushNotificationService()
            service.send_notification(subscription, notification_type, data)
        except PushSubscription.DoesNotExist:
            logger.warning(f"Subscription {subscription_id} not found")

except ImportError:
    # Celery not available
    pass
