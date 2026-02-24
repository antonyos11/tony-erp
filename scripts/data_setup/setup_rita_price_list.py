#!/usr/bin/env python3
"""
سكريبت إنشاء بيانات قوائم الأسعار التجريبية
Setup Sample Price List Data - Rita Mattresses

الاستخدام:
    python manage.py shell < setup_rita_price_list.py
    أو
    python manage.py runscript setup_rita_price_list
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from decimal import Decimal
from smart_pricing.models_price_list import (
    ProductSize, ProductFamily, ProductVariant, 
    CostCategory, PriceList, ProductVariantPrice, PriceListSettings
)


def create_sizes():
    """إنشاء المقاسات الشائعة للمراتب"""
    print("📏 إنشاء المقاسات...")
    
    # مقاسات المراتب الشائعة
    sizes_data = [
        # (العرض، الطول، معامل السعر)
        (90, 190, 1.000),
        (90, 195, 1.029),
        (90, 200, 1.053),
        (100, 190, 1.111),
        (100, 195, 1.140),
        (100, 200, 1.170),
        (120, 190, 1.333),
        (120, 195, 1.368),
        (120, 200, 1.404),
        (140, 190, 1.556),
        (140, 195, 1.596),
        (140, 200, 1.637),
        (150, 190, 1.667),
        (150, 195, 1.711),
        (150, 200, 1.754),
        (160, 190, 1.778),
        (160, 195, 1.825),
        (160, 200, 1.871),
        (175, 190, 1.944),
        (175, 195, 1.996),
        (175, 200, 2.047),
        (180, 190, 2.000),
        (180, 195, 2.053),
        (180, 200, 2.105),
        (190, 190, 2.111),
        (190, 195, 2.167),
        (190, 200, 2.222),
        (200, 200, 2.339),
    ]
    
    created = 0
    for idx, (width, length, multiplier) in enumerate(sizes_data):
        size, was_created = ProductSize.objects.get_or_create(
            width=width,
            length=length,
            defaults={
                'price_multiplier': Decimal(str(multiplier)),
                'cost_multiplier': Decimal(str(multiplier)),
                'sort_order': idx,
            }
        )
        if was_created:
            created += 1
    
    print(f"   ✅ تم إنشاء {created} مقاس جديد")
    return ProductSize.objects.all()


def create_product_families(sizes):
    """إنشاء عائلات منتجات ريتا"""
    print("📦 إنشاء عائلات المنتجات...")
    
    # بيانات المنتجات من قائمة ريتا
    families_data = [
        # (الكود، الاسم، السعر الأساسي، التكلفة الأساسية)
        ('LITE-RITA', 'لايت ريتا', 5067, 3500),
        ('MEDIUM-FOAM', 'ميديوم فوم', 4301, 3000),
        ('FULL-FOAM', 'فل فوم', 3658, 2500),
        ('POCKET', 'بوكيت', 10008, 7000),
        ('TANKEL', 'تنكل', 12196, 8500),
        ('ZEFIRA', 'زفيره', 10352, 7200),
        ('MILAN-POCKET', 'ميلان بوكيت', 9090, 6300),
        ('TREBIA', 'تربيز', 6571, 4500),
        ('COMFORT', 'كومفورت', 5697, 3900),
        ('TROPEZ', 'تروبيز', 4320, 3000),
        ('LAND-SURIZES', 'لاند سروريز', 4082, 2800),
        ('FULL-SURIZES', 'فل سروريز', 4679, 3200),
        ('LURA-BAS', 'لوراباس', 3866, 2700),
        ('LURA', 'لورا', 4345, 3000),
    ]
    
    # الحصول على كل المقاسات النشطة
    all_sizes = ProductSize.objects.filter(is_active=True)
    
    created = 0
    for code, name, base_price, base_cost in families_data:
        family, was_created = ProductFamily.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'name_en': code.replace('-', ' ').title(),
                'base_price': Decimal(str(base_price)),
                'base_cost': Decimal(str(base_cost)),
                'show_in_price_list': True,
            }
        )
        if was_created:
            # ربط المقاسات
            family.available_sizes.set(all_sizes)
            created += 1
    
    print(f"   ✅ تم إنشاء {created} عائلة منتجات")
    return ProductFamily.objects.all()


def create_price_lists():
    """إنشاء قوائم الأسعار"""
    print("📋 إنشاء قوائم الأسعار...")
    
    lists_data = [
        # (الكود، الاسم، النوع، الخصم، شامل الضريبة)
        ('RETAIL', 'أسعار القطاعي', 'retail', 0, False),
        ('WHOLESALE', 'أسعار الجملة', 'wholesale', 15, False),
        ('DISTRIBUTOR', 'أسعار الموزعين', 'distributor', 25, False),
        ('RETAIL-TAX', 'أسعار القطاعي شامل الضريبة', 'retail', 0, True),
        ('VIP', 'أسعار عملاء VIP', 'vip', 10, False),
    ]
    
    created = 0
    for code, name, list_type, discount, includes_tax in lists_data:
        pl, was_created = PriceList.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'list_type': list_type,
                'discount_percentage': Decimal(str(discount)),
                'includes_tax': includes_tax,
                'tax_rate': Decimal('14.00'),  # ضريبة مصر
                'is_default': code == 'RETAIL',
            }
        )
        if was_created:
            created += 1
    
    print(f"   ✅ تم إنشاء {created} قائمة أسعار")
    return PriceList.objects.all()


def create_cost_categories():
    """إنشاء فئات التكاليف"""
    print("💰 إنشاء فئات التكاليف...")
    
    categories_data = [
        ('مواد خام - فوم', 'direct_material', True, 0),
        ('مواد خام - قماش', 'direct_material', True, 1),
        ('مواد خام - سوست', 'direct_material', True, 2),
        ('مواد خام - إسفنج', 'direct_material', True, 3),
        ('أجور عمال مباشرة', 'direct_labor', True, 10),
        ('مصاريف تصنيع غير مباشرة', 'manufacturing_overhead', False, 20),
        ('مصاريف كهرباء ومياه', 'manufacturing_overhead', False, 21),
        ('مصاريف إيجار', 'admin_expense', False, 30),
        ('مصاريف إدارية', 'admin_expense', False, 31),
        ('مصاريف تغليف', 'packaging', True, 40),
        ('مصاريف شحن', 'shipping', True, 41),
    ]
    
    created = 0
    for name, cost_type, is_direct, sort_order in categories_data:
        cat, was_created = CostCategory.objects.get_or_create(
            name=name,
            defaults={
                'cost_type': cost_type,
                'is_direct': is_direct,
                'sort_order': sort_order,
            }
        )
        if was_created:
            created += 1
    
    print(f"   ✅ تم إنشاء {created} فئة تكلفة")


def create_settings():
    """إنشاء إعدادات النظام"""
    print("⚙️ إنشاء الإعدادات...")
    
    settings = PriceListSettings.get_settings()
    settings.company_name = 'ريتا للمراتب'
    settings.company_name_en = 'RITA FOR MATTRESSES'
    settings.phone = '01234567890'
    settings.email = 'info@ritamattresses.com'
    settings.website = 'www.ritamattresses.com'
    settings.default_tax_rate = Decimal('14.00')
    settings.price_validity_text = 'الأسعار صالحة من تاريخ الإصدار'
    settings.save()
    
    print("   ✅ تم حفظ الإعدادات")


def generate_variant_prices(families, price_lists):
    """إنشاء أسعار النسخ"""
    print("💵 إنشاء أسعار النسخ...")
    
    created = 0
    for family in families:
        for size in family.available_sizes.all():
            # إنشاء نسخة المنتج
            variant, _ = ProductVariant.objects.get_or_create(
                family=family,
                size=size,
            )
            
            # إنشاء أسعار لكل قائمة
            for pl in price_lists:
                vp, was_created = ProductVariantPrice.objects.get_or_create(
                    family=family,
                    size=size,
                    price_list=pl,
                )
                if was_created:
                    created += 1
    
    print(f"   ✅ تم إنشاء {created} سعر")


def main():
    """الدالة الرئيسية"""
    print("\n" + "="*60)
    print("🏭 إعداد بيانات قوائم أسعار ريتا للمراتب")
    print("="*60 + "\n")
    
    # إنشاء البيانات
    sizes = create_sizes()
    families = create_product_families(sizes)
    price_lists = create_price_lists()
    create_cost_categories()
    create_settings()
    generate_variant_prices(families, price_lists)
    
    print("\n" + "="*60)
    print("✅ تم إعداد البيانات بنجاح!")
    print("="*60)
    
    # ملخص
    print(f"""
📊 ملخص:
   - المقاسات: {ProductSize.objects.count()}
   - عائلات المنتجات: {ProductFamily.objects.count()}
   - قوائم الأسعار: {PriceList.objects.count()}
   - نسخ المنتجات: {ProductVariant.objects.count()}
   - أسعار النسخ: {ProductVariantPrice.objects.count()}
   - فئات التكاليف: {CostCategory.objects.count()}

🔗 للوصول للنظام:
   - لوحة التحكم: /smart-pricing/price-lists/
   - Admin: /admin/smart_pricing/
""")


if __name__ == '__main__':
    main()
