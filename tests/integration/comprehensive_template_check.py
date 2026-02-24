#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكربت فحص شامل لمشروع Django
يبحث عن:
1. القوالب الناقصة
2. URLs الناقصة
3. قوالب فارغة أو تحتاج تطوير
4. Views غير مكتملة
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# المسار الرئيسي للمشروع
BASE_DIR = Path(__file__).resolve().parent

# المجلدات المستثناة
EXCLUDED_DIRS = {'.venv', '.venv_new', '__pycache__', 'migrations', 'dist', '_migration_package', 
                 '.git', 'node_modules', 'staticfiles', 'media', 'backups'}

def should_skip_dir(path):
    """تحقق إذا كان يجب تخطي هذا المجلد"""
    parts = Path(path).parts
    return any(excluded in parts for excluded in EXCLUDED_DIRS)

def find_files(extension, base_path=BASE_DIR):
    """البحث عن ملفات بامتداد معين"""
    files = []
    for root, dirs, filenames in os.walk(base_path):
        # تخطي المجلدات المستثناة
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        
        for filename in filenames:
            if filename.endswith(extension):
                files.append(os.path.join(root, filename))
    return files

def extract_templates_from_views():
    """استخراج أسماء القوالب من ملفات views.py"""
    templates_used = []
    view_files = find_files('views.py')
    
    # أنماط البحث عن القوالب
    patterns = [
        # render(request, 'template.html', ...)
        r"render\s*\(\s*[^,]+,\s*['\"]([^'\"]+\.html)['\"]",
        # template_name = 'template.html'
        r"template_name\s*=\s*['\"]([^'\"]+\.html)['\"]",
        # TemplateResponse(..., 'template.html', ...)
        r"TemplateResponse\s*\([^,]+,\s*['\"]([^'\"]+\.html)['\"]",
        # get_template('template.html')
        r"get_template\s*\(\s*['\"]([^'\"]+\.html)['\"]",
        # loader.get_template('template.html')
        r"loader\.get_template\s*\(\s*['\"]([^'\"]+\.html)['\"]",
    ]
    
    for view_file in view_files:
        try:
            with open(view_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern in patterns:
                        matches = re.findall(pattern, line)
                        for template in matches:
                            templates_used.append({
                                'template': template,
                                'file': view_file,
                                'line': line_num,
                                'context': line.strip()
                            })
        except Exception as e:
            print(f"خطأ في قراءة {view_file}: {e}")
    
    return templates_used

def get_existing_templates():
    """الحصول على قائمة القوالب الموجودة"""
    templates_dir = BASE_DIR / 'templates'
    existing = set()
    
    if templates_dir.exists():
        for root, dirs, files in os.walk(templates_dir):
            for f in files:
                if f.endswith('.html'):
                    # الحصول على المسار النسبي
                    full_path = Path(root) / f
                    rel_path = full_path.relative_to(templates_dir)
                    existing.add(str(rel_path).replace('\\', '/'))
    
    # أيضاً البحث في مجلدات templates داخل التطبيقات
    for app_dir in BASE_DIR.iterdir():
        if app_dir.is_dir() and app_dir.name not in EXCLUDED_DIRS:
            app_templates = app_dir / 'templates'
            if app_templates.exists():
                for root, dirs, files in os.walk(app_templates):
                    for f in files:
                        if f.endswith('.html'):
                            full_path = Path(root) / f
                            rel_path = full_path.relative_to(app_templates)
                            existing.add(str(rel_path).replace('\\', '/'))
    
    return existing

def check_missing_templates():
    """فحص القوالب الناقصة"""
    print("\n" + "="*80)
    print("🔍 1. فحص القوالب الناقصة")
    print("="*80)
    
    templates_used = extract_templates_from_views()
    existing_templates = get_existing_templates()
    
    missing = []
    for item in templates_used:
        template = item['template']
        if template not in existing_templates:
            # تحقق من وجود القالب في مسارات بديلة
            alt_paths = [
                template,
                template.replace('/', '\\'),
            ]
            found = any(t in existing_templates for t in alt_paths)
            if not found:
                missing.append(item)
    
    if missing:
        print(f"\n❌ تم العثور على {len(missing)} قالب ناقص:\n")
        for item in missing:
            rel_path = os.path.relpath(item['file'], BASE_DIR)
            print(f"  📄 القالب: {item['template']}")
            print(f"     الملف: {rel_path}:{item['line']}")
            print(f"     الكود: {item['context'][:80]}...")
            print()
    else:
        print("\n✅ جميع القوالب المستخدمة موجودة!")
    
    return missing

def check_incomplete_views():
    """فحص Views غير المكتملة"""
    print("\n" + "="*80)
    print("🔍 4. فحص Views غير المكتملة")
    print("="*80)
    
    view_files = find_files('views.py')
    issues = []
    
    # أنماط المشاكل
    patterns = {
        'pass_only': r'^\s*def\s+\w+\([^)]*\):\s*\n\s*(?:"""[^"]*"""\s*\n\s*)?pass\s*$',
        'todo': r'#\s*TODO|#\s*FIXME|#\s*XXX|#\s*HACK',
        'not_implemented': r'raise\s+NotImplementedError',
        'empty_response': r'return\s+HttpResponse\s*\(\s*[\'\"]{2}\s*\)|return\s+HttpResponse\s*\(\s*\)',
        'placeholder': r'return\s+JsonResponse\s*\(\s*\{\s*\}\s*\)|return\s+JsonResponse\s*\(\s*\[\s*\]\s*\)',
    }
    
    for view_file in view_files:
        try:
            with open(view_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for issue_type, pattern in patterns.items():
                        if issue_type == 'pass_only':
                            # هذا النمط يحتاج فحص متعدد الأسطر
                            continue
                        if re.search(pattern, line, re.IGNORECASE):
                            issues.append({
                                'type': issue_type,
                                'file': view_file,
                                'line': line_num,
                                'context': line.strip()
                            })
                
                # فحص الدوال التي تحتوي فقط على pass
                func_pattern = r'def\s+(\w+)\s*\([^)]*\):\s*\n(\s+)((?:"""[\s\S]*?"""\s*\n\2)?)(pass|\.\.\.)\s*\n'
                for match in re.finditer(func_pattern, content):
                    func_name = match.group(1)
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append({
                        'type': 'empty_function',
                        'file': view_file,
                        'line': line_num,
                        'context': f'def {func_name}(...): pass'
                    })
                    
        except Exception as e:
            print(f"خطأ في قراءة {view_file}: {e}")
    
    if issues:
        print(f"\n⚠️ تم العثور على {len(issues)} مشكلة في Views:\n")
        
        # تجميع حسب النوع
        by_type = defaultdict(list)
        for item in issues:
            by_type[item['type']].append(item)
        
        type_names = {
            'todo': '📝 TODO/FIXME comments',
            'not_implemented': '🚫 NotImplementedError',
            'empty_response': '📭 HttpResponse فارغ',
            'placeholder': '📦 JsonResponse فارغ/placeholder',
            'empty_function': '🔲 دالة فارغة (pass فقط)',
        }
        
        for issue_type, items in by_type.items():
            print(f"\n{type_names.get(issue_type, issue_type)} ({len(items)} مشكلة):")
            for item in items[:10]:  # أول 10 فقط
                rel_path = os.path.relpath(item['file'], BASE_DIR)
                print(f"  • {rel_path}:{item['line']}")
                print(f"    {item['context'][:70]}...")
            if len(items) > 10:
                print(f"  ... و {len(items) - 10} مشاكل أخرى")
    else:
        print("\n✅ جميع Views مكتملة!")
    
    return issues

def check_empty_templates():
    """فحص القوالب الفارغة أو التي تحتاج تطوير"""
    print("\n" + "="*80)
    print("🔍 3. فحص القوالب الفارغة أو غير المكتملة")
    print("="*80)
    
    templates_dir = BASE_DIR / 'templates'
    issues = []
    
    if not templates_dir.exists():
        print("❌ مجلد templates غير موجود!")
        return issues
    
    for root, dirs, files in os.walk(templates_dir):
        for f in files:
            if not f.endswith('.html'):
                continue
                
            file_path = Path(root) / f
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    lines = content.split('\n')
                    line_count = len(lines)
                    
                    # تحقق من وجود TODO أو FIXME
                    has_todo = bool(re.search(r'TODO|FIXME|XXX|HACK', content, re.IGNORECASE))
                    
                    # تحقق إذا كان القالب فارغ تقريباً
                    # إزالة التعليقات والمسافات
                    stripped = re.sub(r'{#.*?#}', '', content)
                    stripped = re.sub(r'<!--.*?-->', '', stripped, flags=re.DOTALL)
                    stripped = re.sub(r'\s+', ' ', stripped).strip()
                    
                    # تحقق إذا كان يحتوي فقط على extends و block فارغ
                    only_extends = bool(re.match(
                        r'^{%\s*extends\s+[\'"][^\'"]+[\'"]\s*%}\s*({%\s*load\s+[^%]+%}\s*)*({%\s*block\s+\w+\s*%}\s*{%\s*endblock\s*%}\s*)*$',
                        stripped
                    ))
                    
                    # حساب المحتوى الفعلي (بدون tags)
                    actual_content = re.sub(r'{%.*?%}|{{.*?}}|{#.*?#}', '', content)
                    actual_content = re.sub(r'<[^>]+>', '', actual_content)
                    actual_content = actual_content.strip()
                    
                    rel_path = file_path.relative_to(templates_dir)
                    
                    if only_extends:
                        issues.append({
                            'file': str(rel_path),
                            'full_path': str(file_path),
                            'type': 'extends_only',
                            'lines': line_count,
                            'description': 'يحتوي فقط على extends و blocks فارغة'
                        })
                    elif has_todo:
                        issues.append({
                            'file': str(rel_path),
                            'full_path': str(file_path),
                            'type': 'has_todo',
                            'lines': line_count,
                            'description': 'يحتوي على TODO/FIXME'
                        })
                    elif line_count < 20 and len(actual_content) < 100:
                        issues.append({
                            'file': str(rel_path),
                            'full_path': str(file_path),
                            'type': 'minimal_content',
                            'lines': line_count,
                            'description': f'محتوى قليل جداً ({line_count} سطر)'
                        })
                        
            except Exception as e:
                print(f"خطأ في قراءة {file_path}: {e}")
    
    if issues:
        print(f"\n⚠️ تم العثور على {len(issues)} قالب يحتاج مراجعة:\n")
        
        by_type = defaultdict(list)
        for item in issues:
            by_type[item['type']].append(item)
        
        type_names = {
            'extends_only': '🔲 قوالب تحتوي فقط على extends',
            'has_todo': '📝 قوالب تحتوي على TODO/FIXME',
            'minimal_content': '📄 قوالب بمحتوى قليل',
        }
        
        for issue_type, items in by_type.items():
            print(f"\n{type_names.get(issue_type, issue_type)} ({len(items)}):")
            for item in items[:15]:
                print(f"  • {item['file']} ({item['lines']} سطر)")
            if len(items) > 15:
                print(f"  ... و {len(items) - 15} قوالب أخرى")
    else:
        print("\n✅ جميع القوالب مكتملة!")
    
    return issues

def check_urls_issues():
    """فحص مشاكل URLs"""
    print("\n" + "="*80)
    print("🔍 2. فحص URLs الناقصة أو غير المكتملة")
    print("="*80)
    
    url_files = find_files('urls.py')
    issues = []
    
    for url_file in url_files:
        try:
            with open(url_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # البحث عن patterns فارغة
                    if re.search(r'path\s*\(\s*[\'"][^\'"]*[\'"]\s*,\s*\)', line):
                        issues.append({
                            'type': 'empty_path',
                            'file': url_file,
                            'line': line_num,
                            'context': line.strip()
                        })
                    
                    # البحث عن TODO في URLs
                    if re.search(r'#\s*TODO|#\s*FIXME', line, re.IGNORECASE):
                        issues.append({
                            'type': 'todo_in_urls',
                            'file': url_file,
                            'line': line_num,
                            'context': line.strip()
                        })
                    
                    # البحث عن urlpatterns فارغ
                    if re.search(r'urlpatterns\s*=\s*\[\s*\]', line):
                        issues.append({
                            'type': 'empty_urlpatterns',
                            'file': url_file,
                            'line': line_num,
                            'context': line.strip()
                        })
                        
        except Exception as e:
            print(f"خطأ في قراءة {url_file}: {e}")
    
    # فحص views المشار إليها في urls مع البحث في جميع ملفات views
    for url_file in url_files:
        app_dir = Path(url_file).parent
        
        try:
            with open(url_file, 'r', encoding='utf-8') as f:
                url_content = f.read()
            
            # جمع جميع الدوال والـ classes من جميع ملفات views في التطبيق
            all_view_functions = set()
            all_view_classes = set()
            
            for vf in app_dir.glob('*views*.py'):
                try:
                    with open(vf, 'r', encoding='utf-8') as f:
                        vc = f.read()
                        all_view_functions.update(re.findall(r'^def\s+(\w+)\s*\(', vc, re.MULTILINE))
                        all_view_classes.update(re.findall(r'^class\s+(\w+)\s*\(', vc, re.MULTILINE))
                except:
                    pass
            
            # البحث عن views مستخدمة في urls (views.xxx فقط)
            used_views = re.findall(r'\bviews\.(\w+)', url_content)
            
            for view_name in set(used_views):
                if view_name == 'generic':
                    continue  # تخطي generic imports
                if view_name not in all_view_functions and view_name not in all_view_classes:
                    line_num = 0
                    for i, line in enumerate(url_content.split('\n'), 1):
                        if f'views.{view_name}' in line:
                            line_num = i
                            break
                    issues.append({
                        'type': 'missing_view',
                        'file': url_file,
                        'line': line_num,
                        'context': f'views.{view_name} غير موجود في ملفات views'
                    })
                        
        except Exception as e:
            pass
    
    if issues:
        print(f"\n⚠️ تم العثور على {len(issues)} مشكلة في URLs:\n")
        
        by_type = defaultdict(list)
        for item in issues:
            by_type[item['type']].append(item)
        
        type_names = {
            'empty_path': '🔲 path فارغ',
            'todo_in_urls': '📝 TODO في URLs',
            'empty_urlpatterns': '📭 urlpatterns فارغ',
            'missing_view': '❌ View غير موجود',
        }
        
        for issue_type, items in by_type.items():
            print(f"\n{type_names.get(issue_type, issue_type)} ({len(items)}):")
            for item in items[:10]:
                rel_path = os.path.relpath(item['file'], BASE_DIR)
                print(f"  • {rel_path}:{item['line']}")
                print(f"    {item['context'][:70]}")
            if len(items) > 10:
                print(f"  ... و {len(items) - 10} مشاكل أخرى")
    else:
        print("\n✅ جميع URLs صحيحة!")
    
    return issues

def check_template_urls():
    """فحص الروابط المستخدمة في القوالب"""
    print("\n" + "="*80)
    print("🔍 2.1 فحص روابط url في القوالب")
    print("="*80)
    
    templates_dir = BASE_DIR / 'templates'
    issues = []
    
    # جمع جميع أسماء URLs المعرفة
    url_names = set()
    url_files = find_files('urls.py')
    
    for url_file in url_files:
        try:
            with open(url_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # البحث عن name='...' أو name="..."
                names = re.findall(r"name\s*=\s*['\"]([^'\"]+)['\"]", content)
                url_names.update(names)
        except:
            pass
    
    # فحص القوالب
    if templates_dir.exists():
        for root, dirs, files in os.walk(templates_dir):
            for f in files:
                if not f.endswith('.html'):
                    continue
                    
                file_path = Path(root) / f
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        lines = content.split('\n')
                        
                        for line_num, line in enumerate(lines, 1):
                            # البحث عن {% url 'name' %} أو {% url "name" %}
                            url_tags = re.findall(r"{%\s*url\s+['\"]([^'\"]+)['\"]", line)
                            for url_name in url_tags:
                                # تجاهل URLs مع namespace
                                base_name = url_name.split(':')[-1] if ':' in url_name else url_name
                                # لا نستطيع التحقق من URLs مع namespace بدون تحليل أعمق
                                if ':' not in url_name and base_name not in url_names:
                                    rel_path = file_path.relative_to(templates_dir)
                                    issues.append({
                                        'file': str(rel_path),
                                        'line': line_num,
                                        'url_name': url_name,
                                        'context': line.strip()[:60]
                                    })
                except:
                    pass
    
    if issues:
        print(f"\n⚠️ تم العثور على {len(issues)} رابط قد يكون غير معرف:\n")
        for item in issues[:20]:
            print(f"  • {item['file']}:{item['line']}")
            print(f"    URL: '{item['url_name']}'")
        if len(issues) > 20:
            print(f"  ... و {len(issues) - 20} روابط أخرى")
    else:
        print("\n✅ جميع الروابط في القوالب معرفة!")
    
    return issues

def generate_summary(missing_templates, url_issues, template_issues, view_issues):
    """توليد ملخص التقرير"""
    print("\n" + "="*80)
    print("📊 ملخص التقرير")
    print("="*80)
    
    total_issues = len(missing_templates) + len(url_issues) + len(template_issues) + len(view_issues)
    
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                    📋 ملخص الفحص الشامل                    ║
    ╠══════════════════════════════════════════════════════════╣
    ║  1. القوالب الناقصة:           {len(missing_templates):>4} مشكلة               ║
    ║  2. مشاكل URLs:                {len(url_issues):>4} مشكلة               ║
    ║  3. قوالب تحتاج تطوير:         {len(template_issues):>4} قالب                ║
    ║  4. Views غير مكتملة:          {len(view_issues):>4} مشكلة               ║
    ╠══════════════════════════════════════════════════════════╣
    ║  إجمالي المشاكل:              {total_issues:>4} مشكلة               ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    return {
        'missing_templates': missing_templates,
        'url_issues': url_issues,
        'template_issues': template_issues,
        'view_issues': view_issues,
        'total': total_issues
    }

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║        🔍 فحص شامل لمشروع Django                          ║
    ║        البحث عن القوالب والـ Views الناقصة               ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    print(f"📂 مسار المشروع: {BASE_DIR}")
    
    # 1. فحص القوالب الناقصة
    missing_templates = check_missing_templates()
    
    # 2. فحص URLs
    url_issues = check_urls_issues()
    
    # 2.1 فحص روابط القوالب
    template_url_issues = check_template_urls()
    url_issues.extend(template_url_issues)
    
    # 3. فحص القوالب الفارغة
    template_issues = check_empty_templates()
    
    # 4. فحص Views غير المكتملة
    view_issues = check_incomplete_views()
    
    # توليد الملخص
    summary = generate_summary(missing_templates, url_issues, template_issues, view_issues)
    
    print("\n✅ اكتمل الفحص!")
    
    return summary

if __name__ == '__main__':
    main()
