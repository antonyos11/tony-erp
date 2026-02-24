#!/usr/bin/env python3
"""
سكريبت سريع لملء slugs وإنشاء كوبون تجريبي
"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from ecommerce.models import OnlineProduct, Coupon
from django.utils.text import slugify
from datetime import datetime, timedelta

print("🔧 1. ملء slugs للمنتجات...")
count = 0
for i, p in enumerate(OnlineProduct.objects.all(), 1):
    if not p.slug:
        base_slug = slugify(p.display_name or (p.inventory_item.name if p.inventory_item else f"product-{i}"))
        slug = base_slug
        counter = 1
        while OnlineProduct.objects.filter(slug=slug).exclude(id=p.id).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        p.slug = slug
        p.save(update_fields=['slug'])
        count += 1
print(f"✅ تم تحديث {count} منتج")

print("\n🎟️ 2. إنشاء كوبون تجريبي...")
coupon, created = Coupon.objects.get_or_create(
    code="WELCOME10",
    defaults={
        'discount_type': 'percentage',
        'discount_value': 10,
        'valid_from': datetime.now(),
        'valid_to': datetime.now() + timedelta(days=365),
        'is_active': True,
        'min_order_amount': 0
    }
)
print(f"✅ كوبون {'تم إنشاؤه' if created else 'موجود'}: {coupon.code} - خصم {coupon.discount_value}%")

print("\n✅ تم بنجاح!")
