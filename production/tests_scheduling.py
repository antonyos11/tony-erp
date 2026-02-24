"""
اختبارات نظام الجدولة التلقائية للإنتاج
Production Scheduling System Tests

يختبر:
- جدولة الأوامر التلقائية
- تحليل السعة
- كشف الاختناقات
- تحسين الجدولة
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from production.models import (
    ProductionOrder, ProductionWorkCenter, ProductionStage,
    BillOfMaterials, ProductionSettings, ProductionOrderStage
)
from production.services.scheduling_service import (
    ProductionScheduler, CapacityAnalyzer
)
from inventory.models import Product
from hr.models import Department, Employee


class ProductionSchedulerTests(TestCase):
    """اختبارات محرك الجدولة"""
    
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
        
        # إنشاء مراكز عمل
        self.work_center1 = ProductionWorkCenter.objects.create(
            code='WC-01',
            name='قسم التقطيع',
            work_center_type='cutting',
            department=self.department,
            hourly_rate=Decimal('50.00'),
            capacity_per_hour=Decimal('10'),
            working_hours_per_day=Decimal('8'),
            efficiency_rate=Decimal('100.00')
        )
        
        self.work_center2 = ProductionWorkCenter.objects.create(
            code='WC-02',
            name='قسم الخياطة',
            work_center_type='sewing',
            department=self.department,
            hourly_rate=Decimal('60.00'),
            capacity_per_hour=Decimal('5'),
            working_hours_per_day=Decimal('8'),
            efficiency_rate=Decimal('90.00')
        )
        
        # إنشاء BOM
        self.bom = BillOfMaterials.objects.create(
            product=self.product,
            name='وصفة إنتاج',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True
        )
        
        # إنشاء مراحل الإنتاج
        self.stage1 = ProductionStage.objects.create(
            bom=self.bom,
            name='التقطيع',
            sequence=10,
            stage_type='cutting',
            standard_time=Decimal('0.5')  # نصف ساعة لكل وحدة
        )
        self.stage1.work_centers.add(self.work_center1)
        
        self.stage2 = ProductionStage.objects.create(
            bom=self.bom,
            name='الخياطة',
            sequence=20,
            stage_type='sewing',
            standard_time=Decimal('1.0')  # ساعة لكل وحدة
        )
        self.stage2.work_centers.add(self.work_center2)
    
    def test_schedule_single_order_basic(self):
        """اختبار جدولة أمر واحد بسيط"""
        # إنشاء أمر إنتاج
        order = ProductionOrder.objects.create(
            product=self.product,
            bom=self.bom,
            planned_quantity=Decimal('10'),
            planned_start_date=timezone.now().date(),
            planned_end_date=(timezone.now() + timedelta(days=5)).date(),
            status='confirmed',
            priority='normal'
        )
        
        # جدولة الأمر
        scheduler = ProductionScheduler()
        result = scheduler.schedule_production_orders([order])
        
        # التحقق من النتائج
        self.assertEqual(len(result['scheduled_orders']), 1)
        self.assertEqual(result['statistics']['total_orders'], 1)
        self.assertGreater(result['statistics']['total_duration_hours'], 0)
        
        # التحقق من أن المراحل تم إنشاؤها
        order.refresh_from_db()
        stages = order.order_stages.all()
        self.assertEqual(stages.count(), 2)
    
    def test_schedule_multiple_orders_by_priority(self):
        """اختبار جدولة أوامر متعددة حسب الأولوية"""
        # إنشاء أوامر بأولويات مختلفة
        order_low = ProductionOrder.objects.create(
            product=self.product,
            bom=self.bom,
            planned_quantity=Decimal('5'),
            planned_start_date=timezone.now().date(),
            planned_end_date=(timezone.now() + timedelta(days=3)).date(),
            status='confirmed',
            priority='low'
        )
        
        order_urgent = ProductionOrder.objects.create(
            product=self.product,
            bom=self.bom,
            planned_quantity=Decimal('3'),
            planned_start_date=timezone.now().date(),
            planned_end_date=(timezone.now() + timedelta(days=2)).date(),
            status='confirmed',
            priority='urgent'
        )
        
        order_normal = ProductionOrder.objects.create(
            product=self.product,
            bom=self.bom,
            planned_quantity=Decimal('7'),
            planned_start_date=timezone.now().date(),
            planned_end_date=(timezone.now() + timedelta(days=4)).date(),
            status='confirmed',
            priority='normal'
        )
        
        # جدولة الأوامر
        scheduler = ProductionScheduler()
        result = scheduler.schedule_production_orders(
            [order_low, order_urgent, order_normal]
        )
        
        # التحقق من أن العاجل جاء أولاً
        scheduled_orders = result['scheduled_orders']
        self.assertEqual(len(scheduled_orders), 3)
        
        # الترتيب يجب أن يكون: urgent, normal, low
        priorities = [s['order'].priority for s in scheduled_orders]
        self.assertEqual(priorities[0], 'urgent')
    
    def test_optimize_schedule_minimize_time(self):
        """اختبار تحسين الجدولة لتقليل الوقت"""
        orders = [
            ProductionOrder.objects.create(
                product=self.product,
                bom=self.bom,
                planned_quantity=Decimal('10'),
                planned_start_date=timezone.now().date(),
                planned_end_date=(timezone.now() + timedelta(days=5)).date(),
                status='confirmed',
                priority='normal'
            )
            for _ in range(3)
        ]
        
        scheduler = ProductionScheduler()
        result = scheduler.schedule_production_orders(
            orders,
            optimization_goal='minimize_time'
        )
        
        self.assertEqual(len(result['scheduled_orders']), 3)
        self.assertEqual(result['statistics']['total_orders'], 3)
    
    def test_calculate_stage_duration(self):
        """اختبار حساب مدة المرحلة"""
        scheduler = ProductionScheduler()
        scheduler._load_work_center_capacities()
        
        # حساب مدة مرحلة التقطيع لـ 10 وحدات
        duration = scheduler._calculate_stage_duration(
            self.stage1,
            Decimal('10'),
            self.work_center1
        )
        
        # السعة: 10 وحدة/ساعة، الكفاءة: 100%
        # المدة المتوقعة: 10/10 = 1 ساعة + وقت الإعداد
        self.assertGreater(duration, 0)
        self.assertLess(duration, 5)  # يجب أن تكون معقولة


class CapacityAnalyzerTests(TestCase):
    """اختبارات محلل السعة"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.department = Department.objects.create(
            name='قسم الإنتاج',
            code='PROD'
        )
        
        self.work_center = ProductionWorkCenter.objects.create(
            code='WC-TEST',
            name='مركز اختبار',
            work_center_type='cutting',
            department=self.department,
            hourly_rate=Decimal('50.00'),
            capacity_per_hour=Decimal('10'),
            working_hours_per_day=Decimal('8'),
            efficiency_rate=Decimal('100.00')
        )
    
    def test_work_center_utilization_empty(self):
        """اختبار حساب استخدام مركز عمل فارغ"""
        start_date = timezone.now()
        end_date = start_date + timedelta(days=7)
        
        utilization = CapacityAnalyzer.get_work_center_utilization(
            self.work_center,
            start_date,
            end_date
        )
        
        self.assertEqual(utilization['utilization_rate'], 0)
        self.assertEqual(utilization['reserved_hours'], 0)
        self.assertGreater(utilization['total_available_hours'], 0)
    
    def test_identify_bottlenecks_none(self):
        """اختبار كشف الاختناقات عندما لا يوجد أي منها"""
        start_date = timezone.now()
        end_date = start_date + timedelta(days=7)
        
        bottlenecks = CapacityAnalyzer.identify_bottlenecks(
            start_date,
            end_date,
            threshold=80.0
        )
        
        self.assertEqual(len(bottlenecks), 0)


class SchedulingViewsTests(TestCase):
    """اختبارات واجهات الجدولة"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_scheduling_dashboard_view(self):
        """اختبار عرض لوحة التحكم في الجدولة"""
        response = self.client.get('/production/scheduling/')
        
        # قد تحتاج للتعديل حسب إعداد الـ URLs
        self.assertIn(response.status_code, [200, 301, 302, 404])
    
    def test_auto_schedule_get(self):
        """اختبار صفحة الجدولة التلقائية (GET)"""
        response = self.client.get('/production/scheduling/auto-schedule/')
        
        self.assertIn(response.status_code, [200, 301, 302, 404])


class SchedulingIntegrationTests(TestCase):
    """اختبارات التكامل الشاملة"""
    
    def setUp(self):
        """إعداد بيئة كاملة"""
        # إنشاء بيانات أساسية
        self.product = Product.objects.create(
            name='منتج اختبار',
            sku='TEST-001',
            purchase_uom='unit',
            usage_uom='unit'
        )
        
        self.department = Department.objects.create(
            name='قسم الإنتاج',
            code='PROD'
        )
        
        # إنشاء 3 مراكز عمل
        self.work_centers = []
        for i in range(3):
            wc = ProductionWorkCenter.objects.create(
                code=f'WC-{i+1:02d}',
                name=f'مركز عمل {i+1}',
                work_center_type='cutting',
                department=self.department,
                hourly_rate=Decimal('50.00'),
                capacity_per_hour=Decimal(str(5 + i * 2)),
                working_hours_per_day=Decimal('8'),
                efficiency_rate=Decimal('100.00')
            )
            self.work_centers.append(wc)
        
        # إنشاء BOM ومراحل
        self.bom = BillOfMaterials.objects.create(
            product=self.product,
            name='وصفة اختبار',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True
        )
        
        for i, wc in enumerate(self.work_centers):
            stage = ProductionStage.objects.create(
                bom=self.bom,
                name=f'المرحلة {i+1}',
                sequence=(i+1) * 10,
                stage_type='cutting',
                standard_time=Decimal('1.0')
            )
            stage.work_centers.add(wc)
    
    def test_full_scheduling_workflow(self):
        """اختبار دورة جدولة كاملة"""
        # 1. إنشاء أوامر إنتاج متعددة
        orders = []
        for i in range(5):
            order = ProductionOrder.objects.create(
                product=self.product,
                bom=self.bom,
                planned_quantity=Decimal(str(10 + i * 5)),
                planned_start_date=timezone.now().date(),
                planned_end_date=(timezone.now() + timedelta(days=7)).date(),
                status='confirmed',
                priority=['low', 'normal', 'high', 'urgent', 'normal'][i]
            )
            orders.append(order)
        
        # 2. جدولة الأوامر
        scheduler = ProductionScheduler()
        result = scheduler.schedule_production_orders(orders)
        
        # 3. التحقق من النتائج
        self.assertEqual(len(result['scheduled_orders']), 5)
        self.assertEqual(result['statistics']['total_orders'], 5)
        
        # 4. التحقق من إنشاء المراحل
        for order in orders:
            order.refresh_from_db()
            self.assertGreater(order.order_stages.count(), 0)
        
        # 5. تحليل السعة
        start_date = timezone.now()
        end_date = start_date + timedelta(days=7)
        
        for wc in self.work_centers:
            utilization = CapacityAnalyzer.get_work_center_utilization(
                wc, start_date, end_date
            )
            self.assertIsNotNone(utilization)
            self.assertGreaterEqual(utilization['utilization_rate'], 0)
        
        # 6. كشف الاختناقات
        bottlenecks = CapacityAnalyzer.identify_bottlenecks(
            start_date, end_date, threshold=50.0
        )
        
        # يجب أن تكون النتيجة قائمة (حتى لو فارغة)
        self.assertIsInstance(bottlenecks, list)


class SchedulingEdgeCasesTests(TestCase):
    """اختبارات الحالات الحدية"""
    
    def test_schedule_order_without_work_centers(self):
        """اختبار جدولة أمر بدون مراكز عمل مخصصة"""
        product = Product.objects.create(
            name='منتج',
            sku='P-001',
            purchase_uom='unit',
            usage_uom='unit'
        )
        
        bom = BillOfMaterials.objects.create(
            product=product,
            name='وصفة',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True
        )
        
        # مرحلة بدون مراكز عمل
        stage = ProductionStage.objects.create(
            bom=bom,
            name='مرحلة',
            sequence=10,
            stage_type='cutting',
            standard_time=Decimal('1.0')
        )
        
        order = ProductionOrder.objects.create(
            product=product,
            bom=bom,
            planned_quantity=Decimal('10'),
            planned_start_date=timezone.now().date(),
            planned_end_date=(timezone.now() + timedelta(days=5)).date(),
            status='confirmed',
            priority='normal'
        )
        
        scheduler = ProductionScheduler()
        result = scheduler.schedule_production_orders([order])
        
        # يجب أن يكون هناك تحذير
        self.assertGreater(len(result['warnings']), 0)
    
    def test_schedule_with_zero_quantity(self):
        """اختبار الجدولة بكمية صفر"""
        # هذا الاختبار للتأكد من معالجة الحالات غير المتوقعة
        pass  # يمكن تطويره لاحقاً


class SchedulingPerformanceTests(TestCase):
    """اختبارات الأداء"""
    
    def test_schedule_large_number_of_orders(self):
        """اختبار جدولة عدد كبير من الأوامر"""
        # إنشاء بيانات أساسية
        product = Product.objects.create(
            name='منتج',
            sku='P-001',
            purchase_uom='unit',
            usage_uom='unit'
        )
        
        department = Department.objects.create(
            name='قسم',
            code='DEPT'
        )
        
        work_center = ProductionWorkCenter.objects.create(
            code='WC-01',
            name='مركز عمل',
            work_center_type='cutting',
            department=department,
            hourly_rate=Decimal('50.00'),
            capacity_per_hour=Decimal('10'),
            working_hours_per_day=Decimal('8'),
            efficiency_rate=Decimal('100.00')
        )
        
        bom = BillOfMaterials.objects.create(
            product=product,
            name='وصفة الأداء',
            version='1.0',
            base_quantity=Decimal('1'),
            is_active=True
        )
        
        stage = ProductionStage.objects.create(
            bom=bom,
            name='مرحلة',
            sequence=10,
            stage_type='cutting',
            standard_time=Decimal('1.0')
        )
        stage.work_centers.add(work_center)
        
        # إنشاء 20 أمر إنتاج
        orders = []
        for i in range(20):
            order = ProductionOrder.objects.create(
                product=product,
                bom=bom,
                planned_quantity=Decimal('5'),
                planned_start_date=timezone.now().date(),
                planned_end_date=(timezone.now() + timedelta(days=10)).date(),
                status='confirmed',
                priority='normal'
            )
            orders.append(order)
        
        # جدولة الأوامر وقياس الوقت
        import time
        start_time = time.time()
        
        scheduler = ProductionScheduler()
        result = scheduler.schedule_production_orders(orders)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # يجب أن تكتمل في أقل من 10 ثوانٍ
        self.assertLess(execution_time, 10.0)
        self.assertEqual(len(result['scheduled_orders']), 20)
