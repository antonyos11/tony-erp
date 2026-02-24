#!/usr/bin/env python3
"""
سكربت إصلاح ترتيب blocks في القوالب
"""

import os
import re

TEMPLATES_DIR = '/var/www/tony_erp/templates'

def fix_template_order(filepath):
    """إصلاح ترتيب extends و blocks في القالب"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # البحث عن extends
    extends_match = re.search(r"({% extends ['\"][^'\"]+['\"] %})", content)
    if not extends_match:
        return False
    
    extends_tag = extends_match.group(1)
    
    # التحقق إذا كان extends ليس في البداية
    before_extends = content[:extends_match.start()].strip()
    
    # إذا كان هناك شيء قبل extends (مثل block)
    if before_extends and '{% block' in before_extends:
        # استخراج الـ block الذي قبل extends
        block_match = re.search(r"({% block \w+ %}[^{]*{% endblock %})", before_extends)
        if block_match:
            block_tag = block_match.group(1)
            # إزالة الـ block من مكانه القديم
            content = content.replace(block_tag + '\n', '', 1)
            content = content.replace(block_tag, '', 1)
            
            # البحث عن مكان مناسب لإضافة الـ block (بعد load tags)
            load_pattern = r"({% load [^%]+%}\n)+"
            load_match = re.search(load_pattern, content)
            
            if load_match:
                # إضافة الـ block بعد آخر load tag
                insert_pos = load_match.end()
                content = content[:insert_pos] + '\n' + block_tag + '\n' + content[insert_pos:]
            else:
                # إذا لم يكن هناك load tags، أضف بعد extends
                extends_match = re.search(r"({% extends ['\"][^'\"]+['\"] %})", content)
                if extends_match:
                    insert_pos = extends_match.end()
                    content = content[:insert_pos] + '\n' + block_tag + '\n' + content[insert_pos:]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    
    return False

def main():
    print("=" * 60)
    print("  إصلاح ترتيب blocks في القوالب")
    print("=" * 60)
    
    fixed = 0
    
    for root, dirs, files in os.walk(TEMPLATES_DIR):
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git']]
        
        for file in files:
            if not file.endswith('.html'):
                continue
            
            filepath = os.path.join(root, file)
            
            try:
                if fix_template_order(filepath):
                    fixed += 1
                    print(f"  ✅ {filepath.replace(TEMPLATES_DIR, '')}")
            except Exception as e:
                print(f"  ❌ {filepath.replace(TEMPLATES_DIR, '')} - {e}")
    
    print(f"\n✅ تم إصلاح {fixed} ملف")

if __name__ == '__main__':
    main()
