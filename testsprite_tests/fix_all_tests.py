#!/usr/bin/env python3
"""
تطبيق إصلاحات شاملة على جميع اختبارات TestSprite
بناءً على الأنماط الناجحة من TC004, TC005, TC008
"""
import re
import os
import glob

def fix_status_values(content):
    """إصلاح قيم الحالة إلى أحرف صغيرة"""
    replacements = {
        r'"status":\s*"Draft"': '"status": "draft"',
        r'"status":\s*"Open"': '"status": "open"',
        r'"status":\s*"Closed"': '"status": "closed"',
        r'"status":\s*"Pending"': '"status": "pending"',
        r'"status":\s*"Approved"': '"status": "approved"',
        r'"status":\s*"Rejected"': '"status": "rejected"',
        r'"status":\s*"Active"': '"status": "active"',
        r'"status":\s*"Inactive"': '"status": "inactive"',
        r'"status":\s*"In Progress"': '"status": "in_progress"',
        r'"status":\s*"Completed"': '"status": "completed"',
        r'"status":\s*"Cancelled"': '"status": "cancelled"',
        r'"priority":\s*"High"': '"priority": "high"',
        r'"priority":\s*"Medium"': '"priority": "medium"',
        r'"priority":\s*"Low"': '"priority": "low"',
        r'"priority":\s*"Urgent"': '"priority": "urgent"',
    }
    
    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)
    
    return content

def fix_base_urls(content):
    """إصلاح عناوين URL الأساسية"""
    # تأكد من استخدام BASE_URL الصحيح
    content = re.sub(
        r'http://localhost:8000/dashboard/dashboard',
        'http://localhost:8000',
        content
    )
    
    # إصلاح مسار E-commerce
    content = re.sub(
        r'/api/ecommerce/',
        '/store/api/',
        content
    )
    
    return content

def fix_field_names(content):
    """إصلاح أسماء الحقول الشائعة"""
    # Fleet management
    content = re.sub(
        r'"start_location":\s*',
        '"origin": ',
        content
    )
    content = re.sub(
        r'"end_location":\s*',
        '"destination": ',
        content
    )
    
    return content

def fix_date_formats(content):
    """إصلاح صيغ التاريخ - إزالة الوقت من التواريخ"""
    # نمط: "2026-07-01T08:00:00Z" -> "2026-07-01"
    content = re.sub(
        r'"(planned_start_date|planned_end_date|start_date|end_date|date)":\s*"(\d{4}-\d{2}-\d{2})T[\d:]+Z?"',
        r'"\1": "\2"',
        content
    )
    
    return content

def process_file(filepath):
    """معالجة ملف اختبار واحد"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # تطبيق الإصلاحات
        content = fix_base_urls(content)
        content = fix_status_values(content)
        content = fix_field_names(content)
        content = fix_date_formats(content)
        
        # حفظ فقط إذا تغير المحتوى
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, filepath
        
        return False, None
        
    except Exception as e:
        return False, f"Error in {filepath}: {e}"

# معالجة جميع ملفات الاختبار
test_files = glob.glob('TC*.py')
test_files = [f for f in test_files if not f.startswith('backup/')]

modified = []
errors = []

for test_file in sorted(test_files):
    changed, result = process_file(test_file)
    if changed:
        modified.append(result)
    elif result and 'Error' in str(result):
        errors.append(result)

print(f"✅ تم إصلاح {len(modified)} ملف")
if modified:
    for f in modified[:10]:  # عرض أول 10 فقط
        print(f"   - {f}")
    if len(modified) > 10:
        print(f"   ... و {len(modified) - 10} ملف آخر")

if errors:
    print(f"\n❌ أخطاء في {len(errors)} ملف:")
    for e in errors:
        print(f"   - {e}")

