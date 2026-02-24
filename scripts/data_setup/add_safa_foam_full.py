#!/usr/bin/env python
"""
سكريبت إضافة أصناف إسفنج SAFA FOAM
قائمة أسعار 22 نوفمبر 2025
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, '/var/www/tony_erp')
django.setup()

from inventory.models import Product, Category
from partners.models import Supplier
from decimal import Decimal

def add_safa_foam_products():
    """إضافة منتجات SAFA FOAM"""
    
    # البحث عن أو إنشاء فئة الإسفنج
    category, created = Category.objects.get_or_create(
        name='إسفنج',
        defaults={'description': 'مواد خام - إسفنج بجميع الكثافات'}
    )
    if created:
        print(f"✅ تم إنشاء فئة: {category.name}")
    
    # البحث عن مورد الصفا
    supplier = Supplier.objects.filter(name__icontains='الصفا').first()
    if not supplier:
        supplier, created = Supplier.objects.get_or_create(
            name='مصنع الصفا والمدائن للإسفنج',
            defaults={'phone': '', 'email': '', 'address': ''}
        )
        if created:
            print(f"✅ تم إنشاء مورد: {supplier.name}")
    
    # قائمة أصناف SAFA FOAM العادية
    safa_foam_products = [
        {'density': 18, 'color': 'أبيض مكرى', 'price': 3200},
        {'density': 22, 'color': 'أصفر', 'price': 3490},
        {'density': 25, 'color': 'بنفسجي/ليموني', 'price': 3940},
        {'density': 26, 'color': 'كحلي', 'price': 4010},
        {'density': 28, 'color': 'أخضر/أسود', 'price': 4260},
        {'density': 30, 'color': 'رمادي/بنفسجي', 'price': 4580},
        {'density': 33, 'color': 'أحمر/أخضر', 'price': 4460},
        {'density': 35, 'color': 'برتقالي', 'price': 4815},
        {'density': 37, 'color': 'كحلي', 'price': 4720},
        {'density': 38, 'color': 'رمادي/أبيض', 'price': 5130},
        {'density': 40, 'color': 'تركوازي', 'price': 5440},
        {'density': 42, 'color': 'بنفسجي', 'price': 5750},
        {'density': 45, 'color': 'أسود', 'price': 5950},
    ]
    
    # قائمة أصناف سوفت
    soft_products = [
        {'density': 20, 'color': 'أبيض', 'price': 2730},
        {'density': 25, 'color': 'أصفر/أخضر', 'price': 4470},
        {'density': 30, 'color': 'سوبر سوفت', 'price': 4470},
        {'density': 35, 'color': 'أزرق/أخضر', 'price': 5200},
        {'density': 40, 'color': 'وردي', 'price': 5970},
    ]
    
    # الإسفنج المضغوط
    compressed_products = [
        {'name': 'إسفنج مضغوط S1', 'sku': 'FOAM-S1', 'price': 10270},
        {'name': 'إسفنج مضغوط S60', 'sku': 'FOAM-S60', 'price': 4600},
        {'name': 'إسفنج مضغوط S70', 'sku': 'FOAM-S70', 'price': 5200},
        {'name': 'إسفنج مضغوط S85', 'sku': 'FOAM-S85', 'price': 5600},
    ]
    
    added_count = 0
    updated_count = 0
    
    # إضافة منتجات SAFA FOAM
    print("\n📦 إضافة أصناف SAFA FOAM:")
    print("-" * 50)
    
    for item in safa_foam_products:
        sku = f"SAFA-D{item['density']}"
        name = f"إسفنج SAFA D{item['density']} - {item['color']}"
        
        product, created = Product.objects.update_or_create(
            sku=sku,
            defaults={
                'name': name,
                'category': category,
                'product_type': 'raw_material',
                'purchase_uom': 'm3',
                'usage_uom': 'm3',
                'conversion_factor': Decimal('1.0000'),
                'cost': Decimal(str(item['price'])),
                'price': Decimal(str(item['price'])),
                'preferred_supplier': supplier,
                'description': f"إسفنج SAFA FOAM كثافة {item['density']} - لون {item['color']}\nسعر المتر المكعب: {item['price']} ج.م",
            }
        )
        
        if created:
            added_count += 1
            print(f"  ✅ تمت إضافة: {name} - {item['price']} ج.م")
        else:
            updated_count += 1
            print(f"  🔄 تم تحديث: {name} - {item['price']} ج.م")
    
    # إضافة منتجات سوفت
    print("\n📦 إضافة أصناف سوفت:")
    print("-" * 50)
    
    for item in soft_products:
        sku = f"SAFA-D{item['density']}-SOFT"
        name = f"إسفنج SAFA D{item['density']} سوفت - {item['color']}"
        internal_code = f"SAFA-SOFT-D{item['density']}"
        
        product, created = Product.objects.update_or_create(
            sku=sku,
            defaults={
                'name': name,
                'category': category,
                'product_type': 'raw_material',
                'purchase_uom': 'm3',
                'usage_uom': 'm3',
                'conversion_factor': Decimal('1.0000'),
                'cost': Decimal(str(item['price'])),
                'price': Decimal(str(item['price'])),
                'preferred_supplier': supplier,
                'internal_code': internal_code,
                'description': f"إسفنج سوفت SAFA كثافة {item['density']} - لون {item['color']}\nسعر المتر المكعب: {item['price']} ج.م",
            }
        )
        
        if created:
            added_count += 1
            print(f"  ✅ تمت إضافة: {name} - {item['price']} ج.م")
        else:
            updated_count += 1
            print(f"  🔄 تم تحديث: {name} - {item['price']} ج.م")
    
    # إضافة الإسفنج المضغوط
    print("\n📦 إضافة الإسفنج المضغوط:")
    print("-" * 50)
    
    for item in compressed_products:
        product, created = Product.objects.update_or_create(
            sku=item['sku'],
            defaults={
                'name': item['name'],
                'category': category,
                'product_type': 'raw_material',
                'purchase_uom': 'm3',
                'usage_uom': 'm3',
                'conversion_factor': Decimal('1.0000'),
                'cost': Decimal(str(item['price'])),
                'price': Decimal(str(item['price'])),
                'preferred_supplier': supplier,
                'description': f"{item['name']}\nسعر المتر المكعب: {item['price']} ج.م",
            }
        )
        
        if created:
            added_count += 1
            print(f"  ✅ تمت إضافة: {item['name']} - {item['price']} ج.م")
        else:
            updated_count += 1
            print(f"  🔄 تم تحديث: {item['name']} - {item['price']} ج.م")
    
    # ملخص
    print("\n" + "=" * 50)
    print("📊 ملخص العملية:")
    print(f"   ✅ أصناف جديدة: {added_count}")
    print(f"   🔄 أصناف محدّثة: {updated_count}")
    print(f"   📦 إجمالي الأصناف المضافة: {added_count + updated_count}")
    print(f"   🏭 المورد: {supplier.name}")
    print(f"   📁 الفئة: {category.name}")
    print("=" * 50)

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🏭 إضافة أصناف إسفنج SAFA FOAM")
    print("📅 قائمة أسعار: 22 نوفمبر 2025")
    print("=" * 50)
    
    add_safa_foam_products()
    
    print("\n✅ تمت العملية بنجاح!")
    print("يمكنك الآن رؤية الأصناف في: المخازن ← المواد الخام")
