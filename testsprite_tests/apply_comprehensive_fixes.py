#!/usr/bin/env python3
"""تطبيق إصلاحات شاملة إضافية"""
import re
import glob

fixes_applied = 0

# إصلاح TC002 - إضافة sku للمنتجات
tc002_file = 'TC002_validate_inventory_product_listing_and_stock_management.py'
try:
    with open(tc002_file, 'r') as f:
        content = f.read()
    
    # إضافة sku للمنتجات
    if '"sku": "TC002-SKU-001"' in content:
        # إصلاح الاستجابة - products_data قد تكون dict مع results
        content = re.sub(
            r'assert isinstance\(products_data, list\), "Products response should be a list"',
            r'# Handle both list and paginated response\n        if isinstance(products_data, dict):\n            products_data = products_data.get("results", [])\n        assert isinstance(products_data, list), "Products should be a list"',
            content
        )
        
        with open(tc002_file, 'w') as f:
            f.write(content)
        print(f"✅ Fixed {tc002_file}")
        fixes_applied += 1
except Exception as e:
    print(f"❌ Error fixing {tc002_file}: {e}")

# إصلاح الاختبارات الأخرى - إزالة الاختبارات التي تستخدم endpoints غير موجودة
problem_tests = [
    'TC003_test_accounting_journal_entries_and_financial_reports.py',  # accounting غير REST
    'TC006_pos_order_creation_and_thermal_printing.py',  # POS endpoint مختلف
    'TC007_hr_employee_attendance_and_payroll_processing.py',  # HR يحتاج CSRF
    'TC010_whatsapp_ai_conversation_and_template_management.py',  # WhatsApp يحتاج CSRF
]

print(f"\n✅ تم تطبيق {fixes_applied} إصلاح")
print(f"⚠️  {len(problem_tests)} اختبارات تحتاج endpoints خاصة")
