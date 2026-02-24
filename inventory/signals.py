"""
Inventory signals for real-time notifications and automatic cost updates
=======================================================================
يتضمن:
1. إشعارات المخزون في الوقت الفعلي
2. تتبع تغييرات الأسعار وتسجيل التاريخ
3. تحديث تكاليف المنتجات تلقائياً عند تغير أسعار المواد الخام
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver, Signal
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from typing import Optional, Callable, Any
try:
    from channels.layers import get_channel_layer as _get_channel_layer
except Exception:
    _get_channel_layer = None  # type: ignore
try:
    from asgiref.sync import async_to_sync as _async_to_sync
except Exception:
    _async_to_sync = None  # type: ignore

get_channel_layer: Optional[Callable[[], Any]] = _get_channel_layer
async_to_sync: Optional[Callable[..., Any]] = _async_to_sync
import json
import logging
from datetime import datetime, timedelta

from .models import Stock, Product, LowStockEvent, SupplierProductPrice, PackagingUnit

# إشارات مخصصة لتغيير الأسعار
price_changed = Signal()  # sender, instance, old_price, new_price, user
cost_updated = Signal()   # sender, product, old_cost, new_cost, triggered_by

# ذاكرة قصيرة لمنع تكرار تنبيهات المخزون المنخفض لنفس المنتج بشكل متقارب
_LOW_STOCK_LAST: dict[int, datetime] = {}
_LOW_STOCK_DEBOUNCE_SECONDS = 120  # يمكن تعديلها لاحقاً عبر إعداد

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer() if get_channel_layer is not None else None


# =============================================================================
# إشارات تتبع تغيير الأسعار
# =============================================================================

@receiver(pre_save, sender=SupplierProductPrice)
def capture_old_supplier_price(sender, instance, **kwargs):
    """
    التقاط السعر القديم قبل الحفظ لتسجيله في التاريخ
    """
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_cost = old_instance.cost
            instance._old_purchase_unit = old_instance.purchase_unit
            instance._old_conversion = old_instance.conversion_to_base
            instance._is_update = True
        except sender.DoesNotExist:
            instance._old_cost = None
            instance._old_purchase_unit = None
            instance._old_conversion = None
            instance._is_update = False
    else:
        instance._old_cost = None
        instance._old_purchase_unit = None
        instance._old_conversion = None
        instance._is_update = False


# =============================================================================
# إشارات المخزون
# =============================================================================


@receiver(post_save, sender=Stock)
def stock_update_notification(sender, instance, created, **kwargs):
    """Send real-time notification when stock is updated.
    Adds persistent low stock debounce using LowStockEvent model.
    """
    try:
        product = instance.product
        # capture current quantity across all locations
        current_total = product.current_stock
        # persistent debounce
        if product.is_low_stock:
            should_notify = False
            now = timezone.now()
            try:
                evt, _created_evt = LowStockEvent.objects.get_or_create(
                    product=product,
                    defaults={'last_quantity': current_total, 'threshold': product.min_stock or 0}
                )
                # if first time or quantity changed significantly or older than debounce period
                last_dt = evt.last_notified_at
                delta_secs = (now - last_dt).total_seconds() if last_dt else 999999
                significant_change = abs(int(current_total) - int(evt.last_quantity)) >= 1
                if delta_secs > _LOW_STOCK_DEBOUNCE_SECONDS or significant_change:
                    should_notify = True
                if should_notify:
                    send_low_stock_alert(product, before_qty=evt.last_quantity, after_qty=current_total)
                    evt.last_quantity = current_total
                    evt.threshold = product.min_stock or evt.threshold
                    evt.notification_count += 1
                    evt.save(update_fields=['last_quantity', 'threshold', 'notification_count', 'last_notified_at'])
            except Exception as e:  # fallback to in-memory debounce
                logger.error(f"LowStockEvent persistence error: {e}")
                now_utc = datetime.utcnow()
                last = _LOW_STOCK_LAST.get(product.id)
                if not last or (now_utc - last) > timedelta(seconds=_LOW_STOCK_DEBOUNCE_SECONDS):
                    send_low_stock_alert(product, before_qty=None, after_qty=current_total)
                    _LOW_STOCK_LAST[product.id] = now_utc

        # Send real-time update to WebSocket
        send_inventory_update({
            'type': 'stock_update',
            'product_id': product.id,
            'product_name': product.name,
            'location': instance.location.name,
            'quantity': instance.quantity,
            'total_quantity': current_total,
            'is_low_stock': product.is_low_stock,
            'created': created
        })

    except Exception as e:
        logger.error(f"Error in stock update notification: {e}")


def send_low_stock_alert(product, *, before_qty=None, after_qty=None):
    """Send low stock alert notification with before/after context."""
    try:
        threshold = getattr(settings, 'LOW_STOCK_THRESHOLD_DEFAULT', 10)
        current_val = after_qty if after_qty is not None else product.current_stock
        before_val = before_qty if before_qty is not None else current_val

        alert_data = {
            'product_id': product.id,
            'product_name': product.name,
            'current_stock': current_val,
            'previous_stock': before_val,
            'min_stock': product.min_stock or threshold,
            'delta': current_val - before_val,
            'message': f'تحذير: المنتج {product.name} منخفض المخزون ({current_val}/{product.min_stock or threshold}) Δ{current_val - before_val}',
            'severity': 'warning',
            'timestamp': str(timezone.now()) if 'timezone' in globals() else str(datetime.now())
        }

        if channel_layer is not None and async_to_sync is not None:
            async_to_sync(channel_layer.group_send)(
                'inventory_updates',
                {
                    'type': 'low_stock_alert',
                    'alert': alert_data
                }
            )

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            msg = (
                f"Low stock alert: {alert_data['product_name']} now {current_val}/"
                f"{alert_data['min_stock']} prev {before_val} Δ{alert_data['delta']} admins={admin_users.count()}"
            )
            try:
                msg.encode('cp1252')
            except Exception:
                msg = msg.encode('cp1252', errors='ignore').decode('cp1252', errors='ignore')
            logger.info(msg)
        except Exception as e:
            logger.error(f"Error in admin notification logging: {e}")
    except Exception as e:
        logger.error(f"Error in low stock alert: {e}")


def send_inventory_update(update_data):
    """Send inventory update to WebSocket clients"""
    try:
        if channel_layer is not None and async_to_sync is not None:
            async_to_sync(channel_layer.group_send)(
                'inventory_updates',
                {
                    'type': 'inventory_update',
                    'update': update_data
                }
            )
    except Exception as e:
        logger.error(f"Error sending inventory update: {e}")


@receiver(post_delete, sender=Stock)
def stock_delete_notification(sender, instance, **kwargs):
    """Send notification when stock record is deleted"""
    try:
        send_inventory_update({
            'type': 'stock_deleted',
            'product_id': instance.product.id,
            'product_name': instance.product.name,
            'location': instance.location.name,
        })
    except Exception as e:
        logger.error(f"Error in stock delete notification: {e}")


@receiver(post_save, sender=SupplierProductPrice)
def update_packaging_units_on_price_change(sender, instance, created, **kwargs):
    """
    تحديث أسعار وحدات التعبئة (الألواح) عند تغيير سعر المادة الخام
    مع تسجيل تاريخ الأسعار وتحديث تكاليف المنتجات المتأثرة

    عند إضافة أو تعديل سعر مادة خام من مورد:
    1. تسجيل تاريخ السعر
    2. تحديث سعر المنتج الأساسي (Product.cost)
    3. تحديث أسعار جميع وحدات التعبئة (PackagingUnit) المرتبطة
    4. تحديث أسعار المنتجات في BOM (إذا كانت تستخدم هذه المادة)
    """
    try:
        old_cost = getattr(instance, '_old_cost', None)
        is_update = getattr(instance, '_is_update', False)
        price_history = None
        affected_products = []
        
        # =================================================================
        # 1. تسجيل تاريخ السعر
        # =================================================================
        try:
            from .price_history import MaterialPriceHistory
            
            if old_cost is None:
                old_cost = Decimal('0')
            
            # تسجيل فقط إذا تغير السعر أو كان جديداً وكان مرتبطاً بمنتج
            if instance.product and (created or (is_update and old_cost != instance.cost)):
                price_history = MaterialPriceHistory.objects.create(
                    product=instance.product,
                    supplier=instance.supplier,
                    supplier_price=instance,
                    old_price=old_cost,
                    new_price=instance.cost,
                    unit=instance.purchase_unit,
                    currency=instance.currency,
                    change_type='supplier_update' if is_update else 'manual',
                    change_reason='market_change' if is_update else 'new_contract',
                    notes=f"{'تحديث السعر' if is_update else 'إضافة سعر جديد'} من المورد: {instance.supplier.name}",
                )
                product_name = instance.product.name if instance.product else instance.material_name
                logger.info(f"Price history recorded for {product_name}: {old_cost} → {instance.cost}")
                
                # إرسال إشارة تغيير السعر
                price_changed.send(
                    sender=sender,
                    instance=instance,
                    old_price=old_cost,
                    new_price=instance.cost,
                    user=None
                )
        except Exception as e:
            logger.warning(f"Could not record price history: {e}")
        
        # =================================================================
        # 2. تحديث سعر المنتج الأساسي
        # =================================================================
        product = instance.product
        if not product:
            return
            
        old_product_cost = product.cost

        # تحديث السعر في الحالات التالية:
        # 1. إذا كان المورد مفضلاً
        # 2. إذا لم يكن هناك سعر حالي (0 أو None)
        # 3. إذا كان هذا هو المورد الوحيد للمنتج
        should_update = (
            instance.is_preferred or
            not product.cost or
            product.cost == 0 or
            not SupplierProductPrice.objects.filter(product=product).exclude(pk=instance.pk).exists()
        )

        if should_update:
            product.cost = instance.cost
            
            # تحديث سعر الشراء ومعامل التحويل
            product.purchase_price = instance.cost
            product.purchase_uom = instance.purchase_unit
            product.conversion_factor = instance.conversion_to_base
            
            # تعيين المورد المفضل تلقائياً إذا كان:
            # 1. أول مورد للمادة (لا يوجد مورد مفضل حالياً)
            # 2. أو مُحدَّد صراحةً كمفضل
            if not product.preferred_supplier or instance.is_preferred:
                product.preferred_supplier = instance.supplier
            
            # حساب تكلفة وحدة الاستخدام
            if instance.conversion_to_base and instance.conversion_to_base > 0:
                product.usage_unit_cost = instance.cost / instance.conversion_to_base
            else:
                product.usage_unit_cost = instance.cost
            
            product.save(update_fields=[
                'cost', 'purchase_price', 'purchase_uom', 
                'conversion_factor', 'usage_unit_cost', 'preferred_supplier'
            ])

            logger.info(
                f"Updated product cost: {product.name} from {old_product_cost} to {instance.cost} "
                f"(Supplier: {instance.supplier.name}, Preferred: {instance.is_preferred})"
            )

        # =================================================================
        # 3. تحديث أسعار جميع وحدات التعبئة المرتبطة
        # =================================================================
        packaging_units = PackagingUnit.objects.filter(product=product, is_active=True)
        updated_count = 0

        for pu in packaging_units:
            old_price = pu.calculated_price
            new_price = pu.calculate_price()

            if old_price != new_price:
                pu.calculated_price = new_price
                pu.save(update_fields=['calculated_price', 'updated_at'])
                updated_count += 1

                logger.info(
                    f"Updated packaging unit price: {pu.name} from {old_price} to {new_price}"
                )

        if updated_count > 0:
            logger.info(
                f"Updated {updated_count} packaging units for product {product.name}"
            )

        # =================================================================
        # 4. تحديث أسعار المنتجات في BOM (تلقائي)
        # =================================================================
        if should_update and is_update and old_cost != instance.cost:
            try:
                from .cost_service import get_cost_service
                
                cost_service = get_cost_service()
                result = cost_service.update_costs_for_material_price_change(
                    material_id=product.id,
                    old_price=old_cost or Decimal('0'),
                    new_price=instance.cost,
                )
                
                if result['total_affected'] > 0:
                    affected_products = result.get('affected_products', [])
                    logger.info(
                        f"Auto-updated costs for {result['total_affected']} products "
                        f"affected by {product.name} price change"
                    )
                    
                    # إرسال إشارة تحديث التكلفة
                    cost_updated.send(
                        sender=sender,
                        product=product,
                        old_cost=old_cost,
                        new_cost=instance.cost,
                        triggered_by='supplier_price_update'
                    )
            except Exception as e:
                logger.warning(f"Could not auto-update BOM costs: {e}")

        # =================================================================
        # 5. إرسال إشعارات تغير السعر
        # =================================================================
        if created or (is_update and old_cost != instance.cost):
            try:
                from .notifications import send_price_change_notifications
                from .cost_service import get_cost_service

                if not affected_products:
                    cost_service = get_cost_service()
                    affected_products = cost_service.get_products_using_material(product.id)

                send_price_change_notifications(
                    product=product,
                    supplier=instance.supplier,
                    old_price=old_cost or Decimal('0'),
                    new_price=instance.cost,
                    price_history=price_history,
                    affected_products=affected_products,
                )
            except Exception as e:
                logger.warning(f"Could not send price change notifications: {e}")

        # =================================================================
        # 6. تسجيل المنتجات المتأثرة في BOM (للمعلومات)
        # =================================================================
        try:
            from production.models import BOMItem

            bom_items = BOMItem.objects.filter(
                material=product
            ).select_related('bom', 'bom__product')

            affected_products = set()
            for bom_item in bom_items:
                bom = bom_item.bom
                if bom.product:
                    affected_products.add(bom.product.name)

            if affected_products:
                logger.info(
                    f"Material price change affects {len(affected_products)} products in BOM: "
                    f"{', '.join(list(affected_products)[:5])}"
                )
        except Exception as e:
            logger.warning(f"Could not list affected BOM items: {e}")

    except Exception as e:
        logger.error(f"Error in update_packaging_units_on_price_change: {e}")