#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكربت تحليل القوالب المتقدم
===========================
يفحص القوالب غير المستخدمة وجودة المحتوى والتوافق مع Bootstrap
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def analyze_templates():
    """تحليل شامل للقوالب"""
    
    app_dir = Path('.')
    templates_dir = app_dir / 'templates'
    
    # جمع القوالب المستخدمة
    used_templates = set()
    for py_file in app_dir.rglob('*.py'):
        if '.venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            for match in re.finditer(r"['\"]([^'\"]+\.html)['\"]", content):
                used_templates.add(match.group(1))
        except:
            pass
    
    # القوالب الموجودة
    existing = {}
    if templates_dir.exists():
        for t in templates_dir.rglob('*.html'):
            rel = str(t.relative_to(templates_dir)).replace('\\', '/')
            existing[rel] = t
    
    # 1. القوالب غير المستخدمة
    unused = set(existing.keys()) - used_templates
    # استثناء الأساسية
    base_keywords = ['base', 'partial', 'include', 'component', 'email', 'modal', 'widget', 'sidebar', 'navbar', 'footer', 'header']
    unused_filtered = {t for t in unused if not any(x in t.lower() for x in base_keywords)}
    
    print('=' * 70)
    print('📊 تحليل القوالب المتقدم')
    print('=' * 70)
    
    # 2. تحليل جودة القوالب
    stub_templates = []  # قوالب stub تلقائية
    no_extends = []  # قوالب بدون extends
    small_content = []  # محتوى صغير
    missing_bootstrap = []  # بدون Bootstrap classes
    good_templates = []  # قوالب جيدة
    
    bootstrap_classes = ['container', 'row', 'col-', 'btn', 'card', 'table', 'form-', 'alert', 'modal', 'nav']
    
    for template_name, template_path in existing.items():
        try:
            content = template_path.read_text(encoding='utf-8', errors='ignore')
            content_stripped = content.strip()
            
            # فحص stub templates
            if 'Stub template' in content or 'هذا القالب تم توليده تلقائيًا' in content:
                stub_templates.append((template_name, template_path))
                continue
            
            # فحص الامتداد
            has_extends = '{% extends' in content or '{% include' in content
            has_html = '<!DOCTYPE' in content or '<html' in content
            
            if not has_extends and not has_html and len(content_stripped) > 50:
                no_extends.append((template_name, len(content_stripped)))
            
            # فحص حجم المحتوى
            if len(content_stripped) < 200 and has_extends:
                # قالب صغير لكن قد يكون جزئي
                if 'block content' in content and content.count('<') < 5:
                    small_content.append((template_name, len(content_stripped)))
            
            # فحص Bootstrap
            has_bootstrap = any(bc in content for bc in bootstrap_classes)
            if not has_bootstrap and len(content_stripped) > 300 and not any(x in template_name.lower() for x in ['email', 'txt', 'xml']):
                missing_bootstrap.append((template_name, len(content_stripped)))
            
            # القوالب الجيدة
            if len(content_stripped) > 500 and (has_extends or has_html) and has_bootstrap:
                good_templates.append((template_name, len(content_stripped)))
                
        except Exception as e:
            pass
    
    # طباعة التقرير
    print(f'\n📈 إحصائيات عامة:')
    print(f'   • إجمالي القوالب: {len(existing)}')
    print(f'   • القوالب المستخدمة: {len(used_templates)}')
    print(f'   • القوالب الجيدة: {len(good_templates)}')
    
    if stub_templates:
        print(f'\n' + '=' * 70)
        print(f'🔧 قوالب Stub تحتاج تطوير ({len(stub_templates)}):')
        print('-' * 70)
        
        # تجميع حسب المجلد
        by_folder = defaultdict(list)
        for t, p in stub_templates:
            folder = t.split('/')[0] if '/' in t else 'root'
            by_folder[folder].append(t)
        
        for folder in sorted(by_folder.keys()):
            print(f'\n📁 {folder}: ({len(by_folder[folder])} قالب)')
            for t in sorted(by_folder[folder])[:10]:
                print(f'   🔧 {t}')
            if len(by_folder[folder]) > 10:
                print(f'   ... و {len(by_folder[folder]) - 10} آخرين')
    
    if small_content:
        print(f'\n' + '=' * 70)
        print(f'📝 قوالب بمحتوى قليل ({len(small_content)}):')
        print('-' * 70)
        for t, size in sorted(small_content, key=lambda x: x[1])[:15]:
            print(f'   📝 {t} ({size} حرف)')
        if len(small_content) > 15:
            print(f'   ... و {len(small_content) - 15} آخرين')
    
    if missing_bootstrap:
        print(f'\n' + '=' * 70)
        print(f'🎨 قوالب بدون Bootstrap classes ({len(missing_bootstrap)}):')
        print('-' * 70)
        for t, size in sorted(missing_bootstrap)[:15]:
            print(f'   🎨 {t}')
        if len(missing_bootstrap) > 15:
            print(f'   ... و {len(missing_bootstrap) - 15} آخرين')
    
    if unused_filtered:
        print(f'\n' + '=' * 70)
        print(f'📭 قوالب غير مستخدمة مباشرة ({len(unused_filtered)}):')
        print('-' * 70)
        for t in sorted(unused_filtered)[:20]:
            print(f'   📭 {t}')
        if len(unused_filtered) > 20:
            print(f'   ... و {len(unused_filtered) - 20} آخرين')
    
    print('\n' + '=' * 70)
    
    # ملخص الأولويات
    print('🎯 أولويات التطوير:')
    print('-' * 70)
    if stub_templates:
        print(f'   1️⃣ تطوير {len(stub_templates)} قالب stub (أولوية عالية)')
    if small_content:
        print(f'   2️⃣ إثراء {len(small_content)} قالب صغير')
    if missing_bootstrap:
        print(f'   3️⃣ إضافة Bootstrap لـ {len(missing_bootstrap)} قالب')
    if unused_filtered:
        print(f'   4️⃣ مراجعة {len(unused_filtered)} قالب غير مستخدم')
    
    if not stub_templates and not small_content:
        print('   ✅ جميع القوالب بحالة جيدة!')
    
    print('\n' + '=' * 70)
    print('✅ انتهى التحليل')
    print('=' * 70)
    
    return {
        'stub_templates': stub_templates,
        'small_content': small_content,
        'missing_bootstrap': missing_bootstrap,
        'unused': unused_filtered,
        'good': good_templates
    }

if __name__ == '__main__':
    analyze_templates()
