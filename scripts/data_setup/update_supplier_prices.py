"""
تحديث أسعار الموردين بسهولة

الاستخدام:
    python manage.py shell < update_supplier_prices.py
"""

from django.db import transaction
from decimal import Decimal
from partners.models import Supplier, SupplierProduct
from inventory.models import Product

print("=" * 80)
print("💰 تحديث أسعار الموردين")
print("=" * 80)


# ═══════════════════════════════════════════════════════════════════════════════
# 📝 عدّل الأسعار هنا
# ═══════════════════════════════════════════════════════════════════════════════

# مثال: تحديث أسعار الإسفنج من المورد أ
PRICE_UPDATES = [
    {
        'supplier_code': 'FOAM-SUP-A',  # كود المورد
        'product_sku': 'FOAM-D18',      # كود المنتج
        'new_price': Decimal('3150'),   # السعر الجديد
    },
    {
        'supplier_code': 'FOAM-SUP-A',
        'product_sku': 'FOAM-D30',
        'new_price': Decimal('4200'),
    },
    # أضف المزيد هنا...
]


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 لا تعدل تحت هذا الخط
# ═══════════════════════════════════════════════════════════════════════════════

def update_prices():
    """تحديث الأسعار"""
    
    print("\n📊 تحديث الأسعار...")
    print("-" * 80)
    
    updated_count = 0
    not_found_count = 0
    
    for update in PRICE_UPDATES:
        try:
            supplier = Supplier.objects.get(code=update['supplier_code'])
            product = Product.objects.get(sku=update['product_sku'])
            
            sp = SupplierProduct.objects.get(
                supplier=supplier,
                product=product
            )
            
            old_price = sp.price
            sp.price = update['new_price']
            sp.save()
            
            # تحديث تكلفة المنتج إذا كان هذا المورد هو المفضل
            if sp.is_preferred:
                product.cost = update['new_price']
                product.save(update_fields=['cost'])
                print(f"   ✅ {product.name} ← {supplier.name}")
                print(f"      السعر القديم: {old_price} ج/م³")
                print(f"      السعر الجديد: {update['new_price']} ج/م³")
                print(f"      🔄 تم تحديث تكلفة المنتج أيضاً")
            else:
                print(f"   ✅ {product.name} ← {supplier.name}")
                print(f"      السعر القديم: {old_price} ج/م³")
                print(f"      السعر الجديد: {update['new_price']} ج/م³")
            
            updated_count += 1
            
        except Supplier.DoesNotExist:
            print(f"   ⚠️  المورد {update['supplier_code']} غير موجود!")
            not_found_count += 1
        except Product.DoesNotExist:
            print(f"   ⚠️  المنتج {update['product_sku']} غير موجود!")
            not_found_count += 1
        except SupplierProduct.DoesNotExist:
            print(f"   ⚠️  لا يوجد ربط بين المورد {update['supplier_code']} والمنتج {update['product_sku']}!")
            not_found_count += 1
    
    print("\n" + "=" * 80)
    print(f"✅ تم تحديث {updated_count} سعر")
    if not_found_count > 0:
        print(f"⚠️  {not_found_count} تحديث فشل")
    print("=" * 80)


# تنفيذ
with transaction.atomic():
    update_prices()

print("\n💡 لتحديث أسعار أخرى:")
print("   1. افتح الملف: update_supplier_prices.py")
print("   2. عدّل قائمة PRICE_UPDATES")
print("   3. شغل السكريبت مرة أخرى")

