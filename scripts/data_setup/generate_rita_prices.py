#!/usr/bin/env python3
"""
سكريبت توليد أسعار قائمة RITA للمراتب
يقوم بحساب وحفظ أسعار جميع المقاسات لجميع العائلات في قائمة الأسعار
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from smart_pricing.models_price_list import (
    PriceList, ProductFamily, ProductSize, ProductVariant, ProductVariantPrice
)
from decimal import Decimal


def generate_all_prices(price_list_id=6):
    """
    توليد جميع الأسعار لقائمة أسعار معينة
    
    Args:
        price_list_id: رقم قائمة الأسعار (افتراضي 6)
    """
    
    try:
        price_list = PriceList.objects.get(id=price_list_id)
        print(f'\n{"="*60}')
        print(f'توليد الأسعار لقائمة: {price_list.name}')
        print(f'{"="*60}\n')
    except PriceList.DoesNotExist:
        print(f'❌ قائمة الأسعار رقم {price_list_id} غير موجودة!')
        return
    
    # جلب جميع العائلات النشطة
    families = ProductFamily.objects.filter(
        is_active=True,
        show_in_price_list=True
    ).order_by('sort_order', 'name')
    
    # جلب جميع المقاسات النشطة
    sizes = ProductSize.objects.filter(is_active=True).order_by('sort_order')
    
    print(f'📦 عدد العائلات: {families.count()}')
    print(f'📏 عدد المقاسات: {sizes.count()}')
    print(f'🎯 إجمالي الأسعار المتوقعة: {families.count() * sizes.count()}\n')
    
    created_count = 0
    updated_count = 0
    skipped_count = 0
    
    for family in families:
        print(f'\n🔄 معالجة عائلة: {family.name} ({family.code})')
        print(f'   السعر الأساسي: {family.base_price}')
        print(f'   التكلفة الأساسية: {family.base_cost}')
        
        # التأكد من وجود المقاسات المتاحة
        available_sizes = family.available_sizes.all()
        if not available_sizes.exists():
            print(f'   ⚠️  لا توجد مقاسات متاحة لهذه العائلة - سيتم استخدام جميع المقاسات')
            available_sizes = sizes
        
        for size in available_sizes:
            # التحقق من وجود Variant أولاً
            variant, variant_created = ProductVariant.objects.get_or_create(
                family=family,
                size=size,
                defaults={
                    'is_active': True
                }
            )
            
            if variant_created:
                print(f'   ✨ تم إنشاء نسخة جديدة: {variant.sku}')
            
            # حساب السعر
            base_price = family.base_price * size.price_multiplier
            
            # تطبيق الخصم
            calculated_price = price_list.apply_discount(base_price)
            
            # حساب السعر النهائي (مع أو بدون ضريبة)
            final_price = price_list.apply_tax(calculated_price)
            
            # إنشاء أو تحديث السعر
            variant_price, created = ProductVariantPrice.objects.update_or_create(
                family=family,
                size=size,
                price_list=price_list,
                defaults={
                    'custom_price': None,  # استخدام الحساب التلقائي
                    'calculated_price': calculated_price,
                    'final_price': final_price,
                    'is_active': True,
                }
            )
            
            # حساب هامش الربح للعرض فقط
            base_cost = family.base_cost * size.cost_multiplier
            if calculated_price > 0 and base_cost > 0:
                margin_amount = calculated_price - base_cost
                margin_percentage = (margin_amount / calculated_price * 100) if calculated_price > 0 else Decimal('0')
            else:
                margin_amount = Decimal('0')
                margin_percentage = Decimal('0')
            
            if created:
                created_count += 1
                status = '✅ جديد'
            else:
                updated_count += 1
                status = '🔄 محدّث'
            
            # عرض تفاصيل السعر
            size_display = f"{size.width}×{size.length}"
            print(f'      {status} {size_display:15} | سعر: {final_price:>8.0f} | تكلفة: {base_cost:>8.0f} | هامش: {margin_percentage:>5.1f}%')
    
    print(f'\n{"="*60}')
    print(f'✨ اكتمل التوليد بنجاح!')
    print(f'{"="*60}')
    print(f'📊 الإحصائيات:')
    print(f'   ✅ أسعار جديدة: {created_count}')
    print(f'   🔄 أسعار محدّثة: {updated_count}')
    print(f'   📝 إجمالي الأسعار: {created_count + updated_count}')
    print(f'\n🔗 رابط القائمة: http://72.62.176.249/smart-pricing/price-lists/lists/{price_list_id}/\n')


def show_price_statistics(price_list_id=6):
    """عرض إحصائيات الأسعار"""
    from django.db.models import Count, Min, Max, Avg
    
    try:
        price_list = PriceList.objects.get(id=price_list_id)
    except PriceList.DoesNotExist:
        print(f'❌ قائمة الأسعار رقم {price_list_id} غير موجودة!')
        return
    
    prices = ProductVariantPrice.objects.filter(price_list=price_list)
    
    print(f'\n📊 إحصائيات قائمة الأسعار: {price_list.name}')
    print(f'{"="*60}')
    print(f'عدد الأسعار: {prices.count()}')
    
    if prices.exists():
        stats = prices.aggregate(
            min_price=Min('final_price'),
            max_price=Max('final_price'),
            avg_price=Avg('final_price'),
        )
        
        print(f'\n💰 الأسعار:')
        print(f'   الحد الأدنى: {stats["min_price"]:.2f}')
        print(f'   الحد الأقصى: {stats["max_price"]:.2f}')
        print(f'   المتوسط: {stats["avg_price"]:.2f}')
    
    print(f'{"="*60}\n')


if __name__ == '__main__':
    import sys
    
    # السماح بتمرير رقم قائمة الأسعار كمعامل
    price_list_id = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    
    print('\n🚀 بدء توليد أسعار المراتب...\n')
    
    generate_all_prices(price_list_id)
    show_price_statistics(price_list_id)
    
    print('✅ تم الانتهاء بنجاح!\n')
