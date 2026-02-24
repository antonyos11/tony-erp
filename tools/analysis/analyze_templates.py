# -*- coding: utf-8 -*-
"""
تحليل شامل للـ Templates المفقودة في مشروع Django ERP
"""
import os
import re
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / 'templates'

# التطبيقات المطلوب فحصها
APPS = [
    'users', 'accounts', 'core', 'inventory', 'sales', 'purchases', 
    'accounting', 'partners', 'reports', 'api', 'hr', 'crm', 
    'production', 'maintenance', 'payments', 'exports', 'fleet',
    'pos', 'showrooms', 'approvals', 'notifications', 
    'woocommerce_integration', 'fixed_assets', 'contracting', 
    'shipping', 'eservices', 'projects', 'ecommerce', 'ai_assistant'
]

# التطبيقات ذات الأولوية
PRIORITY_APPS = ['payments', 'contracting', 'shipping', 'eservices', 'projects', 'fixed_assets']

def extract_templates_from_views(views_file):
    """استخراج أسماء Templates من ملف views.py"""
    templates = set()
    
    if not os.path.exists(views_file):
        return templates
    
    try:
        with open(views_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return templates
    
    # البحث عن render()
    render_patterns = [
        r"render\s*\(\s*request\s*,\s*['\"]([^'\"]+)['\"]",
        r"template_name\s*=\s*['\"]([^'\"]+)['\"]",
        r"get_template\s*\(\s*['\"]([^'\"]+)['\"]",
        r"render_to_string\s*\(\s*['\"]([^'\"]+)['\"]",
    ]
    
    for pattern in render_patterns:
        matches = re.findall(pattern, content)
        templates.update(matches)
    
    return templates

def extract_views_from_urls(urls_file):
    """استخراج الـ views من ملف urls.py"""
    views = []
    
    if not os.path.exists(urls_file):
        return views
    
    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return views
    
    # البحث عن path() و url()
    patterns = [
        r"path\s*\([^)]*,\s*(\w+)\.as_view\s*\(",
        r"path\s*\([^)]*,\s*views\.(\w+)",
        r"path\s*\([^)]*,\s*(\w+),",
        r"url\s*\([^)]*,\s*views\.(\w+)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content)
        views.extend(matches)
    
    return list(set(views))

def get_existing_templates(app_name):
    """الحصول على Templates الموجودة"""
    templates = set()
    app_template_dir = TEMPLATES_DIR / app_name
    
    if not app_template_dir.exists():
        return templates
    
    for root, dirs, files in os.walk(app_template_dir):
        for file in files:
            if file.endswith('.html'):
                rel_path = os.path.relpath(os.path.join(root, file), TEMPLATES_DIR)
                templates.add(rel_path.replace('\\', '/'))
    
    return templates

def analyze_app(app_name):
    """تحليل تطبيق واحد"""
    app_dir = BASE_DIR / app_name
    
    result = {
        'app_name': app_name,
        'exists': app_dir.exists(),
        'views_count': 0,
        'required_templates': [],
        'existing_templates': [],
        'missing_templates': [],
        'urls_file_exists': False,
        'views_file_exists': False,
    }
    
    if not app_dir.exists():
        return result
    
    # فحص urls.py
    urls_file = app_dir / 'urls.py'
    result['urls_file_exists'] = urls_file.exists()
    views_from_urls = extract_views_from_urls(str(urls_file))
    result['views_count'] = len(views_from_urls)
    
    # فحص views.py و views/
    views_files = []
    views_py = app_dir / 'views.py'
    views_dir = app_dir / 'views'
    
    if views_py.exists():
        views_files.append(str(views_py))
        result['views_file_exists'] = True
    
    if views_dir.exists():
        for file in views_dir.glob('*.py'):
            views_files.append(str(file))
        result['views_file_exists'] = True
    
    # استخراج Templates المطلوبة
    required_templates = set()
    for vf in views_files:
        required_templates.update(extract_templates_from_views(vf))
    
    result['required_templates'] = sorted(list(required_templates))
    
    # الحصول على Templates الموجودة
    existing_templates = get_existing_templates(app_name)
    result['existing_templates'] = sorted(list(existing_templates))
    
    # تحديد Templates المفقودة
    missing = []
    for template in required_templates:
        template_path = TEMPLATES_DIR / template
        if not template_path.exists():
            missing.append(template)
    
    result['missing_templates'] = sorted(missing)
    
    return result

def main():
    print("=" * 80)
    print("تحليل شامل للـ Templates في مشروع Django ERP")
    print("=" * 80)
    print()
    
    all_results = []
    all_missing = []
    
    # تحليل التطبيقات ذات الأولوية أولاً
    print("=" * 80)
    print("التطبيقات ذات الأولوية العالية")
    print("=" * 80)
    
    for app in PRIORITY_APPS:
        result = analyze_app(app)
        all_results.append(result)
        
        print(f"\n{'='*60}")
        print(f"التطبيق: {app}")
        print(f"{'='*60}")
        print(f"  - موجود: {'نعم' if result['exists'] else 'لا'}")
        print(f"  - urls.py موجود: {'نعم' if result['urls_file_exists'] else 'لا'}")
        print(f"  - views.py موجود: {'نعم' if result['views_file_exists'] else 'لا'}")
        print(f"  - عدد Views: {result['views_count']}")
        print(f"  - Templates المطلوبة: {len(result['required_templates'])}")
        print(f"  - Templates الموجودة: {len(result['existing_templates'])}")
        print(f"  - Templates المفقودة: {len(result['missing_templates'])}")
        
        if result['missing_templates']:
            print(f"\n  Templates المفقودة:")
            for t in result['missing_templates']:
                print(f"    - {t}")
                all_missing.append({'app': app, 'template': t, 'priority': True})
    
    # تحليل باقي التطبيقات
    print("\n\n" + "=" * 80)
    print("باقي التطبيقات")
    print("=" * 80)
    
    for app in APPS:
        if app in PRIORITY_APPS:
            continue
            
        result = analyze_app(app)
        all_results.append(result)
        
        if result['missing_templates']:
            print(f"\n{'='*60}")
            print(f"التطبيق: {app}")
            print(f"{'='*60}")
            print(f"  - عدد Views: {result['views_count']}")
            print(f"  - Templates المطلوبة: {len(result['required_templates'])}")
            print(f"  - Templates الموجودة: {len(result['existing_templates'])}")
            print(f"  - Templates المفقودة: {len(result['missing_templates'])}")
            print(f"\n  Templates المفقودة:")
            for t in result['missing_templates']:
                print(f"    - {t}")
                all_missing.append({'app': app, 'template': t, 'priority': False})
    
    # ملخص نهائي
    print("\n\n" + "=" * 80)
    print("الملخص النهائي")
    print("=" * 80)
    
    total_required = sum(len(r['required_templates']) for r in all_results)
    total_existing = sum(len(r['existing_templates']) for r in all_results)
    total_missing = len(all_missing)
    
    print(f"\nإجمالي Templates المطلوبة: {total_required}")
    print(f"إجمالي Templates الموجودة: {total_existing}")
    print(f"إجمالي Templates المفقودة: {total_missing}")
    
    # جدول ملخص
    print("\n" + "-" * 80)
    print(f"{'التطبيق':<25} {'Views':<8} {'مطلوب':<8} {'موجود':<8} {'مفقود':<8}")
    print("-" * 80)
    
    for r in all_results:
        if r['exists']:
            print(f"{r['app_name']:<25} {r['views_count']:<8} {len(r['required_templates']):<8} {len(r['existing_templates']):<8} {len(r['missing_templates']):<8}")
    
    # حفظ التقرير
    report = {
        'summary': {
            'total_required': total_required,
            'total_existing': total_existing,
            'total_missing': total_missing,
        },
        'apps': all_results,
        'all_missing_templates': all_missing
    }
    
    with open('templates_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n\nتم حفظ التقرير في: templates_analysis_report.json")
    
    # طباعة قائمة المفقودة الكاملة
    if all_missing:
        print("\n\n" + "=" * 80)
        print("قائمة جميع Templates المفقودة (مع المسار الكامل)")
        print("=" * 80)
        
        for item in all_missing:
            full_path = f"templates/{item['template']}"
            priority_mark = " [أولوية عالية]" if item['priority'] else ""
            print(f"  - {full_path}{priority_mark}")

if __name__ == '__main__':
    main()
