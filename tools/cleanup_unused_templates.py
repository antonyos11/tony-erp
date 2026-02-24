#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكربت حذف القوالب غير المستخدمة
=================================
يحذف القوالب التي لا تستخدم في الكود مع الاحتفاظ بنسخة احتياطية
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

def cleanup_unused_templates():
    """حذف القوالب غير المستخدمة"""
    
    app_dir = Path('.')
    templates_dir = app_dir / 'templates'
    backup_dir = app_dir / ('templates_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    
    # جمع القوالب المستخدمة
    used_templates = set()
    
    # البحث في ملفات Python
    for py_file in app_dir.rglob('*.py'):
        if '.venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            for match in re.finditer(r"['\"]([^'\"]+\.html)['\"]", content):
                used_templates.add(match.group(1))
        except:
            pass
    
    # البحث في ملفات HTML (includes و extends)
    for html_file in templates_dir.rglob('*.html'):
        try:
            content = html_file.read_text(encoding='utf-8', errors='ignore')
            # extends
            for match in re.finditer(r"{%\s*extends\s*['\"]([^'\"]+)['\"]", content):
                used_templates.add(match.group(1))
            # include
            for match in re.finditer(r"{%\s*include\s*['\"]([^'\"]+)['\"]", content):
                used_templates.add(match.group(1))
        except:
            pass
    
    # القوالب الموجودة
    existing = {}
    if templates_dir.exists():
        for t in templates_dir.rglob('*.html'):
            rel = str(t.relative_to(templates_dir)).replace('\\', '/')
            existing[rel] = t
    
    # غير المستخدمة
    unused = set(existing.keys()) - used_templates
    
    # استثناء الأساسية والمهمة
    base_keywords = ['base', 'partial', 'include', 'component', 'email', 'modal', 'widget', 
                     'sidebar', 'navbar', 'footer', 'header', 'error', '404', '500', '403',
                     'login', 'password', 'register', 'profile']
    unused_filtered = {t for t in unused if not any(x in t.lower() for x in base_keywords)}
    
    if not unused_filtered:
        print('✅ لا توجد قوالب غير مستخدمة للحذف')
        return {'deleted': 0, 'backup': None}
    
    # إنشاء نسخة احتياطية
    backup_dir.mkdir(exist_ok=True)
    
    deleted = 0
    for template_name in sorted(unused_filtered):
        template_path = existing[template_name]
        
        # نسخ احتياطية
        backup_path = backup_dir / template_name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template_path, backup_path)
        
        # حذف
        template_path.unlink()
        deleted += 1
        print(f'🗑️  حذف: {template_name}')
    
    # حذف المجلدات الفارغة
    for folder in sorted(templates_dir.rglob('*'), reverse=True):
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
            print(f'📁 حذف مجلد فارغ: {folder.relative_to(templates_dir)}')
    
    print('\n' + '=' * 70)
    print(f'✅ تم حذف {deleted} قالب غير مستخدم')
    print(f'📦 النسخة الاحتياطية في: {backup_dir}')
    print('=' * 70)
    
    return {'deleted': deleted, 'backup': str(backup_dir)}

if __name__ == '__main__':
    cleanup_unused_templates()
