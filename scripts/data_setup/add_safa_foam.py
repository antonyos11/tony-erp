#!/usr/bin/env python
"""
سكريبت إضافة أصناف إسفنج الصفا
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
    """إضافة منتجات إسفنج الصفا"""
    
    # البحث عن أو إنشاء فئة المواد الخام
    category, created = Category.objects.get_or_create(
        name='إسفنج',
        defaults={'description': 'مواد خام - إسفنج بجميع الكثافات'}
    )
    if created:
        print(f"✅ تم إنشاء فئة: {category.name}")
    
    # البحث عن أو إنشاء مورد الصفا
    supplier, created = Supplier.objects.get_or_create(
        name='مصنع الصفا والمدائن للإسفنج',
        defaults={
            'phone': '',
            'email': '',
            'address': ''
        }
    )
    if created:
        print(f"✅ تم إنشاء مورد: {supplier.name}")
    
    # قائمة أصناف Safa Star
    safa_star_products = [
        {'density': 16, 'color': 'أبيض', 'price_block': 112, 'price_cut': 125},
        {'density': 18, 'color': 'أخضر', 'price_block': 112, 'price_cut': 121},
        {'density': 20, 'color': 'أخضر', 'price_block': 112, 'price_cut': 121},
        {'density': 22, 'color': 'أصفر ليموني', 'price_block': 112, 'price_cut': 121},
        {'density': 25, 'color': 'برتقالي/أسود', 'price_block': 112, 'price_cut': 121},
        {'density': 26, 'color': 'كحلي', 'price_block': 112, 'price_cut': 121},
        {'density': 28, 'color': 'كحلي', 'price_block': 112, 'price_cut': 121},
        {'density': 30, 'color': 'أزرق رمادي', 'price_block': 112, 'price_cut': 121},
        {'density': 33, 'color': 'بنفسجي', 'price_block': 112, 'price_cut': 121},
        {'density': 38, 'color': 'كريمي', 'price_block': 112, 'price_cut': 121},
        {'density': 40, 'color': 'تركوازي', 'price_block': 112, 'price_cut': 121},
    ]
    
    # قائمة أصناف سوفت
    soft_products = [
        {'density': 26, 'color': 'أصفر', 'price_block': 112, 'price_cut': 112, 'type': 'سوفت'},
        {'density': 30, 'color': 'وردي', 'price_block': 112, 'price_cut': 121, 'type': 'سوفت'},
    ]
    
    added_count = 0
    updated_count = 0
    
    # إضافة منتجات Safa Star
    print("\n📦 إضافة أصناف Safa Star:")
    print("-" * 50)
    
    for item in safa_star_products:
        sku = f"FOAM-D{item['density']}"
        name = f"إسفنج D{item['density']} - {item['color']} (Safa Star)"
        
        product, created = Product.objects.update_or_create(
            sku=sku,
            defaults={
                'name': name,
                'category': category,
                'product_type': 'raw_material',
                'purchase_uom': 'm3',
                'usage_uom': 'm3',
                'conversion_factor': Decimal('1.0000'),
                'cost': Decimal(str(item['price_block'])),
                'price': Decimal(str(item['price_cut'])),
                'preferred_supplier': supplier,
                'description': f"إسفنج كثافة {item['density']} - لون {item['color']}\nسعر البلوكة: {item['price_block']} ج.م/م³\nسعر المقصوص: {item['price_cut']} ج.م/م³",
            }
        )
        
        if created:
            added_count += 1
            print(f"  ✅ تمت إضافة: {name}")
        else:
            updated_count += 1
            print(f"  🔄 تم تحديث: {name}")
    
    # إضافة منتجات سوفت
    print("\n📦 إضافة أصناف سوفت:")
    print("-" * 50)
    
    for item in soft_products:
        sku = f"FOAM-D{item['density']}-SOFT"
        name = f"إسفنج D{item['density']} سوفت - {item['color']}"
        internal_code = f"SOFT-D{item['density']}"
        
        product, created = Product.objects.update_or_create(
            sku=sku,
            defaults={
                'name': name,
                'category': category,
                'product_type': 'raw_material',
                'purchase_uom': 'm3',
                'usage_uom': 'm3',
                'conversion_factor': Decimal('1.0000'),
                'cost': Decimal(str(item['price_block'])),
                'price': Decimal(str(item['price_cut'])),
                'preferred_supplier': supplier,
                'internal_code': internal_code,
                'description': f"إسفنج سوفت كثافة {item['density']} - لون {item['color']}\nسعر البلوكة: {item['price_block']} ج.م/م³\nسعر المقصوص: {item['price_cut']} ج.م/م³",
            }
        )
        
        if created:
            added_count += 1
            print(f"  ✅ تمت إضافة: {name}")
        else:
            updated_count += 1
            print(f"  🔄 تم تحديث: {name}")
    
    # ملخص
    print("\n" + "=" * 50)
    print("📊 ملخص العملية:")
    print(f"   ✅ أصناف جديدة: {added_count}")
    print(f"   🔄 أصناف محدّثة: {updated_count}")
    print(f"   📦 إجمالي الأصناف: {added_count + updated_count}")
    print(f"   🏭 المورد: {supplier.name}")
    print(f"   📁 الفئة: {category.name}")
    print("=" * 50)

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🏭 إضافة أصناف إسفنج الصفا والمدائن")
    print("📅 قائمة أسعار: 22 نوفمبر 2025")
    print("=" * 50)
    
    add_safa_foam_products()
    
    print("\n✅ تمت العملية بنجاح!")
    print("يمكنك الآن رؤية الأصناف في: المخازن ← المنتجات")
