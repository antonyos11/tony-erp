#!/usr/bin/env python
"""اختبار قائمة المحاسبة المنظمة الجديدة"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from accounting.navigation import BASE_NAVIGATION

print("=" * 80)
print("📋 قائمة المحاسبة المنظمة الجديدة")
print("=" * 80)

total_items = 0
for i, section in enumerate(BASE_NAVIGATION, 1):
    emoji = "🔵" if "daily" in section.key else ("🟢" if "master" in section.key else "🟡")
    print(f"\n{emoji} {i}. {section.label} ({section.key})")
    print(f"   الأيقونة: {section.icon}")
    print(f"   البنود: {len(section.items)}")
    total_items += len(section.items)
    
    for j, item in enumerate(section.items, 1):
        badge_txt = f" [شارة: {item.badge}]" if item.badge else ""
        shortcut_txt = f" ({item.shortcut})" if item.shortcut else ""
        print(f"      {j}. {item.label}{badge_txt}{shortcut_txt}")

print("\n" + "=" * 80)
print(f"✅ المجموع: {len(BASE_NAVIGATION)} مجموعات، {total_items} بند")
print("=" * 80)
