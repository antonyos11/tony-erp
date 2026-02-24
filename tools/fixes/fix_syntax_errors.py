#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إصلاح أخطاء syntax في models.py
"""

import re
import os

def fix_models_syntax(file_path):
    """إصلاح أخطاء syntax في ملفات النماذج"""
    if not os.path.exists(file_path):
        return False
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # إصلاح مشكلة id field في مكان خاطئ داخل CHOICES
    # Pattern: CHOICES = [\n    id = models.AutoField(...)\n    ('choice1', ...),
    
    # البحث عن كل class مع choices وid في مكان خاطئ
    pattern = r'(class\s+\w+\([^)]+\):\s*\n(?:\s*"""[^"]*"""\s*\n)?\s*)(\w+_(?:STATUS|TYPES?|CHOICES))\s*=\s*\[\s*\n\s*id\s*=\s*models\.AutoField\([^)]+\)\s*#[^\n]*\n(\s*\([^)]+\),[^\]]*\])'
    
    def fix_class_choices(match):
        class_def = match.group(1)
        choices_name = match.group(2)
        choices_content = match.group(3)
        
        return f"""{class_def}{choices_name} = [
{choices_content}
    
    id = models.AutoField(primary_key=True)  # Explicit ID field for type checking"""
    
    content = re.sub(pattern, fix_class_choices, content, flags=re.MULTILINE | re.DOTALL)
    
    if content != original_content:
        # التحقق من syntax قبل الحفظ
        try:
            import ast
            ast.parse(content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"تم إصلاح syntax errors في {file_path}")
            return True
        except SyntaxError as e:
            print(f"⚠️ خطأ syntax بعد الإصلاح في {file_path}: {e}")
            return False
    
    return False

def main():
    # إصلاح ملفات المشروع الرئيسي
    models_files = [
        r'd:\الشامل\الشامل\الشامل\app\accounting\models.py',
    ]
    
    for file_path in models_files:
        try:
            if fix_models_syntax(file_path):
                print(f"✅ تم إصلاح {file_path}")
            else:
                print(f"⏭️ لا توجد مشاكل في {file_path}")
        except Exception as e:
            print(f"❌ خطأ في إصلاح {file_path}: {e}")

if __name__ == "__main__":
    main()