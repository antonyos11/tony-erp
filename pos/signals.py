"""Signals for POS app - Including auto production order creation"""
from __future__ import annotations
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from pos.models import POSSession, POSOrder, POSOrderLine

logger = logging.getLogger(__name__)


@receiver(post_save, sender=POSSession)
def _log_session_created(sender, instance, created, **kwargs):
    """Minimal hook to verify signal wiring without touching the DB heavily."""
    if created:
        logger.debug("pos.signals: session created id=%s", instance.pk)


@receiver(post_save, sender=POSOrder)
def check_production_on_pos_order(sender, instance, created, **kwargs):
    """
    فحص المخزون وإنشاء أوامر تصنيع تلقائية عند إنشاء طلب POS
    """
    # تطبيق فقط على الطلبات المدفوعة
    if instance.status != 'paid':
        return
    
    # تجاهل المرتجعات
    if instance.is_return:
        return
    
    # 1. إرسال رسالة تأكيد الطلب
    try:
        from notifications.messaging_service import AutoMessagingService
        
        if created:  # فقط عند الإنشاء
            result = AutoMessagingService.send_order_confirmation(instance)
            if result['success']:
                logger.info(f"Order confirmation sent for POS-{instance.number}")
            else:
                logger.warning(f"Failed to send confirmation: {result.get('error')}")
    except Exception as e:
        logger.error(f"Error sending order confirmation: {e}", exc_info=True)
    
    # 2. فحص الإنتاج
    try:
        from production.services.auto_order_service import AutoProductionOrderService
    except ImportError:
        logger.warning("AutoProductionOrderService not available")
        return
    
    # معالجة كل منتج في الطلب
    for line in instance.lines.all():
        product = line.product
        
        # يمكن إضافة فلترة حسب نوع المنتج لاحقاً
        # if hasattr(product, 'type') and product.type != 'manufactured':
        #     continue
        
        try:
            result = AutoProductionOrderService.check_and_create_order(
                product=product,
                quantity=line.quantity,
                showroom=instance.showroom,
                location=instance.location,
                reference=f'POS-{instance.number}',
                user=instance.session.user if instance.session else None
            )
            
            if result['order_created']:
                logger.info(
                    f"Auto production order created: {result['production_order'].number} "
                    f"for product {product.name} (POS: {instance.number})"
                )
            elif result['needs_production'] and not result['order_created']:
                logger.warning(
                    f"Production needed but order not created for {product.name}: "
                    f"{result['message']}"
                )
        
        except Exception as e:
            logger.error(
                f"Error creating auto production order for product {product.name}: {e}",
                exc_info=True
            )
