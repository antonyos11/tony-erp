"""
إشارات المزامنة التلقائية
Automatic Sync Signals

تعمل على مزامنة البيانات بين:
- قوائم الأسعار ومنتجات المخزون
- تحديث الأسعار تلقائياً عند التغيير
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import models
from decimal import Decimal


@receiver(post_save, sender='smart_pricing.ProductVariant')
def sync_variant_to_inventory(sender, instance, created, **kwargs):
    """
    مزامنة الـ variant مع المخزون عند الإنشاء أو التحديث
    """
    # تجنب التكرار اللانهائي
    if getattr(instance, '_skip_sync', False):
        return
    
    # مزامنة مع المخزون إذا كان مرتبطاً
    if instance.product or (instance.family and instance.family.base_product):
        try:
            instance._skip_sync = True
            instance.sync_to_inventory()
        finally:
            instance._skip_sync = False


@receiver(post_save, sender='smart_pricing.ProductVariantPrice')
def update_inventory_price_on_price_change(sender, instance, created, **kwargs):
    """
    تحديث سعر المخزون عند تغيير سعر القائمة
    
    يعمل فقط إذا كانت قائمة الأسعار هي القائمة الافتراضية (retail)
    """
    # تحقق من أن القائمة هي قائمة التجزئة (الافتراضية)
    if not instance.price_list or instance.price_list.list_type != 'retail':
        return
    
    # البحث عن الـ variant المرتبط
    from .models_price_list import ProductVariant
    
    variant = ProductVariant.objects.filter(
        family=instance.family,
        size=instance.size
    ).first()
    
    if variant and variant.product:
        try:
            # تحديث سعر المخزون
            product = variant.product
            product.price = instance.final_price
            product.save(update_fields=['price'])
        except Exception as e:
            # تسجيل الخطأ بدون إيقاف العملية
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync price to inventory: {e}")


@receiver(post_save, sender='smart_pricing.VariantCostBreakdown')
def update_variant_cost_on_breakdown_change(sender, instance, **kwargs):
    """
    تحديث تكلفة الـ variant عند تغيير تفاصيل التكلفة
    """
    variant = instance.variant
    
    # إعادة حساب التكلفة الإجمالية
    from .models_price_list import VariantCostBreakdown
    
    total_cost = VariantCostBreakdown.objects.filter(
        variant=variant
    ).aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0')
    
    # تحديث الـ variant
    if variant.total_cost != total_cost:
        variant.total_cost = total_cost
        variant.save(update_fields=['total_cost'])
        
        # مزامنة مع المخزون
        if variant.product:
            try:
                variant.product.cost = total_cost
                variant.product.save(update_fields=['cost'])
            except Exception:
                pass


@receiver(pre_save, sender='smart_pricing.ProductFamily')
def update_family_products_on_base_price_change(sender, instance, **kwargs):
    """
    تحديث أسعار المنتجات عند تغيير السعر الأساسي للعائلة
    """
    if not instance.pk:
        return
    
    try:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.base_price != instance.base_price:
            # سيتم تحديث الأسعار بعد الحفظ
            instance._base_price_changed = True
            instance._old_base_price = old_instance.base_price
    except sender.DoesNotExist:
        pass


@receiver(post_save, sender='smart_pricing.ProductFamily')
def sync_family_products_prices(sender, instance, **kwargs):
    """
    مزامنة أسعار منتجات العائلة عند تغيير السعر الأساسي
    """
    if not getattr(instance, '_base_price_changed', False):
        return
    
    from .models_price_list import ProductVariant
    
    # تحديث جميع variants المرتبطة بالمخزون
    variants = ProductVariant.objects.filter(
        family=instance,
        product__isnull=False
    ).select_related('product', 'size')
    
    for variant in variants:
        try:
            new_price = instance.base_price * variant.size.price_multiplier
            variant.product.price = new_price
            variant.product.save(update_fields=['price'])
        except Exception:
            pass
    
    # مسح العلامة
    instance._base_price_changed = False


# ============================================
# وظائف المزامنة اليدوية
# ============================================

def sync_all_variants_to_inventory():
    """
    مزامنة جميع الـ variants مع المخزون
    
    تستخدم من الـ admin أو management command
    """
    from .models_price_list import ProductVariant
    
    results = {
        'synced': 0,
        'created': 0,
        'errors': [],
    }
    
    variants = ProductVariant.objects.select_related('family', 'size').all()
    
    for variant in variants:
        try:
            created = variant.sync_to_inventory()
            if created:
                results['created'] += 1
            else:
                results['synced'] += 1
        except Exception as e:
            results['errors'].append({
                'variant': str(variant),
                'error': str(e)
            })
    
    return results


def sync_inventory_prices_from_price_list(price_list_code='retail'):
    """
    تحديث أسعار المخزون من قائمة أسعار محددة
    
    Args:
        price_list_code: كود قائمة الأسعار (افتراضي: retail)
    """
    from .models_price_list import PriceList, ProductVariantPrice, ProductVariant
    
    try:
        price_list = PriceList.objects.get(code=price_list_code, is_active=True)
    except PriceList.DoesNotExist:
        return {'error': f'Price list "{price_list_code}" not found'}
    
    results = {
        'updated': 0,
        'skipped': 0,
        'errors': [],
    }
    
    # الحصول على جميع أسعار القائمة
    variant_prices = ProductVariantPrice.objects.filter(
        price_list=price_list
    ).select_related('family', 'size')
    
    for vp in variant_prices:
        # البحث عن الـ variant
        variant = ProductVariant.objects.filter(
            family=vp.family,
            size=vp.size,
            product__isnull=False
        ).select_related('product').first()
        
        if variant:
            try:
                variant.product.price = vp.final_price
                variant.product.save(update_fields=['price'])
                results['updated'] += 1
            except Exception as e:
                results['errors'].append({
                    'variant': str(variant),
                    'error': str(e)
                })
        else:
            results['skipped'] += 1
    
    return results


# ============================================
# تثبيت الأسعار عند إنشاء أوامر البيع
# ============================================

@receiver(post_save, sender='sales.SalesOrder')
def lock_prices_on_order_confirm(sender, instance, created, **kwargs):
    """
    تثبيت الأسعار تلقائياً عند تأكيد أمر البيع
    """
    # تثبيت فقط عند تأكيد الأمر
    if instance.status == 'confirmed':
        # تجنب التكرار
        if getattr(instance, '_prices_locked', False):
            return
        
        try:
            from .services_versioning import PriceLockService
            PriceLockService.lock_prices_from_sales_order(instance)
            instance._prices_locked = True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to lock prices for order {instance.number}: {e}")
