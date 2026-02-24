"""
سكربت حذف جميع البيانات ماعدا: المستخدمين، الموردين، موظفين HR، الفروع
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.apps import apps
from django.db import connection

# التطبيقات المحمية - لن يتم مسح بياناتها
KEEP_APPS = {
    'auth',           # المستخدمين
    'users',          # ملفات المستخدمين
    'accounts',       # حسابات الدخول
    'admin',          # Django admin
    'contenttypes',   # Django content types
    'sessions',       # Sessions
    'partners',       # الموردين
    'hr',             # الموارد البشرية
    'branches',       # الفروع
}

# موديلات محددة للحفظ من تطبيق core
KEEP_CORE_MODELS = {
    'Currency', 'Company', 'AppSettings', 'Country', 'State', 'Branch',
    'Sequence',  # تسلسل الأكواد
}

# موديلات Django الداخلية - لا تمسح
SKIP_APPS = {
    'auth', 'contenttypes', 'sessions', 'admin',
    'users', 'accounts', 'partners', 'hr', 'branches',
}


def cleanup():
    print("=" * 60)
    print("  بدء عملية تنظيف البيانات")
    print("  المحفوظ: المستخدمين، الموردين، HR، الفروع")
    print("=" * 60)
    
    deleted_total = 0
    errors = []
    skipped = []
    
    # جمع كل الموديلات المطلوب حذفها
    models_to_delete = []
    
    for app_config in apps.get_app_configs():
        app_label = app_config.label
        
        if app_label in SKIP_APPS:
            print(f"  ✓ تخطي التطبيق المحمي: {app_label}")
            continue
        
        for model in app_config.get_models():
            # تخطي الموديلات المحمية في core
            if app_label == 'core' and model.__name__ in KEEP_CORE_MODELS:
                print(f"  ✓ حفظ core.{model.__name__}")
                continue
            
            # تخطي الجداول الوسيطة ManyToMany التلقائية
            if model._meta.auto_created:
                continue
                
            models_to_delete.append(model)
    
    print(f"\n  عدد الموديلات المطلوب تنظيفها: {len(models_to_delete)}")
    print("-" * 60)
    
    # حذف البيانات - نحاول عدة مرات بسبب العلاقات المتداخلة
    remaining = list(models_to_delete)
    max_passes = 5
    
    for pass_num in range(1, max_passes + 1):
        if not remaining:
            break
            
        print(f"\n  --- المرور {pass_num} ---")
        still_remaining = []
        
        for model in remaining:
            table_name = model._meta.db_table
            model_name = f"{model._meta.app_label}.{model.__name__}"
            
            try:
                count = model.objects.count()
                if count == 0:
                    continue
                
                # حذف مباشر بـ SQL لتجنب مشاكل العلاقات
                with connection.cursor() as cursor:
                    cursor.execute(f'DELETE FROM "{table_name}"')
                
                deleted_total += count
                print(f"  🗑️  {model_name}: حذف {count} سجل")
                
            except Exception as e:
                error_msg = str(e)
                if 'FOREIGN KEY' in error_msg.upper() or 'foreign key' in error_msg or 'constraint' in error_msg.lower():
                    still_remaining.append(model)
                else:
                    # محاولة بـ ORM
                    try:
                        count = model.objects.count()
                        if count > 0:
                            model.objects.all().delete()
                            deleted_total += count
                            print(f"  🗑️  {model_name}: حذف {count} سجل (ORM)")
                    except Exception as e2:
                        still_remaining.append(model)
                        if pass_num == max_passes:
                            errors.append(f"{model_name}: {str(e2)[:100]}")
        
        remaining = still_remaining
    
    # محاولة أخيرة مع PRAGMA foreign_keys = OFF (SQLite)
    if remaining:
        print(f"\n  --- محاولة أخيرة مع تعطيل FK ---")
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            for model in remaining:
                table_name = model._meta.db_table
                model_name = f"{model._meta.app_label}.{model.__name__}"
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                    count = cursor.fetchone()[0]
                    if count > 0:
                        cursor.execute(f'DELETE FROM "{table_name}"')
                        deleted_total += count
                        print(f"  🗑️  {model_name}: حذف {count} سجل (FK OFF)")
                except Exception as e:
                    errors.append(f"{model_name}: {str(e)[:100]}")
            
            cursor.execute("PRAGMA foreign_keys = ON")
    
    # إعادة تعيين auto-increment
    print("\n  --- إعادة تعيين العدادات ---")
    with connection.cursor() as cursor:
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name NOT IN (SELECT name FROM sqlite_sequence WHERE name LIKE 'auth_%' OR name LIKE 'users_%' OR name LIKE 'accounts_%' OR name LIKE 'partners_%' OR name LIKE 'hr_%' OR name LIKE 'branches_%')")
            print("  ✓ تم إعادة تعيين العدادات")
        except Exception:
            pass
    
    # تقرير
    print("\n" + "=" * 60)
    print(f"  ✅ تم حذف {deleted_total} سجل بنجاح")
    
    if errors:
        print(f"\n  ⚠️ أخطاء ({len(errors)}):")
        for e in errors[:10]:
            print(f"    - {e}")
    
    print("\n  المحفوظ:")
    print("    ✓ المستخدمين (Users)")
    print("    ✓ الموردين (Partners/Suppliers)")
    print("    ✓ الموارد البشرية (HR)")
    print("    ✓ الفروع (Branches)")
    print("    ✓ العملات والدول والشركة (Core basics)")
    print("=" * 60)


if __name__ == '__main__':
    cleanup()
