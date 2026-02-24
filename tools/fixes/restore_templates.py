#!/usr/bin/env python
"""
سكريبت استعادة القوالب المتضررة
يستعيد القوالب من _migration_package ويحدث extends إلى base_v2.html
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

# المسارات
APP_DIR = Path(__file__).parent
TEMPLATES_DIR = APP_DIR / 'templates'
MIGRATION_TEMPLATES = APP_DIR / '_migration_package' / 'src' / 'templates'

# النمط الذي يدل على القالب التالف
BROKEN_PATTERN = "page_title|default:'قائمة البيانات'"

# قائمة القوالب التي تم إصلاحها يدوياً (لا تستبدلها)
MANUALLY_FIXED = [
    'core/company_settings.html',
    'registration/login.html',
]

def is_template_broken(file_path):
    """تحقق إذا كان القالب تالف"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return BROKEN_PATTERN in content
    except:
        return False

def find_original_template(relative_path):
    """ابحث عن القالب الأصلي في _migration_package"""
    original = MIGRATION_TEMPLATES / relative_path
    if original.exists():
        return original
    return None

def update_extends(content):
    """تحديث extends من base.html إلى base_v2.html"""
    # أنماط extends المختلفة
    patterns = [
        (r"{%\s*extends\s+['\"]base\.html['\"]\s*%}", "{% extends 'base_v2.html' %}"),
        (r"{%\s*extends\s+['\"]core/base\.html['\"]\s*%}", "{% extends 'base_v2.html' %}"),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    return content

def restore_template(broken_path, original_path, log_file):
    """استعادة قالب من الأصل"""
    try:
        with open(original_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # تحديث extends
        updated_content = update_extends(content)
        
        # حفظ القالب المحدث
        with open(broken_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        log_file.write(f"✅ استعادة: {broken_path}\n")
        return True
    except Exception as e:
        log_file.write(f"❌ خطأ في استعادة {broken_path}: {e}\n")
        return False

def main():
    print("=" * 60)
    print("سكريبت استعادة القوالب المتضررة")
    print("=" * 60)
    
    # إنشاء ملف السجل
    log_path = APP_DIR / f'restore_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    
    broken_templates = []
    restored_count = 0
    not_found_count = 0
    skipped_count = 0
    
    with open(log_path, 'w', encoding='utf-8') as log_file:
        log_file.write("سجل استعادة القوالب\n")
        log_file.write("=" * 50 + "\n")
        log_file.write(f"التاريخ: {datetime.now()}\n\n")
        
        # البحث عن القوالب التالفة
        print("\n🔍 البحث عن القوالب التالفة...")
        
        for root, dirs, files in os.walk(TEMPLATES_DIR):
            # تجاهل المجلدات الاحتياطية
            dirs[:] = [d for d in dirs if 'backup' not in d.lower()]
            
            for file in files:
                if file.endswith('.html'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(TEMPLATES_DIR)
                    
                    # تجاهل القوالب المصلحة يدوياً
                    if str(relative_path).replace('\\', '/') in MANUALLY_FIXED:
                        continue
                    
                    if is_template_broken(file_path):
                        broken_templates.append((file_path, relative_path))
        
        print(f"   تم العثور على {len(broken_templates)} قالب تالف")
        log_file.write(f"عدد القوالب التالفة: {len(broken_templates)}\n\n")
        
        # محاولة استعادة كل قالب
        print("\n🔄 جاري استعادة القوالب...")
        
        not_found_list = []
        
        for broken_path, relative_path in broken_templates:
            original = find_original_template(relative_path)
            
            if original:
                if restore_template(broken_path, original, log_file):
                    restored_count += 1
                    print(f"   ✅ {relative_path}")
            else:
                not_found_count += 1
                not_found_list.append(str(relative_path))
                log_file.write(f"⚠️ لم يُعثر على الأصل: {relative_path}\n")
                print(f"   ⚠️ لم يُعثر على الأصل: {relative_path}")
        
        # ملخص
        print("\n" + "=" * 60)
        print("📊 ملخص العملية:")
        print(f"   - القوالب التالفة: {len(broken_templates)}")
        print(f"   - تم استعادتها: {restored_count}")
        print(f"   - لم يُعثر على الأصل: {not_found_count}")
        print(f"   - تم تجاهلها (مصلحة يدوياً): {len(MANUALLY_FIXED)}")
        
        log_file.write("\n" + "=" * 50 + "\n")
        log_file.write("ملخص:\n")
        log_file.write(f"تم استعادة: {restored_count}\n")
        log_file.write(f"لم يُعثر على الأصل: {not_found_count}\n")
        
        if not_found_list:
            log_file.write("\nالقوالب التي لم يُعثر على أصلها:\n")
            for item in not_found_list:
                log_file.write(f"  - {item}\n")
    
    print(f"\n📝 تم حفظ السجل في: {log_path}")
    
    return not_found_list

if __name__ == '__main__':
    not_found = main()
    
    if not_found:
        print("\n⚠️ القوالب التالية تحتاج إصلاح يدوي:")
        for item in not_found:
            print(f"   - {item}")
