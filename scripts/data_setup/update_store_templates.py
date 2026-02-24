#!/usr/bin/env python3
"""
سكريبت لتحديث جميع قوالب إدارة المتجر لاستخدام base_admin.html بدلاً من base.html
"""
import os
import re

# مسار مجلد القوالب
TEMPLATES_DIR = '/var/www/tony_erp/templates/ecommerce/admin'
ECOMMERCE_TEMPLATES_DIR = '/var/www/tony_erp/ecommerce/templates/ecommerce/admin'

# القوالب المختلفة التي نريد استبدالها
REPLACEMENTS = [
    (r"{% extends ['\"]base\.html['\"] %}", "{% extends 'ecommerce/admin/base_admin.html' %}"),
    (r"{% extends ['\"]base_v2\.html['\"] %}", "{% extends 'ecommerce/admin/base_admin.html' %}"),
    (r"{% extends BASE_TEMPLATE %}", "{% extends 'ecommerce/admin/base_admin.html' %}"),
    (r"{% extends ['\"]base_templates/modern_form\.html['\"] %}", "{% extends 'ecommerce/admin/base_admin.html' %}"),
    (r"{% extends ['\"]base_templates/_form_professional\.html['\"] %}", "{% extends 'ecommerce/admin/base_admin.html' %}"),
]

def update_template(file_path):
    """تحديث ملف قالب واحد"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # تطبيق جميع الاستبدالات
        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content)
        
        # إذا تم التغيير، احفظ الملف
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ تم تحديث: {file_path}")
            return True
        else:
            print(f"⏭️  لا يحتاج لتحديث: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في {file_path}: {e}")
        return False

def update_all_templates():
    """تحديث جميع القوالب في المجلدات المحددة"""
    updated_count = 0
    total_count = 0
    
    # معالجة المجلدين
    for templates_dir in [TEMPLATES_DIR, ECOMMERCE_TEMPLATES_DIR]:
        if not os.path.exists(templates_dir):
            print(f"⚠️  المجلد غير موجود: {templates_dir}")
            continue
            
        print(f"\n📁 معالجة المجلد: {templates_dir}")
        print("=" * 80)
        
        # البحث عن جميع ملفات HTML بشكل متكرر
        for root, dirs, files in os.walk(templates_dir):
            for file in files:
                if file.endswith('.html'):
                    file_path = os.path.join(root, file)
                    total_count += 1
                    if update_template(file_path):
                        updated_count += 1
    
    print("\n" + "=" * 80)
    print(f"📊 الإحصائيات:")
    print(f"   - إجمالي الملفات: {total_count}")
    print(f"   - الملفات المحدثة: {updated_count}")
    print(f"   - الملفات بدون تغيير: {total_count - updated_count}")
    print("=" * 80)

if __name__ == '__main__':
    print("🔄 بدء تحديث قوالب إدارة المتجر...")
    print("=" * 80)
    update_all_templates()
    print("\n✅ تم الانتهاء من التحديث!")
