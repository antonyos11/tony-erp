#!/usr/bin/env python3
"""
إصلاح الاختبارات المتبقية
"""
import os
import re

print("🔧 إصلاح الاختبارات المتبقية...\n")

# ==========================================
# إصلاح TC003 - المحاسبة
# ==========================================
print("📝 إصلاح TC003 - المحاسبة...")
tc003_file = 'TC003_test_accounting_journal_entries_and_financial_reports.py'
if os.path.exists(tc003_file):
    with open(tc003_file, 'r') as f:
        content = f.read()
    
    # تغيير مسار المحاسبة
    content = content.replace('/accounting/', '/api/accounting/')
    
    with open(tc003_file, 'w') as f:
        f.write(content)
    print("   ✅ تم إصلاح مسارات المحاسبة\n")

# ==========================================
# إصلاح TC006 - نقاط البيع
# ==========================================
print("📝 إصلاح TC006 - نقاط البيع...")
tc006_file = 'TC006_pos_order_creation_and_thermal_printing.py'
if os.path.exists(tc006_file):
    with open(tc006_file, 'r') as f:
        content = f.read()
    
    # تغيير مسار POS
    content = content.replace('/api/pos/orders/', '/pos/api/orders/')
    
    with open(tc006_file, 'w') as f:
        f.write(content)
    print("   ✅ تم إصلاح مسارات POS\n")

# ==========================================
# إصلاح TC007 & TC010 - إضافة دعم CSRF
# ==========================================
print("📝 تحديث TC007 & TC010 لاستخدام CSRF...")
for test_file in ['TC007_hr_employee_attendance_and_payroll_processing.py',
                   'TC010_whatsapp_ai_conversation_and_template_management.py']:
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            content = f.read()
        
        # إضافة import لـ CSRF helper
        if 'from csrf_helper import get_csrf_token' not in content:
            import_line = 'from requests.auth import HTTPBasicAuth\n'
            new_import = import_line + 'from csrf_helper import get_csrf_token\n'
            content = content.replace(import_line, new_import, 1)
        
        # إضافة CSRF token في بداية الاختبار
        if 'csrf_token, session = get_csrf_token' not in content:
            # البحث عن بداية دالة test
            pattern = r'(def test_\w+\(\):.*?\n\s+)(.*?)(try:)'
            replacement = r'\1\2# Get CSRF token for session\n    csrf_token, session = get_csrf_token(BASE_URL, AUTH)\n    headers = {"X-CSRFToken": csrf_token} if csrf_token else {}\n    \3'
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        with open(test_file, 'w') as f:
            f.write(content)
        print(f"   ✅ تم تحديث {test_file}\n")

print("✅ تم إصلاح جميع الاختبارات المتبقية!")
