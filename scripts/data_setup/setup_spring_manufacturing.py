"""
إعداد نظام تصنيع السوست
- السلك الحديد = مادة خام
- السوست = نصف مصنع (يتم تصنيعها داخلياً)
- BOM لكل نوع سوست

الاستخدام:
    python manage.py shell < setup_spring_manufacturing.py
"""

from django.db import transaction
from decimal import Decimal
from inventory.models import Product, Category
from production.models import BillOfMaterials, BOMItem

print("=" * 80)
print("🔧 إعداد نظام تصنيع السوست")
print("=" * 80)


def update_wire_as_raw_material():
    """تحديث السلك الحديد كمادة خام"""
    
    print("\n🔩 تحديث السلك الحديد كمادة خام...")
    print("-" * 80)
    
    # السلك الحديد بسماكات مختلفة
    wires = [
        {'sku': 'WIRE-1.5', 'name': 'سلك حديد قطر 1.5 مم', 'cost': Decimal('18.00'), 'min_stock': 500},
        {'sku': 'WIRE-1.8', 'name': 'سلك حديد قطر 1.8 مم', 'cost': Decimal('19.00'), 'min_stock': 800},
        {'sku': 'WIRE-2.0', 'name': 'سلك حديد قطر 2.0 مم', 'cost': Decimal('20.00'), 'min_stock': 1000},
        {'sku': 'WIRE-2.2', 'name': 'سلك حديد قطر 2.2 مم', 'cost': Decimal('21.00'), 'min_stock': 1200},
        {'sku': 'WIRE-2.4', 'name': 'سلك حديد قطر 2.4 مم', 'cost': Decimal('22.00'), 'min_stock': 800},
        {'sku': 'WIRE-2.5', 'name': 'سلك حديد قطر 2.5 مم', 'cost': Decimal('22.50'), 'min_stock': 600},
        {'sku': 'WIRE-3.0', 'name': 'سلك حديد قطر 3.0 مم', 'cost': Decimal('24.00'), 'min_stock': 400},
    ]
    
    wire_cat = Category.objects.filter(name='أسلاك فولاذية').first()
    
    for wire in wires:
        obj, created = Product.objects.update_or_create(
            sku=wire['sku'],
            defaults={
                'name': wire['name'],
                'category': wire_cat,
                'product_type': 'raw_material',
                'purchase_uom': 'kg',
                'usage_uom': 'kg',
                'cost': wire['cost'],
                'price': wire['cost'] * Decimal('1.2'),
                'min_stock': wire['min_stock'],
                'is_active': True,
            }
        )
        status = "✅ جديد" if created else "🔄 محدث"
        print(f"   {status}: {wire['name']}")
    
    print(f"\n✅ تم تحديث {len(wires)} نوع سلك حديد")


def create_springs_as_semi_finished():
    """إنشاء السوست كمنتجات نصف مصنعة"""
    
    print("\n⚙️ إنشاء السوست كمنتجات نصف مصنعة...")
    print("-" * 80)
    
    # فئة السوست المصنعة
    springs_cat, _ = Category.objects.get_or_create(
        name='سوست مصنعة',
        defaults={
            'description': 'السوست المصنعة داخلياً من السلك الحديد',
            'parent': Category.objects.filter(name='نصف مصنع').first(),
        }
    )
    
    # السوست المصنعة
    springs = [
        # سوست بونيل
        {'sku': 'SPR-BNL-S90', 'name': 'سوست بونيل - قطر سلك 2.0 مم', 'wire_sku': 'WIRE-2.0', 
         'wire_weight': Decimal('0.015'), 'labor_cost': Decimal('0.30')},
        {'sku': 'SPR-BNL-S100', 'name': 'سوست بونيل - قطر سلك 2.2 مم', 'wire_sku': 'WIRE-2.2',
         'wire_weight': Decimal('0.018'), 'labor_cost': Decimal('0.35')},
        {'sku': 'SPR-BNL-S120', 'name': 'سوست بونيل - قطر سلك 2.4 مم (Heavy Duty)', 'wire_sku': 'WIRE-2.4',
         'wire_weight': Decimal('0.022'), 'labor_cost': Decimal('0.40')},
        
        # سوست متصلة
        {'sku': 'SPR-CNT-001', 'name': 'سوست متصلة Continuous - قطر 1.8 مم', 'wire_sku': 'WIRE-1.8',
         'wire_weight': Decimal('0.012'), 'labor_cost': Decimal('0.25')},
        {'sku': 'SPR-CNT-002', 'name': 'سوست متصلة Continuous - قطر 2.0 مم', 'wire_sku': 'WIRE-2.0',
         'wire_weight': Decimal('0.015'), 'labor_cost': Decimal('0.30')},
        
        # سوست منفصلة (Pocket)
        {'sku': 'SPR-PKT-S', 'name': 'سوست منفصلة Pocket - صغير (5 سم)', 'wire_sku': 'WIRE-1.8',
         'wire_weight': Decimal('0.020'), 'labor_cost': Decimal('0.60'), 'fabric_cost': Decimal('0.50')},
        {'sku': 'SPR-PKT-M', 'name': 'سوست منفصلة Pocket - متوسط (7 سم)', 'wire_sku': 'WIRE-2.0',
         'wire_weight': Decimal('0.025'), 'labor_cost': Decimal('0.70'), 'fabric_cost': Decimal('0.60')},
        {'sku': 'SPR-PKT-L', 'name': 'سوست منفصلة Pocket - كبير (10 سم)', 'wire_sku': 'WIRE-2.2',
         'wire_weight': Decimal('0.030'), 'labor_cost': Decimal('0.80'), 'fabric_cost': Decimal('0.70')},
    ]
    
    created_count = 0
    
    for spring in springs:
        # حساب التكلفة
        wire_product = Product.objects.filter(sku=spring['wire_sku']).first()
        if not wire_product:
            print(f"   ⚠️  السلك {spring['wire_sku']} غير موجود!")
            continue
        
        wire_cost = spring['wire_weight'] * wire_product.cost
        labor_cost = spring['labor_cost']
        fabric_cost = spring.get('fabric_cost', Decimal('0'))
        total_cost = wire_cost + labor_cost + fabric_cost
        
        # إنشاء المنتج
        obj, created = Product.objects.update_or_create(
            sku=spring['sku'],
            defaults={
                'name': spring['name'],
                'category': springs_cat,
                'product_type': 'semi_finished',
                'purchase_uom': 'unit',
                'usage_uom': 'unit',
                'cost': total_cost,
                'price': total_cost * Decimal('1.3'),
                'min_stock': 5000,
                'is_active': True,
            }
        )
        
        if created:
            created_count += 1
        
        status = "✅ جديد" if created else "🔄 محدث"
        print(f"   {status}: {spring['name']} (تكلفة: {total_cost:.2f} جنيه)")
        
        # إنشاء BOM للسوست
        create_spring_bom(obj, spring, wire_product)
    
    print(f"\n✅ تم إنشاء/تحديث {len(springs)} نوع سوست")


def create_spring_bom(spring_product, spring_data, wire_product):
    """إنشاء BOM لتصنيع السوست"""
    
    # إنشاء أو تحديث BOM
    bom, created = BillOfMaterials.objects.update_or_create(
        product=spring_product,
        version='1.0',
        defaults={
            'name': f'تصنيع {spring_product.name}',
            'description': f'وصفة تصنيع سوست من السلك الحديد',
            'base_quantity': Decimal('1'),
            'is_default': True,
            'is_active': True,
        }
    )
    
    if created:
        # إضافة السلك الحديد
        BOMItem.objects.create(
            bom=bom,
            material=wire_product,
            item_type='material',
            quantity=spring_data['wire_weight'],
            unit_cost=wire_product.cost,
            wastage_percentage=Decimal('3'),  # 3% هدر في التصنيع
            sequence=1,
            notes='السلك الحديد الخام'
        )
        
        # إضافة قماش للسوست المنفصلة (Pocket Springs)
        if 'fabric_cost' in spring_data and spring_data['fabric_cost'] > 0:
            fabric = Product.objects.filter(sku='FAB-POL-STD').first()
            if fabric:
                BOMItem.objects.create(
                    bom=bom,
                    material=fabric,
                    item_type='material',
                    quantity=Decimal('0.02'),  # 2 سم قماش لكل سوست
                    unit_cost=fabric.cost,
                    wastage_percentage=Decimal('5'),
                    sequence=2,
                    notes='قماش لتغليف السوست المنفصلة'
                )


# تنفيذ
with transaction.atomic():
    update_wire_as_raw_material()
    create_springs_as_semi_finished()

print("\n" + "=" * 80)
print("✅ تم إعداد نظام تصنيع السوست بنجاح!")
print("=" * 80)

