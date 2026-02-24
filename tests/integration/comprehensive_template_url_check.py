#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
فحص شامل للقوالب و URLs الناقصة أو غير المكتملة
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
IGNORE_DIRS = {'.venv', '.venv_new', '__pycache__', 'migrations', 'node_modules', 'dist', '_migration_package', 'staticfiles', 'static', 'vendor', 'backups', 'templates_backup_20251228_064150'}

# التطبيقات الرئيسية
APPS = ['accounting', 'accounts', 'ai_assistant', 'api', 'accountant_pro', 'approvals', 'contracting', 'core', 'crm', 
        'data_import', 'ecommerce', 'eservices', 'fixed_assets', 'fleet', 'home_services', 'hr', 
        'inventory', 'maintenance', 'notifications', 'partners', 'payments', 'pos', 'production',
        'projects', 'purchases', 'reports', 'sales', 'shipping', 'showrooms', 'taxes', 'users', 'woocommerce_integration']


def collect_all_defined_urls():
    """جمع جميع URLs المعرفة مع أسمائها"""
    defined_urls = {}  # {name: (app, path_pattern, view_name)}
    name_pattern = re.compile(r"path\s*\(\s*['\"]([^'\"]*)['\"],\s*([^,]+),\s*name\s*=\s*['\"]([^'\"]+)['\"]")
    
    for app in APPS:
        # البحث في urls.py الرئيسي
        urls_file = BASE_DIR / app / 'urls.py'
        if urls_file.exists():
            try:
                content = urls_file.read_text(encoding='utf-8')
                # البحث عن app_name
                app_name_match = re.search(r"app_name\s*=\s*['\"]([^'\"]+)['\"]", content)
                url_app_name = app_name_match.group(1) if app_name_match else app
                
                matches = name_pattern.findall(content)
                for path_str, view_ref, name in matches:
                    defined_urls[name] = (url_app_name, path_str, view_ref.strip())
                    defined_urls[f'{url_app_name}:{name}'] = (url_app_name, path_str, view_ref.strip())
            except Exception as e:
                pass
        
        # البحث في المجلدات الفرعية
        for subdir in (BASE_DIR / app).glob('*'):
            if subdir.is_dir() and subdir.name not in IGNORE_DIRS:
                urls_file = subdir / 'urls.py'
                if urls_file.exists():
                    try:
                        content = urls_file.read_text(encoding='utf-8')
                        app_name_match = re.search(r"app_name\s*=\s*['\"]([^'\"]+)['\"]", content)
                        url_app_name = app_name_match.group(1) if app_name_match else f'{app}.{subdir.name}'
                        
                        matches = name_pattern.findall(content)
                        for path_str, view_ref, name in matches:
                            defined_urls[name] = (url_app_name, path_str, view_ref.strip())
                            defined_urls[f'{url_app_name}:{name}'] = (url_app_name, path_str, view_ref.strip())
                    except Exception:
                        pass
    
    return defined_urls


def check_url_references_in_templates():
    """فحص روابط URL المستخدمة في القوالب"""
    url_refs = defaultdict(list)
    url_pattern = re.compile(r"{%\s*url\s*['\"]([^'\"]+)['\"]")
    
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
                            for i, line in enumerate(lines, 1):
                                matches = url_pattern.findall(line)
                                for match in matches:
                                    rel_path = os.path.relpath(file_path, template_dir)
                                    url_refs[match].append((rel_path, i))
                        except Exception:
                            pass
    
    return url_refs


def find_missing_views_in_urls():
    """البحث عن Views مستخدمة في URLs لكن قد لا تكون موجودة"""
    missing_views = []
    view_in_url_pattern = re.compile(r"path\s*\([^,]+,\s*(views[^\s,\)]+|[A-Z][a-zA-Z]*View)")
    
    for app in APPS:
        urls_file = BASE_DIR / app / 'urls.py'
        if urls_file.exists():
            try:
                content = urls_file.read_text(encoding='utf-8')
                views_file = BASE_DIR / app / 'views.py'
                views_content = ""
                
                if views_file.exists():
                    views_content = views_file.read_text(encoding='utf-8')
                
                # استخراج Views المستخدمة
                matches = view_in_url_pattern.findall(content)
                for view_ref in matches:
                    # تحويل views.function_name إلى function_name
                    func_name = view_ref.replace('views.', '').replace('views_auth.', '').replace('views_', '')
                    
                    # تحقق إذا كانت الوظيفة موجودة
                    if func_name and not re.search(rf'def\s+{func_name}\s*\(|class\s+{func_name}\s*\(', views_content):
                        # ربما في ملف views آخر
                        found = False
                        for vf in (BASE_DIR / app).glob('views*.py'):
                            try:
                                vc = vf.read_text(encoding='utf-8')
                                if re.search(rf'def\s+{func_name}\s*\(|class\s+{func_name}\s*\(', vc):
                                    found = True
                                    break
                            except:
                                pass
                        
                        if not found and 'View.as_view' not in view_ref:
                            missing_views.append({
                                'app': app,
                                'view': view_ref,
                                'file': str(urls_file)
                            })
            except Exception as e:
                pass
    
    return missing_views


def find_incomplete_features():
    """البحث عن ميزات غير مكتملة في Views"""
    incomplete = []
    
    patterns = [
        (r'#\s*TODO[:\s]*(.*)', 'TODO'),
        (r'#\s*FIXME[:\s]*(.*)', 'FIXME'),
        (r'raise\s+NotImplementedError', 'NotImplementedError'),
        (r'return\s+HttpResponse\s*\(\s*["\']["\']', 'Empty HttpResponse'),
        (r'return\s+JsonResponse\s*\(\s*\{\s*\}\s*\)', 'Empty JsonResponse'),
    ]
    
    for app in APPS:
        for views_file in (BASE_DIR / app).glob('views*.py'):
            if views_file.exists():
                try:
                    content = views_file.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern, issue_type in patterns:
                            match = re.search(pattern, line)
                            if match:
                                incomplete.append({
                                    'app': app,
                                    'type': issue_type,
                                    'file': str(views_file),
                                    'line': i,
                                    'content': match.group(1) if match.groups() else line.strip()
                                })
                except Exception:
                    pass
    
    return incomplete


def find_stub_templates():
    """البحث عن القوالب الفارغة أو Stub"""
    stubs = []
    
    for template_dir in TEMPLATE_DIRS:
        if template_dir.exists():
            for root, dirs, files in os.walk(template_dir):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    if f.endswith('.html'):
                        file_path = os.path.join(root, f)
                        try:
                            content = open(file_path, 'r', encoding='utf-8').read()
                            lines = [l for l in content.split('\n') if l.strip()]
                            rel_path = os.path.relpath(file_path, template_dir)
                            
                            # فحص TODO/FIXME
                            if 'TODO' in content or 'FIXME' in content:
                                stubs.append({
                                    'template': rel_path,
                                    'type': 'TODO/FIXME',
                                    'file': file_path
                                })
                            
                            # فحص قوالب صغيرة جداً مع extends فقط
                            if len(lines) < 15:
                                has_extends = '{% extends' in content
                                has_block = '{% block' in content
                                
                                # استخراج محتوى blocks
                                block_contents = re.findall(r'{%\s*block\s+\w+\s*%}(.*?){%\s*endblock', content, re.DOTALL)
                                all_blocks_empty = all(not bc.strip() for bc in block_contents) if block_contents else False
                                
                                if has_extends and (all_blocks_empty or len(block_contents) == 0):
                                    stubs.append({
                                        'template': rel_path,
                                        'type': 'STUB (extends only, empty blocks)',
                                        'file': file_path,
                                        'lines': len(lines)
                                    })
                        except Exception:
                            pass
    
    return stubs


def check_template_extends():
    """فحص extends غير موجودة"""
    missing_extends = []
    existing_templates = set()
    
    # جمع القوالب الموجودة
    for template_dir in TEMPLATE_DIRS:
        if template_dir.exists():
            for root, dirs, files in os.walk(template_dir):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    if f.endswith('.html'):
                        rel_path = os.path.relpath(os.path.join(root, f), template_dir)
                        existing_templates.add(rel_path.replace('\\', '/'))
    
    # فحص extends
    extend_pattern = re.compile(r"{%\s*extends\s*['\"]([^'\"]+)['\"]")
    include_pattern = re.compile(r"{%\s*include\s*['\"]([^'\"]+)['\"]")
    
    for template_dir in TEMPLATE_DIRS:
        if template_dir.exists():
            for root, dirs, files in os.walk(template_dir):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in files:
                    if f.endswith('.html'):
                        file_path = os.path.join(root, f)
                        try:
                            content = open(file_path, 'r', encoding='utf-8').read()
                            rel_path = os.path.relpath(file_path, template_dir)
                            
                            # فحص extends
                            for match in extend_pattern.findall(content):
                                if match not in existing_templates:
                                    missing_extends.append({
                                        'template': rel_path,
                                        'missing': match,
                                        'type': 'extends',
                                        'file': file_path
                                    })
                            
                            # فحص include
                            for match in include_pattern.findall(content):
                                if match not in existing_templates and not match.startswith('django'):
                                    # تجاهل المتغيرات
                                    if '{{' not in match and 'variable' not in match.lower():
                                        missing_extends.append({
                                            'template': rel_path,
                                            'missing': match,
                                            'type': 'include',
                                            'file': file_path
                                        })
                        except Exception:
                            pass
    
    return missing_extends


def main():
    print("=" * 90)
    print("تقرير فحص شامل للقوالب و URLs الناقصة أو غير المكتملة")
    print("=" * 90)
    print()
    
    # 1. URLs غير معرفة
    print("-" * 90)
    print("1. 🔗 URLs مستخدمة في القوالب لكن غير معرفة في urls.py:")
    print("-" * 90)
    
    defined_urls = collect_all_defined_urls()
    url_refs = check_url_references_in_templates()
    
    missing_urls = []
    for url_name, locations in url_refs.items():
        if url_name not in defined_urls:
            # تحقق من الاسم الأساسي
            base_name = url_name.split(':')[-1] if ':' in url_name else url_name
            namespace = url_name.split(':')[0] if ':' in url_name else None
            
            # البحث عن مطابقة جزئية
            found = False
            for defined_name in defined_urls.keys():
                if defined_name == base_name or defined_name.endswith(':' + base_name):
                    found = True
                    break
            
            if not found:
                missing_urls.append({
                    'url_name': url_name,
                    'namespace': namespace,
                    'locations': locations[:3]  # أول 3 مواقع فقط
                })
    
    if missing_urls:
        for item in sorted(missing_urls, key=lambda x: x['url_name']):
            print(f"\n  ❌ {item['url_name']}")
            if item['namespace']:
                print(f"     Namespace: {item['namespace']}")
            print(f"     مستخدم في:")
            for loc, line in item['locations']:
                print(f"       - {loc}:{line}")
    else:
        print("  ✅ جميع URLs معرفة")
    
    print(f"\n  📊 المجموع: {len(missing_urls)} URL غير معرف")
    print()
    
    # 2. extends/include غير موجودة
    print("-" * 90)
    print("2. 📄 قوالب extends/include غير موجودة:")
    print("-" * 90)
    
    missing_extends = check_template_extends()
    if missing_extends:
        for item in missing_extends:
            print(f"\n  ❌ {item['missing']}")
            print(f"     النوع: {item['type']}")
            print(f"     مستخدم في: {item['template']}")
    else:
        print("  ✅ جميع extends/include موجودة")
    
    print(f"\n  📊 المجموع: {len(missing_extends)} قالب مفقود")
    print()
    
    # 3. ميزات غير مكتملة
    print("-" * 90)
    print("3. ⚠️ ميزات غير مكتملة في Views (TODO/FIXME/NotImplemented):")
    print("-" * 90)
    
    incomplete = find_incomplete_features()
    if incomplete:
        by_app = defaultdict(list)
        for item in incomplete:
            by_app[item['app']].append(item)
        
        for app, items in sorted(by_app.items()):
            print(f"\n  📦 {app}:")
            for item in items[:5]:  # أول 5 فقط لكل تطبيق
                print(f"     [{item['type']}] {item['file'].split(os.sep)[-1]}:{item['line']}")
                if item['content']:
                    print(f"       └─ {item['content'][:80]}")
            if len(items) > 5:
                print(f"     ... و {len(items) - 5} أخرى")
    else:
        print("  ✅ لا توجد ميزات غير مكتملة")
    
    print(f"\n  📊 المجموع: {len(incomplete)} ميزة غير مكتملة")
    print()
    
    # 4. قوالب Stub
    print("-" * 90)
    print("4. 📝 قوالب Stub أو تحتاج تطوير:")
    print("-" * 90)
    
    stubs = find_stub_templates()
    if stubs:
        for item in stubs[:20]:  # أول 20 فقط
            print(f"\n  ⚠️ {item['template']}")
            print(f"     النوع: {item['type']}")
    else:
        print("  ✅ لا توجد قوالب stub")
    
    print(f"\n  📊 المجموع: {len(stubs)} قالب")
    print()
    
    # 5. Views غير موجودة
    print("-" * 90)
    print("5. 🔧 Views مُشار إليها في URLs لكن قد لا تكون موجودة:")
    print("-" * 90)
    
    missing_views = find_missing_views_in_urls()
    if missing_views:
        for item in missing_views[:20]:
            print(f"\n  ❌ [{item['app']}] {item['view']}")
    else:
        print("  ✅ جميع Views موجودة")
    
    print(f"\n  📊 المجموع: {len(missing_views)} view")
    print()
    
    # ملخص نهائي
    print("=" * 90)
    print("📋 الملخص النهائي:")
    print("=" * 90)
    print(f"  • URLs غير معرفة: {len(missing_urls)}")
    print(f"  • قوالب extends/include مفقودة: {len(missing_extends)}")
    print(f"  • ميزات غير مكتملة (TODO/FIXME): {len(incomplete)}")
    print(f"  • قوالب Stub: {len(stubs)}")
    print(f"  • Views غير موجودة: {len(missing_views)}")
    print("=" * 90)
    
    total_issues = len(missing_urls) + len(missing_extends) + len(incomplete) + len(stubs) + len(missing_views)
    print(f"\n  🎯 إجمالي المشاكل: {total_issues}")
    
    if total_issues == 0:
        print("\n  🎉 ممتاز! لا توجد مشاكل!")
    elif total_issues < 10:
        print("\n  ✨ جيد جداً! عدد قليل من المشاكل")
    elif total_issues < 50:
        print("\n  📌 متوسط - يحتاج بعض العمل")
    else:
        print("\n  ⚠️ يحتاج مراجعة شاملة")


if __name__ == '__main__':
    main()
