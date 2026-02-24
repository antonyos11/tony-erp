"""
سكريبت إنشاء بيانات تجريبية لمصنع المراتب والمفروشات
يشمل: المخازن، المنتجات، قوائم المواد (BOM)، مراكز العمل، مراحل الإنتاج

الاستخدام:
    python manage.py shell < setup_mattress_factory.py
    أو
    python manage.py shell
    >>> exec(open('setup_mattress_factory.py').read())
"""

from django.db import transaction
from decimal import Decimal

# =============================================
# 1. إنشاء المخازن (Locations/Warehouses)
# =============================================
def create_warehouses():
    from inventory.models import Location
    
    warehouses = [
        # مخازن المواد الخام
        {'name': 'مخزن الأقمشة', 'code': 'WH-FAB', 'type': 'raw', 'address': 'المنطقة الصناعية - مبنى 1'},
        {'name': 'مخزن الإسفنج', 'code': 'WH-FOAM', 'type': 'raw', 'address': 'المنطقة الصناعية - مبنى 2'},
        {'name': 'مخزن السوست والمعادن', 'code': 'WH-SPR', 'type': 'raw', 'address': 'المنطقة الصناعية - مبنى 3'},
        {'name': 'مخزن الأخشاب', 'code': 'WH-WOOD', 'type': 'raw', 'address': 'المنطقة الصناعية - مبنى 4'},
        
        # مخازن نصف مصنع
        {'name': 'مخزن الأغطية المخيطة', 'code': 'WH-COV', 'type': 'wip', 'address': 'خط الإنتاج - منطقة 1'},
        {'name': 'مخزن الإطارات الجاهزة', 'code': 'WH-FRM', 'type': 'wip', 'address': 'خط الإنتاج - منطقة 2'},
        {'name': 'مخزن الحشوات الجاهزة', 'code': 'WH-PAD', 'type': 'wip', 'address': 'خط الإنتاج - منطقة 3'},
        
        # مخازن المنتج التام
        {'name': 'مخزن المراتب التامة', 'code': 'WH-MAT-FIN', 'type': 'finished', 'address': 'منطقة التخزين الرئيسية', 'is_default': True},
        {'name': 'مخزن الوسائد التامة', 'code': 'WH-PIL-FIN', 'type': 'finished', 'address': 'منطقة التخزين - قسم الوسائد'},
        {'name': 'مخزن المفروشات التامة', 'code': 'WH-BED-FIN', 'type': 'finished', 'address': 'منطقة التخزين - قسم المفروشات'},
        
        # المعارض
        {'name': 'المعرض الرئيسي', 'code': 'SH-MAIN', 'type': 'store', 'address': 'شارع التحرير - المبنى الرئيسي'},
        {'name': 'معرض المدينة الجديدة', 'code': 'SH-NEW', 'type': 'store', 'address': 'المدينة الجديدة - المول التجاري'},
        
        # قطع غيار
        {'name': 'مخزن قطع الغيار', 'code': 'WH-SPARE', 'type': 'spare', 'address': 'المنطقة الصناعية - مبنى الصيانة'},
    ]
    
    created_count = 0
    for wh in warehouses:
        obj, created = Location.objects.update_or_create(
            code=wh['code'],
            defaults=wh
        )
        if created:
            created_count += 1
            print(f"✅ تم إنشاء: {wh['name']}")
        else:
            print(f"🔄 موجود مسبقاً: {wh['name']}")
    
    print(f"\n📦 إجمالي المخازن: {Location.objects.count()} | جديد: {created_count}")
    return Location.objects.all()


# =============================================
# 2. إنشاء فئات المنتجات
# =============================================
def create_categories():
    from inventory.models import Category
    
    categories = [
        {'name': 'مواد خام', 'description': 'المواد الخام الأساسية للتصنيع'},
        {'name': 'أقمشة', 'description': 'أقمشة المراتب والمفروشات', 'parent_name': 'مواد خام'},
        {'name': 'إسفنج', 'description': 'أنواع الإسفنج المختلفة', 'parent_name': 'مواد خام'},
        {'name': 'سوست ومعادن', 'description': 'السوست والإطارات المعدنية', 'parent_name': 'مواد خام'},
        {'name': 'أخشاب', 'description': 'الأخشاب والألواح', 'parent_name': 'مواد خام'},
        {'name': 'مستهلكات', 'description': 'خيوط، غراء، مواد تغليف', 'parent_name': 'مواد خام'},
        
        {'name': 'نصف مصنع', 'description': 'المنتجات تحت التشغيل'},
        {'name': 'أغطية مخيطة', 'description': 'أغطية المراتب الجاهزة للحشو', 'parent_name': 'نصف مصنع'},
        {'name': 'إطارات جاهزة', 'description': 'إطارات السوست الجاهزة', 'parent_name': 'نصف مصنع'},
        
        {'name': 'منتج تام', 'description': 'المنتجات النهائية'},
        {'name': 'مراتب', 'description': 'جميع أنواع المراتب', 'parent_name': 'منتج تام'},
        {'name': 'وسائد', 'description': 'جميع أنواع الوسائد', 'parent_name': 'منتج تام'},
        {'name': 'مفروشات', 'description': 'ملايات، لحف، بطاطين', 'parent_name': 'منتج تام'},
    ]
    
    created_count = 0
    for cat in categories:
        parent = None
        if 'parent_name' in cat:
            parent = Category.objects.filter(name=cat['parent_name']).first()
        
        obj, created = Category.objects.update_or_create(
            name=cat['name'],
            defaults={
                'description': cat.get('description', ''),
                'parent': parent,
            }
        )
        if created:
            created_count += 1
            print(f"✅ تم إنشاء فئة: {cat['name']}")
    
    print(f"\n📁 إجمالي الفئات: {Category.objects.count()} | جديد: {created_count}")
    return Category.objects.all()


# =============================================
# 3. إنشاء المنتجات (خامات، نصف مصنع، تام)
# =============================================
def create_products():
    from inventory.models import Product, Category
    
    products = [
        # ========== مواد خام ==========
        # أقمشة
        {'sku': 'FAB-COT-001', 'name': 'قماش قطني أبيض', 'product_type': 'raw_material', 'category': 'أقمشة', 
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('25.00'), 'min_stock': 500},
        {'sku': 'FAB-POL-001', 'name': 'قماش بوليستر مطبوع', 'product_type': 'raw_material', 'category': 'أقمشة',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('35.00'), 'min_stock': 300},
        {'sku': 'FAB-VEL-001', 'name': 'قماش قطيفة فاخر', 'product_type': 'raw_material', 'category': 'أقمشة',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('55.00'), 'min_stock': 200},
        
        # إسفنج
        {'sku': 'FOAM-D25-001', 'name': 'إسفنج كثافة 25', 'product_type': 'raw_material', 'category': 'إسفنج',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('35.00'), 'min_stock': 1000},
        {'sku': 'FOAM-D30-001', 'name': 'إسفنج كثافة 30', 'product_type': 'raw_material', 'category': 'إسفنج',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('45.00'), 'min_stock': 800},
        {'sku': 'FOAM-D35-001', 'name': 'إسفنج كثافة 35 (طبي)', 'product_type': 'raw_material', 'category': 'إسفنج',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('60.00'), 'min_stock': 500},
        {'sku': 'FOAM-MEM-001', 'name': 'إسفنج ميموري فوم', 'product_type': 'raw_material', 'category': 'إسفنج',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('120.00'), 'min_stock': 200},
        
        # سوست ومعادن
        {'sku': 'SPR-BNL-001', 'name': 'سوست بونل متصلة', 'product_type': 'raw_material', 'category': 'سوست ومعادن',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('1.50'), 'min_stock': 10000},
        {'sku': 'SPR-PKT-001', 'name': 'سوست منفصلة (Pocket)', 'product_type': 'raw_material', 'category': 'سوست ومعادن',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('3.00'), 'min_stock': 5000},
        {'sku': 'FRM-MTL-001', 'name': 'إطار معدني 200×200', 'product_type': 'raw_material', 'category': 'سوست ومعادن',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('150.00'), 'min_stock': 100},
        
        # أخشاب
        {'sku': 'WOOD-PLY-001', 'name': 'خشب أبلكاش 18 مم', 'product_type': 'raw_material', 'category': 'أخشاب',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('250.00'), 'min_stock': 50},
        
        # مستهلكات
        {'sku': 'CON-THR-001', 'name': 'خيط خياطة صناعي', 'product_type': 'raw_material', 'category': 'مستهلكات',
         'purchase_uom': 'roll', 'usage_uom': 'm', 'conversion_factor': Decimal('5000'), 'cost': Decimal('50.00'), 'min_stock': 100},
        {'sku': 'CON-GLU-001', 'name': 'غراء صناعي', 'product_type': 'raw_material', 'category': 'مستهلكات',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('80.00'), 'min_stock': 50},
        {'sku': 'CON-FLT-001', 'name': 'لباد عازل', 'product_type': 'raw_material', 'category': 'مستهلكات',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('15.00'), 'min_stock': 500},
        {'sku': 'PKG-NYL-001', 'name': 'نايلون تغليف', 'product_type': 'raw_material', 'category': 'مستهلكات',
         'purchase_uom': 'roll', 'usage_uom': 'm', 'conversion_factor': Decimal('100'), 'cost': Decimal('120.00'), 'min_stock': 50},
        
        # ========== نصف مصنع ==========
        {'sku': 'WIP-COV-200', 'name': 'غطاء مرتبة 200×200 مخيط', 'product_type': 'semi_finished', 'category': 'أغطية مخيطة',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('250.00'), 'min_stock': 20},
        {'sku': 'WIP-COV-180', 'name': 'غطاء مرتبة 180×200 مخيط', 'product_type': 'semi_finished', 'category': 'أغطية مخيطة',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('220.00'), 'min_stock': 20},
        {'sku': 'WIP-FRM-200', 'name': 'إطار سوست 200×200 جاهز', 'product_type': 'semi_finished', 'category': 'إطارات جاهزة',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('400.00'), 'min_stock': 15},
        {'sku': 'WIP-FRM-180', 'name': 'إطار سوست 180×200 جاهز', 'product_type': 'semi_finished', 'category': 'إطارات جاهزة',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('350.00'), 'min_stock': 15},
        
        # ========== منتج تام ==========
        # مراتب
        {'sku': 'MAT-STD-200', 'name': 'مرتبة ستاندرد 200×200', 'product_type': 'finished', 'category': 'مراتب',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('2500.00'), 'price': Decimal('4500.00'), 'min_stock': 10},
        {'sku': 'MAT-STD-180', 'name': 'مرتبة ستاندرد 180×200', 'product_type': 'finished', 'category': 'مراتب',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('2200.00'), 'price': Decimal('4000.00'), 'min_stock': 10},
        {'sku': 'MAT-DLX-200', 'name': 'مرتبة ديلوكس 200×200', 'product_type': 'finished', 'category': 'مراتب',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('3500.00'), 'price': Decimal('6500.00'), 'min_stock': 8},
        {'sku': 'MAT-MED-200', 'name': 'مرتبة طبية 200×200', 'product_type': 'finished', 'category': 'مراتب',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('4500.00'), 'price': Decimal('8500.00'), 'min_stock': 5},
        
        # وسائد
        {'sku': 'PIL-STD-001', 'name': 'وسادة ستاندرد', 'product_type': 'finished', 'category': 'وسائد',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('80.00'), 'price': Decimal('180.00'), 'min_stock': 50},
        {'sku': 'PIL-MEM-001', 'name': 'وسادة ميموري فوم', 'product_type': 'finished', 'category': 'وسائد',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('200.00'), 'price': Decimal('450.00'), 'min_stock': 30},
        
        # مفروشات
        {'sku': 'BED-SHT-200', 'name': 'ملاية قطنية 200×200', 'product_type': 'finished', 'category': 'مفروشات',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('120.00'), 'price': Decimal('280.00'), 'min_stock': 30},
        {'sku': 'BED-CVR-200', 'name': 'لحاف 200×220', 'product_type': 'finished', 'category': 'مفروشات',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('350.00'), 'price': Decimal('750.00'), 'min_stock': 20},
    ]
    
    created_count = 0
    for prod in products:
        category = None
        if 'category' in prod:
            category = Category.objects.filter(name=prod['category']).first()
        
        # التحقق من وجود المنتج أولاً
        existing = Product.objects.filter(sku=prod['sku']).first()
        if existing:
            # تحديث المنتج الموجود
            existing.name = prod['name']
            existing.product_type = prod.get('product_type', 'finished')
            existing.category = category
            existing.purchase_uom = prod.get('purchase_uom', 'unit')
            existing.usage_uom = prod.get('usage_uom', 'unit')
            existing.conversion_factor = prod.get('conversion_factor', Decimal('1'))
            existing.cost = prod.get('cost', Decimal('0'))
            existing.price = prod.get('price', Decimal('0'))
            existing.min_stock = prod.get('min_stock', 0)
            existing.save()
            print(f"🔄 موجود مسبقاً: {prod['name']}")
        else:
            # إنشاء منتج جديد
            try:
                new_product = Product.objects.create(
                    sku=prod['sku'],
                    name=prod['name'],
                    product_type=prod.get('product_type', 'finished'),
                    category=category,
                    purchase_uom=prod.get('purchase_uom', 'unit'),
                    usage_uom=prod.get('usage_uom', 'unit'),
                    conversion_factor=prod.get('conversion_factor', Decimal('1')),
                    cost=prod.get('cost', Decimal('0')),
                    price=prod.get('price', Decimal('0')),
                    min_stock=prod.get('min_stock', 0),
                    internal_code=f"INT-{prod['sku']}",  # كود داخلي فريد
                )
                created_count += 1
                print(f"✅ تم إنشاء منتج: {prod['name']}")
            except Exception as e:
                print(f"⚠️ خطأ في إنشاء {prod['name']}: {str(e)[:50]}")
    
    print(f"\n📦 إجمالي المنتجات: {Product.objects.count()} | جديد: {created_count}")
    return Product.objects.all()


# =============================================
# 4. إنشاء مراكز العمل
# =============================================
def create_work_centers():
    from production.models import ProductionWorkCenter
    
    work_centers = [
        {'code': 'CUT-001', 'name': 'قسم التقطيع', 'work_center_type': 'cutting',
         'hourly_rate': Decimal('50.00'), 'capacity_per_hour': Decimal('10'), 'working_hours_per_day': Decimal('8')},
        {'code': 'SEW-001', 'name': 'قسم الخياطة', 'work_center_type': 'sewing',
         'hourly_rate': Decimal('60.00'), 'capacity_per_hour': Decimal('6'), 'working_hours_per_day': Decimal('8')},
        {'code': 'FIL-001', 'name': 'قسم الحشو', 'work_center_type': 'filling',
         'hourly_rate': Decimal('55.00'), 'capacity_per_hour': Decimal('5'), 'working_hours_per_day': Decimal('8')},
        {'code': 'ASM-001', 'name': 'قسم التجميع', 'work_center_type': 'assembly',
         'hourly_rate': Decimal('65.00'), 'capacity_per_hour': Decimal('4'), 'working_hours_per_day': Decimal('8')},
        {'code': 'FIN-001', 'name': 'قسم التشطيب', 'work_center_type': 'finishing',
         'hourly_rate': Decimal('45.00'), 'capacity_per_hour': Decimal('8'), 'working_hours_per_day': Decimal('8')},
        {'code': 'QUA-001', 'name': 'قسم الجودة', 'work_center_type': 'quality',
         'hourly_rate': Decimal('70.00'), 'capacity_per_hour': Decimal('15'), 'working_hours_per_day': Decimal('8')},
        {'code': 'PKG-001', 'name': 'قسم التعبئة', 'work_center_type': 'packaging',
         'hourly_rate': Decimal('40.00'), 'capacity_per_hour': Decimal('12'), 'working_hours_per_day': Decimal('8')},
    ]
    
    created_count = 0
    for wc in work_centers:
        obj, created = ProductionWorkCenter.objects.update_or_create(
            code=wc['code'],
            defaults=wc
        )
        if created:
            created_count += 1
            print(f"✅ تم إنشاء مركز عمل: {wc['name']}")
    
    print(f"\n🏭 إجمالي مراكز العمل: {ProductionWorkCenter.objects.count()} | جديد: {created_count}")
    return ProductionWorkCenter.objects.all()


# =============================================
# 5. إنشاء مراحل الإنتاج
# =============================================
def create_production_stages():
    from production.models import ProductionStage, ProductionWorkCenter
    
    stages = [
        {'code': 'STG-CUT', 'name': 'تقطيع الأقمشة والإسفنج', 'stage_type': 'cutting', 'sequence': 1,
         'operation_time': Decimal('15'), 'required_workers': 2, 'work_center_code': 'CUT-001'},
        {'code': 'STG-SEW', 'name': 'خياطة الأغطية', 'stage_type': 'sewing', 'sequence': 2,
         'operation_time': Decimal('30'), 'required_workers': 3, 'work_center_code': 'SEW-001'},
        {'code': 'STG-FRM', 'name': 'تركيب إطار السوست', 'stage_type': 'assembly', 'sequence': 3,
         'operation_time': Decimal('20'), 'required_workers': 2, 'work_center_code': 'ASM-001'},
        {'code': 'STG-FIL', 'name': 'الحشو والتجميع', 'stage_type': 'assembly', 'sequence': 4,
         'operation_time': Decimal('25'), 'required_workers': 2, 'work_center_code': 'FIL-001'},
        {'code': 'STG-FIN', 'name': 'التشطيب النهائي', 'stage_type': 'finishing', 'sequence': 5,
         'operation_time': Decimal('15'), 'required_workers': 1, 'work_center_code': 'FIN-001'},
        {'code': 'STG-QUA', 'name': 'فحص الجودة', 'stage_type': 'quality', 'sequence': 6,
         'operation_time': Decimal('10'), 'required_workers': 1, 'requires_quality_check': True, 'work_center_code': 'QUA-001'},
        {'code': 'STG-PKG', 'name': 'التغليف والتعبئة', 'stage_type': 'other', 'sequence': 7,
         'operation_time': Decimal('10'), 'required_workers': 2, 'work_center_code': 'PKG-001'},
    ]
    
    created_count = 0
    for stg in stages:
        work_center = ProductionWorkCenter.objects.filter(code=stg.get('work_center_code')).first()
        
        obj, created = ProductionStage.objects.update_or_create(
            code=stg['code'],
            defaults={
                'name': stg['name'],
                'stage_type': stg['stage_type'],
                'sequence': stg['sequence'],
                'operation_time': stg['operation_time'],
                'required_workers': stg['required_workers'],
                'requires_quality_check': stg.get('requires_quality_check', False),
                'work_center': work_center,
                'is_active': True,
            }
        )
        if created:
            created_count += 1
            print(f"✅ تم إنشاء مرحلة: {stg['name']}")
    
    print(f"\n⚙️ إجمالي مراحل الإنتاج: {ProductionStage.objects.count()} | جديد: {created_count}")
    return ProductionStage.objects.all()


# =============================================
# 6. إنشاء قوائم المواد (BOM)
# =============================================
def create_bom():
    from production.models import BillOfMaterials, BOMItem
    from inventory.models import Product
    
    # قائمة مواد لمرتبة ستاندرد 200×200
    product = Product.objects.filter(sku='MAT-STD-200').first()
    if not product:
        print("⚠️ المنتج MAT-STD-200 غير موجود")
        return
    
    bom, created = BillOfMaterials.objects.update_or_create(
        product=product,
        version='1.0',
        defaults={
            'name': 'وصفة مرتبة ستاندرد 200×200',
            'description': 'قائمة المواد الكاملة لإنتاج مرتبة ستاندرد مقاس 200×200 سم',
            'base_quantity': Decimal('1'),
            'is_active': True,
            'is_default': True,
        }
    )
    
    if created:
        print(f"✅ تم إنشاء قائمة المواد: {bom.name}")
    
    # إضافة المكونات
    bom_items = [
        {'sku': 'FAB-COT-001', 'quantity': Decimal('12'), 'item_type': 'material', 'wastage_percentage': Decimal('5')},
        {'sku': 'FOAM-D30-001', 'quantity': Decimal('20'), 'item_type': 'material', 'wastage_percentage': Decimal('3')},
        {'sku': 'SPR-BNL-001', 'quantity': Decimal('200'), 'item_type': 'material', 'wastage_percentage': Decimal('2')},
        {'sku': 'FRM-MTL-001', 'quantity': Decimal('1'), 'item_type': 'component', 'wastage_percentage': Decimal('0')},
        {'sku': 'CON-FLT-001', 'quantity': Decimal('8'), 'item_type': 'material', 'wastage_percentage': Decimal('5')},
        {'sku': 'CON-THR-001', 'quantity': Decimal('100'), 'item_type': 'consumable', 'wastage_percentage': Decimal('10')},
        {'sku': 'CON-GLU-001', 'quantity': Decimal('0.5'), 'item_type': 'consumable', 'wastage_percentage': Decimal('5')},
        {'sku': 'PKG-NYL-001', 'quantity': Decimal('5'), 'item_type': 'consumable', 'wastage_percentage': Decimal('2')},
    ]
    
    for seq, item in enumerate(bom_items, 1):
        material = Product.objects.filter(sku=item['sku']).first()
        if material:
            obj, created = BOMItem.objects.update_or_create(
                bom=bom,
                material=material,
                defaults={
                    'quantity': item['quantity'],
                    'item_type': item['item_type'],
                    'wastage_percentage': item['wastage_percentage'],
                    'unit_cost': material.cost,
                    'sequence': seq,
                }
            )
            if created:
                print(f"   ➕ تم إضافة: {material.name}")
    
    print(f"\n📋 تم إنشاء قائمة المواد بـ {BOMItem.objects.filter(bom=bom).count()} عنصر")


# =============================================
# تشغيل السكريبت
# =============================================
@transaction.atomic
def setup_all():
    print("=" * 60)
    print("🏭 بدء إعداد بيانات مصنع المراتب والمفروشات")
    print("=" * 60)
    
    print("\n" + "=" * 40)
    print("📦 1. إنشاء المخازن...")
    print("=" * 40)
    create_warehouses()
    
    print("\n" + "=" * 40)
    print("📁 2. إنشاء فئات المنتجات...")
    print("=" * 40)
    create_categories()
    
    print("\n" + "=" * 40)
    print("🏷️ 3. إنشاء المنتجات...")
    print("=" * 40)
    create_products()
    
    print("\n" + "=" * 40)
    print("🏭 4. إنشاء مراكز العمل...")
    print("=" * 40)
    create_work_centers()
    
    print("\n" + "=" * 40)
    print("⚙️ 5. إنشاء مراحل الإنتاج...")
    print("=" * 40)
    create_production_stages()
    
    print("\n" + "=" * 40)
    print("📋 6. إنشاء قوائم المواد (BOM)...")
    print("=" * 40)
    create_bom()
    
    print("\n" + "=" * 60)
    print("✅ تم الانتهاء من إعداد بيانات المصنع!")
    print("=" * 60)


# تشغيل تلقائي عند استيراد الملف
if __name__ == '__main__':
    setup_all()
else:
    # عند تنفيذه من shell
    setup_all()
