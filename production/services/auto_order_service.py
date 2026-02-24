"""
خدمة إنشاء أوامر التصنيع التلقائية
Auto Production Order Service

هذه الخدمة مسؤولة عن:
- فحص توفر المخزون عند البيع
- إنشاء أوامر تصنيع تلقائية للمنتجات الناقصة
- حساب تاريخ التسليم المتوقع
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, Any, Tuple
from django.db.models import Sum, Q
from django.utils import timezone
from django.conf import settings


class AutoProductionOrderService:
    """خدمة إدارة أوامر الإنتاج التلقائية"""
    
    # إعدادات افتراضية
    DEFAULT_SETTINGS = {
        'ENABLED': True,
        'MIN_SHORTAGE_TO_TRIGGER': 1,
        'SAFETY_STOCK_MULTIPLIER': 1.2,
        'LEAD_TIME_BUFFER_DAYS': 2,
        'AUTO_APPROVE_ORDERS': False,
        'PRIORITY_HIGH_THRESHOLD': 10,
    }
    
    @classmethod
    def get_settings(cls):
        """الحصول على الإعدادات من Django settings أو استخدام الافتراضية"""
        return getattr(settings, 'AUTO_PRODUCTION_SETTINGS', cls.DEFAULT_SETTINGS)
    
    @staticmethod
    def check_stock_availability(product, location, required_qty: int) -> Dict[str, Any]:
        """
        فحص توفر المخزون للمنتج في موقع محدد
        
        Returns:
            dict: {
                'available': int,
                'pending_production': int,
                'shortage': int,
                'needs_production': bool
            }
        """
        from inventory.models import Stock
        from production.models import ProductionOrder
        
        # 1. المخزون الحالي
        available = Stock.objects.filter(
            product=product,
            location=location
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # 2. الكمية في أوامر الإنتاج الجارية
        pending_production = ProductionOrder.objects.filter(
            product=product,
            status__in=['draft', 'confirmed', 'in_progress']
        ).aggregate(total=Sum('planned_quantity'))['total'] or 0
        
        # 3. حساب النقص
        total_available = available + pending_production
        shortage = max(0, required_qty - total_available)
        
        return {
            'available': int(available),
            'pending_production': int(pending_production),
            'total_available': int(total_available),
            'shortage': int(shortage),
            'needs_production': shortage > 0
        }
    
    @staticmethod
    def calculate_production_quantity(shortage: int, safety_multiplier: float = 1.2) -> int:
        """
        حساب كمية الإنتاج المطلوبة مع مخزون الأمان
        
        Args:
            shortage: النقص الفعلي
            safety_multiplier: معامل مخزون الأمان (افتراضي 1.2 = 20% إضافي)
        """
        return int(shortage * safety_multiplier)
    
    @staticmethod
    def estimate_delivery_date(product, quantity: int) -> Tuple[date, Dict[str, Any]]:
        """
        تقدير تاريخ التسليم بناءً على BOM وطاقة المصنع
        
        Returns:
            tuple: (delivery_date, details_dict)
        """
        from production.models import BillOfMaterials
        from production.services.scheduling_service import CapacityAnalyzer
        
        settings_config = AutoProductionOrderService.get_settings()
        buffer_days = settings_config.get('LEAD_TIME_BUFFER_DAYS', 2)
        
        # البحث عن BOM للمنتج
        bom = BillOfMaterials.objects.filter(
            product=product,
            is_active=True
        ).first()
        
        if not bom:
            # لا توجد BOM - تقدير افتراضي
            estimated_days = 7
            delivery_date = date.today() + timedelta(days=estimated_days + buffer_days)
            return delivery_date, {
                'production_days': estimated_days,
                'buffer_days': buffer_days,
                'capacity_delay': 0,
                'has_bom': False,
                'method': 'default_estimate'
            }
        
        # حساب وقت الإنتاج من المراحل
        production_time_minutes = 0
        stages = bom.stages.all() if hasattr(bom, 'stages') else []
        
        for stage_link in stages:
            stage = stage_link.stage
            operation_time = getattr(stage, 'operation_time', 0) or 0
            production_time_minutes += operation_time * quantity
        
        # تحويل الدقائق إلى أيام (8 ساعات عمل يومياً)
        if production_time_minutes > 0:
            production_days = int((production_time_minutes / (8 * 60)) + 0.5)  # تقريب لأعلى
        else:
            production_days = 5  # افتراضي 5 أيام
        
        # فحص ضغط المصنع (إذا كانت الخدمة متوفرة)
        capacity_delay = 0
        try:
            analyzer = CapacityAnalyzer()
            capacity = analyzer.get_available_capacity(
                start_date=date.today(),
                days=14
            )
            utilization = capacity.get('utilization', 0)
            
            if utilization > 0.95:  # 95% capacity
                capacity_delay = 7
            elif utilization > 0.85:  # 85% capacity
                capacity_delay = 3
        except Exception:
            # الخدمة غير متوفرة - لا نضيف تأخير
            pass
        
        # التاريخ النهائي
        total_days = production_days + capacity_delay + buffer_days
        delivery_date = date.today() + timedelta(days=total_days)
        
        return delivery_date, {
            'production_days': production_days,
            'buffer_days': buffer_days,
            'capacity_delay': capacity_delay,
            'total_days': total_days,
            'has_bom': True,
            'production_time_minutes': production_time_minutes,
            'method': 'bom_based'
        }
    
    @staticmethod
    def create_production_order(product, quantity: int, showroom=None, 
                               reference: str = '', user=None) -> Optional[Any]:
        """
        إنشاء أمر تصنيع جديد
        
        Args:
            product: المنتج
            quantity: الكمية المطلوبة
            showroom: المعرض المطلوب (اختياري)
            reference: مرجع الطلب (رقم POS مثلاً)
            user: المستخدم المنشئ
            
        Returns:
            ProductionOrder أو None
        """
        from production.models import ProductionOrder, BillOfMaterials
        
        settings_config = AutoProductionOrderService.get_settings()
        high_threshold = settings_config.get('PRIORITY_HIGH_THRESHOLD', 10)
        
        # تحديد الأولوية
        if quantity >= high_threshold:
            priority = 'high'
        else:
            priority = 'normal'
        
        # البحث عن BOM
        bom = BillOfMaterials.objects.filter(
            product=product,
            is_active=True
        ).first()
        
        if not bom:
            # لا يمكن إنشاء أمر بدون BOM
            return None
        
        # حساب تاريخ التسليم
        delivery_date, details = AutoProductionOrderService.estimate_delivery_date(
            product, quantity
        )
        
        # إنشاء أمر الإنتاج
        order = ProductionOrder.objects.create(
            product=product,
            bom=bom,
            planned_quantity=quantity,
            planned_start_date=date.today(),
            planned_end_date=delivery_date,
            priority=priority,
            notes=f'أمر تلقائي - مرجع: {reference}' if reference else 'أمر تلقائي من POS',
            created_by=user,
            status='draft'
        )
        
        # حفظ البيانات الإضافية
        if showroom:
            # يمكن إضافة حقل reference_showroom في ProductionOrder لاحقاً
            pass
        
        return order
    
    @staticmethod
    def check_and_create_order(product, quantity: int, showroom=None, 
                               location=None, reference: str = '', 
                               user=None) -> Dict[str, Any]:
        """
        الدالة الرئيسية: فحص المخزون وإنشاء أمر إنتاج إذا لزم
        
        Returns:
            dict: {
                'needs_production': bool,
                'order_created': bool,
                'production_order': ProductionOrder or None,
                'delivery_date': date or None,
                'stock_info': dict,
                'message': str
            }
        """
        settings_config = AutoProductionOrderService.get_settings()
        
        # التحقق من التفعيل
        if not settings_config.get('ENABLED', True):
            return {
                'needs_production': False,
                'order_created': False,
                'production_order': None,
                'delivery_date': None,
                'message': 'خدمة الإنتاج التلقائي معطلة'
            }
        
        # استخدام location المعرض إذا لم يُحدد
        if not location and showroom:
            location = showroom.location
        
        # فحص المخزون
        stock_info = AutoProductionOrderService.check_stock_availability(
            product, location, quantity
        )
        
        if not stock_info['needs_production']:
            return {
                'needs_production': False,
                'order_created': False,
                'production_order': None,
                'delivery_date': None,
                'stock_info': stock_info,
                'message': f'متوفر في المخزون ({stock_info["available"]} قطعة)'
            }
        
        # حساب الكمية المطلوبة مع الأمان
        shortage = stock_info['shortage']
        min_trigger = settings_config.get('MIN_SHORTAGE_TO_TRIGGER', 1)
        
        if shortage < min_trigger:
            return {
                'needs_production': True,
                'order_created': False,
                'production_order': None,
                'delivery_date': None,
                'stock_info': stock_info,
                'message': f'النقص ({shortage}) أقل من الحد الأدنى ({min_trigger})'
            }
        
        # حساب الكمية مع مخزون الأمان
        safety_multiplier = settings_config.get('SAFETY_STOCK_MULTIPLIER', 1.2)
        production_qty = AutoProductionOrderService.calculate_production_quantity(
            shortage, safety_multiplier
        )
        
        # إنشاء أمر الإنتاج
        try:
            order = AutoProductionOrderService.create_production_order(
                product=product,
                quantity=production_qty,
                showroom=showroom,
                reference=reference,
                user=user
            )
            
            if order:
                return {
                    'needs_production': True,
                    'order_created': True,
                    'production_order': order,
                    'delivery_date': order.planned_end_date,
                    'stock_info': stock_info,
                    'production_quantity': production_qty,
                    'message': f'تم إنشاء أمر إنتاج #{order.number} لـ {production_qty} قطعة'
                }
            else:
                return {
                    'needs_production': True,
                    'order_created': False,
                    'production_order': None,
                    'delivery_date': None,
                    'stock_info': stock_info,
                    'message': 'لا توجد قائمة مواد (BOM) للمنتج'
                }
        
        except Exception as e:
            return {
                'needs_production': True,
                'order_created': False,
                'production_order': None,
                'delivery_date': None,
                'stock_info': stock_info,
                'message': f'خطأ في إنشاء أمر الإنتاج: {str(e)}'
            }
