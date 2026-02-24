"""
Smart Delivery Promise Service
خدمة حساب وعد التسليم الذكي

تحسب موعد التسليم بناءً على:
- المخزون المتاح
- ضغط الإنتاج الحالي
- الطاقة الإنتاجية
- أوقات التصنيع
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple
from django.db.models import Sum, Q, F
from django.utils import timezone


class DeliveryPromiseCalculator:
    """حاسبة وعد التسليم الذكي"""
    
    def __init__(self):
        self.default_buffer_days = 2  # أيام احتياطية
        self.safety_margin = Decimal('0.1')  # هامش أمان 10%
    
    def calculate_promise(
        self,
        product,
        quantity: int,
        location=None,
        customer_type: str = 'regular'
    ) -> Dict:
        """
        حساب وعد التسليم لمنتج
        
        Args:
            product: المنتج المطلوب
            quantity: الكمية المطلوبة
            location: الموقع المطلوب منه (اختياري)
            customer_type: نوع العميل (vip, regular, wholesale)
        
        Returns:
            Dict يحتوي على:
            - delivery_date: تاريخ التسليم المتوقع
            - source: المصدر (stock, production, partial)
            - confidence: درجة الثقة (high, medium, low)
            - details: تفاصيل الحساب
        """
        from inventory.models import Stock, Location
        from production.models import ProductionOrder, BillOfMaterials
        
        # التحقق من المخزون المتاح
        stock_info = self._check_stock_availability(product, quantity, location)
        
        if stock_info['available'] >= quantity:
            # متوفر بالكامل من المخزون
            return self._create_stock_promise(stock_info, customer_type)
        
        # التحقق من إمكانية التصنيع
        bom = BillOfMaterials.objects.filter(
            product=product,
            is_active=True,
            is_default=True
        ).first()
        
        if not bom:
            # لا توجد وصفة تصنيع
            return self._create_unavailable_promise(product, quantity)
        
        # حساب وقت التصنيع
        production_info = self._calculate_production_time(
            bom,
            quantity - stock_info['available'],
            customer_type
        )
        
        if stock_info['available'] > 0:
            # جزء من المخزون وجزء من الإنتاج
            return self._create_partial_promise(
                stock_info,
                production_info,
                quantity,
                customer_type
            )
        else:
            # كل الكمية من الإنتاج
            return self._create_production_promise(
                production_info,
                quantity,
                customer_type
            )
    
    def _check_stock_availability(
        self,
        product,
        quantity: int,
        location=None
    ) -> Dict:
        """التحقق من توفر المخزون"""
        from inventory.models import Stock
        
        query = Q(product=product, quantity__gt=0)
        if location:
            query &= Q(location=location)
        
        stocks = Stock.objects.filter(query).select_related('location')
        total_available = sum(s.quantity for s in stocks)
        
        return {
            'available': min(total_available, quantity),
            'locations': [
                {
                    'location': s.location,
                    'quantity': s.quantity
                }
                for s in stocks
            ],
            'total': total_available
        }
    
    def _calculate_production_time(
        self,
        bom,
        quantity: int,
        customer_type: str
    ) -> Dict:
        """حساب وقت الإنتاج المطلوب"""
        from production.models import ProductionOrder, ProductionWorkCenter
        
        # حساب الطاقة الإنتاجية المتاحة
        work_centers = ProductionWorkCenter.objects.filter(
            is_active=True
        ).order_by('-capacity_per_hour')
        
        if not work_centers.exists():
            return {
                'days_required': 7,  # افتراضي
                'confidence': 'low',
                'capacity_available': False
            }
        
        # حساب الضغط الحالي على الإنتاج
        active_orders = ProductionOrder.objects.filter(
            status__in=['draft', 'confirmed', 'in_progress']
        ).aggregate(
            total_qty=Sum('quantity_to_produce')
        )['total_qty'] or 0
        
        # اختيار أفضل خط إنتاج
        best_wc = work_centers.first()
        daily_capacity = float(best_wc.capacity_per_hour * best_wc.working_hours_per_day)
        
        # حساب عدد الأيام المطلوبة
        current_load = float(active_orders) / daily_capacity if daily_capacity > 0 else 0
        production_days = quantity / daily_capacity if daily_capacity > 0 else 7
        
        # إضافة وقت الانتظار بناءً على الضغط
        if current_load > 5:  # ضغط عالي
            wait_days = 3
            confidence = 'low'
        elif current_load > 2:  # ضغط متوسط
            wait_days = 1
            confidence = 'medium'
        else:  # ضغط منخفض
            wait_days = 0
            confidence = 'high'
        
        # أولوية عالية للـ VIP
        if customer_type == 'vip':
            wait_days = max(0, wait_days - 1)
        
        total_days = int(production_days + wait_days + self.default_buffer_days)
        
        return {
            'days_required': total_days,
            'confidence': confidence,
            'capacity_available': True,
            'work_center': best_wc,
            'current_load': current_load,
            'production_days': production_days,
            'wait_days': wait_days
        }
    
    def _create_stock_promise(self, stock_info: Dict, customer_type: str) -> Dict:
        """إنشاء وعد تسليم من المخزون"""
        # التسليم خلال 1-2 أيام من المخزون
        days = 1 if customer_type == 'vip' else 2
        delivery_date = timezone.now().date() + timedelta(days=days)
        
        return {
            'delivery_date': delivery_date,
            'source': 'stock',
            'confidence': 'high',
            'days_until_delivery': days,
            'details': {
                'message': 'متوفر في المخزون - تسليم سريع',
                'available_locations': len(stock_info['locations']),
                'stock_quantity': stock_info['total']
            }
        }
    
    def _create_production_promise(
        self,
        production_info: Dict,
        quantity: int,
        customer_type: str
    ) -> Dict:
        """إنشاء وعد تسليم من الإنتاج"""
        days = production_info['days_required']
        delivery_date = timezone.now().date() + timedelta(days=days)
        
        return {
            'delivery_date': delivery_date,
            'source': 'production',
            'confidence': production_info['confidence'],
            'days_until_delivery': days,
            'details': {
                'message': f'سيتم التصنيع خصيصاً - التسليم خلال {days} يوم',
                'production_days': production_info['production_days'],
                'wait_days': production_info['wait_days'],
                'current_load': production_info['current_load'],
                'work_center': production_info['work_center'].name if production_info.get('work_center') else None
            }
        }
    
    def _create_partial_promise(
        self,
        stock_info: Dict,
        production_info: Dict,
        quantity: int,
        customer_type: str
    ) -> Dict:
        """إنشاء وعد تسليم جزئي (جزء من المخزون وجزء من الإنتاج)"""
        # يمكن تسليم جزء فوراً والباقي لاحقاً
        stock_days = 1 if customer_type == 'vip' else 2
        production_days = production_info['days_required']
        
        full_delivery_date = timezone.now().date() + timedelta(days=production_days)
        partial_delivery_date = timezone.now().date() + timedelta(days=stock_days)
        
        return {
            'delivery_date': full_delivery_date,
            'source': 'partial',
            'confidence': 'medium',
            'days_until_delivery': production_days,
            'details': {
                'message': f'متوفر {stock_info["available"]} قطعة فوراً، والباقي خلال {production_days} يوم',
                'partial_delivery_date': partial_delivery_date,
                'partial_quantity': stock_info['available'],
                'production_quantity': quantity - stock_info['available'],
                'full_delivery_date': full_delivery_date
            }
        }
    
    def _create_unavailable_promise(self, product, quantity: int) -> Dict:
        """إنشاء وعد لمنتج غير متاح حالياً"""
        return {
            'delivery_date': None,
            'source': 'unavailable',
            'confidence': 'none',
            'days_until_delivery': None,
            'details': {
                'message': 'المنتج غير متاح حالياً - يرجى التواصل مع المبيعات',
                'reason': 'لا توجد وصفة تصنيع أو مخزون'
            }
        }
    
    def bulk_calculate(self, items: list) -> Dict:
        """
        حساب وعد التسليم لعدة منتجات دفعة واحدة
        
        Args:
            items: قائمة من dict تحتوي على {product, quantity, location}
        
        Returns:
            Dict يحتوي على نتائج كل منتج ووعد التسليم الإجمالي
        """
        results = []
        max_days = 0
        overall_confidence = 'high'
        
        for item in items:
            promise = self.calculate_promise(
                product=item['product'],
                quantity=item['quantity'],
                location=item.get('location'),
                customer_type=item.get('customer_type', 'regular')
            )
            results.append({
                'product': item['product'],
                'promise': promise
            })
            
            if promise['days_until_delivery']:
                max_days = max(max_days, promise['days_until_delivery'])
            
            if promise['confidence'] in ['low', 'none']:
                overall_confidence = 'low'
            elif promise['confidence'] == 'medium' and overall_confidence == 'high':
                overall_confidence = 'medium'
        
        overall_delivery_date = timezone.now().date() + timedelta(days=max_days) if max_days > 0 else None
        
        return {
            'items': results,
            'overall_delivery_date': overall_delivery_date,
            'overall_confidence': overall_confidence,
            'days_until_delivery': max_days,
            'message': f'التسليم الكامل خلال {max_days} يوم' if max_days > 0 else 'غير متاح'
        }


# Singleton instance
delivery_calculator = DeliveryPromiseCalculator()
