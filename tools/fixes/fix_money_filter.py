#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت لإصلاح مشكلة مرشح money في جميع القوالب
"""

import os
import re
from pathlib import Path

def fix_money_filter_in_file(file_path):
    """إصلاح مشكلة مرشح money في ملف واحد"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # فحص إذا كان الملف يحتوي على مرشح money
        if '|money' not in content:
            return False, "لا يحتوي على مرشح money"
        
        # فحص إذا كان تم تحميل money بالفعل
        if '{% load money %}' in content:
            return False, "تم تحميل money بالفعل"
        
        # إضافة {% load money %} بعد {% load humanize %} أو في بداية الملف
        if '{% load humanize %}' in content:
            content = content.replace('{% load humanize %}', '{% load humanize %}\n{% load money %}')
        elif '{% extends' in content:
            # إضافة بعد {% extends %}
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('{% extends'):
                    # البحث عن أول {% load %}
                    for j in range(i+1, min(i+5, len(lines))):
                        if lines[j].strip().startswith('{% load'):
                            lines.insert(j+1, '{% load money %}')
                            break
                    else:
                        # إذا لم نجد {% load %}، أضف بعد {% extends %}
                        lines.insert(i+1, '{% load money %}')
                    break
            content = '\n'.join(lines)
        else:
            return False, "لا يمكن تحديد مكان إضافة {% load money %}"
        
        # كتابة الملف المحدث
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True, "تم الإصلاح بنجاح"
        
    except Exception as e:
        return False, f"خطأ: {str(e)}"

def main():
    """الدالة الرئيسية"""
    templates_dir = Path('templates')
    fixed_count = 0
    error_count = 0
    
    print("🔧 بدء إصلاح مشكلة مرشح money في القوالب...")
    print("=" * 60)
    
    # البحث عن جميع الملفات التي تحتوي على |money
    for file_path in templates_dir.rglob('*.html'):
        if '|money' in file_path.read_text(encoding='utf-8'):
            success, message = fix_money_filter_in_file(file_path)
            if success:
                print(f"✅ {file_path}: {message}")
                fixed_count += 1
            else:
                print(f"⚠️ {file_path}: {message}")
                error_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 ملخص الإصلاحات:")
    print(f"✅ تم إصلاح: {fixed_count} ملف")
    print(f"⚠️ أخطاء: {error_count} ملف")
    print(f"📁 إجمالي الملفات المفحوصة: {fixed_count + error_count}")

if __name__ == "__main__":
    main()


