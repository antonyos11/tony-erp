"""
أمثلة جاهزة لقوائم المواد (BOM) لمنتجات المراتب والمفروشات

الاستخدام:
    1. تأكد من تشغيل setup_complete_mattress_materials.py أولاً
    2. ثم شغل هذا الملف:
       python manage.py shell < setup_bom_examples.py
"""

from django.db import transaction
from decimal import Decimal
from inventory.models import Product, Category
from production.models import BillOfMaterials, BOMItem

print("=" * 80)
print("🏭 إنشاء أمثلة BOM لمنتجات المراتب والمفروشات")
print("=" * 80)


def create_sample_products_and_boms():
    """إنشاء منتجات نهائية مع قوائم موادها"""
    
    # ========================================
    # 1. مرتبة سوست بونيل 120×200
    # ========================================
    print("\n📦 إنشاء: مرتبة سوست بونيل 120×200...")
    
    mattress_cat = Category.objects.filter(name='مراتب').first()
    
    mattress_120, created = Product.objects.update_or_create(
        sku='MAT-SPR-120',
        defaults={
            'name': 'مرتبة سوست بونيل 120×200 سم',
            'category': mattress_cat,
            'product_type': 'finished',
            'purchase_uom': 'unit',
            'usage_uom': 'unit',
            'price': Decimal('2500.00'),
            'min_stock': 10,
            'is_active': True,
        }
    )
    
    if created:
        print("   ✅ تم إنشاء المنتج")
    else:
        print("   🔄 المنتج موجود مسبقاً")
    
    # إنشاء BOM للمرتبة
    bom_120, created = BillOfMaterials.objects.update_or_create(
        product=mattress_120,
        version='1.0',
        defaults={
            'name': 'قائمة مواد مرتبة سوست بونيل 120×200',
            'description': 'مرتبة سوست بونيل قياس 120×200 سم - جودة عالية',
            'base_quantity': Decimal('1'),
            'is_default': True,
            'is_active': True,
        }
    )
    
    if created:
        print("   ✅ تم إنشاء BOM")
        
        # إضافة المواد
        materials = [
            {'sku': 'FRM-MTL-120', 'qty': Decimal('1'), 'wastage': Decimal('0'), 'type': 'component'},
            {'sku': 'SPR-BNL-S100', 'qty': Decimal('450'), 'wastage': Decimal('2'), 'type': 'material'},
            {'sku': 'FOAM-HD30', 'qty': Decimal('8'), 'wastage': Decimal('5'), 'type': 'material'},
            {'sku': 'FELT-STD-10', 'qty': Decimal('2.5'), 'wastage': Decimal('3'), 'type': 'material'},
            {'sku': 'FAB-JAC-PRT', 'qty': Decimal('3'), 'wastage': Decimal('5'), 'type': 'material'},
            {'sku': 'THR-POL-WHT', 'qty': Decimal('150'), 'wastage': Decimal('2'), 'type': 'consumable'},
            {'sku': 'GLU-FOAM', 'qty': Decimal('0.5'), 'wastage': Decimal('5'), 'type': 'consumable'},
            {'sku': 'BAG-PVC-L', 'qty': Decimal('1'), 'wastage': Decimal('0'), 'type': 'consumable'},
            {'sku': 'LABEL-BRAND', 'qty': Decimal('1'), 'wastage': Decimal('0'), 'type': 'consumable'},
        ]
        
        for idx, mat in enumerate(materials, 1):
            material_product = Product.objects.filter(sku=mat['sku']).first()
            if material_product:
                BOMItem.objects.create(
                    bom=bom_120,
                    material=material_product,
                    item_type=mat['type'],
                    quantity=mat['qty'],
                    unit_cost=material_product.cost,
                    wastage_percentage=mat['wastage'],
                    sequence=idx,
                )
                print(f"      • {material_product.name}: {mat['qty']} {material_product.usage_uom}")
    else:
        print("   🔄 BOM موجود مسبقاً")
    
    # ========================================
    # 2. مرتبة ميموري فوم 160×200 (فاخرة)
    # ========================================
    print("\n📦 إنشاء: مرتبة ميموري فوم 160×200 (فاخرة)...")
    
    mattress_160, created = Product.objects.update_or_create(
        sku='MAT-MEM-160',
        defaults={
            'name': 'مرتبة ميموري فوم 160×200 سم - Premium',
            'category': mattress_cat,
            'product_type': 'finished',
            'purchase_uom': 'unit',
            'usage_uom': 'unit',
            'price': Decimal('4500.00'),
            'min_stock': 5,
            'is_active': True,
        }
    )
    
    if created:
        print("   ✅ تم إنشاء المنتج")
    
    bom_160, created = BillOfMaterials.objects.update_or_create(
        product=mattress_160,
        version='1.0',
        defaults={
            'name': 'قائمة مواد مرتبة ميموري فوم 160×200',
            'description': 'مرتبة ميموري فوم فاخرة - راحة طبية',
            'base_quantity': Decimal('1'),
            'is_default': True,
            'is_active': True,
        }
    )
    
    if created:
        print("   ✅ تم إنشاء BOM")
        
        materials = [
            {'sku': 'FRM-MTL-160', 'qty': Decimal('1'), 'wastage': Decimal('0'), 'type': 'component'},
            {'sku': 'SPR-PKT-M', 'qty': Decimal('600'), 'wastage': Decimal('2'), 'type': 'material'},
            {'sku': 'FOAM-MEM-60', 'qty': Decimal('12'), 'wastage': Decimal('3'), 'type': 'material'},
            {'sku': 'FOAM-HD35', 'qty': Decimal('10'), 'wastage': Decimal('5'), 'type': 'material'},
            {'sku': 'FELT-COMP', 'qty': Decimal('3.5'), 'wastage': Decimal('3'), 'type': 'material'},
            {'sku': 'FAB-TENCEL', 'qty': Decimal('4'), 'wastage': Decimal('5'), 'type': 'material'},
            {'sku': 'THR-POL-WHT', 'qty': Decimal('200'), 'wastage': Decimal('2'), 'type': 'consumable'},
            {'sku': 'GLU-FOAM', 'qty': Decimal('0.8'), 'wastage': Decimal('5'), 'type': 'consumable'},
            {'sku': 'BAG-VAC', 'qty': Decimal('1'), 'wastage': Decimal('0'), 'type': 'consumable'},
        ]
        
        for idx, mat in enumerate(materials, 1):
            material_product = Product.objects.filter(sku=mat['sku']).first()
            if material_product:
                BOMItem.objects.create(
                    bom=bom_160,
                    material=material_product,
                    item_type=mat['type'],
                    quantity=mat['qty'],
                    unit_cost=material_product.cost,
                    wastage_percentage=mat['wastage'],
                    sequence=idx,
                )
                print(f"      • {material_product.name}: {mat['qty']} {material_product.usage_uom}")
    
    # حساب التكاليف
    print("\n💰 حساب التكاليف:")
    print(f"   • مرتبة 120×200: تكلفة المواد = {bom_120.total_material_cost:.2f} جنيه")
    print(f"   • مرتبة 160×200: تكلفة المواد = {bom_160.total_material_cost:.2f} جنيه")


# تنفيذ
with transaction.atomic():
    create_sample_products_and_boms()

print("\n" + "=" * 80)
print("✅ تم إنشاء أمثلة BOM بنجاح!")
print("=" * 80)

