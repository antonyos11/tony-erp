#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
فحص القوالب الناقصة و URLs غير المكتملة
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# تحديد المسار الأساسي
BASE_DIR = Path(__file__).parent
TEMPLATE_DIRS = [
    BASE_DIR / 'templates',
]

# المجلدات التي نتجاهلها
IGNORE_DIRS = {'.venv', '.venv_new', '__pycache__', 'migrations', 'node_modules', 'dist', '_migration_package', 'staticfiles', 'static', 'vendor', 'backups'}

# التطبيقات الرئيسية
APPS = ['accounting', 'accounts', 'ai_assistant', 'api', 'approvals', 'contracting', 'core', 'crm', 
        'data_import', 'ecommerce', 'eservices', 'fixed_assets', 'fleet', 'home_services', 'hr', 
        'inventory', 'maintenance', 'notifications', 'partners', 'payments', 'pos', 'production',
        'projects', 'purchases', 'reports', 'sales', 'shipping', 'showrooms', 'taxes', 'users', 'woocommerce_integration']

def get_all_templates():
    """جمع جميع القوالب الموجودة"""
    templates = set()
    
    # القوالب في مجلد templates الرئيسي
    for template_dir in TEMPLATE_DIRS:
        if template_dir.exists():
            for root, dirs, files in os.walk(template_dir):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    if f.endswith('.html'):
                        rel_path = os.path.relpath(os.path.join(root, f), template_dir)
                        templates.add(rel_path.replace('\\', '/'))
    
    # القوالب داخل كل تطبيق
    for app in APPS:
        app_template_dir = BASE_DIR / app / 'templates'
        if app_template_dir.exists():
            for root, dirs, files in os.walk(app_template_dir):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    if f.endswith('.html'):
                        rel_path = os.path.relpath(os.path.join(root, f), app_template_dir)
                        templates.add(rel_path.replace('\\', '/'))
    
    return templates

def extract_templates_from_views():
    """استخراج القوالب المستخدمة في Views"""
    template_refs = []
    template_patterns = [
        r'template_name\s*=\s*["\']([^"\']+)["\']',
        r'render\s*\([^,]+,\s*["\']([^"\']+)["\']',
        r'TemplateResponse\s*\([^,]+,\s*["\']([^"\']+)["\']',
        r'get_template\s*\(\s*["\']([^"\']+)["\']',
        r'loader\.get_template\s*\(\s*["\']([^"\']+)["\']',
        r'render_to_string\s*\(\s*["\']([^"\']+)["\']',
    ]
    
    for app in APPS:
        views_file = BASE_DIR / app / 'views.py'
        if views_file.exists():
            try:
                content = views_file.read_text(encoding='utf-8')
                for pattern in template_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        template_refs.append((app, match, str(views_file)))
            except Exception as e:
                pass
        
        # البحث في المجلدات الفرعية
        for subdir in (BASE_DIR / app).glob('*'):
            if subdir.is_dir() and subdir.name not in IGNORE_DIRS:
                views_file = subdir / 'views.py'
                if views_file.exists():
                    try:
                        content = views_file.read_text(encoding='utf-8')
                        for pattern in template_patterns:
                            matches = re.findall(pattern, content)
                            for match in matches:
                                template_refs.append((app, match, str(views_file)))
                    except Exception:
                        pass
    
    return template_refs

def extract_templates_from_templates():
    """استخراج القوالب المستخدمة في extends و include"""
    template_refs = []
    patterns = [
        r'{%\s*extends\s*["\']([^"\']+)["\']',
        r'{%\s*include\s*["\']([^"\']+)["\']',
    ]
    
    for template_dir in TEMPLATE_DIRS:
        if template_dir.exists():
            for root, dirs, files in os.walk(template_dir):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    if f.endswith('.html'):
                        file_path = os.path.join(root, f)
                        try:
                            content = open(file_path, 'r', encoding='utf-8').read()
                            for pattern in patterns:
                                matches = re.findall(pattern, content)
                                for match in matches:
                                    template_refs.append(('templates', match, file_path))
                        except Exception:
                            pass
    
    return template_refs

def check_url_patterns():
    """فحص URL patterns الناقصة"""
    issues = []
    url_pattern = re.compile(r'path\s*\(\s*["\']([^"\']*)["\']')
    view_pattern = re.compile(r'path\s*\([^,]+,\s*([^\s,\)]+)')
    
    for app in APPS:
        urls_file = BASE_DIR / app / 'urls.py'
        if urls_file.exists():
            try:
                content = urls_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # فحص paths فارغة
                    if 'path(' in line and ('pass' in line or line.strip().endswith('path(')):
                        issues.append({
                            'type': 'empty_path',
                            'app': app,
                            'file': str(urls_file),
                            'line': i,
                            'content': line.strip()
                        })
                    
                    # فحص TODO في URLs
                    if 'TODO' in line or 'FIXME' in line:
                        issues.append({
                            'type': 'todo_in_url',
                            'app': app,
                            'file': str(urls_file),
                            'line': i,
                            'content': line.strip()
                        })
            except Exception as e:
                pass
    
    return issues

def check_empty_views():
    """فحص Views الفارغة أو غير المكتملة"""
    issues = []
    
    for app in APPS:
        views_file = BASE_DIR / app / 'views.py'
        if views_file.exists():
            try:
                content = views_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # فحص pass
                    if re.match(r'^\s*pass\s*$', line):
                        # تحقق من السياق
                        if i > 1 and ('def ' in lines[i-2] or 'class ' in lines[i-2]):
                            issues.append({
                                'type': 'empty_function',
                                'app': app,
                                'file': str(views_file),
                                'line': i,
                                'content': lines[i-2].strip() + ' -> pass'
                            })
                    
                    # فحص TODO و NotImplementedError
                    if 'TODO' in line or 'FIXME' in line:
                        issues.append({
                            'type': 'todo_in_view',
                            'app': app,
                            'file': str(views_file),
                            'line': i,
                            'content': line.strip()
                        })
                    
                    if 'NotImplementedError' in line:
                        issues.append({
                            'type': 'not_implemented',
                            'app': app,
                            'file': str(views_file),
                            'line': i,
                            'content': line.strip()
                        })
            except Exception:
                pass
    
    return issues

def check_stub_templates():
    """فحص القوالب الفارغة أو التي تحتاج تطوير"""
    issues = []
    
    for template_dir in TEMPLATE_DIRS:
        if template_dir.exists():
            for root, dirs, files in os.walk(template_dir):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    if f.endswith('.html'):
                        file_path = os.path.join(root, f)
                        try:
                            content = open(file_path, 'r', encoding='utf-8').read()
                            lines = content.split('\n')
                            rel_path = os.path.relpath(file_path, template_dir)
                            
                            # فحص TODO و FIXME
                            for i, line in enumerate(lines, 1):
                                if 'TODO' in line or 'FIXME' in line:
                                    issues.append({
                                        'type': 'todo_in_template',
                                        'template': rel_path,
                                        'file': file_path,
                                        'line': i,
                                        'content': line.strip()
                                    })
                            
                            # فحص قوالب صغيرة جداً مع محتوى قليل
                            non_empty_lines = [l for l in lines if l.strip() and not l.strip().startswith('{#')]
                            if len(non_empty_lines) < 10:
                                # تحقق إن كان القالب يحتوي على extends فقط
                                has_extends = '{%' in content and 'extends' in content
                                has_block = '{%' in content and 'block' in content
                                block_content = re.findall(r'{%\s*block\s+\w+\s*%}(.*?){%\s*endblock', content, re.DOTALL)
                                
                                if has_extends and has_block:
                                    all_empty = all(not bc.strip() or bc.strip() == '' for bc in block_content)
                                    if all_empty:
                                        issues.append({
                                            'type': 'stub_template',
                                            'template': rel_path,
                                            'file': file_path,
                                            'line': 1,
                                            'content': f'قالب stub - يحتوي على extends و blocks فارغة ({len(non_empty_lines)} سطور)'
                                        })
                        except Exception:
                            pass
    
    return issues

def check_url_references_in_templates():
    """فحص روابط URL المستخدمة في القوالب"""
    url_refs = defaultdict(list)
    url_pattern = re.compile(r'{%\s*url\s*["\']([^"\']+)["\']')
    
    for template_dir in TEMPLATE_DIRS:
        if template_dir.exists():
            for root, dirs, files in os.walk(template_dir):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    if f.endswith('.html'):
                        file_path = os.path.join(root, f)
                        try:
                            content = open(file_path, 'r', encoding='utf-8').read()
                            matches = url_pattern.findall(content)
                            for match in matches:
                                url_refs[match].append(file_path)
                        except Exception:
                            pass
    
    return url_refs

def collect_defined_urls():
    """جمع جميع URLs المعرفة"""
    defined_urls = set()
    name_pattern = re.compile(r'name\s*=\s*["\']([^"\']+)["\']')
    
    for app in APPS:
        urls_file = BASE_DIR / app / 'urls.py'
        if urls_file.exists():
            try:
                content = urls_file.read_text(encoding='utf-8')
                matches = name_pattern.findall(content)
                for match in matches:
                    defined_urls.add(match)
                    defined_urls.add(f'{app}:{match}')
            except Exception:
                pass
    
    # أيضاً URLs الأساسية
    main_urls = BASE_DIR / 'الشامل' / 'urls.py'
    if main_urls.exists():
        try:
            content = main_urls.read_text(encoding='utf-8')
            matches = name_pattern.findall(content)
            for match in matches:
                defined_urls.add(match)
        except Exception:
            pass
    
    return defined_urls

def main():
    print("=" * 80)
    print("تقرير فحص القوالب و URLs الناقصة")
    print("=" * 80)
    print()
    
    # 1. جمع القوالب الموجودة
    existing_templates = get_all_templates()
    print(f"عدد القوالب الموجودة: {len(existing_templates)}")
    print()
    
    # 2. فحص القوالب المستخدمة في Views
    print("-" * 80)
    print("1. القوالب الناقصة (مستخدمة في Views لكن غير موجودة):")
    print("-" * 80)
    template_refs = extract_templates_from_views()
    missing_templates = []
    for app, template, file in template_refs:
        if template not in existing_templates:
            # تحقق بشكل مختلف
            found = False
            for existing in existing_templates:
                if existing.endswith(template) or template.endswith(existing):
                    found = True
                    break
            if not found:
                missing_templates.append((app, template, file))
    
    if missing_templates:
        for app, template, file in sorted(set(missing_templates)):
            print(f"  ❌ [{app}] {template}")
            print(f"     الملف: {file}")
    else:
        print("  ✅ لا توجد قوالب ناقصة")
    print()
    
    # 3. فحص القوالب في extends/include
    print("-" * 80)
    print("2. القوالب المفقودة في extends/include:")
    print("-" * 80)
    template_refs2 = extract_templates_from_templates()
    missing_includes = []
    for source, template, file in template_refs2:
        if template not in existing_templates:
            found = False
            for existing in existing_templates:
                if existing.endswith(template) or template.endswith(existing):
                    found = True
                    break
            if not found:
                missing_includes.append((template, file))
    
    if missing_includes:
        for template, file in sorted(set(missing_includes)):
            print(f"  ❌ {template}")
            print(f"     مُستخدم في: {file}")
    else:
        print("  ✅ لا توجد قوالب مفقودة")
    print()
    
    # 4. فحص URL patterns الناقصة
    print("-" * 80)
    print("3. مشاكل في URLs:")
    print("-" * 80)
    url_issues = check_url_patterns()
    if url_issues:
        for issue in url_issues:
            print(f"  ⚠️ [{issue['app']}] {issue['type']}")
            print(f"     الملف: {issue['file']}:{issue['line']}")
            print(f"     المحتوى: {issue['content']}")
    else:
        print("  ✅ لا توجد مشاكل")
    print()
    
    # 5. فحص Views الفارغة
    print("-" * 80)
    print("4. Views غير مكتملة أو فارغة:")
    print("-" * 80)
    view_issues = check_empty_views()
    if view_issues:
        for issue in view_issues:
            print(f"  ⚠️ [{issue['app']}] {issue['type']}")
            print(f"     الملف: {issue['file']}:{issue['line']}")
            print(f"     المحتوى: {issue['content'][:100]}")
    else:
        print("  ✅ لا توجد views فارغة")
    print()
    
    # 6. فحص القوالب الفارغة
    print("-" * 80)
    print("5. قوالب تحتاج تطوير (stub templates / TODO):")
    print("-" * 80)
    stub_issues = check_stub_templates()
    if stub_issues:
        for issue in stub_issues:
            print(f"  ⚠️ {issue['template']}")
            print(f"     النوع: {issue['type']}")
            print(f"     الملف: {issue['file']}:{issue['line']}")
            if issue['content']:
                print(f"     المحتوى: {issue['content'][:100]}")
    else:
        print("  ✅ لا توجد قوالب تحتاج تطوير")
    print()
    
    # 7. فحص URL references في القوالب
    print("-" * 80)
    print("6. URLs مستخدمة في القوالب لكن قد لا تكون معرفة:")
    print("-" * 80)
    url_refs = check_url_references_in_templates()
    defined_urls = collect_defined_urls()
    
    undefined_urls = []
    for url_name, files in url_refs.items():
        if url_name not in defined_urls:
            # تحقق بشكل مختلف
            base_name = url_name.split(':')[-1] if ':' in url_name else url_name
            if base_name not in defined_urls and url_name not in defined_urls:
                undefined_urls.append((url_name, files))
    
    if undefined_urls:
        for url_name, files in sorted(undefined_urls)[:30]:  # أول 30 فقط
            print(f"  ❓ {url_name}")
            print(f"     مستخدم في: {len(files)} ملف(ات)")
    else:
        print("  ✅ جميع URLs معرفة")
    print()
    
    # ملخص
    print("=" * 80)
    print("الملخص:")
    print("=" * 80)
    print(f"  • قوالب ناقصة: {len(set(missing_templates))}")
    print(f"  • قوالب extends/include مفقودة: {len(set(missing_includes))}")
    print(f"  • مشاكل URLs: {len(url_issues)}")
    print(f"  • Views غير مكتملة: {len(view_issues)}")
    print(f"  • قوالب تحتاج تطوير: {len(stub_issues)}")
    print(f"  • URLs غير معرفة: {len(undefined_urls)}")
    print("=" * 80)

if __name__ == '__main__':
    main()
