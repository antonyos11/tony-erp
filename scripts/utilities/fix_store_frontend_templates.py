#!/usr/bin/env python3
"""
سكريبت لفصل جميع صفحات المتجر الأمامية عن النظام الرئيسي
"""
import os
import re

# مسارات مجلدات القوالب
TEMPLATES_DIRS = [
    '/var/www/tony_erp/templates/ecommerce',
    '/var/www/tony_erp/ecommerce/templates/ecommerce',
]

# القوالب المختلفة التي نريد استبدالها
# نستثني صفحات admin لأنها تم تحديثها مسبقاً
REPLACEMENTS = [
    # صفحات المتجر الأمامية - تستخدم store_base
    (r"{% extends ['\"]base_v2\.html['\"] %}", "{% extends 'ecommerce/store_base.html' %}"),
    (r"{% extends ['\"]base\.html['\"] %}", "{% extends 'ecommerce/store_base.html' %}"),
    (r"{% extends BASE_TEMPLATE %}", "{% extends 'ecommerce/store_base.html' %}"),
    (r"{% extends ['\"]base_templates/modern_detail\.html['\"] %}", "{% extends 'ecommerce/store_base.html' %}"),
    (r"{% extends ['\"]base_templates/_list_professional\.html['\"] %}", "{% extends 'ecommerce/store_base.html' %}"),
]

def should_skip_file(file_path):
    """تحديد ما إذا كان يجب تخطي الملف"""
    # تخطي ملفات admin (تم تحديثها مسبقاً)
    if '/admin/' in file_path:
        return True
    # تخطي base templates نفسها
    if 'base_admin.html' in file_path or 'store_base.html' in file_path or 'base_auth.html' in file_path:
        return True
    return False

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
            return False
            
    except Exception as e:
        print(f"❌ خطأ في {file_path}: {e}")
        return False

def update_all_templates():
    """تحديث جميع القوالب في المجلدات المحددة"""
    updated_count = 0
    skipped_count = 0
    total_count = 0
    
    # معالجة المجلدات
    for templates_dir in TEMPLATES_DIRS:
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
                    
                    if should_skip_file(file_path):
                        skipped_count += 1
                        print(f"⏭️  تخطي (admin): {file_path}")
                        continue
                    
                    if update_template(file_path):
                        updated_count += 1
    
    print("\n" + "=" * 80)
    print(f"📊 الإحصائيات:")
    print(f"   - إجمالي الملفات: {total_count}")
    print(f"   - الملفات المحدثة: {updated_count}")
    print(f"   - الملفات المتخطاة (admin): {skipped_count}")
    print(f"   - الملفات بدون تغيير: {total_count - updated_count - skipped_count}")
    print("=" * 80)

if __name__ == '__main__':
    print("🔄 بدء تحديث قوالب المتجر الأمامية...")
    print("=" * 80)
    update_all_templates()
    print("\n✅ تم الانتهاء من التحديث!")
