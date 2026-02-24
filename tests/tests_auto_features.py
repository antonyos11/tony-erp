"""
اختبارات الميزات التلقائية الجديدة
Automated Features Tests
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from inventory.models import Product, Location, Stock
from showrooms.models import Showroom, ShowroomPricingRule
from showrooms.services.pricing_service import ShowroomPricingService
from production.services.auto_order_service import AutoProductionOrderService
from production.models import BillOfMaterials, ProductionOrder

User = get_user_model()


class ShowroomPricingTests(TestCase):
    """اختبارات نظام التسعير المرن"""
    
    def setUp(self):
        """إعداد البيانات الأساسية"""
        self.user = User.objects.create_user('testuser', password='test123')
        self.location = Location.objects.create(name='Test Location', code='LOC01')
        self.showroom = Showroom.objects.create(
            code='SH01',
            name='Test Showroom',
            location=self.location
        )
        self.product = Product.objects.create(
            name='Test Product',
            sku='PROD001',
            price=Decimal('1000.00'),
            cost=Decimal('600.00')
        )
    
    def test_fixed_price_rule(self):
        """اختبار قاعدة السعر الثابت"""
        rule = ShowroomPricingRule.objects.create(
            showroom=self.showroom,
            product=self.product,
            adjustment_type='fixed',
            value=Decimal('900.00'),
            effective_from=date.today(),
            is_active=True
        )
        
        price_info = ShowroomPricingService.get_product_price(
            self.product, self.showroom
        )
        
        self.assertEqual(price_info['final_price'], Decimal('900.00'))
        self.assertTrue(price_info['has_special_price'])
    
    def test_percentage_discount(self):
        """اختبار خصم النسبة المئوية"""
        # خصم 10% = 90% من السعر
        ShowroomPricingRule.objects.create(
            showroom=self.showroom,
            product=self.product,
            adjustment_type='percentage',
            value=Decimal('90.00'),  # 90%
            effective_from=date.today(),
            is_active=True
        )
        
        price_info = ShowroomPricingService.get_product_price(
            self.product, self.showroom
        )
        
        expected = Decimal('1000.00') * Decimal('0.90')
        self.assertEqual(price_info['final_price'], expected)
    
    def test_no_rule_uses_base_price(self):
        """اختبار استخدام السعر الأساسي عند عدم وجود قاعدة"""
        price_info = ShowroomPricingService.get_product_price(
            self.product, self.showroom
        )
        
        self.assertEqual(price_info['final_price'], self.product.price)
        self.assertFalse(price_info['has_special_price'])
    
    def test_expired_rule_not_applied(self):
        """اختبار عدم تطبيق القاعدة المنتهية"""
        ShowroomPricingRule.objects.create(
            showroom=self.showroom,
            product=self.product,
            adjustment_type='fixed',
            value=Decimal('800.00'),
            effective_from=date.today() - timedelta(days=10),
            effective_to=date.today() - timedelta(days=1),  # منتهية
            is_active=True
        )
        
        price_info = ShowroomPricingService.get_product_price(
            self.product, self.showroom
        )
        
        # يجب استخدام السعر الأساسي
        self.assertEqual(price_info['final_price'], self.product.price)


class AutoProductionOrderTests(TestCase):
    """اختبارات نظام الإنتاج التلقائي"""
    
    def setUp(self):
        """إعداد البيانات"""
        self.user = User.objects.create_user('testuser', password='test123')
        self.location = Location.objects.create(name='Factory', code='FAC01')
        self.showroom = Showroom.objects.create(
            code='SH01',
            name='Test Showroom',
            location=self.location
        )
        self.product = Product.objects.create(
            name='Manufactured Product',
            sku='MFG001',
            price=Decimal('2000.00'),
            cost=Decimal('1200.00')
        )
        
        # إنشاء BOM للمنتج
        self.bom = BillOfMaterials.objects.create(
            product=self.product,
            name='Test BOM',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True
        )
    
    def test_check_stock_availability_sufficient(self):
        """اختبار المخزون الكافي"""
        # إضافة مخزون
        Stock.objects.create(
            product=self.product,
            location=self.location,
            quantity=100
        )
        
        stock_info = AutoProductionOrderService.check_stock_availability(
            self.product, self.location, 50
        )
        
        self.assertEqual(stock_info['available'], 100)
        self.assertFalse(stock_info['needs_production'])
    
    def test_check_stock_availability_shortage(self):
        """اختبار نقص المخزون"""
        # مخزون قليل
        Stock.objects.create(
            product=self.product,
            location=self.location,
            quantity=5
        )
        
        stock_info = AutoProductionOrderService.check_stock_availability(
            self.product, self.location, 50
        )
        
        self.assertEqual(stock_info['shortage'], 45)
        self.assertTrue(stock_info['needs_production'])
    
    def test_create_production_order(self):
        """اختبار إنشاء أمر إنتاج"""
        order = AutoProductionOrderService.create_production_order(
            product=self.product,
            quantity=20,
            showroom=self.showroom,
            reference='TEST-001',
            user=self.user
        )
        
        self.assertIsNotNone(order)
        self.assertEqual(order.product, self.product)
        self.assertEqual(order.planned_quantity, 20)
        self.assertEqual(order.bom, self.bom)
        self.assertIn('TEST-001', order.notes)
    
    def test_auto_order_creation_with_shortage(self):
        """اختبار الإنشاء التلقائي عند النقص"""
        # لا مخزون
        result = AutoProductionOrderService.check_and_create_order(
            product=self.product,
            quantity=10,
            showroom=self.showroom,
            location=self.location,
            user=self.user
        )
        
        self.assertTrue(result['needs_production'])
        self.assertTrue(result['order_created'])
        self.assertIsNotNone(result['production_order'])
        
        # التحقق من إنشاء الأمر في قاعدة البيانات
        orders = ProductionOrder.objects.filter(product=self.product)
        self.assertEqual(orders.count(), 1)


class MessagingServiceTests(TestCase):
    """اختبارات نظام الرسائل"""
    
    def test_message_template_formatting(self):
        """اختبار تنسيق قوالب الرسائل"""
        from notifications.messaging_service import MessageTemplates
        
        message = MessageTemplates.format_message(
            'order_confirmed',
            {
                'customer_name': 'أحمد محمد',
                'order_number': 'POS-2026-001',
                'total': 1500.50
            }
        )
        
        self.assertIsNotNone(message)
        self.assertIn('أحمد محمد', message)
        self.assertIn('POS-2026-001', message)
        self.assertIn('1500.5', message)
    
    def test_message_service_disabled_by_default(self):
        """اختبار أن الخدمة معطلة افتراضياً"""
        from notifications.messaging_service import AutoMessagingService
        
        # بدون إعدادات - يجب أن تكون معطلة
        enabled = AutoMessagingService.is_enabled('sms')
        self.assertFalse(enabled)


class IntegrationTests(TestCase):
    """اختبارات التكامل بين الأنظمة"""
    
    def setUp(self):
        """إعداد البيئة الكاملة"""
        self.user = User.objects.create_user('testuser', password='test123')
        self.location = Location.objects.create(name='Factory', code='FAC01')
        self.showroom = Showroom.objects.create(
            code='SH01',
            name='Cairo Showroom',
            location=self.location
        )
        self.product = Product.objects.create(
            name='Premium Mattress',
            sku='MAT001',
            price=Decimal('5000.00'),
            cost=Decimal('3000.00')
        )
        
        # BOM
        self.bom = BillOfMaterials.objects.create(
            product=self.product,
            name='Mattress BOM',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True
        )
    
    def test_pricing_and_production_flow(self):
        """اختبار التدفق الكامل: تسعير + إنتاج"""
        # 1. إنشاء قاعدة تسعير
        ShowroomPricingRule.objects.create(
            showroom=self.showroom,
            product=self.product,
            adjustment_type='percentage',
            value=Decimal('95'),  # خصم 5%
            effective_from=date.today(),
            is_active=True
        )
        
        # 2. الحصول على السعر
        price_info = ShowroomPricingService.get_product_price(
            self.product, self.showroom
        )
        expected_price = Decimal('5000.00') * Decimal('0.95')
        self.assertEqual(price_info['final_price'], expected_price)
        
        # 3. محاكاة بيع (مخزون قليل)
        Stock.objects.create(
            product=self.product,
            location=self.location,
            quantity=2
        )
        
        # 4. طلب 10 قطع (سيُنشئ أمر تصنيع)
        result = AutoProductionOrderService.check_and_create_order(
            product=self.product,
            quantity=10,
            showroom=self.showroom,
            location=self.location,
            user=self.user
        )
        
        self.assertTrue(result['order_created'])
        self.assertGreater(result['production_quantity'], 8)  # مع الأمان


# تشغيل الاختبارات:
# python3 manage.py test pos.tests_auto_features -v 2
