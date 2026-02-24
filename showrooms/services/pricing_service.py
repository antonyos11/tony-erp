"""
خدمة التسعير الذكي للمعارض
Smart Pricing Service for Showrooms
"""
from decimal import Decimal
from django.utils import timezone
from typing import Optional, Dict, Any


class ShowroomPricingService:
    """خدمة حساب الأسعار حسب قواعد المعرض"""
    
    @staticmethod
    def get_product_price(product, showroom, quantity: int = 1) -> Dict[str, Any]:
        """
        الحصول على السعر النهائي للمنتج في معرض محدد
        
        Args:
            product: المنتج
            showroom: المعرض
            quantity: الكمية (للخصومات الكمية المستقبلية)
            
        Returns:
            dict: {
                'final_price': Decimal,
                'base_price': Decimal,
                'adjustment': Decimal,
                'rule_applied': ShowroomPricingRule or None,
                'rule_type': str or None
            }
        """
        from showrooms.models import ShowroomPricingRule
        
        base_price = product.price or Decimal('0')
        today = timezone.now().date()
        
        # البحث عن قاعدة تسعير نشطة
        active_rules = ShowroomPricingRule.objects.filter(
            showroom=showroom,
            product=product,
            is_active=True,
            effective_from__lte=today
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=today)
        ).order_by('-priority', '-created_at')
        
        rule = active_rules.first()
        
        if rule:
            final_price = rule.calculate_price(base_price)
            adjustment = final_price - base_price
            
            return {
                'final_price': final_price,
                'base_price': base_price,
                'adjustment': adjustment,
                'rule_applied': rule,
                'rule_type': rule.adjustment_type,
                'has_special_price': True
            }
        
        # لا توجد قاعدة - استخدام السعر الأساسي
        return {
            'final_price': base_price,
            'base_price': base_price,
            'adjustment': Decimal('0'),
            'rule_applied': None,
            'rule_type': None,
            'has_special_price': False
        }
    
    @staticmethod
    def bulk_get_prices(products_list, showroom):
        """
        الحصول على أسعار مجموعة منتجات دفعة واحدة (أفضل للأداء)
        
        Args:
            products_list: قائمة المنتجات
            showroom: المعرض
            
        Returns:
            dict: {product_id: price_info}
        """
        from showrooms.models import ShowroomPricingRule
        
        today = timezone.now().date()
        product_ids = [p.id for p in products_list]
        
        # جلب كل القواعد النشطة مرة واحدة
        active_rules = ShowroomPricingRule.objects.filter(
            showroom=showroom,
            product_id__in=product_ids,
            is_active=True,
            effective_from__lte=today
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=today)
        ).select_related('product').order_by('product_id', '-priority', '-created_at')
        
        # تنظيم القواعد حسب المنتج
        rules_by_product = {}
        for rule in active_rules:
            if rule.product_id not in rules_by_product:
                rules_by_product[rule.product_id] = rule
        
        # حساب الأسعار
        result = {}
        for product in products_list:
            base_price = product.price or Decimal('0')
            rule = rules_by_product.get(product.id)
            
            if rule:
                final_price = rule.calculate_price(base_price)
                result[product.id] = {
                    'final_price': final_price,
                    'base_price': base_price,
                    'adjustment': final_price - base_price,
                    'has_special_price': True
                }
            else:
                result[product.id] = {
                    'final_price': base_price,
                    'base_price': base_price,
                    'adjustment': Decimal('0'),
                    'has_special_price': False
                }
        
        return result
    
    @staticmethod
    def create_pricing_rule(showroom, product, adjustment_type, value, 
                           effective_from=None, effective_to=None, 
                           priority=1, notes='', user=None):
        """
        إنشاء قاعدة تسعير جديدة
        
        Args:
            showroom: المعرض
            product: المنتج
            adjustment_type: نوع التعديل (fixed, percentage, markup, discount)
            value: القيمة
            effective_from: ساري من (اختياري)
            effective_to: ساري حتى (اختياري)
            priority: الأولوية
            notes: ملاحظات
            user: المستخدم المنشئ
        """
        from showrooms.models import ShowroomPricingRule
        
        if effective_from is None:
            effective_from = timezone.now().date()
        
        rule = ShowroomPricingRule.objects.create(
            showroom=showroom,
            product=product,
            adjustment_type=adjustment_type,
            value=value,
            effective_from=effective_from,
            effective_to=effective_to,
            priority=priority,
            notes=notes,
            is_active=True,
            created_by=user
        )
        
        return rule
    
    @staticmethod
    def bulk_create_pricing_rules(showroom, products, adjustment_type, value,
                                  effective_from=None, effective_to=None,
                                  user=None):
        """
        إنشاء قواعد تسعير جماعية لعدة منتجات دفعة واحدة
        
        مثال: خصم 10% على كل المراتب في معرض القاهرة
        """
        from showrooms.models import ShowroomPricingRule
        
        if effective_from is None:
            effective_from = timezone.now().date()
        
        rules = []
        for product in products:
            rules.append(ShowroomPricingRule(
                showroom=showroom,
                product=product,
                adjustment_type=adjustment_type,
                value=value,
                effective_from=effective_from,
                effective_to=effective_to,
                is_active=True,
                created_by=user
            ))
        
        # إنشاء جماعي للأداء
        created_rules = ShowroomPricingRule.objects.bulk_create(rules)
        
        return created_rules
    
    @staticmethod
    def deactivate_expired_rules():
        """
        تعطيل القواعد المنتهية تلقائياً
        (يمكن تشغيلها كمهمة دورية)
        """
        from showrooms.models import ShowroomPricingRule
        
        today = timezone.now().date()
        
        expired = ShowroomPricingRule.objects.filter(
            is_active=True,
            effective_to__lt=today
        ).update(is_active=False)
        
        return expired


# Import Django Q for queries
from django.db import models
