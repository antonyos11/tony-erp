"""
خدمات إدارة إصدارات قوائم الأسعار
Price List Versioning Services
"""

from decimal import Decimal
from django.utils import timezone
from django.db import transaction, models
from typing import Optional, List, Dict


class PriceVersioningService:
    """خدمة إدارة إصدارات قوائم الأسعار"""
    
    @staticmethod
    def create_new_version(price_list, user=None, grace_period_days=0, 
                           effective_from=None, change_reason='', auto_activate=False):
        """
        إنشاء إصدار جديد من قائمة الأسعار
        
        Args:
            price_list: قائمة الأسعار
            user: المستخدم
            grace_period_days: فترة السماح
            effective_from: تاريخ البدء (افتراضي: الآن)
            change_reason: سبب التغيير
            auto_activate: تفعيل تلقائي
            
        Returns:
            PriceListVersion instance
        """
        from .models_versioning import PriceListVersion, VersionedPrice, PriceChangeLog
        from .models_price_list import ProductFamily, ProductVariantPrice
        
        with transaction.atomic():
            # إنشاء الإصدار الجديد
            version = PriceListVersion.objects.create(
                price_list=price_list,
                grace_period_days=grace_period_days,
                effective_from=effective_from or timezone.now(),
                change_reason=change_reason,
                created_by=user,
                status='draft'
            )
            
            # نسخ الأسعار الحالية إلى الإصدار
            families = ProductFamily.objects.filter(is_active=True, show_in_price_list=True)
            
            for family in families:
                for size in family.available_sizes.all():
                    # الحصول على السعر الحالي
                    variant_price = ProductVariantPrice.objects.filter(
                        family=family,
                        size=size,
                        price_list=price_list
                    ).first()
                    
                    if variant_price:
                        base_price = family.base_price * size.price_multiplier
                        discounted_price = variant_price.effective_price
                        final_price = variant_price.final_price
                    else:
                        base_price = family.base_price * size.price_multiplier
                        discounted_price = price_list.apply_discount(base_price)
                        final_price = price_list.apply_tax(discounted_price)
                    
                    # حساب التكلفة والهامش
                    cost = family.base_cost * size.cost_multiplier
                    margin = ((discounted_price - cost) / cost * 100) if cost else Decimal('0')
                    
                    VersionedPrice.objects.create(
                        version=version,
                        family=family,
                        size=size,
                        base_price=base_price,
                        discounted_price=discounted_price,
                        final_price=final_price,
                        cost=cost,
                        margin_percentage=margin
                    )
            
            if auto_activate:
                version.activate(user)
            
            return version
    
    @staticmethod
    def activate_version(version, user=None):
        """
        تفعيل إصدار وإنشاء سجل التغييرات
        
        Args:
            version: PriceListVersion instance
            user: المستخدم
        """
        from .models_versioning import PriceListVersion, VersionedPrice, PriceChangeLog
        
        with transaction.atomic():
            # الحصول على الإصدار السابق للمقارنة
            previous_version = PriceListVersion.objects.filter(
                price_list=version.price_list,
                status='active'
            ).exclude(pk=version.pk).first()
            
            # إنشاء سجل التغييرات
            if previous_version:
                PriceVersioningService._log_price_changes(
                    version, previous_version, user
                )
            
            # تفعيل الإصدار
            version.activate(user)
    
    @staticmethod
    def _log_price_changes(new_version, old_version, user=None):
        """تسجيل تغييرات الأسعار بين إصدارين"""
        from .models_versioning import VersionedPrice, PriceChangeLog
        
        # الحصول على أسعار الإصدار الجديد
        new_prices = {
            (p.family_id, p.size_id): p
            for p in VersionedPrice.objects.filter(version=new_version)
        }
        
        # الحصول على أسعار الإصدار القديم
        old_prices = {
            (p.family_id, p.size_id): p
            for p in VersionedPrice.objects.filter(version=old_version)
        }
        
        # المقارنة وتسجيل التغييرات
        all_keys = set(new_prices.keys()) | set(old_prices.keys())
        
        logs = []
        for key in all_keys:
            new_price = new_prices.get(key)
            old_price = old_prices.get(key)
            
            if new_price and old_price:
                if new_price.final_price != old_price.final_price:
                    logs.append(PriceChangeLog(
                        price_list=new_version.price_list,
                        version=new_version,
                        family_id=key[0],
                        size_id=key[1],
                        old_price=old_price.final_price,
                        new_price=new_price.final_price,
                        changed_by=user,
                        reason=new_version.change_reason
                    ))
            elif new_price:
                # سعر جديد
                logs.append(PriceChangeLog(
                    price_list=new_version.price_list,
                    version=new_version,
                    family_id=key[0],
                    size_id=key[1],
                    old_price=Decimal('0'),
                    new_price=new_price.final_price,
                    changed_by=user,
                    reason=new_version.change_reason
                ))
        
        if logs:
            PriceChangeLog.objects.bulk_create(logs)
    
    @staticmethod
    def get_price_for_date(price_list, family, size, target_date=None):
        """
        الحصول على السعر في تاريخ معين
        
        Args:
            price_list: قائمة الأسعار
            family: عائلة المنتج
            size: المقاس
            target_date: التاريخ المطلوب (افتراضي: الآن)
            
        Returns:
            dict مع السعر والإصدار
        """
        from .models_versioning import PriceListVersion, VersionedPrice
        
        if target_date is None:
            target_date = timezone.now()
        
        # البحث عن الإصدار الساري في هذا التاريخ
        version = PriceListVersion.objects.filter(
            price_list=price_list,
            status__in=['active', 'expired'],
            effective_from__lte=target_date
        ).filter(
            models.Q(effective_until__isnull=True) | 
            models.Q(effective_until__gte=target_date)
        ).order_by('-effective_from').first()
        
        if not version:
            # لا يوجد إصدار، استخدم الأسعار الحالية
            from .models_price_list import ProductVariantPrice
            
            vp = ProductVariantPrice.objects.filter(
                family=family,
                size=size,
                price_list=price_list
            ).first()
            
            if vp:
                return {
                    'price': vp.effective_price,
                    'final_price': vp.final_price,
                    'version': None,
                    'version_name': 'الحالي'
                }
            
            base_price = family.base_price * size.price_multiplier
            return {
                'price': price_list.apply_discount(base_price),
                'final_price': price_list.apply_tax(price_list.apply_discount(base_price)),
                'version': None,
                'version_name': 'الحالي'
            }
        
        # الحصول على السعر من الإصدار
        versioned_price = VersionedPrice.objects.filter(
            version=version,
            family=family,
            size=size
        ).first()
        
        if versioned_price:
            return {
                'price': versioned_price.discounted_price,
                'final_price': versioned_price.final_price,
                'version': version,
                'version_name': version.version_name
            }
        
        return None


class PriceLockService:
    """خدمة تثبيت الأسعار"""
    
    @staticmethod
    def lock_price_for_customer(customer, family, size, price_list=None, 
                                 valid_days=None, user=None, notes=''):
        """
        تثبيت سعر لعميل يدوياً
        
        Args:
            customer: العميل
            family: عائلة المنتج
            size: المقاس
            price_list: قائمة الأسعار (افتراضي: retail)
            valid_days: عدد أيام الصلاحية (None = دائم)
            user: المستخدم
            notes: ملاحظات
            
        Returns:
            LockedPrice instance
        """
        from .models_versioning import LockedPrice, PriceListVersion
        from .models_price_list import PriceList, ProductVariantPrice
        from datetime import timedelta
        
        # تحديد قائمة الأسعار
        if price_list is None:
            price_list = PriceList.objects.filter(
                is_active=True, list_type='retail'
            ).first()
        
        if not price_list:
            raise ValueError("لم يتم العثور على قائمة أسعار")
        
        # الحصول على السعر الحالي
        vp = ProductVariantPrice.objects.filter(
            family=family,
            size=size,
            price_list=price_list
        ).first()
        
        if vp:
            locked_price = vp.effective_price
            locked_price_with_tax = vp.final_price
        else:
            base_price = family.base_price * size.price_multiplier
            locked_price = price_list.apply_discount(base_price)
            locked_price_with_tax = price_list.apply_tax(locked_price)
        
        # الحصول على الإصدار الحالي
        current_version = PriceListVersion.objects.filter(
            price_list=price_list,
            status='active'
        ).first()
        
        # حساب تاريخ الانتهاء
        valid_until = None
        if valid_days:
            valid_until = timezone.now() + timedelta(days=valid_days)
        
        # إلغاء أي سعر مثبت سابق لنفس المنتج
        LockedPrice.objects.filter(
            customer=customer,
            family=family,
            size=size,
            is_active=True
        ).update(is_active=False)
        
        # إنشاء السعر المثبت
        locked = LockedPrice.objects.create(
            lock_type='manual',
            customer=customer,
            family=family,
            size=size,
            price_list=price_list,
            price_version=current_version,
            locked_price=locked_price,
            locked_price_with_tax=locked_price_with_tax,
            valid_until=valid_until,
            created_by=user,
            notes=notes
        )
        
        return locked
    
    @staticmethod
    def lock_prices_from_sales_order(sales_order, user=None):
        """
        تثبيت أسعار أمر البيع تلقائياً
        
        Args:
            sales_order: SalesOrder instance
            user: المستخدم
            
        Returns:
            قائمة بالأسعار المثبتة
        """
        from .models_versioning import LockedPrice
        return LockedPrice.lock_from_order(sales_order, user)
    
    @staticmethod
    def get_effective_price(customer, family, size, price_list=None, check_date=None):
        """
        الحصول على السعر الفعال للعميل
        يتحقق أولاً من السعر المثبت، ثم من فترة السماح، ثم السعر الحالي
        
        Args:
            customer: العميل
            family: عائلة المنتج
            size: المقاس
            price_list: قائمة الأسعار
            check_date: تاريخ للتحقق (افتراضي: الآن)
            
        Returns:
            dict مع السعر والمصدر
        """
        from .models_versioning import LockedPrice, PriceListVersion
        from .models_price_list import PriceList, ProductVariantPrice
        from django.db import models
        
        if check_date is None:
            check_date = timezone.now()
        
        if price_list is None:
            price_list = PriceList.objects.filter(
                is_active=True, list_type='retail'
            ).first()
        
        # 1. التحقق من السعر المثبت
        locked = LockedPrice.objects.filter(
            customer=customer,
            family=family,
            size=size,
            is_active=True,
            valid_from__lte=check_date
        ).filter(
            models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=check_date)
        ).order_by('-created_at').first()
        
        if locked:
            return {
                'price': locked.locked_price,
                'final_price': locked.locked_price_with_tax,
                'source': 'locked',
                'source_name': 'سعر مثبت',
                'locked_price': locked,
                'can_use_old_price': True
            }
        
        # 2. التحقق من فترة السماح
        current_version = PriceListVersion.objects.filter(
            price_list=price_list,
            status='active'
        ).first()
        
        if current_version and current_version.is_in_grace_period():
            # نحن في فترة السماح، يمكن استخدام السعر القديم
            previous_version = PriceListVersion.objects.filter(
                price_list=price_list,
                status='expired'
            ).order_by('-effective_until').first()
            
            if previous_version:
                from .models_versioning import VersionedPrice
                old_price = VersionedPrice.objects.filter(
                    version=previous_version,
                    family=family,
                    size=size
                ).first()
                
                if old_price:
                    return {
                        'price': old_price.discounted_price,
                        'final_price': old_price.final_price,
                        'source': 'grace_period',
                        'source_name': f'فترة السماح ({previous_version.version_name})',
                        'grace_period_ends': current_version.grace_period_end,
                        'can_use_old_price': True,
                        'new_price': None  # سيتم ملؤه أدناه
                    }
        
        # 3. السعر الحالي
        vp = ProductVariantPrice.objects.filter(
            family=family,
            size=size,
            price_list=price_list
        ).first()
        
        if vp:
            price = vp.effective_price
            final_price = vp.final_price
        else:
            base_price = family.base_price * size.price_multiplier
            price = price_list.apply_discount(base_price)
            final_price = price_list.apply_tax(price)
        
        return {
            'price': price,
            'final_price': final_price,
            'source': 'current',
            'source_name': 'السعر الحالي',
            'can_use_old_price': False
        }
    
    @staticmethod
    def get_customer_locked_prices(customer, active_only=True):
        """
        الحصول على جميع الأسعار المثبتة للعميل
        """
        from .models_versioning import LockedPrice
        
        queryset = LockedPrice.objects.filter(customer=customer)
        
        if active_only:
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True,
                valid_from__lte=now
            ).filter(
                models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=now)
            )
        
        return queryset.select_related('family', 'size', 'price_list')
    
    @staticmethod
    def expire_old_locks():
        """
        إنهاء الأسعار المثبتة المنتهية الصلاحية
        يمكن تشغيلها دورياً
        """
        from .models_versioning import LockedPrice
        
        now = timezone.now()
        expired = LockedPrice.objects.filter(
            is_active=True,
            valid_until__lt=now
        )
        
        count = expired.count()
        expired.update(is_active=False)
        
        return count
