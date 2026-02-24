#!/usr/bin/env python
"""إصلاح الأرقام المكررة في طلبات المواد"""
import os
import sys
import django

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from inventory.models import Requisition
from django.db.models import Count

print("🔍 البحث عن الأرقام المكررة...")

# البحث عن الأرقام المكررة
duplicates = Requisition.objects.values('number').annotate(
    count=Count('id')
).filter(count__gt=1)

if not duplicates:
    print("✅ لا توجد أرقام مكررة!")
else:
    print(f"⚠️ وجدت {len(duplicates)} رقم مكرر:")
    
    for dup in duplicates:
        number = dup['number']
        count = dup['count']
        print(f"\n  الرقم: {number} (مكرر {count} مرة)")
        
        # جلب جميع السجلات بهذا الرقم
        reqs = Requisition.objects.filter(number=number).order_by('id')
        
        # الاحتفاظ بالأول وتعديل الباقي
        for i, req in enumerate(reqs):
            if i == 0:
                print(f"    ✓ الاحتفاظ بـ: {req.id} - {req.number}")
            else:
                import time
                new_number = f"{number}-FIX{i}-{int(time.time())}"
                old_number = req.number
                req.number = new_number
                req.save()
                print(f"    → تم تغيير {req.id}: {old_number} → {new_number}")

print("\n✅ تم إصلاح جميع التكرارات!")
