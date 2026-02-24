"""
إعداد نظام الإسفنج مع الموردين والأسعار

- الشراء بالمتر المكعب (m³)
- الاستخدام بالمتر المكعب (m³)
- ربط كل مادة بالموردين وأسعارهم
- تحديث الأسعار بسهولة

الاستخدام:
    python manage.py shell < setup_foam_with_suppliers.py
"""

from django.db import transaction
from decimal import Decimal
from inventory.models import Product, Category
from partners.models import Supplier, SupplierProduct

print("=" * 80)
print("🧊 إعداد نظام الإسفنج مع الموردين")
print("=" * 80)


def create_foam_products():
    """إنشاء منتجات الإسفنج"""

    print("\n🧊 إنشاء منتجات الإسفنج...")
    print("-" * 80)

    # الحصول على الفئة
    foam_cat = Category.objects.filter(name__icontains='فوم عادي').first()
    if not foam_cat:
        foam_cat = Category.objects.filter(name__icontains='إسفنج').first()
    
    # منتجات الإسفنج من الصورة
    foams = [
        # إسفنج عادي
        {'sku': 'FOAM-D11', 'name': 'إسفنج D11 - كثافة 11', 'density': 11, 'default_price': Decimal('2200')},
        {'sku': 'FOAM-D16', 'name': 'إسفنج D16 - كثافة 16', 'density': 16, 'default_price': Decimal('2860')},
        {'sku': 'FOAM-D18', 'name': 'إسفنج D18 - كثافة 18', 'density': 18, 'default_price': Decimal('3120')},
        {'sku': 'FOAM-D20', 'name': 'إسفنج D20 - كثافة 20', 'density': 20, 'default_price': Decimal('3900')},
        {'sku': 'FOAM-D22', 'name': 'إسفنج D22 - كثافة 22', 'density': 22, 'default_price': Decimal('3490')},
        {'sku': 'FOAM-D24', 'name': 'إسفنج D24 - كثافة 24', 'density': 24, 'default_price': Decimal('3535')},
        {'sku': 'FOAM-D25', 'name': 'إسفنج D25 - كثافة 25', 'density': 25, 'default_price': Decimal('3860')},
        {'sku': 'FOAM-D26', 'name': 'إسفنج D26 - كثافة 26', 'density': 26, 'default_price': Decimal('3860')},
        {'sku': 'FOAM-D28', 'name': 'إسفنج D28 - كثافة 28', 'density': 28, 'default_price': Decimal('4180')},
        {'sku': 'FOAM-D30', 'name': 'إسفنج D30 - كثافة 30', 'density': 30, 'default_price': Decimal('4100')},
        {'sku': 'FOAM-D33', 'name': 'إسفنج D33 - كثافة 33', 'density': 33, 'default_price': Decimal('4380')},
        
        # إسفنج سوبر سوفت
        {'sku': 'FOAM-D35-SS', 'name': 'إسفنج D35 - سوبر سوفت', 'density': 35, 'default_price': Decimal('4585')},
        {'sku': 'FOAM-D36-SS', 'name': 'إسفنج D36 - سوبر سوفت', 'density': 36, 'default_price': Decimal('5000')},
        {'sku': 'FOAM-D40-SS', 'name': 'إسفنج D40 - سوبر سوفت', 'density': 40, 'default_price': Decimal('5170')},
        {'sku': 'FOAM-D40P-SS', 'name': 'إسفنج D40P - سوبر سوفت', 'density': 40, 'default_price': Decimal('5650')},
        {'sku': 'FOAM-D60P-SS', 'name': 'إسفنج D60P - سوبر سوفت', 'density': 60, 'default_price': Decimal('6190')},
        
        # إسفنج سوفت
        {'sku': 'FOAM-D24-S', 'name': 'إسفنج D24 S - سوفت', 'density': 24, 'default_price': Decimal('3830')},
        {'sku': 'FOAM-D28-S', 'name': 'إسفنج D28 S - سوفت', 'density': 28, 'default_price': Decimal('3850')},
        {'sku': 'FOAM-D30-S', 'name': 'إسفنج D30 S - سوفت', 'density': 30, 'default_price': Decimal('4030')},
        {'sku': 'FOAM-D33-S', 'name': 'إسفنج D33 S - سوفت', 'density': 33, 'default_price': Decimal('4415')},
        {'sku': 'FOAM-D30-SOFT', 'name': 'إسفنج D30 Soft', 'density': 30, 'default_price': Decimal('4775')},
        {'sku': 'FOAM-D35-S', 'name': 'إسفنج D35 S - سوفت', 'density': 35, 'default_price': Decimal('4815')},
        {'sku': 'FOAM-D45-S', 'name': 'إسفنج D45 S - سوفت', 'density': 45, 'default_price': Decimal('6120')},
        
        # إسفنج ريزل
        {'sku': 'FOAM-R1', 'name': 'ريزل R1', 'density': 0, 'default_price': Decimal('4500')},
        {'sku': 'FOAM-R2', 'name': 'ريزل R2', 'density': 0, 'default_price': Decimal('5150')},
        
        # مستورد
        {'sku': 'FOAM-M2', 'name': 'إسفنج مستورد M2', 'density': 0, 'default_price': Decimal('14200')},
    ]
    
    created_count = 0
    
    for foam in foams:
        obj, created = Product.objects.update_or_create(
            sku=foam['sku'],
            defaults={
                'name': foam['name'],
                'category': foam_cat,
                'product_type': 'raw_material',
                'purchase_uom': 'm3',  # الشراء بالمتر المكعب
                'usage_uom': 'm3',     # الاستخدام بالمتر المكعب
                'cost': foam['default_price'],
                'price': foam['default_price'] * Decimal('1.5'),  # سعر البيع
                'min_stock': Decimal('2'),  # 2 متر مكعب حد أدنى
                'is_active': True,
                'description': f'كثافة {foam["density"]} - السعر بالمتر المكعب',
            }
        )
        
        if created:
            created_count += 1
        
        status = "✅ جديد" if created else "🔄 محدث"
        print(f"   {status}: {foam['name']} - {foam['default_price']} ج/م³")
    
    print(f"\n✅ تم إنشاء/تحديث {len(foams)} نوع إسفنج")
    print(f"   📦 جديد: {created_count}")
    print(f"   🔄 محدث: {len(foams) - created_count}")


def create_example_suppliers():
    """إنشاء موردين كأمثلة"""
    
    print("\n👥 إنشاء موردين للإسفنج...")
    print("-" * 80)
    
    suppliers_data = [
        {
            'name': 'مورد الإسفنج أ',
            'code': 'FOAM-SUP-A',
            'contact_person': 'أحمد محمد',
            'phone': '01012345678',
        },
        {
            'name': 'مورد الإسفنج ب',
            'code': 'FOAM-SUP-B',
            'contact_person': 'محمود علي',
            'phone': '01098765432',
        },
    ]
    
    suppliers = []
    for sup_data in suppliers_data:
        sup, created = Supplier.objects.get_or_create(
            code=sup_data['code'],
            defaults=sup_data
        )
        suppliers.append(sup)
        status = "✅ جديد" if created else "🔄 موجود"
        print(f"   {status}: {sup.name}")
    
    return suppliers


def link_suppliers_to_products(suppliers):
    """ربط الموردين بالمنتجات مع الأسعار"""
    
    print("\n🔗 ربط الموردين بالمنتجات...")
    print("-" * 80)
    
    # مثال: إسفنج D18 من موردين مختلفين بأسعار مختلفة
    examples = [
        {
            'product_sku': 'FOAM-D18',
            'supplier_index': 0,  # المورد أ
            'price': Decimal('3120'),
            'is_preferred': True,
        },
        {
            'product_sku': 'FOAM-D18',
            'supplier_index': 1,  # المورد ب
            'price': Decimal('3200'),
            'is_preferred': False,
        },
        {
            'product_sku': 'FOAM-D30',
            'supplier_index': 0,  # المورد أ
            'price': Decimal('4100'),
            'is_preferred': True,
        },
    ]
    
    for ex in examples:
        try:
            product = Product.objects.get(sku=ex['product_sku'])
            supplier = suppliers[ex['supplier_index']]
            
            sp, created = SupplierProduct.objects.update_or_create(
                supplier=supplier,
                product=product,
                defaults={
                    'supplier_sku': f"{supplier.code}-{product.sku}",
                    'price': ex['price'],
                    'is_preferred': ex['is_preferred'],
                }
            )
            
            status = "✅" if created else "🔄"
            preferred = "⭐ مفضل" if ex['is_preferred'] else ""
            print(f"   {status} {product.name} ← {supplier.name}: {ex['price']} ج/م³ {preferred}")
            
        except Product.DoesNotExist:
            print(f"   ⚠️  المنتج {ex['product_sku']} غير موجود!")


# تنفيذ
with transaction.atomic():
    create_foam_products()
    suppliers = create_example_suppliers()
    link_suppliers_to_products(suppliers)

print("\n" + "=" * 80)
print("✅ تم إعداد نظام الإسفنج بنجاح!")
print("=" * 80)
print("\n💡 الآن يمكنك:")
print("   1. إضافة موردين جدد")
print("   2. ربط كل مادة بموردها وسعرها")
print("   3. تحديث الأسعار عند تغييرها")
print("   4. استلام الإسفنج بالمتر المكعب")
print("   5. استخدامه في BOM بالمتر المكعب")

