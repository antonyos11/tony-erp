#!/usr/bin/env python3
"""
إضافة بيانات تجريبية متقدمة للمخزون مع منتجات منخفضة المخزون
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from inventory.models import Product, Location, Stock
from django.db import transaction


def create_low_stock_scenarios():
    """إنشاء سيناريوهات مخزون منخفض لاختبار النظام"""
    
    print("بدء إنشاء بيانات متقدمة للمخزون المنخفض...")
    
    with transaction.atomic():
        # الحصول على المواقع الموجودة أو إنشاء موقع افتراضي
        default_location = Location.objects.get_or_create(
            code='MAIN',
            defaults={
                'name': 'المستودع الرئيسي',
                'type': 'warehouse',
                'is_default': True,
                'is_active': True,
            }
        )[0]
        
        # إنشاء مواقع إضافية
        locations = []
        location_data = [
            ('STORE1', 'متجر الفرع الأول', 'retail'),
            ('STORE2', 'متجر الفرع الثاني', 'retail'),
            ('BACKUP', 'مستودع النسخ الاحتياطي', 'warehouse'),
        ]
        
        for code, name, loc_type in location_data:
            location, created = Location.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'type': loc_type,
                    'is_active': True,
                }
            )
            locations.append(location)
            if created:
                print(f"   تم إنشاء موقع: {name}")
        
        # إنشاء منتجات مع حالات مخزون مختلفة
        products_data = [
            # منتجات نفد مخزونها (للإنذارات الحرجة)
            ('CRIT001', 'أقلام جافة زرقاء', 'أقلام كتابة عالية الجودة', 2.50, 1.20, 0, 10),
            ('CRIT002', 'دفاتر مسطرة A4', 'دفاتر للمكاتب والمدارس', 8.00, 4.50, 0, 15),
            ('CRIT003', 'مشابك ورق معدنية', 'مشابك للأوراق الرسمية', 5.00, 2.80, 0, 20),
            
            # منتجات مخزون منخفض
            ('LOW001', 'أوراق طباعة A4', 'أوراق بيضاء للطباعة', 12.00, 8.50, 3, 50),
            ('LOW002', 'أقلام رصاص HB', 'أقلام رصاص للكتابة والرسم', 1.75, 0.90, 8, 25),
            ('LOW003', 'مجلدات بلاستيكية', 'مجلدات لحفظ الأوراق', 6.50, 3.20, 5, 30),
            ('LOW004', 'شريط لاصق شفاف', 'شريط لاصق للمكاتب', 3.25, 1.60, 12, 40),
            
            # منتجات مخزون جيد
            ('GOOD001', 'طابعة ليزر HP', 'طابعة مكتبية عالية الجودة', 850.00, 650.00, 45, 10),
            ('GOOD002', 'كراسي مكتبية', 'كراسي مريحة للعمل', 320.00, 220.00, 28, 5),
            ('GOOD003', 'شاشات كمبيوتر 24 بوصة', 'شاشات عالية الدقة', 450.00, 350.00, 35, 8),
            
            # منتجات مخزون عالي
            ('HIGH001', 'أكواب القهوة الورقية', 'أكواب يمكن التخلص منها', 0.25, 0.10, 2500, 100),
            ('HIGH002', 'أكياس بلاستيكية صغيرة', 'أكياس للنفايات المكتبية', 0.15, 0.08, 5000, 200),
            ('HIGH003', 'مناديل ورقية', 'مناديل للاستخدام اليومي', 4.50, 2.20, 150, 20),
        ]
        
        created_products = []
        for sku, name, desc, price, cost, stock, min_stock in products_data:
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'description': desc,
                    'price': Decimal(str(price)),
                    'cost': Decimal(str(cost)),
                    'min_stock': min_stock,
                }
            )
            
            if created:
                created_products.append(product)
                print(f"   تم إنشاء منتج: {name} (مخزون: {stock})")
                
                # إنشاء مخزون في الموقع الافتراضي
                Stock.objects.get_or_create(
                    product=product,
                    location=default_location,
                    defaults={'quantity': stock}
                )
                
                # توزيع بعض المخزون على مواقع أخرى للمنتجات عالية المخزون
                if stock > 50:
                    for i, location in enumerate(locations[:2]):
                        additional_stock = max(1, stock // (4 + i))
                        Stock.objects.get_or_create(
                            product=product,
                            location=location,
                            defaults={'quantity': additional_stock}
                        )
        
        # إنشاء باركودات للمنتجات الجديدة
        for product in created_products:
            if not product.barcode:
                # إنشاء باركود بسيط (EAN-13 مبسط)
                base_code = f"2{product.id:011d}"
                # حساب check digit بسيط
                check_digit = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base_code)) % 10
                check_digit = (10 - check_digit) % 10
                product.barcode = base_code + str(check_digit)
                product.save()
        
    print(f"\nإحصائيات المخزون الجديدة:")
    print(f"   - المنتجات الجديدة: {len(created_products)}")

    # إحصائيات المخزون
    all_products = Product.objects.all()
    critical_stock = [p for p in all_products if p.current_stock == 0]
    low_stock = [p for p in all_products if p.is_low_stock and p.current_stock > 0]
    good_stock = [p for p in all_products if not p.is_low_stock and p.current_stock > 0]

    print(f"   - منتجات نفد مخزونها: {len(critical_stock)}")
    print(f"   - منتجات مخزون منخفض: {len(low_stock)}")
    print(f"   - منتجات مخزون جيد: {len(good_stock)}")

    total_value = sum(float(p.current_stock * (p.price or 0)) for p in all_products)
    print(f"   - إجمالي قيمة المخزون: {total_value:,.2f}")

    print("\nالمنتجات التي تحتاج إنذارات:")
    for product in (critical_stock + low_stock)[:10]:
        status = "نفد المخزون" if product.current_stock == 0 else "مخزون منخفض"
        print(f"   تنبيه: {product.name} - {status} (متبقي: {product.current_stock})")


if __name__ == '__main__':
    create_low_stock_scenarios()
    print("\nتم إنشاء بيانات المخزون المنخفض بنجاح!")
    print("\nلاختبار النظام:")
    print("   - زر لوحة تحكم المخزون")
    print("   - انقر على 'مراقبة المخزون المنخفض'")
    print("   - جرب 'التحليلات المتقدمة'")
    print("   - اختبر تصدير البيانات")