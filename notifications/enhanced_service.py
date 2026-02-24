"""
نظام التنبيهات والإشعارات المحسّن
Enhanced Notification System
"""

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """خدمة الإشعارات المركزية"""
    
    @staticmethod
    def send_notification(user, title, message, notification_type='info', send_email=False, send_sms=False):
        """
        إرسال إشعار للمستخدم
        
        Args:
            user: المستخدم
            title: عنوان الإشعار
            message: محتوى الإشعار
            notification_type: نوع الإشعار (info, warning, error, success)
            send_email: إرسال بريد إلكتروني؟
            send_sms: إرسال SMS؟
        """
        from notifications.models import Notification
        
        # إنشاء إشعار في النظام
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            is_read=False
        )
        
        # إرسال بريد إلكتروني
        if send_email and user.email:
            try:
                send_mail(
                    subject=title,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f"فشل إرسال البريد الإلكتروني: {str(e)}")
        
        # إرسال SMS
        if send_sms and hasattr(user, 'phone') and user.phone:
            try:
                # يمكن دمج خدمة SMS هنا
                pass
            except Exception as e:
                logger.error(f"فشل إرسال SMS: {str(e)}")
        
        return notification
    
    @staticmethod
    def notify_low_stock(product):
        """إشعار بنقص المخزون"""
        from core.models import User
        
        # الحصول على مدراء المخزون
        inventory_managers = User.objects.filter(
            role__in=['INVENTORY_MANAGER', 'SUPER_ADMIN'],
            is_active=True
        )
        
        for user in inventory_managers:
            NotificationService.send_notification(
                user=user,
                title=f'تنبيه: مخزون منخفض - {product.name}',
                message=f'المنتج {product.name} (SKU: {product.sku}) وصل إلى مستوى الحد الأدنى. الكمية الحالية: {product.stock_quantity}',
                notification_type='warning',
                send_email=True
            )
    
    @staticmethod
    def notify_delayed_order(order):
        """إشعار بتأخير الطلب"""
        from core.models import User
        
        # إشعار موظف المشتريات
        if order.created_by:
            NotificationService.send_notification(
                user=order.created_by,
                title=f'تأخير في الطلب #{order.order_number}',
                message=f'الطلب #{order.order_number} من {order.supplier.name} متأخر عن الموعد المحدد ({order.expected_date})',
                notification_type='warning',
                send_email=True
            )
        
        # إشعار المدير
        managers = User.objects.filter(
            role__in=['PURCHASING_MANAGER', 'SUPER_ADMIN'],
            is_active=True
        )
        
        for user in managers:
            NotificationService.send_notification(
                user=user,
                title=f'تأخير في الطلب #{order.order_number}',
                message=f'الطلب من {order.supplier.name} متأخر',
                notification_type='warning'
            )


@shared_task(name='notifications.enhanced_service.check_delayed_orders')
def check_delayed_orders():
    """
    مهمة مجدولة للتحقق من الطلبات المتأخرة
    يتم تشغيلها يومياً
    """
    from purchasing.models import PurchaseOrder
    
    logger.info("بدء فحص الطلبات المتأخرة")
    
    # البحث عن الطلبات المتأخرة
    delayed_orders = PurchaseOrder.objects.filter(
        status__in=['pending', 'confirmed'],
        expected_date__lt=timezone.now().date()
    )
    
    count = 0
    for order in delayed_orders:
        # إرسال إشعار
        NotificationService.notify_delayed_order(order)
        count += 1
    
    logger.info(f"تم إرسال {count} إشعار للطلبات المتأخرة")
    
    return {
        'success': True,
        'delayed_orders': count,
        'timestamp': timezone.now().isoformat()
    }


@shared_task(name='notifications.enhanced_service.check_low_stock')
def check_low_stock():
    """
    مهمة مجدولة للتحقق من المنتجات قليلة المخزون
    يتم تشغيلها يومياً
    """
    from inventory.models import Product
    from django.db.models import F
    
    logger.info("بدء فحص المنتجات قليلة المخزون")
    
    # المنتجات التي وصلت للحد الأدنى
    low_stock_products = Product.objects.filter(
        stock_quantity__lte=F('min_stock_level'),
        is_active=True
    )
    
    count = 0
    for product in low_stock_products:
        NotificationService.notify_low_stock(product)
        count += 1
    
    logger.info(f"تم إرسال {count} إشعار للمنتجات قليلة المخزون")
    
    return {
        'success': True,
        'low_stock_products': count,
        'timestamp': timezone.now().isoformat()
    }


@shared_task(name='notifications.enhanced_service.send_daily_summary')
def send_daily_summary():
    """
    إرسال ملخص يومي لجميع المدراء
    يتم تشغيلها يومياً الساعة 6 مساءً
    """
    from django.contrib.auth import get_user_model
    from sales.models import Invoice
    from purchasing.models import PurchaseOrder
    from django.db.models import Sum, Count
    
    User = get_user_model()
    
    try:
        today = timezone.now().date()
        
        # إحصائيات اليوم
        today_sales = Invoice.objects.filter(
            invoice_date=today,
            status='approved'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        today_invoices_count = Invoice.objects.filter(
            invoice_date=today
        ).count()
        
        pending_approvals = Invoice.objects.filter(
            status='pending'
        ).count()
        
        # إنشاء رسالة الملخص
        message = f"""
        ملخص يوم {today}:
        
        - إجمالي المبيعات: {today_sales:,.2f}
        - عدد الفواتير: {today_invoices_count}
        - الفواتير المعلقة: {pending_approvals}
        """
        
        # إرسال لجميع المدراء
        managers = User.objects.filter(
            is_active=True,
            is_staff=True
        )
        
        count = 0
        for user in managers:
            NotificationService.send_notification(
                user=user,
                title=f'ملخص يومي - {today}',
                message=message,
                notification_type='info',
                send_email=True
            )
            count += 1
        
        logger.info(f"تم إرسال الملخص اليومي لـ {count} مدير")
        return {'status': 'success', 'managers_notified': count}
        
    except Exception as e:
        logger.error(f"خطأ في إرسال الملخص اليومي: {str(e)}")
        return {'status': 'error', 'message': str(e)}
