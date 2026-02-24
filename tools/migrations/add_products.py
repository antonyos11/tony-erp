#!/usr/bin/env python
"""إضافة منتجات جديدة للمخزون"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from inventory.models import Product, Location, Stock
from decimal import Decimal

new_products = [
    ('ELEC-001', 'شاشة LCD 24 بوصة', 1200.00, 800.00),
    ('ELEC-002', 'لوحة مفاتيح لاسلكية', 150.00, 80.00),
    ('ELEC-003', 'ماوس ألعاب', 200.00, 100.00),
    ('ELEC-004', 'سماعة بلوتوث', 350.00, 180.00),
    ('ELEC-005', 'شاحن سريع USB-C', 80.00, 40.00),
    ('OFF-001', 'طابعة ليزر', 1500.00, 900.00),
    ('OFF-002', 'ورق A4 500 ورقة', 45.00, 25.00),
    ('OFF-003', 'حبر طابعة أسود', 120.00, 60.00),
    ('OFF-004', 'دباسة معدنية', 25.00, 12.00),
    ('OFF-005', 'مجلد ملفات', 15.00, 7.00),
    ('FURN-001', 'كرسي مكتب دوار', 800.00, 450.00),
    ('FURN-002', 'مكتب خشبي 120سم', 1200.00, 700.00),
    ('CONS-001', 'زجاجة مياه 500مل', 3.00, 1.50),
    ('CONS-002', 'قهوة عربية 250جم', 45.00, 25.00),
]

location = Location.objects.filter(is_default=True).first() or Location.objects.first()
created_count = 0

for sku, name, price, cost in new_products:
    product, created = Product.objects.get_or_create(
        sku=sku,
        defaults={
            'name': name,
            'price': Decimal(str(price)),
            'cost': Decimal(str(cost)),
            'min_stock': 5,
        }
    )
    if created:
        created_count += 1
        Stock.objects.get_or_create(
            product=product,
            location=location,
            defaults={'quantity': 50}
        )
        print(f'Created: {name}')

print(f'Total created: {created_count}')
print(f'Total products: {Product.objects.count()}')
