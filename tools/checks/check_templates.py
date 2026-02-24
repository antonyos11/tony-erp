#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكربت فحص القوالب
==================
يفحص جميع القوالب المستخدمة في الكود ويحدد الناقصة والتي تحتاج تطوير
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def check_templates():
    """فحص القوالب في المشروع"""
    
    app_dir = Path('.')
    templates_dir = app_dir / 'templates'
    
    # جمع كل القوالب المستخدمة في الكود مع مواقعها
    used_templates = defaultdict(list)
    
    # البحث في ملفات Python
    for py_file in app_dir.rglob('*.py'):
        if '.venv' in str(py_file) or '_migration' in str(py_file) or '__pycache__' in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            
            # البحث عن template_name
            for match in re.finditer(r"template_name\s*=\s*['\"]([^'\"]+)['\"]", content):
                template = match.group(1)
                used_templates[template].append(str(py_file))
            
            # البحث عن render
            for match in re.finditer(r"render\s*\([^,]+,\s*['\"]([^'\"]+)['\"]", content):
                template = match.group(1)
                used_templates[template].append(str(py_file))
            
            # البحث عن get_template
            for match in re.finditer(r"get_template\s*\(\s*['\"]([^'\"]+)['\"]", content):
                template = match.group(1)
                used_templates[template].append(str(py_file))
                
            # البحث عن TemplateResponse
            for match in re.finditer(r"TemplateResponse\s*\([^,]+,\s*['\"]([^'\"]+)['\"]", content):
                template = match.group(1)
                used_templates[template].append(str(py_file))
                
        except Exception as e:
            pass
    
    # جمع كل القوالب الموجودة فعلياً
    existing_templates = {}
    if templates_dir.exists():
        for t in templates_dir.rglob('*.html'):
            rel_path = t.relative_to(templates_dir)
            template_name = str(rel_path).replace('\\', '/')
            existing_templates[template_name] = t
    
    # تحليل النتائج
    missing_templates = []
    empty_templates = []
    small_templates = []
    
    for template in sorted(used_templates.keys()):
        if template not in existing_templates:
            missing_templates.append((template, used_templates[template]))
        else:
            # فحص محتوى القالب
            template_path = existing_templates[template]
            try:
                content = template_path.read_text(encoding='utf-8', errors='ignore')
                content_stripped = content.strip()
                
                if not content_stripped:
                    empty_templates.append((template, template_path))
                elif len(content_stripped) < 100:
                    small_templates.append((template, template_path, len(content_stripped)))
                elif '{% extends' not in content and '<!DOCTYPE' not in content and '<html' not in content:
                    # قالب قد يكون غير مكتمل
                    if '<div' not in content and '<form' not in content and '<table' not in content:
                        small_templates.append((template, template_path, len(content_stripped)))
            except:
                pass
    
    # طباعة التقرير
    print('=' * 70)
    print('📋 تقرير فحص القوالب الشامل')
    print('=' * 70)
    print(f'\n📊 الإحصائيات:')
    print(f'   • إجمالي القوالب المستخدمة في الكود: {len(used_templates)}')
    print(f'   • إجمالي القوالب الموجودة: {len(existing_templates)}')
    print(f'   • القوالب الناقصة: {len(missing_templates)}')
    print(f'   • القوالب الفارغة: {len(empty_templates)}')
    print(f'   • القوالب الصغيرة جداً: {len(small_templates)}')
    
    if missing_templates:
        print('\n' + '=' * 70)
        print(f'❌ القوالب الناقصة ({len(missing_templates)}):')
        print('-' * 70)
        
        # تجميع حسب الوحدة
        by_module = defaultdict(list)
        for template, locations in missing_templates:
            module = template.split('/')[0] if '/' in template else 'root'
            by_module[module].append((template, locations))
        
        for module in sorted(by_module.keys()):
            print(f'\n📁 {module}:')
            for template, locations in by_module[module]:
                print(f'   ❌ {template}')
                for loc in locations[:2]:
                    print(f'      └─ مستخدم في: {loc}')
                if len(locations) > 2:
                    print(f'      └─ ... و {len(locations) - 2} ملفات أخرى')
    
    if empty_templates:
        print('\n' + '=' * 70)
        print(f'⚠️ القوالب الفارغة ({len(empty_templates)}):')
        print('-' * 70)
        for template, path in empty_templates:
            print(f'   ⚠️ {template}')
    
    if small_templates:
        print('\n' + '=' * 70)
        print(f'🔧 القوالب التي قد تحتاج تطوير ({len(small_templates)}):')
        print('-' * 70)
        for template, path, size in small_templates[:20]:
            print(f'   🔧 {template} ({size} حرف)')
        if len(small_templates) > 20:
            print(f'   ... و {len(small_templates) - 20} قالب آخر')
    
    # قائمة القوالب غير المستخدمة
    unused = set(existing_templates.keys()) - set(used_templates.keys())
    # استثناء القوالب الأساسية والجزئية
    unused = {t for t in unused if not any(x in t for x in ['base', 'partial', 'include', 'component', 'email'])}
    
    if unused and len(unused) < 50:
        print('\n' + '=' * 70)
        print(f'📭 القوالب غير المستخدمة مباشرة ({len(unused)}):')
        print('-' * 70)
        for t in sorted(unused)[:30]:
            print(f'   📭 {t}')
        if len(unused) > 30:
            print(f'   ... و {len(unused) - 30} قالب آخر')
    
    print('\n' + '=' * 70)
    print('✅ انتهى الفحص')
    print('=' * 70)
    
    return {
        'missing': missing_templates,
        'empty': empty_templates,
        'small': small_templates,
        'total_used': len(used_templates),
        'total_existing': len(existing_templates)
    }

if __name__ == '__main__':
    check_templates()
