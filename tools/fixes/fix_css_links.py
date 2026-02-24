#!/usr/bin/env python3
"""
سكربت إصلاح الصفحات التي لا تزال تستخدم CSS القديم
يقوم بإضافة رابط CSS الحديث وتحديث الأنماط
"""

import os
import re

TEMPLATES_DIR = '/var/www/tony_erp/templates'

# قائمة الملفات التي تحتاج تحديث CSS
def find_files_needing_css_update():
    """البحث عن الملفات التي تحتوي على أنماط قديمة"""
    files_to_update = []
    
    for root, dirs, files in os.walk(TEMPLATES_DIR):
        # تجاهل المجلدات الخاصة
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git']]
        
        for file in files:
            if not file.endswith('.html'):
                continue
            
            filepath = os.path.join(root, file)
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # تحقق إذا كان يستخدم base_v2.html ويحتوي على أنماط قديمة
            if "extends 'base_v2.html'" in content or 'extends "base_v2.html"' in content:
                # تحقق من وجود CSS القديم
                if 'form-hero' in content or 'form-card' in content:
                    # تحقق إذا كان modern_pages.css غير موجود
                    if 'modern_pages.css' not in content:
                        files_to_update.append(filepath)
    
    return files_to_update

def add_modern_css_to_file(filepath):
    """إضافة رابط CSS الحديث للملف"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # إضافة CSS في block extra_css أو extra_head
    if '{% block extra_css %}' in content:
        # أضف بعد block extra_css
        content = re.sub(
            r'({% block extra_css %})',
            r'\1\n<link href="{% static \'css/modern_pages.css\' %}?v=2" rel="stylesheet">',
            content
        )
    elif '{% block extra_head %}' in content:
        # أضف بعد block extra_head
        content = re.sub(
            r'({% block extra_head %})',
            r'\1\n<link href="{% static \'css/modern_pages.css\' %}?v=2" rel="stylesheet">',
            content
        )
    else:
        # أضف block جديد
        content = re.sub(
            r"({% extends ['\"]base_v2\.html['\"] %})",
            r"\1\n{% load static %}\n\n{% block extra_css %}\n<link href=\"{% static 'css/modern_pages.css' %}?v=2\" rel=\"stylesheet\">\n{% endblock %}",
            content
        )
    
    # تحديث الأنماط القديمة
    replacements = [
        # تحويل form-hero إلى mp-page-hero
        ('class="form-hero"', 'class="mp-page-hero"'),
        ('class="form-card"', 'class="mp-form-card"'),
        ('class="section-title"', 'class="mp-section-title"'),
        ('class="form-section"', 'class="mp-form-section"'),
        ('class="form-actions"', 'class="mp-form-actions"'),
        ('class="btn-save"', 'class="mp-btn mp-btn-primary"'),
        ('class="btn-cancel"', 'class="mp-btn mp-btn-outline"'),
        ('class="btn-submit"', 'class="mp-btn mp-btn-primary"'),
        # تحديث الأنماط الأخرى
        ('class="stat-card"', 'class="mp-stat-card"'),
        ('class="data-card"', 'class="mp-card"'),
        ('class="filter-card"', 'class="mp-card mp-filters"'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def main():
    print("=" * 60)
    print("  إصلاح الصفحات - إضافة CSS الحديث")
    print("=" * 60)
    
    files = find_files_needing_css_update()
    print(f"\n📊 تم العثور على {len(files)} ملف يحتاج تحديث CSS\n")
    
    for filepath in files:
        try:
            add_modern_css_to_file(filepath)
            print(f"  ✅ {filepath.replace(TEMPLATES_DIR, '')}")
        except Exception as e:
            print(f"  ❌ {filepath.replace(TEMPLATES_DIR, '')} - {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ تم تحديث {len(files)} ملف")
    print("=" * 60)

if __name__ == '__main__':
    main()
