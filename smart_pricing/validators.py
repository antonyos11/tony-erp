"""
Loss Prevention & Price Validation System
نظام منع البيع الخاسر والتحقق من الأسعار

يمنع البيع تحت التكلفة ويحمي هوامش الربح
"""

from decimal import Decimal
from typing import Dict, Tuple, Optional
from django.core.exceptions import ValidationError


class PriceValidator:
    """مدقق الأسعار"""
    
    def __init__(self):
        self.allow_manager_override = True
        self.send_alerts = True
    
    def validate_price(
        self,
        product,
        price: Decimal,
        quantity: int = 1,
        customer_type: str = 'regular',
        user=None
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        التحقق من صحة سعر البيع
        
        Returns:
            Tuple of (is_valid, error_message, warning_data)
        """
        # الحصول على التكلفة
        product_cost = self._get_product_cost(product, quantity)
        
        # الحصول على هامش الربح المطلوب
        min_margin = self._get_minimum_margin(product, customer_type)
        
        # حساب السعر الأدنى المسموح
        min_allowed_price = product_cost * (1 + min_margin / 100)
        
        # التحقق من السعر
        if price < product_cost:
            # بيع تحت التكلفة - ممنوع تماماً
            return False, f'خطأ: السعر ({price}) أقل من التكلفة ({product_cost})', {
                'type': 'below_cost',
                'price': float(price),
                'product_cost': float(product_cost),
                'loss_amount': float(product_cost - price),
                'requires_approval': True
            }
        
        elif price < min_allowed_price:
            # بيع تحت هامش الربح الأدنى - يحتاج موافقة
            margin = ((price - product_cost) / product_cost * 100) if product_cost > 0 else Decimal('0')
            
            warning_msg = f'تحذير: هامش الربح ({margin:.2f}%) أقل من الحد الأدنى ({min_margin}%)'
            
            # التحقق من صلاحيات المستخدم
            if user and self._has_override_permission(user):
                return True, warning_msg, {
                    'type': 'below_minimum_margin',
                    'price': float(price),
                    'product_cost': float(product_cost),
                    'current_margin': float(margin),
                    'minimum_margin': float(min_margin),
                    'approved_by': user.username,
                    'requires_approval': False
                }
            else:
                return False, warning_msg + ' - يتطلب موافقة المدير', {
                    'type': 'below_minimum_margin',
                    'price': float(price),
                    'product_cost': float(product_cost),
                    'current_margin': float(margin),
                    'minimum_margin': float(min_margin),
                    'requires_approval': True
                }
        
        # السعر مقبول
        margin = ((price - product_cost) / product_cost * 100) if product_cost > 0 else Decimal('0')
        return True, None, {
            'type': 'acceptable',
            'price': float(price),
            'product_cost': float(product_cost),
            'margin': float(margin)
        }
    
    def validate_bulk_prices(
        self,
        items: list,
        user=None
    ) -> Dict:
        """
        التحقق من أسعار عدة منتجات دفعة واحدة
        
        Args:
            items: قائمة من dict تحتوي على {product, price, quantity}
        
        Returns:
            Dict يحتوي على نتائج التحقق لكل منتج
        """
        results = []
        has_errors = False
        requires_approval = False
        
        for item in items:
            is_valid, message, data = self.validate_price(
                product=item['product'],
                price=item['price'],
                quantity=item.get('quantity', 1),
                customer_type=item.get('customer_type', 'regular'),
                user=user
            )
            
            results.append({
                'product': item['product'].name,
                'is_valid': is_valid,
                'message': message,
                'data': data
            })
            
            if not is_valid:
                has_errors = True
            
            if data and data.get('requires_approval'):
                requires_approval = True
        
        return {
            'items': results,
            'overall_valid': not has_errors,
            'requires_approval': requires_approval,
            'total_items': len(items),
            'invalid_items': sum(1 for r in results if not r['is_valid'])
        }
    
    def _get_product_cost(self, product, quantity: int = 1) -> Decimal:
        """الحصول على تكلفة المنتج"""
        from production.models import BillOfMaterials
        
        # محاولة الحصول على التكلفة من BOM
        bom = BillOfMaterials.objects.filter(
            product=product,
            is_active=True,
            is_default=True
        ).first()
        
        if bom:
            # تكلفة المواد + العمالة + التكاليف الإضافية
            total_cost = bom.total_material_cost + bom.total_labor_cost + bom.total_overhead_cost
            unit_cost = total_cost / bom.base_quantity if bom.base_quantity > 0 else bom.total_material_cost
            return unit_cost
        else:
            # استخدام التكلفة المخزنة
            return product.cost
    
    def _get_minimum_margin(self, product, customer_type: str) -> Decimal:
        """الحصول على هامش الربح الأدنى المطلوب"""
        from smart_pricing.models import PricingRule
        
        # محاولة الحصول على قاعدة التسعير للمنتج
        pricing_rule = PricingRule.objects.filter(
            is_active=True
        ).order_by('-id').first()
        
        if pricing_rule:
            min_margin = pricing_rule.min_profit_margin
        else:
            # هامش افتراضي
            min_margin = Decimal('15.0')
        
        # تعديل بناءً على نوع العميل
        if customer_type == 'wholesale':
            min_margin = min_margin * Decimal('0.7')  # خصم 30% للجملة
        elif customer_type == 'vip':
            min_margin = min_margin * Decimal('0.85')  # خصم 15% للـ VIP
        
        return min_margin
    
    def _has_override_permission(self, user) -> bool:
        """التحقق من صلاحية تجاوز التحذيرات"""
        # التحقق من صلاحيات المستخدم
        if user.is_superuser:
            return True
        
        # التحقق من المجموعات
        allowed_groups = ['Sales Manager', 'Financial Manager', 'CEO']
        return user.groups.filter(name__in=allowed_groups).exists()
    
    def calculate_recommended_price(
        self,
        product,
        customer_type: str = 'regular'
    ) -> Dict:
        """حساب السعر الموصى به"""
        cost = self._get_product_cost(product)
        min_margin = self._get_minimum_margin(product, customer_type)
        
        # السعر الأدنى
        min_price = cost * (1 + min_margin / 100)
        
        # السعر المستهدف (هامش أعلى)
        target_margin = min_margin * Decimal('1.5')
        target_price = cost * (1 + target_margin / 100)
        
        # السعر الأقصى (حسب السوق)
        max_margin = min_margin * Decimal('2.5')
        max_price = cost * (1 + max_margin / 100)
        
        return {
            'cost': float(cost),
            'min_price': float(min_price),
            'min_margin': float(min_margin),
            'target_price': float(target_price),
            'target_margin': float(target_margin),
            'max_price': float(max_price),
            'max_margin': float(max_margin),
            'customer_type': customer_type
        }


class LossPreventionService:
    """خدمة منع الخسارة"""
    
    def __init__(self):
        self.validator = PriceValidator()
    
    def analyze_pricing_risks(self, period_days: int = 30) -> Dict:
        """تحليل مخاطر التسعير"""
        from sales.models import InvoiceItem
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        # الحصول على جميع المبيعات
        items = InvoiceItem.objects.filter(
            invoice__invoice_date__gte=start_date
        ).select_related('product')
        
        risky_sales = []
        total_potential_loss = Decimal('0')
        
        for item in items:
            cost = self.validator._get_product_cost(item.product, item.quantity)
            selling_price = item.price
            
            if selling_price < cost:
                loss = (cost - selling_price) * item.quantity
                total_potential_loss += loss
                
                risky_sales.append({
                    'invoice': item.invoice.invoice_number,
                    'product': item.product.name,
                    'quantity': item.quantity,
                    'selling_price': float(selling_price),
                    'cost': float(cost),
                    'loss_per_unit': float(cost - selling_price),
                    'total_loss': float(loss)
                })
        
        return {
            'period_days': period_days,
            'total_sales': items.count(),
            'risky_sales': len(risky_sales),
            'risk_percentage': (len(risky_sales) / items.count() * 100) if items.count() > 0 else 0,
            'total_potential_loss': float(total_potential_loss),
            'details': risky_sales[:10]  # أول 10 فقط
        }
    
    def get_profit_protection_report(self) -> Dict:
        """تقرير حماية الأرباح"""
        from inventory.models import Product
        from smart_pricing.models import PricingRule
        
        products = Product.objects.all()[:100]  # أول 100 منتج
        
        results = []
        
        for product in products:
            recommended = self.validator.calculate_recommended_price(product)
            current_price = float(product.price)
            
            status = 'ok'
            if current_price < recommended['min_price']:
                status = 'risky'
            elif current_price < recommended['target_price']:
                status = 'warning'
            
            results.append({
                'product': product.name,
                'current_price': current_price,
                'recommended_min': recommended['min_price'],
                'recommended_target': recommended['target_price'],
                'status': status
            })
        
        risky_products = [r for r in results if r['status'] == 'risky']
        warning_products = [r for r in results if r['status'] == 'warning']
        
        return {
            'total_products': len(results),
            'risky_products': len(risky_products),
            'warning_products': len(warning_products),
            'safe_products': len(results) - len(risky_products) - len(warning_products),
            'details': {
                'risky': risky_products[:5],
                'warning': warning_products[:5]
            }
        }


# Singleton instances
price_validator = PriceValidator()
loss_prevention = LossPreventionService()
