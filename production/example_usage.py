"""
مثال عملي شامل لاستخدام نظام الإنتاج المتكامل

هذا المثال يوضح كيفية استخدام النظام من البداية للنهاية
"""

from django.contrib.auth.models import User
from decimal import Decimal
from datetime import datetime, timedelta

from production.models import (
    ProductionOrder, BillOfMaterials, BOMItem, ProductionSettings,
    ProductionWorkCenter, ProductManufacturingProfile
)
from production.services import (
    ProductionLifecycleService,
    ProductionInventoryService,
    ProductionAccountingService
)
from inventory.models import Product, Location
from accounting.models import Account, CostCenter


def setup_production_system():
    """
    الخطوة 1: إعداد النظام الأساسي
    """
    print("=" * 60)
    print("الخطوة 1: إعداد النظام")
    print("=" * 60)
    
    # 1. إنشاء الحسابات المحاسبية
    print("\n1. إنشاء الحسابات المحاسبية...")
    
    wip_account, _ = Account.objects.get_or_create(
        code='1510',
        defaults={
            'name': 'الإنتاج تحت التشغيل',
            'type': 'asset',
            'parent': None
        }
    )
    
    finished_goods_account, _ = Account.objects.get_or_create(
        code='1520',
        defaults={
            'name': 'البضائع التامة',
            'type': 'asset',
            'parent': None
        }
    )
    
    raw_materials_account, _ = Account.objects.get_or_create(
        code='1530',
        defaults={
            'name': 'المواد الخام',
            'type': 'asset',
            'parent': None
        }
    )
    
    labor_account, _ = Account.objects.get_or_create(
        code='5110',
        defaults={
            'name': 'تكلفة العمالة',
            'type': 'expense',
            'parent': None
        }
    )
    
    overhead_account, _ = Account.objects.get_or_create(
        code='5120',
        defaults={
            'name': 'التكاليف الإضافية',
            'type': 'expense',
            'parent': None
        }
    )
    
    print("   ✓ تم إنشاء الحسابات المحاسبية")
    
    # 2. تكوين إعدادات الإنتاج
    print("\n2. تكوين إعدادات الإنتاج...")
    
    settings, created = ProductionSettings.objects.get_or_create(
        id=1,
        defaults={
            'company_name': 'مصنع المراتب والمفروشات',
            'wip_account': wip_account,
            'finished_goods_account': finished_goods_account,
            'raw_materials_account': raw_materials_account,
            'labor_cost_account': labor_account,
            'overhead_account': overhead_account,
            'overhead_allocation_method': 'labor_hours',
            'overhead_rate': Decimal('1.5')
        }
    )
    
    print("   ✓ تم تكوين إعدادات الإنتاج")
    
    # 3. إنشاء المواقع في المخزون
    print("\n3. إنشاء مواقع المخزون...")
    
    raw_location, _ = Location.objects.get_or_create(
        code='RAW-01',
        defaults={
            'name': 'مخزن المواد الخام',
            'type': 'raw_material',
            'is_active': True
        }
    )
    
    wip_location, _ = Location.objects.get_or_create(
        code='WIP-01',
        defaults={
            'name': 'مخزن الإنتاج تحت التشغيل',
            'type': 'wip',
            'is_active': True
        }
    )
    
    finished_location, _ = Location.objects.get_or_create(
        code='FG-01',
        defaults={
            'name': 'مخزن المنتجات التامة',
            'type': 'finished_goods',
            'is_active': True
        }
    )
    
    print("   ✓ تم إنشاء مواقع المخزون")
    
    print("\n✅ اكتمل إعداد النظام بنجاح!")
    return {
        'accounts': {
            'wip': wip_account,
            'finished_goods': finished_goods_account,
            'raw_materials': raw_materials_account,
            'labor': labor_account,
            'overhead': overhead_account
        },
        'locations': {
            'raw': raw_location,
            'wip': wip_location,
            'finished': finished_location
        },
        'settings': settings
    }


def create_product_and_bom():
    """
    الخطوة 2: إنشاء منتج وقائمة المواد (BOM)
    """
    print("\n" + "=" * 60)
    print("الخطوة 2: إنشاء المنتج وقائمة المواد")
    print("=" * 60)
    
    # 1. إنشاء المنتج النهائي
    print("\n1. إنشاء المنتج النهائي...")
    
    product, _ = Product.objects.get_or_create(
        code='MAT-001',
        defaults={
            'name': 'مرتبة طبية 200x180',
            'unit_of_measure': 'قطعة',
            'is_active': True,
            'standard_cost': Decimal('980.00')
        }
    )
    
    # إعدادات التصنيع
    mfg_profile, _ = ProductManufacturingProfile.objects.get_or_create(
        product=product,
        defaults={
            'shelf_life_days': 730,  # عامين
            'default_size_text': '200x180 سم'
        }
    )
    
    print(f"   ✓ تم إنشاء المنتج: {product.name}")
    
    # 2. إنشاء المواد الخام
    print("\n2. إنشاء المواد الخام...")
    
    fabric = Product.objects.get_or_create(
        code='RM-001',
        defaults={
            'name': 'قماش خارجي',
            'unit_of_measure': 'متر',
            'is_active': True,
            'standard_cost': Decimal('50.00')
        }
    )[0]
    
    foam = Product.objects.get_or_create(
        code='RM-002',
        defaults={
            'name': 'اسفنج طبي',
            'unit_of_measure': 'متر مكعب',
            'is_active': True,
            'standard_cost': Decimal('200.00')
        }
    )[0]
    
    zipper = Product.objects.get_or_create(
        code='RM-003',
        defaults={
            'name': 'سوستة',
            'unit_of_measure': 'قطعة',
            'is_active': True,
            'standard_cost': Decimal('30.00')
        }
    )[0]
    
    thread = Product.objects.get_or_create(
        code='RM-004',
        defaults={
            'name': 'خيوط',
            'unit_of_measure': 'متر',
            'is_active': True,
            'standard_cost': Decimal('0.50')
        }
    )[0]
    
    print("   ✓ تم إنشاء المواد الخام")
    
    # 3. إنشاء قائمة المواد (BOM)
    print("\n3. إنشاء قائمة المواد (BOM)...")
    
    bom, _ = BillOfMaterials.objects.get_or_create(
        product=product,
        version='1.0',
        defaults={
            'name': 'قائمة مواد مرتبة طبية',
            'description': 'المواد المطلوبة لإنتاج مرتبة طبية واحدة',
            'base_quantity': Decimal('1.0'),
            'is_active': True,
            'is_default': True
        }
    )
    
    # إضافة المواد للـ BOM
    BOMItem.objects.get_or_create(
        bom=bom,
        material=fabric,
        defaults={
            'item_type': 'material',
            'quantity': Decimal('5.0'),
            'unit_cost': fabric.standard_cost,
            'wastage_percentage': Decimal('5.0'),
            'sequence': 1
        }
    )
    
    BOMItem.objects.get_or_create(
        bom=bom,
        material=foam,
        defaults={
            'item_type': 'material',
            'quantity': Decimal('2.0'),
            'unit_cost': foam.standard_cost,
            'wastage_percentage': Decimal('3.0'),
            'sequence': 2
        }
    )
    
    BOMItem.objects.get_or_create(
        bom=bom,
        material=zipper,
        defaults={
            'item_type': 'component',
            'quantity': Decimal('1.0'),
            'unit_cost': zipper.standard_cost,
            'wastage_percentage': Decimal('2.0'),
            'sequence': 3
        }
    )
    
    BOMItem.objects.get_or_create(
        bom=bom,
        material=thread,
        defaults={
            'item_type': 'consumable',
            'quantity': Decimal('100.0'),
            'unit_cost': thread.standard_cost,
            'wastage_percentage': Decimal('10.0'),
            'sequence': 4
        }
    )
    
    # حساب التكلفة الإجمالية
    total_cost = sum(item.total_cost for item in bom.items.all())
    bom.total_material_cost = total_cost
    bom.save()
    
    print(f"   ✓ تم إنشاء BOM - التكلفة الإجمالية: {total_cost} جنيه")
    
    print("\n✅ اكتمل إنشاء المنتج وقائمة المواد!")
    return {
        'product': product,
        'bom': bom,
        'materials': {
            'fabric': fabric,
            'foam': foam,
            'zipper': zipper,
            'thread': thread
        }
    }


def create_production_order(product, bom, user):
    """
    الخطوة 3: إنشاء أمر إنتاج
    """
    print("\n" + "=" * 60)
    print("الخطوة 3: إنشاء أمر إنتاج")
    print("=" * 60)
    
    today = datetime.now().date()
    
    order = ProductionOrder.objects.create(
        product=product,
        bom=bom,
        planned_quantity=Decimal('100.0'),
        order_date=today,
        planned_start_date=today,
        planned_end_date=today + timedelta(days=5),
        status='draft',
        priority='normal',
        created_by=user,
        # التكاليف المقدرة
        estimated_material_cost=bom.total_material_cost * Decimal('100.0'),
        estimated_labor_cost=Decimal('15000.00'),
        estimated_overhead_cost=Decimal('10000.00')
    )
    
    print(f"\n✓ تم إنشاء أمر إنتاج: {order.number}")
    print(f"  المنتج: {product.name}")
    print(f"  الكمية: {order.planned_quantity}")
    print(f"  التكلفة المقدرة: {order.estimated_total_cost} جنيه")
    
    return order


def demonstrate_production_lifecycle(order, user):
    """
    الخطوة 4: تنفيذ دورة حياة الإنتاج الكاملة
    """
    print("\n" + "=" * 60)
    print("الخطوة 4: تنفيذ دورة حياة الإنتاج")
    print("=" * 60)
    
    # 1. التحقق من توفر المواد
    print("\n1. التحقق من توفر المواد...")
    
    all_available, materials = ProductionInventoryService.check_material_availability(order)
    
    print(f"\n   المواد {'متوفرة ✓' if all_available else 'غير كافية ✗'}")
    for material in materials:
        status = "✓" if material['is_available'] else "✗"
        print(f"   {status} {material['material_name']}: "
              f"مطلوب {material['required_quantity']:.2f} - "
              f"متوفر {material['available_quantity']:.2f}")
    
    if not all_available:
        print("\n   ⚠️ تحذير: بعض المواد غير متوفرة!")
        print("   يُنصح بإضافة المواد للمخزون قبل البدء")
    
    # 2. بدء الإنتاج
    print("\n2. بدء الإنتاج...")
    
    success, msg, details = ProductionLifecycleService.start_production_order(
        order,
        user
    )
    
    if success:
        print(f"   ✓ {msg}")
        print(f"   - سند الصرف: {details.get('issue_id')}")
        print(f"   - القيد المحاسبي: {details.get('journal_entry_id')}")
        print(f"   - تكلفة المواد: {details.get('material_cost')} جنيه")
    else:
        print(f"   ✗ فشل: {msg}")
        return
    
    # 3. تسجيل الإنتاج (محاكاة 3 أيام)
    print("\n3. تسجيل الإنتاج...")
    
    production_batches = [
        (Decimal('30.0'), 'اليوم الأول'),
        (Decimal('35.0'), 'اليوم الثاني'),
        (Decimal('35.0'), 'اليوم الثالث')
    ]
    
    for qty, day in production_batches:
        success, msg, details = ProductionLifecycleService.record_production_output(
            order,
            qty,
            user,
            generate_barcodes=True,
            size_text='200x180 سم'
        )
        
        if success:
            print(f"   ✓ {day}: {qty} قطعة - سند استلام: {details.get('receipt_id')}")
            print(f"      باركودات: {len(details.get('barcodes', []))} وحدة")
            print(f"      نسبة الإنجاز: {details.get('completion_percentage'):.1f}%")
        else:
            print(f"   ✗ {day}: فشل - {msg}")
    
    # تحديث الأمر
    order.refresh_from_db()
    
    # 4. تسجيل تكلفة العمالة
    print("\n4. تسجيل تكلفة العمالة...")
    
    success, msg = ProductionLifecycleService.record_labor_cost(
        order,
        Decimal('14200.00'),
        'تكلفة عمالة 3 أيام - 10 عمال'
    )
    
    if success:
        print(f"   ✓ {msg}")
    
    # 5. حساب التكاليف الإضافية
    print("\n5. حساب التكاليف الإضافية...")
    
    success, msg = ProductionLifecycleService.calculate_and_apply_overhead(order)
    
    if success:
        print(f"   ✓ {msg}")
    
    # تحديث الأمر
    order.refresh_from_db()
    
    # 6. إكمال الأمر
    print("\n6. إكمال الأمر...")
    
    success, msg, analysis = ProductionLifecycleService.complete_production_order(order)
    
    if success:
        print(f"   ✓ {msg}")
        print(f"\n   📊 ملخص التكاليف:")
        print(f"   - المواد: {analysis['total_cost']:.2f} جنيه")
        print(f"   - تكلفة الوحدة: {analysis['unit_cost']:.2f} جنيه")
        print(f"   - الكمية المنتجة: {analysis['produced_quantity']}")
        
        # عرض الانحرافات
        variance = analysis.get('variance_analysis', {})
        total_var = variance.get('total', {})
        
        print(f"\n   📈 تحليل الانحرافات:")
        print(f"   - انحراف المواد: {variance.get('material', {}).get('variance', 0):.2f} جنيه")
        print(f"   - انحراف العمالة: {variance.get('labor', {}).get('variance', 0):.2f} جنيه")
        print(f"   - انحراف التكاليف الإضافية: {variance.get('overhead', {}).get('variance', 0):.2f} جنيه")
        print(f"   - الانحراف الإجمالي: {total_var.get('variance', 0):.2f} جنيه ({total_var.get('variance_pct', 0):.2f}%)")
        
        if total_var.get('status') == 'favorable':
            print(f"   ✅ الانحراف مواتي (توفير في التكلفة)")
        else:
            print(f"   ⚠️ الانحراف غير مواتي (زيادة في التكلفة)")


def run_complete_example():
    """
    تشغيل المثال الكامل
    """
    print("\n" + "=" * 60)
    print("مثال عملي كامل لنظام الإنتاج المتكامل")
    print("=" * 60)
    
    # الحصول على مستخدم للاختبار
    user = User.objects.first()
    if not user:
        print("⚠️ يجب إنشاء مستخدم أولاً!")
        return
    
    print(f"\nالمستخدم: {user.username}")
    
    # الخطوة 1: إعداد النظام
    system_config = setup_production_system()
    
    # الخطوة 2: إنشاء المنتج والـ BOM
    product_data = create_product_and_bom()
    
    # الخطوة 3: إنشاء أمر الإنتاج
    order = create_production_order(
        product_data['product'],
        product_data['bom'],
        user
    )
    
    # الخطوة 4: تنفيذ دورة حياة الإنتاج
    demonstrate_production_lifecycle(order, user)
    
    print("\n" + "=" * 60)
    print("✅ اكتمل المثال بنجاح!")
    print("=" * 60)
    print("\nيمكنك الآن:")
    print("1. مراجعة سندات الصرف والاستلام في المخزون")
    print("2. مراجعة القيود المحاسبية")
    print("3. مراجعة الباركودات المولدة")
    print("4. مراجعة تقارير التكاليف والانحرافات")
    print("\nشكراً لاستخدام نظام الإنتاج المتكامل!")


# لتشغيل المثال من Django shell:
# from production.example_usage import run_complete_example
# run_complete_example()
