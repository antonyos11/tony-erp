#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إضافة مخزون للمنتجات في جدول Stock
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from inventory.models import Product, Stock, Location
import random

def main():
    print("\n🔄 إضافة مخزون للمنتجات...\n")
    
    # الحصول على الموقع الأول
    location = Location.objects.first()
    if not location:
        print("❌ لا توجد مواقع في النظام!")
        return
    
    print(f"📍 الموقع: {location.name}\n")
    
    # الحصول على جميع المنتجات
    products = Product.objects.all()
    total = products.count()
    
    print(f"📦 عدد المنتجات: {total}\n")
    
    count = 0
    for product in products:
        # التحقق إذا كان المخزون موجود
        stock, created = Stock.objects.get_or_create(
            product=product,
            location=location,
            defaults={'quantity': random.randint(50, 200)}
        )
        
        if not created and stock.quantity == 0:
            # تحديث الكمية إذا كانت صفر
            stock.quantity = random.randint(50, 200)
            stock.save()
        
        count += 1
        if count % 100 == 0:
            print(f"✓ تم معالجة {count}/{total} منتج...")
    
    print(f"\n✅ تم إضافة/تحديث مخزون {count} منتج بنجاح!\n")
    
    # عرض عينة من المخزون
    print("📊 عينة من المخزون:")
    print("-" * 70)
    sample_stocks = Stock.objects.select_related('product').filter(location=location)[:10]
    for stock in sample_stocks:
        print(f"  {stock.product.name[:50]:50} | {stock.quantity:>4} وحدة | {stock.product.price:>8} ج.م")
    print("-" * 70)

if __name__ == '__main__':
    main()
