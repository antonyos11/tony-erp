#!/usr/bin/env python
"""
تحديث أصناف Safa Star - الوحدة بالكيلو
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
sys.path.insert(0, '/var/www/tony_erp')
django.setup()

from inventory.models import Product, Category
from partners.models import Supplier
from decimal import Decimal

def update_safa_star_kg():
    """تحديث أصناف Safa Star للكيلو"""
    
    category, _ = Category.objects.get_or_create(
        name='إسفنج',
        defaults={'description': 'مواد خام - إسفنج بجميع الكثافات'}
    )
    
    supplier = Supplier.objects.filter(name__icontains='الصفا').first()
    if not supplier:
        supplier, _ = Supplier.objects.get_or_create(
            name='مصنع الصفا والمدائن للإسفنج',
            defaults={'phone': '', 'email': '', 'address': ''}
        )
    
    # Safa Star - السعر بالكيلو
    safa_star = [
        {'density': 16, 'color': 'أبيض', 'price_block': 116, 'price_cut': 125},
        {'density': 18, 'color': 'أخضر', 'price_block': 112, 'price_cut': 121},
        {'density': 20, 'color': 'أخضر/بيج', 'price_block': 112, 'price_cut': 121},
        {'density': 22, 'color': 'أصفر ليموني', 'price_block': 112, 'price_cut': 121},
        {'density': 24, 'color': 'برتقالي/أسود', 'price_block': 112, 'price_cut': 121},
        {'density': 26, 'color': 'كحلي', 'price_block': 112, 'price_cut': 121},
        {'density': 28, 'color': 'بنفسجي', 'price_block': 112, 'price_cut': 121},
        {'density': 30, 'color': 'أزرق رمادي', 'price_block': 112, 'price_cut': 121},
        {'density': 33, 'color': 'أحمر/أخضر', 'price_block': 112, 'price_cut': 121},
        {'density': 35, 'color': 'كريمي', 'price_block': 112, 'price_cut': 121},
        {'density': 40, 'color': 'تركوازي', 'price_block': 112, 'price_cut': 121},
    ]
    
    # سوفت
    soft = [
        {'density': 26, 'color': 'أصفر', 'price_block': 112, 'price_cut': 121},
        {'density': 30, 'color': 'وردي', 'price_block': 112, 'price_cut': 121},
    ]
    
    print("\n📦 تحديث أصناف Safa Star (بالكيلو):")
    print("-" * 50)
    
    for item in safa_star:
        sku = f"STAR-D{item['density']}"
        name = f"إسفنج Safa Star D{item['density']} - {item['color']}"
        
        product, created = Product.objects.update_or_create(
            sku=sku,
            defaults={
                'name': name,
                'category': category,
                'product_type': 'raw_material',
                'purchase_uom': 'kg',  # بالكيلو
                'usage_uom': 'kg',
                'conversion_factor': Decimal('1.0000'),
                'cost': Decimal(str(item['price_block'])),
                'price': Decimal(str(item['price_cut'])),
                'preferred_supplier': supplier,
                'description': f"إسفنج Safa Star كثافة {item['density']} - لون {item['color']}\nسعر البلوكة: {item['price_block']} ج.م/كجم\nسعر المقصوص: {item['price_cut']} ج.م/كجم",
            }
        )
        status = "✅ جديد" if created else "🔄 تحديث"
        print(f"  {status}: {name} - {item['price_block']} ج.م/كجم")
    
    print("\n📦 تحديث أصناف سوفت (بالكيلو):")
    print("-" * 50)
    
    for item in soft:
        sku = f"STAR-D{item['density']}-SOFT"
        name = f"إسفنج Safa Star D{item['density']} سوفت - {item['color']}"
        
        product, created = Product.objects.update_or_create(
            sku=sku,
            defaults={
                'name': name,
                'category': category,
                'product_type': 'raw_material',
                'purchase_uom': 'kg',  # بالكيلو
                'usage_uom': 'kg',
                'conversion_factor': Decimal('1.0000'),
                'cost': Decimal(str(item['price_block'])),
                'price': Decimal(str(item['price_cut'])),
                'preferred_supplier': supplier,
                'internal_code': f"STAR-SOFT-D{item['density']}",
                'description': f"إسفنج سوفت Safa Star كثافة {item['density']} - لون {item['color']}\nسعر البلوكة: {item['price_block']} ج.م/كجم\nسعر المقصوص: {item['price_cut']} ج.م/كجم",
            }
        )
        status = "✅ جديد" if created else "🔄 تحديث"
        print(f"  {status}: {name} - {item['price_block']} ج.م/كجم")
    
    # تحديث الأصناف القديمة للكيلو أيضاً
    print("\n📦 تحديث الأصناف القديمة للكيلو:")
    print("-" * 50)
    
    updated = Product.objects.filter(
        product_type='raw_material',
        category=category,
        purchase_uom='m3'
    ).update(purchase_uom='kg', usage_uom='kg')
    
    print(f"  🔄 تم تحديث {updated} صنف من م³ إلى كجم")
    
    print("\n" + "=" * 50)
    print("✅ تم التحديث بنجاح!")
    print("   الوحدة الآن: كيلوجرام (كجم)")
    print("=" * 50)

if __name__ == '__main__':
    update_safa_star_kg()
