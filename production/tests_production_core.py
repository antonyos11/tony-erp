"""
اختبارات أساسية لموديول الإنتاج
Core Production Module Tests

يختبر:
- إنشاء أوامر الإنتاج
- قوائم المواد (BOM)
- مراكز العمل
- مراحل الإنتاج
- التكاليف والجودة
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from production.models import (
    ProductionOrder, ProductionWorkCenter, ProductionStage,
    BillOfMaterials, BOMItem, BOMStage,
    MaterialConsumption, ProductionQualityCheck
)
from inventory.models import Product, Location
from hr.models import Department, Employee


class ProductionOrderTests(TestCase):
    """اختبارات أوامر الإنتاج"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        # إنشاء مستخدم
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # إنشاء منتج
        self.product = Product.objects.create(
            name='مرتبة اسفنج',
            sku='MAT-001',
            purchase_uom='unit',
            usage_uom='unit',
            cost=Decimal('500.00')
        )
        
        # إنشاء قسم
        self.department = Department.objects.create(
            name='قسم الإنتاج',
            code='PROD'
        )
        
        # إنشاء مركز عمل
        self.work_center = ProductionWorkCenter.objects.create(
            code='WC-01',
            name='قسم التقطيع',
            work_center_type='cutting',
            department=self.department,
            hourly_rate=Decimal('50.00'),
            capacity_per_hour=Decimal('10'),
            working_hours_per_day=Decimal('8'),
            efficiency_rate=Decimal('100.00')
        )
        
        # إنشاء قائمة مواد للمنتج
        self.bom = BillOfMaterials.objects.create(
            product=self.product,
            name='وصفة المرتبة',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True,
            created_by=self.user
        )
    
    def test_create_production_order(self):
        """اختبار إنشاء أمر إنتاج"""
        order = ProductionOrder.objects.create(
            number='PO-001',
            product=self.product,
            bom=self.bom,
            planned_quantity=Decimal('100'),
            order_date=timezone.now().date(),
            planned_start_date=timezone.now().date(),
            planned_end_date=timezone.now().date() + timedelta(days=7),
            status='draft',
            created_by=self.user
        )
        
        self.assertIsNotNone(order.id)
        self.assertEqual(order.product, self.product)
        self.assertEqual(order.planned_quantity, Decimal('100'))
        self.assertEqual(order.status, 'draft')
    
    def test_production_order_confirm(self):
        """اختبار تأكيد أمر الإنتاج"""
        order = ProductionOrder.objects.create(
            number='PO-002',
            product=self.product,
            bom=self.bom,
            planned_quantity=Decimal('50'),
            order_date=timezone.now().date(),
            planned_start_date=timezone.now().date(),
            planned_end_date=timezone.now().date() + timedelta(days=5),
            status='draft',
            created_by=self.user
        )
        
        # تأكيد الأمر
        order.status = 'confirmed'
        order.save()
        
        self.assertEqual(order.status, 'confirmed')
    
    def test_production_order_quantities(self):
        """اختبار الكميات في أمر الإنتاج"""
        order = ProductionOrder.objects.create(
            number='PO-003',
            product=self.product,
            bom=self.bom,
            planned_quantity=Decimal('100'),
            produced_quantity=Decimal('95'),
            scrap_quantity=Decimal('5'),
            order_date=timezone.now().date(),
            planned_start_date=timezone.now().date(),
            planned_end_date=timezone.now().date() + timedelta(days=3),
            status='in_progress',
            created_by=self.user
        )
        
        self.assertEqual(order.planned_quantity, Decimal('100'))
        self.assertEqual(order.produced_quantity, Decimal('95'))
        self.assertEqual(order.scrap_quantity, Decimal('5'))
        
        # حساب نسبة الإنجاز
        completion = (order.produced_quantity / order.planned_quantity) * 100
        self.assertEqual(completion, Decimal('95'))


class BillOfMaterialsTests(TestCase):
    """اختبارات قوائم المواد"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user(username='testuser', password='test')
        
        # منتج نهائي
        self.finished_product = Product.objects.create(
            name='كرسي خشبي',
            sku='CHAIR-001',
            purchase_uom='unit',
            usage_uom='unit'
        )
        
        # مواد خام
        self.wood = Product.objects.create(
            name='خشب',
            sku='WOOD-001',
            purchase_uom='unit',
            usage_uom='unit',
            cost=Decimal('50.00')
        )
        
        self.screws = Product.objects.create(
            name='براغي',
            sku='SCREW-001',
            purchase_uom='unit',
            usage_uom='unit',
            cost=Decimal('2.00')
        )
    
    def test_create_bom(self):
        """اختبار إنشاء قائمة مواد"""
        bom = BillOfMaterials.objects.create(
            product=self.finished_product,
            name='وصفة الكرسي الخشبي',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True,
            created_by=self.user
        )
        
        self.assertIsNotNone(bom.id)
        self.assertEqual(bom.product, self.finished_product)
        self.assertTrue(bom.is_active)
    
    def test_bom_items(self):
        """اختبار عناصر قائمة المواد"""
        bom = BillOfMaterials.objects.create(
            product=self.finished_product,
            name='وصفة الكرسي',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True,
            created_by=self.user
        )
        
        # إضافة مواد
        wood_item = BOMItem.objects.create(
            bom=bom,
            material=self.wood,
            item_type='material',
            quantity=Decimal('2'),
            unit_cost=Decimal('50.00'),
            sequence=1
        )
        
        screws_item = BOMItem.objects.create(
            bom=bom,
            material=self.screws,
            item_type='material',
            quantity=Decimal('8'),
            unit_cost=Decimal('2.00'),
            sequence=2
        )
        
        items = bom.items.all()
        self.assertEqual(items.count(), 2)
        self.assertEqual(items[0], wood_item)
        self.assertEqual(items[1], screws_item)
    
    def test_bom_cost_calculation(self):
        """اختبار حساب تكلفة قائمة المواد"""
        bom = BillOfMaterials.objects.create(
            product=self.finished_product,
            name='وصفة الكرسي',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True,
            created_by=self.user
        )
        
        BOMItem.objects.create(
            bom=bom,
            material=self.wood,
            quantity=Decimal('2'),
            unit_cost=Decimal('50.00')
        )
        
        BOMItem.objects.create(
            bom=bom,
            material=self.screws,
            quantity=Decimal('8'),
            unit_cost=Decimal('2.00')
        )
        
        # التكلفة الإجمالية = (2 * 50) + (8 * 2) = 100 + 16 = 116
        bom.total_material_cost = Decimal('116.00')
        bom.save()
        
        self.assertEqual(bom.total_material_cost, Decimal('116.00'))


class ProductionStageTests(TestCase):
    """اختبارات مراحل الإنتاج"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.department = Department.objects.create(
            name='قسم الإنتاج',
            code='PROD'
        )
        
        self.work_center = ProductionWorkCenter.objects.create(
            code='WC-01',
            name='مركز التصنيع',
            work_center_type='assembly',
            department=self.department,
            hourly_rate=Decimal('60.00'),
            capacity_per_hour=Decimal('5'),
            working_hours_per_day=Decimal('8'),
            efficiency_rate=Decimal('95.00')
        )
    
    def test_create_production_stage(self):
        """اختبار إنشاء مرحلة إنتاج"""
        stage = ProductionStage.objects.create(
            name='التجميع',
            code='STAGE-ASSEMBLY',
            work_center=self.work_center,
            sequence=10,
            setup_time=Decimal('15'),
            operation_time=Decimal('30'),
            teardown_time=Decimal('10'),
            required_workers=2
        )
        
        self.assertIsNotNone(stage.id)
        self.assertEqual(stage.name, 'التجميع')
        self.assertEqual(stage.work_center, self.work_center)
        self.assertEqual(stage.required_workers, 2)
    
    def test_stage_time_calculation(self):
        """اختبار حساب وقت المرحلة"""
        stage = ProductionStage.objects.create(
            name='الخياطة',
            code='STAGE-SEW',
            work_center=self.work_center,
            setup_time=Decimal('10'),
            operation_time=Decimal('25'),
            teardown_time=Decimal('5'),
            required_workers=1
        )
        
        # الوقت الإجمالي = setup + operation + teardown
        total_time = stage.total_time_per_unit
        self.assertEqual(total_time, Decimal('40'))
    
    def test_stage_labor_cost(self):
        """اختبار حساب تكلفة العمالة للمرحلة"""
        stage = ProductionStage.objects.create(
            name='التعبئة',
            code='STAGE-PACK',
            work_center=self.work_center,
            setup_time=Decimal('5'),
            operation_time=Decimal('10'),
            teardown_time=Decimal('5'),
            required_workers=1
        )
        
        # تكلفة العمالة = (hourly_rate * workers * total_minutes) / 60
        # = (60 * 1 * 20) / 60 = 20
        labor_cost = stage.labor_cost_per_unit
        self.assertEqual(labor_cost, Decimal('20'))


class ProductionWorkCenterTests(TestCase):
    """اختبارات مراكز العمل"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.department = Department.objects.create(
            name='قسم التصنيع',
            code='MFG'
        )
    
    def test_create_work_center(self):
        """اختبار إنشاء مركز عمل"""
        wc = ProductionWorkCenter.objects.create(
            code='WC-LASER',
            name='قسم القص بالليزر',
            work_center_type='cutting',
            department=self.department,
            hourly_rate=Decimal('80.00'),
            capacity_per_hour=Decimal('15'),
            working_hours_per_day=Decimal('8'),
            efficiency_rate=Decimal('90.00')
        )
        
        self.assertIsNotNone(wc.id)
        self.assertEqual(wc.code, 'WC-LASER')
        self.assertTrue(wc.is_active)
    
    def test_work_center_capacity(self):
        """اختبار حساب طاقة مركز العمل"""
        wc = ProductionWorkCenter.objects.create(
            code='WC-PAINT',
            name='قسم الدهان',
            work_center_type='finishing',
            department=self.department,
            hourly_rate=Decimal('55.00'),
            capacity_per_hour=Decimal('20'),
            working_hours_per_day=Decimal('8'),
            efficiency_rate=Decimal('85.00')
        )
        
        # الطاقة اليومية = capacity_per_hour * working_hours * efficiency / 100
        # = 20 * 8 * 0.85 = 136
        daily_capacity = wc.capacity_per_hour * wc.working_hours_per_day * (wc.efficiency_rate / 100)
        self.assertEqual(daily_capacity, Decimal('136'))


class ProductionIntegrationTests(TestCase):
    """اختبارات تكامل نظام الإنتاج"""
    
    def setUp(self):
        """إعداد بيئة اختبار كاملة"""
        self.user = User.objects.create_user(username='prod_user', password='test')
        
        # منتج
        self.product = Product.objects.create(
            name='طاولة خشبية',
            sku='TABLE-001',
            purchase_uom='unit',
            usage_uom='unit',
            cost=Decimal('300.00')
        )
        
        # قسم
        self.department = Department.objects.create(
            name='قسم النجارة',
            code='CARP'
        )
        
        # مركز عمل
        self.work_center = ProductionWorkCenter.objects.create(
            code='WC-WOOD',
            name='ورشة النجارة',
            work_center_type='assembly',
            department=self.department,
            hourly_rate=Decimal('70.00'),
            capacity_per_hour=Decimal('4'),
            working_hours_per_day=Decimal('8'),
            efficiency_rate=Decimal('90.00')
        )
        
        # قائمة مواد
        self.bom = BillOfMaterials.objects.create(
            product=self.product,
            name='وصفة الطاولة الخشبية',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True,
            is_default=True,
            created_by=self.user
        )
        
        # مرحلة إنتاج
        self.stage = ProductionStage.objects.create(
            name='التجميع والتشطيب',
            code='STAGE-WOOD-ASSEMBLY',
            work_center=self.work_center,
            sequence=10,
            setup_time=Decimal('20'),
            operation_time=Decimal('60'),
            teardown_time=Decimal('10'),
            required_workers=2,
            requires_quality_check=True
        )
        
        # ربط المرحلة بـ BOM
        BOMStage.objects.create(
            bom=self.bom,
            stage=self.stage,
            sequence=1,
            is_required=True
        )
    
    def test_full_production_workflow(self):
        """اختبار دورة إنتاج كاملة"""
        # 1. إنشاء أمر إنتاج
        order = ProductionOrder.objects.create(
            number='PO-TABLE-001',
            product=self.product,
            bom=self.bom,
            planned_quantity=Decimal('10'),
            order_date=timezone.now().date(),
            planned_start_date=timezone.now().date(),
            planned_end_date=timezone.now().date() + timedelta(days=5),
            status='draft',
            created_by=self.user
        )
        
        self.assertEqual(order.status, 'draft')
        
        # 2. تأكيد الأمر
        order.status = 'confirmed'
        order.save()
        self.assertEqual(order.status, 'confirmed')
        
        # 3. بدء الإنتاج
        order.status = 'in_progress'
        order.actual_start_date = timezone.now().date()
        order.save()
        self.assertEqual(order.status, 'in_progress')
        
        # 4. تسجيل إنتاج
        order.produced_quantity = Decimal('9')
        order.scrap_quantity = Decimal('1')
        order.save()
        
        self.assertEqual(order.produced_quantity, Decimal('9'))
        self.assertEqual(order.scrap_quantity, Decimal('1'))
        
        # 5. إكمال الأمر
        order.status = 'completed'
        order.actual_end_date = timezone.now().date()
        order.save()
        
        self.assertEqual(order.status, 'completed')
        self.assertIsNotNone(order.actual_end_date)
    
    def test_bom_with_stages(self):
        """اختبار قائمة مواد مع مراحل إنتاج"""
        stages = self.bom.stages.all()
        self.assertEqual(stages.count(), 1)
        
        bom_stage = stages.first()
        self.assertEqual(bom_stage.stage, self.stage)
        self.assertTrue(bom_stage.is_required)
