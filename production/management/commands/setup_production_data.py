from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from production.models import (
    ProductionSettings, ProductionWorkCenter, BillOfMaterials, BOMItem,
    ProductionStage, BOMStage, ProductionOrder
)
from inventory.models import Product, Location
from hr.models import Employee, Department
from accounting.models import Account, CostCenter


class Command(BaseCommand):
    help = 'إعداد بيانات تجريبية لنظام الإنتاج'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('بدء إعداد بيانات نظام الإنتاج...'))
        
        # إنشاء الحسابات المحاسبية إذا لم تكن موجودة
        self.create_accounts()
        
        # إنشاء مراكز التكلفة
        self.create_cost_centers()
        
        # إنشاء مراكز العمل
        self.create_work_centers()
        
        # إنشاء مراحل الإنتاج
        self.create_production_stages()
        
        # إنشاء منتجات المراتب والمفروشات
        self.create_products()
        
        # إنشاء قوائم المواد
        self.create_boms()
        
        # إنشاء إعدادات الإنتاج
        self.create_production_settings()
        
        # إنشاء أمثلة على أوامر الإنتاج
        self.create_sample_orders()
        
        self.stdout.write(self.style.SUCCESS('تم إعداد بيانات نظام الإنتاج بنجاح!'))

    def create_accounts(self):
        """إنشاء الحسابات المحاسبية"""
        accounts = [
            ('51001', 'الإنتاج تحت التشغيل', 'asset'),
            ('12001', 'البضائع التامة الصنع', 'asset'),
            ('12002', 'المواد الخام', 'asset'),
            ('61001', 'تكلفة العمالة المباشرة', 'expense'),
            ('61002', 'التكاليف الصناعية الإضافية', 'expense'),
        ]
        
        for code, name, account_type in accounts:
            Account.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'account_type': account_type,
                    'can_post': True
                }
            )
        
        self.stdout.write('تم إنشاء الحسابات المحاسبية')

    def create_cost_centers(self):
        """إنشاء مراكز التكلفة"""
        cost_centers = [
            ('PROD-001', 'مركز إنتاج المراتب'),
            ('PROD-002', 'مركز إنتاج الوسائد'),
            ('PROD-003', 'مركز الخياطة'),
            ('PROD-004', 'مركز التعبئة والتغليف'),
        ]
        
        for code, name in cost_centers:
            CostCenter.objects.get_or_create(
                code=code,
                defaults={'name': name, 'is_active': True}
            )
        
        self.stdout.write('تم إنشاء مراكز التكلفة')

    def create_work_centers(self):
        """إنشاء مراكز العمل"""
        # الحصول على قسم افتراضي
        department, created = Department.objects.get_or_create(
            code='PROD',
            defaults={'name': 'قسم الإنتاج', 'is_active': True}
        )
        
        cost_centers = CostCenter.objects.all()
        
        work_centers = [
            {
                'code': 'WC-001',
                'name': 'مركز قطع الإسفنج',
                'work_center_type': 'cutting',
                'hourly_rate': Decimal('25.00'),
                'capacity_per_hour': Decimal('10.0'),
                'efficiency_rate': Decimal('95.0')
            },
            {
                'code': 'WC-002', 
                'name': 'مركز خياطة الأغطية',
                'work_center_type': 'sewing',
                'hourly_rate': Decimal('30.00'),
                'capacity_per_hour': Decimal('8.0'),
                'efficiency_rate': Decimal('90.0')
            },
            {
                'code': 'WC-003',
                'name': 'مركز التجميع والحشو',
                'work_center_type': 'assembly',
                'hourly_rate': Decimal('28.00'),
                'capacity_per_hour': Decimal('6.0'),
                'efficiency_rate': Decimal('88.0')
            },
            {
                'code': 'WC-004',
                'name': 'مركز فحص الجودة',
                'work_center_type': 'quality',
                'hourly_rate': Decimal('35.00'),
                'capacity_per_hour': Decimal('12.0'),
                'efficiency_rate': Decimal('98.0')
            },
            {
                'code': 'WC-005',
                'name': 'مركز التعبئة والتغليف',
                'work_center_type': 'packaging',
                'hourly_rate': Decimal('20.00'),
                'capacity_per_hour': Decimal('15.0'),
                'efficiency_rate': Decimal('95.0')
            }
        ]
        
        for wc_data in work_centers:
            wc_data['department'] = department
            if cost_centers.exists():
                wc_data['cost_center'] = cost_centers.first()
            
            ProductionWorkCenter.objects.get_or_create(
                code=wc_data['code'],
                defaults=wc_data
            )
        
        self.stdout.write('تم إنشاء مراكز العمل')

    def create_production_stages(self):
        """إنشاء مراحل الإنتاج"""
        work_centers = ProductionWorkCenter.objects.all()
        
        if not work_centers.exists():
            return
        
        stages = [
            {
                'code': 'ST-001',
                'name': 'قطع الإسفنج',
                'sequence': 1,
                'operation_time': Decimal('15.0'),  # دقيقة لكل وحدة
                'required_workers': 2,
                'skill_level': 'skilled',
                'work_center': work_centers.filter(work_center_type='cutting').first()
            },
            {
                'code': 'ST-002',
                'name': 'خياطة الغطاء',
                'sequence': 2,
                'operation_time': Decimal('25.0'),
                'required_workers': 1,
                'skill_level': 'expert',
                'work_center': work_centers.filter(work_center_type='sewing').first()
            },
            {
                'code': 'ST-003',
                'name': 'التجميع والحشو',
                'sequence': 3,
                'operation_time': Decimal('20.0'),
                'required_workers': 2,
                'skill_level': 'skilled',
                'work_center': work_centers.filter(work_center_type='assembly').first()
            },
            {
                'code': 'ST-004',
                'name': 'فحص الجودة',
                'sequence': 4,
                'operation_time': Decimal('10.0'),
                'required_workers': 1,
                'skill_level': 'expert',
                'requires_quality_check': True,
                'work_center': work_centers.filter(work_center_type='quality').first()
            },
            {
                'code': 'ST-005',
                'name': 'التعبئة والتغليف',
                'sequence': 5,
                'operation_time': Decimal('8.0'),
                'required_workers': 1,
                'skill_level': 'trainee',
                'work_center': work_centers.filter(work_center_type='packaging').first()
            }
        ]
        
        for stage_data in stages:
            if stage_data['work_center']:
                ProductionStage.objects.get_or_create(
                    code=stage_data['code'],
                    defaults=stage_data
                )
        
        self.stdout.write('تم إنشاء مراحل الإنتاج')

    def create_products(self):
        """إنشاء منتجات المراتب والمفروشات"""
        products = [
            {
                'sku': 'MAT-001',
                'name': 'مرتبة طبية مفردة - 90x190 سم',
                'price': Decimal('800.00'),
                'cost': Decimal('450.00'),
                'min_stock': 10
            },
            {
                'sku': 'MAT-002', 
                'name': 'مرتبة طبية مزدوجة - 150x190 سم',
                'price': Decimal('1200.00'),
                'cost': Decimal('680.00'),
                'min_stock': 5
            },
            {
                'sku': 'PIL-001',
                'name': 'وسادة طبية - 50x70 سم',
                'price': Decimal('120.00'),
                'cost': Decimal('60.00'),
                'min_stock': 50
            },
            {
                'sku': 'COV-001',
                'name': 'غطاء مرتبة قطنية - مفردة',
                'price': Decimal('150.00'),
                'cost': Decimal('75.00'),
                'min_stock': 20
            },
            # مواد خام
            {
                'sku': 'RAW-001',
                'name': 'إسفنج طبي عالي الكثافة - متر مكعب',
                'price': Decimal('200.00'),
                'cost': Decimal('180.00'),
                'min_stock': 100
            },
            {
                'sku': 'RAW-002',
                'name': 'قماش قطني - متر',
                'price': Decimal('25.00'),
                'cost': Decimal('22.00'),
                'min_stock': 500
            },
            {
                'sku': 'RAW-003',
                'name': 'خيوط خياطة - بكرة',
                'price': Decimal('5.00'),
                'cost': Decimal('4.00'),
                'min_stock': 200
            },
            {
                'sku': 'RAW-004',
                'name': 'سحاب - متر',
                'price': Decimal('8.00'),
                'cost': Decimal('6.00'),
                'min_stock': 100
            }
        ]
        
        for product_data in products:
            Product.objects.get_or_create(
                sku=product_data['sku'],
                defaults=product_data
            )
        
        self.stdout.write('تم إنشاء المنتجات والمواد الخام')

    def create_boms(self):
        """إنشاء قوائم المواد"""
        # الحصول على المنتجات والمواد
        mattress_single = Product.objects.filter(sku='MAT-001').first()
        mattress_double = Product.objects.filter(sku='MAT-002').first()
        pillow = Product.objects.filter(sku='PIL-001').first()
        
        foam = Product.objects.filter(sku='RAW-001').first()
        fabric = Product.objects.filter(sku='RAW-002').first()
        thread = Product.objects.filter(sku='RAW-003').first()
        zipper = Product.objects.filter(sku='RAW-004').first()
        
        if not all([mattress_single, foam, fabric, thread]):
            return
        
        # قائمة مواد المرتبة المفردة
        bom_single, created = BillOfMaterials.objects.get_or_create(
            product=mattress_single,
            version='1.0',
            defaults={
                'name': 'قائمة مواد المرتبة الطبية المفردة',
                'base_quantity': Decimal('1.0'),
                'is_active': True,
                'is_default': True
            }
        )
        
        if created:
            # إضافة المواد
            BOMItem.objects.create(
                bom=bom_single,
                material=foam,
                quantity=Decimal('0.15'),  # 0.15 متر مكعب
                unit_cost=foam.cost,
                sequence=1
            )
            BOMItem.objects.create(
                bom=bom_single,
                material=fabric,
                quantity=Decimal('4.5'),   # 4.5 متر قماش
                unit_cost=fabric.cost,
                sequence=2
            )
            BOMItem.objects.create(
                bom=bom_single,
                material=thread,
                quantity=Decimal('0.5'),   # نصف بكرة
                unit_cost=thread.cost,
                sequence=3
            )
            if zipper:
                BOMItem.objects.create(
                    bom=bom_single,
                    material=zipper,
                    quantity=Decimal('2.0'),   # 2 متر سحاب
                    unit_cost=zipper.cost,
                    sequence=4
                )
            
            # إضافة المراحل
            stages = ProductionStage.objects.all()[:5]
            for i, stage in enumerate(stages):
                BOMStage.objects.create(
                    bom=bom_single,
                    stage=stage,
                    sequence=i+1
                )
        
        # قائمة مواد المرتبة المزدوجة
        if mattress_double:
            bom_double, created = BillOfMaterials.objects.get_or_create(
                product=mattress_double,
                version='1.0',
                defaults={
                    'name': 'قائمة مواد المرتبة الطبية المزدوجة',
                    'base_quantity': Decimal('1.0'),
                    'is_active': True,
                    'is_default': True
                }
            )
            
            if created:
                BOMItem.objects.create(
                    bom=bom_double,
                    material=foam,
                    quantity=Decimal('0.25'),  # كمية أكبر للمزدوجة
                    unit_cost=foam.cost,
                    sequence=1
                )
                BOMItem.objects.create(
                    bom=bom_double,
                    material=fabric,
                    quantity=Decimal('7.0'),
                    unit_cost=fabric.cost,
                    sequence=2
                )
                BOMItem.objects.create(
                    bom=bom_double,
                    material=thread,
                    quantity=Decimal('0.8'),
                    unit_cost=thread.cost,
                    sequence=3
                )
                
                # إضافة المراحل
                stages = ProductionStage.objects.all()[:5]
                for i, stage in enumerate(stages):
                    BOMStage.objects.create(
                        bom=bom_double,
                        stage=stage,
                        sequence=i+1
                    )
        
        # قائمة مواد الوسادة
        if pillow:
            bom_pillow, created = BillOfMaterials.objects.get_or_create(
                product=pillow,
                version='1.0',
                defaults={
                    'name': 'قائمة مواد الوسادة الطبية',
                    'base_quantity': Decimal('1.0'),
                    'is_active': True,
                    'is_default': True
                }
            )
            
            if created:
                BOMItem.objects.create(
                    bom=bom_pillow,
                    material=foam,
                    quantity=Decimal('0.025'),  # كمية صغيرة للوسادة
                    unit_cost=foam.cost,
                    sequence=1
                )
                BOMItem.objects.create(
                    bom=bom_pillow,
                    material=fabric,
                    quantity=Decimal('1.2'),
                    unit_cost=fabric.cost,
                    sequence=2
                )
                BOMItem.objects.create(
                    bom=bom_pillow,
                    material=thread,
                    quantity=Decimal('0.1'),
                    unit_cost=thread.cost,
                    sequence=3
                )
        
        self.stdout.write('تم إنشاء قوائم المواد')

    def create_production_settings(self):
        """إنشاء إعدادات الإنتاج"""
        if ProductionSettings.objects.exists():
            return
        
        # الحصول على الحسابات
        wip_account = Account.objects.filter(code='51001').first()
        finished_goods = Account.objects.filter(code='12001').first()
        raw_materials = Account.objects.filter(code='12002').first()
        labor_cost = Account.objects.filter(code='61001').first()
        overhead = Account.objects.filter(code='61002').first()
        
        ProductionSettings.objects.create(
            company_name='مصنع الراحة للمراتب والمفروشات',
            wip_account=wip_account,
            finished_goods_account=finished_goods,
            raw_materials_account=raw_materials,
            labor_cost_account=labor_cost,
            overhead_account=overhead,
            overhead_allocation_method='labor_hours',
            overhead_rate=Decimal('1.25')
        )
        
        self.stdout.write('تم إنشاء إعدادات الإنتاج')

    def create_sample_orders(self):
        """إنشاء أوامر إنتاج تجريبية"""
        # الحصول على المنتجات وقوائم المواد
        mattress_single = Product.objects.filter(sku='MAT-001').first()
        mattress_double = Product.objects.filter(sku='MAT-002').first()
        pillow = Product.objects.filter(sku='PIL-001').first()
        
        if not mattress_single:
            return
        
        bom_single = BillOfMaterials.objects.filter(product=mattress_single).first()
        
        if not bom_single:
            return
        
        # الحصول على مستخدم افتراضي
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
        
        if not user:
            return
        
        today = timezone.now().date()
        
        # أمر إنتاج مكتمل
        order1 = ProductionOrder.objects.create(
            product=mattress_single,
            bom=bom_single,
            planned_quantity=Decimal('20.0'),
            produced_quantity=Decimal('20.0'),
            order_date=today - timedelta(days=10),
            planned_start_date=today - timedelta(days=8),
            planned_end_date=today - timedelta(days=3),
            actual_start_date=today - timedelta(days=8),
            actual_end_date=today - timedelta(days=2),
            status='completed',
            priority='normal',
            created_by=user,
            notes='أمر إنتاج تجريبي مكتمل'
        )
        
        # أمر إنتاج قيد التنفيذ
        order2 = ProductionOrder.objects.create(
            product=mattress_single,
            bom=bom_single,
            planned_quantity=Decimal('15.0'),
            produced_quantity=Decimal('8.0'),
            order_date=today - timedelta(days=5),
            planned_start_date=today - timedelta(days=3),
            planned_end_date=today + timedelta(days=2),
            actual_start_date=today - timedelta(days=3),
            status='in_progress',
            priority='high',
            created_by=user,
            notes='أمر إنتاج قيد التنفيذ'
        )
        
        # أمر إنتاج جديد
        if mattress_double:
            bom_double = BillOfMaterials.objects.filter(product=mattress_double).first()
            if bom_double:
                order3 = ProductionOrder.objects.create(
                    product=mattress_double,
                    bom=bom_double,
                    planned_quantity=Decimal('10.0'),
                    order_date=today,
                    planned_start_date=today + timedelta(days=1),
                    planned_end_date=today + timedelta(days=7),
                    status='confirmed',
                    priority='urgent',
                    created_by=user,
                    notes='طلب عاجل لمراتب مزدوجة'
                )
        
        self.stdout.write('تم إنشاء أوامر الإنتاج التجريبية')