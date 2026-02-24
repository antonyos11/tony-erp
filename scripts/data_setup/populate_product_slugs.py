#!/usr/bin/env python3
"""
سكريبت لتوليد slugs للمنتجات الموجودة
"""
import os
import sys
import django
from django.utils.text import slugify

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from ecommerce.models import OnlineProduct

print("🔄 تحديث slugs للمنتجات الموجودة...")

products = OnlineProduct.objects.filter(slug__isnull=True) | OnlineProduct.objects.filter(slug='')
count = products.count()

print(f"📦 وُجد {count} منتج بدون slug")

for i, product in enumerate(products, 1):
    if product.display_name:
        base_slug = slugify(product.display_name, allow_unicode=True)
    else:
        base_slug = slugify(product.inventory_item.name if product.inventory_item else f"product-{product.id}", allow_unicode=True)
    
    # التأكد من أن slug فريد
    slug = base_slug
    counter = 1
    while OnlineProduct.objects.filter(slug=slug).exclude(id=product.id).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    product.slug = slug
    product.save(update_fields=['slug'])
    
    if i % 10 == 0:
        print(f"  ✓ تم تحديث {i}/{count}")

print(f"\n✅ تم تحديث جميع الـ slugs بنجاح!")
