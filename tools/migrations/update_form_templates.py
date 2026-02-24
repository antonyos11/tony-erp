#!/usr/bin/env python
"""
سكربت لتحديث صفحات النماذج (Forms) لاستخدام التصميم الحديث
"""
import os
import re
import glob

BASE_DIR = '/var/www/tony_erp'
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# تخطيط الوحدات (modules) وأيقوناتها وألوانها
MODULE_CONFIG = {
    'accounting': {'icon': 'bi-calculator-fill', 'module': 'accounting'},
    'partners': {'icon': 'bi-people-fill', 'module': 'partners'},
    'purchases': {'icon': 'bi-bag-fill', 'module': 'purchases'},
    'sales': {'icon': 'bi-receipt', 'module': 'sales'},
    'inventory': {'icon': 'bi-box-seam-fill', 'module': 'inventory'},
    'hr': {'icon': 'bi-person-badge-fill', 'module': 'hr'},
    'crm': {'icon': 'bi-headset', 'module': 'crm'},
    'contracting': {'icon': 'bi-building', 'module': 'contracting'},
    'production': {'icon': 'bi-gear-fill', 'module': 'production'},
    'maintenance': {'icon': 'bi-wrench', 'module': 'maintenance'},
    'pos': {'icon': 'bi-cart-fill', 'module': 'pos'},
    'shipping': {'icon': 'bi-truck', 'module': 'shipping'},
    'ecommerce': {'icon': 'bi-shop', 'module': 'ecommerce'},
    'fixed_assets': {'icon': 'bi-building-fill', 'module': 'assets'},
    'taxes': {'icon': 'bi-percent', 'module': 'taxes'},
    'core': {'icon': 'bi-gear', 'module': 'core'},
    'reports': {'icon': 'bi-bar-chart-fill', 'module': 'reports'},
    'users': {'icon': 'bi-person-fill', 'module': 'users'},
    'approvals': {'icon': 'bi-check-circle-fill', 'module': 'approvals'},
    'payments': {'icon': 'bi-credit-card-fill', 'module': 'payments'},
}

# قوالب لا نريد تعديلها
EXCLUDE_TEMPLATES = [
    'base_templates/modern_form.html',
    'base_templates/modern_list.html',
    'base_templates/modern_detail.html',
    'base_templates/modern_dashboard.html',
    'base_templates/_list_professional.html',
    'purchase_form.html.old',
]

def get_module_from_path(file_path):
    """استخراج اسم الوحدة من مسار الملف"""
    parts = file_path.replace(TEMPLATES_DIR, '').strip('/').split('/')
    if len(parts) > 1:
        return parts[0]
    return None

def get_title_from_content(content):
    """محاولة استخراج العنوان من المحتوى الحالي"""
    # البحث عن عنوان في block title
    match = re.search(r'\{% block title %\}([^{]+)\{% endblock %\}', content)
    if match:
        title = match.group(1).strip()
        # إزالة trans و trans
        title = re.sub(r'\{% trans [\'"]([^\'"]+)[\'"] %\}', r'\1', title)
        title = re.sub(r' - .*$', '', title)  # إزالة اسم الموقع
        return title
    
    # البحث عن h4 أو h3 في card-header
    match = re.search(r'<h[34][^>]*>([^<]+)</h[34]>', content)
    if match:
        return match.group(1).strip()
    
    return None

def check_needs_update(content):
    """فحص ما إذا كان الملف يحتاج تحديث"""
    # إذا كان يستخدم modern_form.html بالفعل - لا يحتاج تحديث
    if "extends 'base_templates/modern_form.html'" in content:
        return False
    
    # إذا كان يستخدم BASE_TEMPLATE أو base_v2.html - يحتاج تحديث
    if "{% extends BASE_TEMPLATE %}" in content or "{% extends 'base_v2.html' %}" in content:
        return True
    
    return False

def add_css_link_if_missing(content):
    """إضافة رابط CSS الحديث إذا لم يكن موجوداً"""
    if "modern_pages.css" not in content:
        # إضافة في extra_head أو extra_css
        if "{% block extra_head %}" in content:
            content = content.replace(
                "{% block extra_head %}",
                "{% block extra_head %}\n<link rel=\"stylesheet\" href=\"{% static 'css/modern_pages.css' %}\">"
            )
        elif "{% block extra_css %}" in content:
            content = content.replace(
                "{% block extra_css %}",
                "{% block extra_css %}\n<link rel=\"stylesheet\" href=\"{% static 'css/modern_pages.css' %}\">"
            )
    return content

def update_form_template(file_path):
    """تحديث قالب نموذج واحد"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not check_needs_update(content):
            return False, "لا يحتاج تحديث"
        
        module = get_module_from_path(file_path)
        config = MODULE_CONFIG.get(module, {'icon': 'bi-file-earmark-text', 'module': 'default'})
        title = get_title_from_content(content) or 'نموذج جديد'
        
        # استخراج المحتوى بين block content
        content_match = re.search(
            r'\{% block content %\}(.*?)\{% endblock %\}',
            content,
            re.DOTALL
        )
        
        if not content_match:
            return False, "لا يوجد block content"
        
        form_content = content_match.group(1).strip()
        
        # استخراج extra_js إن وجد
        js_match = re.search(
            r'\{% block extra_js %\}(.*?)\{% endblock %\}',
            content,
            re.DOTALL
        )
        extra_js = js_match.group(1).strip() if js_match else ''
        
        # استخراج extra_head/extra_css إن وجد
        head_match = re.search(
            r'\{% block extra_(?:head|css) %\}(.*?)\{% endblock %\}',
            content,
            re.DOTALL
        )
        extra_head = head_match.group(1).strip() if head_match else ''
        
        # بناء القالب الجديد
        new_content = f'''{{%% extends 'base_templates/modern_form.html' %%}}
{{%% load static i18n %%}}

{{%% block page_module %%}}{config['module']}{{%% endblock %%}}
{{%% block page_icon %%}}{config['icon']}{{%% endblock %%}}
{{%% block page_title %%}}{{%% trans '{title}' %%}}{{%% endblock %%}}

{{%% block extra_head %%}}
<link rel="stylesheet" href="{{%% static 'css/modern_pages.css' %%}}">
{extra_head}
{{%% endblock %%}}

{{%% block form_content %%}}
{form_content}
{{%% endblock %%}}

{f'{{%% block extra_js %%}}{extra_js}{{%% endblock %%}}' if extra_js else ''}
'''
        
        # حفظ الملف
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True, "تم التحديث بنجاح"
        
    except Exception as e:
        return False, f"خطأ: {str(e)}"

def main():
    print("=" * 60)
    print("🔄 تحديث صفحات النماذج للتصميم الحديث")
    print("=" * 60)
    
    # البحث عن جميع ملفات _form.html
    form_files = glob.glob(os.path.join(TEMPLATES_DIR, '**/*_form.html'), recursive=True)
    
    updated = 0
    skipped = 0
    errors = 0
    
    for file_path in form_files:
        relative_path = file_path.replace(TEMPLATES_DIR + '/', '')
        
        # تخطي الملفات المستثناة
        if any(exc in relative_path for exc in EXCLUDE_TEMPLATES):
            print(f"⏭️  تخطي: {relative_path}")
            skipped += 1
            continue
        
        success, message = update_form_template(file_path)
        
        if success:
            print(f"✅ {relative_path}: {message}")
            updated += 1
        elif "لا يحتاج تحديث" in message:
            print(f"⏭️  {relative_path}: {message}")
            skipped += 1
        else:
            print(f"❌ {relative_path}: {message}")
            errors += 1
    
    print("=" * 60)
    print(f"📊 النتائج:")
    print(f"   ✅ تم تحديث: {updated} ملف")
    print(f"   ⏭️  تخطي: {skipped} ملف")
    print(f"   ❌ أخطاء: {errors} ملف")
    print("=" * 60)

if __name__ == '__main__':
    main()
