#!/usr/bin/env python3
"""
سكريبت إضافة عائلة منتجات جديدة (نوع مرتبة)
"""

import os
import sys
import django

sys.path.insert(0, '/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from smart_pricing.models_price_list import ProductFamily, ProductSize, ProductVariant
from decimal import Decimal


def add_new_mattress_type(
    code: str,
    name_ar: str,
    name_en: str,
    base_price: float,
    base_cost: float,
    height: int = 30
):
    """
    إضافة نوع مرتبة جديد
    
    Args:
        code: الكود (مثل: ROYAL)
        name_ar: الاسم بالعربية (مثل: رويال)
        name_en: الاسم بالإنجليزية (مثل: Royal)
        base_price: السعر الأساسي لأصغر مقاس (90×190)
        base_cost: التكلفة الأساسية لأصغر مقاس
        height: ارتفاع المرتبة بالسم
    """
    
    # التحقق من عدم وجود نفس الكود
    if ProductFamily.objects.filter(code=code).exists():
        print(f'❌ الكود {code} موجود مسبقاً!')
        return None
    
    # إنشاء العائلة
    family = ProductFamily.objects.create(
        code=code,
        name=name_ar,
        name_en=name_en,
        base_price=Decimal(str(base_price)),
        base_cost=Decimal(str(base_cost)),
        default_height=height,
        is_active=True,
        show_in_price_list=True,
    )
    
    # ربط جميع المقاسات المتاحة
    sizes = ProductSize.objects.filter(is_active=True)
    family.available_sizes.set(sizes)
    
    # إنشاء variants لكل مقاس
    for size in sizes:
        ProductVariant.objects.get_or_create(
            family=family,
            size=size,
            defaults={'is_active': True}
        )
    
    print(f'✅ تم إنشاء عائلة: {family.name} ({family.code})')
    print(f'   السعر الأساسي: {family.base_price}')
    print(f'   التكلفة الأساسية: {family.base_cost}')
    print(f'   عدد المقاسات: {sizes.count()}')
    
    return family


def update_mattress_price(code: str, new_base_price: float = None, new_base_cost: float = None):
    """
    تحديث سعر نوع مرتبة موجود
    """
    try:
        family = ProductFamily.objects.get(code=code)
        
        if new_base_price:
            old_price = family.base_price
            family.base_price = Decimal(str(new_base_price))
            print(f'💰 تم تحديث السعر: {old_price} → {family.base_price}')
        
        if new_base_cost:
            old_cost = family.base_cost
            family.base_cost = Decimal(str(new_base_cost))
            print(f'📦 تم تحديث التكلفة: {old_cost} → {family.base_cost}')
        
        family.save()
        print(f'✅ تم تحديث {family.name} بنجاح!')
        
        return family
        
    except ProductFamily.DoesNotExist:
        print(f'❌ الكود {code} غير موجود!')
        return None


def list_all_mattress_types():
    """
    عرض جميع أنواع المراتب
    """
    families = ProductFamily.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    print('\n' + '='*80)
    print('🛏️ قائمة أنواع المراتب')
    print('='*80)
    print(f'{"الكود":15} | {"الاسم":20} | {"السعر الأساسي":>12} | {"التكلفة":>12} | {"الهامش %":>8}')
    print('-'*80)
    
    for f in families:
        margin = ((f.base_price - f.base_cost) / f.base_price * 100) if f.base_price > 0 else 0
        print(f'{f.code:15} | {f.name:20} | {f.base_price:>12.2f} | {f.base_cost:>12.2f} | {margin:>7.1f}%')
    
    print('='*80)
    print(f'📊 إجمالي: {families.count()} نوع\n')


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='إدارة أنواع المراتب')
    parser.add_argument('action', choices=['add', 'update', 'list'], help='الإجراء')
    parser.add_argument('--code', help='كود المرتبة')
    parser.add_argument('--name-ar', help='الاسم بالعربية')
    parser.add_argument('--name-en', help='الاسم بالإنجليزية')
    parser.add_argument('--price', type=float, help='السعر الأساسي')
    parser.add_argument('--cost', type=float, help='التكلفة الأساسية')
    parser.add_argument('--height', type=int, default=30, help='الارتفاع بالسم')
    
    args = parser.parse_args()
    
    if args.action == 'list':
        list_all_mattress_types()
    
    elif args.action == 'add':
        if not all([args.code, args.name_ar, args.price, args.cost]):
            print('❌ مطلوب: --code, --name-ar, --price, --cost')
        else:
            add_new_mattress_type(
                code=args.code,
                name_ar=args.name_ar,
                name_en=args.name_en or args.code,
                base_price=args.price,
                base_cost=args.cost,
                height=args.height
            )
    
    elif args.action == 'update':
        if not args.code:
            print('❌ مطلوب: --code')
        else:
            update_mattress_price(
                code=args.code,
                new_base_price=args.price,
                new_base_cost=args.cost
            )
