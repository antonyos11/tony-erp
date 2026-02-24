#!/usr/bin/env python3
"""
سكربت تحديث القوالب إلى التصميم العصري
يقوم بتحديث جميع صفحات القوائم والنماذج والتفاصيل
"""

import os
import re
import sys

# المسار الأساسي للقوالب
TEMPLATES_DIR = '/var/www/tony_erp/templates'

# تعريف الوحدات وألوانها
MODULES = {
    'partners': {'color': 'purple', 'icon': 'bi-people-fill', 'name': 'الشركاء'},
    'sales': {'color': 'green', 'icon': 'bi-cart-check-fill', 'name': 'المبيعات'},
    'inventory': {'color': 'orange', 'icon': 'bi-box-seam-fill', 'name': 'المخزون'},
    'purchases': {'color': 'blue', 'icon': 'bi-bag-fill', 'name': 'المشتريات'},
    'accounting': {'color': 'indigo', 'icon': 'bi-calculator-fill', 'name': 'المحاسبة'},
    'hr': {'color': 'pink', 'icon': 'bi-person-badge-fill', 'name': 'الموارد البشرية'},
    'fleet': {'color': 'teal', 'icon': 'bi-truck', 'name': 'الأسطول'},
    'production': {'color': 'orange', 'icon': 'bi-gear-fill', 'name': 'الإنتاج'},
    'projects': {'color': 'violet', 'icon': 'bi-kanban-fill', 'name': 'المشاريع'},
    'crm': {'color': 'cyan', 'icon': 'bi-person-lines-fill', 'name': 'العلاقات'},
    'maintenance': {'color': 'gray', 'icon': 'bi-tools', 'name': 'الصيانة'},
    'ecommerce': {'color': 'rose', 'icon': 'bi-shop', 'name': 'التجارة الإلكترونية'},
    'import_export': {'color': 'amber', 'icon': 'bi-arrow-left-right', 'name': 'الاستيراد والتصدير'},
    'installments': {'color': 'emerald', 'icon': 'bi-credit-card-2-front', 'name': 'الأقساط'},
    'fixed_assets': {'color': 'slate', 'icon': 'bi-building', 'name': 'الأصول الثابتة'},
    'shipping': {'color': 'sky', 'icon': 'bi-truck', 'name': 'الشحن'},
    'taxes': {'color': 'red', 'icon': 'bi-percent', 'name': 'الضرائب'},
    'eservices': {'color': 'fuchsia', 'icon': 'bi-phone', 'name': 'الخدمات الإلكترونية'},
    'payments': {'color': 'lime', 'icon': 'bi-cash-stack', 'name': 'المدفوعات'},
    'users': {'color': 'neutral', 'icon': 'bi-person-gear', 'name': 'المستخدمين'},
    'core': {'color': 'gray', 'icon': 'bi-gear', 'name': 'النظام'},
    'contracting': {'color': 'amber', 'icon': 'bi-building-gear', 'name': 'المقاولات'},
    'home_services': {'color': 'teal', 'icon': 'bi-house-gear', 'name': 'الخدمات المنزلية'},
}

def get_module_from_path(filepath):
    """استخراج اسم الوحدة من مسار الملف"""
    parts = filepath.replace(TEMPLATES_DIR, '').strip('/').split('/')
    if parts:
        module = parts[0]
        return module if module in MODULES else 'core'
    return 'core'

def check_if_needs_update(filepath):
    """التحقق إذا كان الملف يحتاج تحديث"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # إذا كان يستخدم القوالب الحديثة، لا يحتاج تحديث
    if 'modern_list.html' in content or 'modern_form.html' in content or 'modern_detail.html' in content:
        return False, 'already_modern'
    
    # إذا كان يستخدم _list_professional.html، لا يحتاج تحديث (تم تحديثه)
    if '_list_professional.html' in content:
        return False, 'uses_professional'
    
    # إذا كان يستخدم base_v2.html مباشرة، يحتاج تحديث
    if "extends 'base_v2.html'" in content or 'extends "base_v2.html"' in content:
        return True, 'uses_base_v2'
    
    return False, 'unknown'

def find_all_templates():
    """البحث عن جميع القوالب التي تحتاج تحديث"""
    templates = {
        'list': [],
        'form': [],
        'detail': [],
        'other': []
    }
    
    for root, dirs, files in os.walk(TEMPLATES_DIR):
        # تجاهل المجلدات الخاصة
        dirs[:] = [d for d in dirs if d not in ['base_templates', 'includes', 'emails', 'components', 'admin']]
        
        for file in files:
            if not file.endswith('.html'):
                continue
                
            filepath = os.path.join(root, file)
            needs_update, reason = check_if_needs_update(filepath)
            
            if not needs_update:
                continue
            
            # تصنيف نوع الصفحة
            if 'list' in file.lower():
                templates['list'].append(filepath)
            elif 'form' in file.lower() or 'create' in file.lower() or 'edit' in file.lower():
                templates['form'].append(filepath)
            elif 'detail' in file.lower() or 'view' in file.lower():
                templates['detail'].append(filepath)
            else:
                templates['other'].append(filepath)
    
    return templates

def update_list_template(filepath):
    """تحديث قالب قائمة ليستخدم التصميم الحديث"""
    module = get_module_from_path(filepath)
    module_info = MODULES.get(module, MODULES['core'])
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # استخراج المعلومات الموجودة
    title_match = re.search(r"{% block title %}(.+?){% endblock %}", content, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "القائمة"
    
    # تحديث extends
    new_content = re.sub(
        r"{% extends ['\"]base_v2\.html['\"] %}",
        "{% extends 'base_templates/_list_professional.html' %}",
        content
    )
    
    # إضافة blocks للوحدة
    if '{% block hero_icon %}' not in new_content:
        # إضافة بعد extends
        new_content = re.sub(
            r"({% extends ['\"]base_templates/_list_professional\.html['\"] %})",
            f"\\1\n\n{{% block hero_icon %}}{module_info['icon']}{{% endblock %}}",
            new_content
        )
    
    # حفظ الملف المحدث
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def update_form_template(filepath):
    """تحديث قالب نموذج ليستخدم التصميم الحديث"""
    module = get_module_from_path(filepath)
    module_info = MODULES.get(module, MODULES['core'])
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # تحديث extends
    new_content = re.sub(
        r"{% extends ['\"]base_v2\.html['\"] %}",
        "{% extends 'base_templates/modern_form.html' %}",
        content
    )
    
    # إضافة page_module block
    if '{% block page_module %}' not in new_content:
        new_content = re.sub(
            r"({% extends ['\"]base_templates/modern_form\.html['\"] %})",
            f"\\1\n\n{{% block page_module %}}{module}{{% endblock %}}",
            new_content
        )
    
    # حفظ الملف المحدث
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def update_detail_template(filepath):
    """تحديث قالب تفاصيل ليستخدم التصميم الحديث"""
    module = get_module_from_path(filepath)
    module_info = MODULES.get(module, MODULES['core'])
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # تحديث extends
    new_content = re.sub(
        r"{% extends ['\"]base_v2\.html['\"] %}",
        "{% extends 'base_templates/modern_detail.html' %}",
        content
    )
    
    # إضافة page_module block
    if '{% block page_module %}' not in new_content:
        new_content = re.sub(
            r"({% extends ['\"]base_templates/modern_detail\.html['\"] %})",
            f"\\1\n\n{{% block page_module %}}{module}{{% endblock %}}",
            new_content
        )
    
    # حفظ الملف المحدث
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def main():
    print("=" * 60)
    print("  تحديث القوالب إلى التصميم العصري")
    print("=" * 60)
    
    # البحث عن القوالب
    print("\n🔍 البحث عن القوالب التي تحتاج تحديث...")
    templates = find_all_templates()
    
    total = sum(len(v) for v in templates.values())
    print(f"\n📊 تم العثور على {total} قالب يحتاج تحديث:")
    print(f"   - قوائم: {len(templates['list'])}")
    print(f"   - نماذج: {len(templates['form'])}")
    print(f"   - تفاصيل: {len(templates['detail'])}")
    print(f"   - أخرى: {len(templates['other'])}")
    
    if '--dry-run' in sys.argv:
        print("\n⚠️ وضع المعاينة - لن يتم تحديث أي ملفات")
        for category, files in templates.items():
            if files:
                print(f"\n{category.upper()}:")
                for f in files[:10]:
                    print(f"  - {f.replace(TEMPLATES_DIR, '')}")
                if len(files) > 10:
                    print(f"  ... و {len(files) - 10} ملفات أخرى")
        return
    
    # تحديث القوالب
    updated = 0
    errors = []
    
    print("\n🔄 جاري تحديث القوالب...")
    
    # تحديث القوائم
    for filepath in templates['list']:
        try:
            if update_list_template(filepath):
                updated += 1
                print(f"  ✅ {filepath.replace(TEMPLATES_DIR, '')}")
        except Exception as e:
            errors.append((filepath, str(e)))
            print(f"  ❌ {filepath.replace(TEMPLATES_DIR, '')} - {e}")
    
    # تحديث النماذج
    for filepath in templates['form']:
        try:
            if update_form_template(filepath):
                updated += 1
                print(f"  ✅ {filepath.replace(TEMPLATES_DIR, '')}")
        except Exception as e:
            errors.append((filepath, str(e)))
            print(f"  ❌ {filepath.replace(TEMPLATES_DIR, '')} - {e}")
    
    # تحديث التفاصيل
    for filepath in templates['detail']:
        try:
            if update_detail_template(filepath):
                updated += 1
                print(f"  ✅ {filepath.replace(TEMPLATES_DIR, '')}")
        except Exception as e:
            errors.append((filepath, str(e)))
            print(f"  ❌ {filepath.replace(TEMPLATES_DIR, '')} - {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ تم تحديث {updated} قالب بنجاح")
    if errors:
        print(f"❌ فشل تحديث {len(errors)} قالب")
    print("=" * 60)

if __name__ == '__main__':
    main()
