#!/usr/bin/env python
"""
Test script to verify accounting menu reorganization
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from core.sidebar_config import SIDEBAR_CONFIG, group_items_by_category, CATEGORY_DAILY, CATEGORY_MASTER, CATEGORY_REPORTS

def test_accounting_menu():
    """Test the reorganized accounting menu"""
    
    print("=" * 80)
    print("اختبار قائمة المحاسبة المنظمة")
    print("=" * 80)
    
    acc = SIDEBAR_CONFIG['accounting']
    items = acc['items']
    
    print(f"\n📊 إجمالي البنود: {len(items)}")
    
    # Group by category
    grouped = group_items_by_category(items)
    
    print(f"\n🔵 عمليات يومية: {len(grouped[CATEGORY_DAILY])} بنود")
    print(f"🟢 تعريفات: {len(grouped[CATEGORY_MASTER])} بنود")
    print(f"🟡 تقارير: {len(grouped[CATEGORY_REPORTS])} بنود")
    
    # Check ordering
    print("\n" + "=" * 80)
    print("العمليات اليومية (مرتبة حسب الأولوية)")
    print("=" * 80)
    for i, item in enumerate(grouped[CATEGORY_DAILY], 1):
        order = item.get('order', '??')
        label = item.get('label', 'N/A')
        badge = f" [شارة: {item['badge_key']}]" if 'badge_key' in item else ""
        print(f"{i}. (order={order:2}) {label}{badge}")
    
    print("\n" + "=" * 80)
    print("التعريفات والإعدادات (مرتبة حسب الأولوية)")
    print("=" * 80)
    for i, item in enumerate(grouped[CATEGORY_MASTER], 1):
        order = item.get('order', '??')
        label = item.get('label', 'N/A')
        print(f"{i}. (order={order:2}) {label}")
    
    print("\n" + "=" * 80)
    print("التقارير والاستعلامات (مرتبة حسب الأولوية)")
    print("=" * 80)
    for i, item in enumerate(grouped[CATEGORY_REPORTS], 1):
        order = item.get('order', '??')
        label = item.get('label', 'N/A')
        print(f"{i}. (order={order:2}) {label}")
    
    # Verify all items have order
    missing_order = [item['id'] for item in items if 'order' not in item]
    if missing_order:
        print(f"\n⚠️  تحذير: البنود التالية لا تحتوي على ترتيب (order): {missing_order}")
    else:
        print("\n✅ جميع البنود تحتوي على ترتيب (order)")
    
    # Check for badges
    badges = [item['id'] for item in items if 'badge_key' in item]
    print(f"\n🔔 البنود ذات الشارات: {len(badges)}")
    for item_id in badges:
        item = next(i for i in items if i['id'] == item_id)
        print(f"   - {item['label']}: {item['badge_key']}")
    
    print("\n" + "=" * 80)
    print("✅ الاختبار اكتمل بنجاح!")
    print("=" * 80)

if __name__ == '__main__':
    test_accounting_menu()
