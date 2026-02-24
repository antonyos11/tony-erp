#!/usr/bin/env python
"""
سكريبت تصفير النظام بالكامل
يحذف جميع البيانات ويبقي على هيكل قاعدة البيانات

⚠️ تحذير: هذا السكريبت مخصص لبيئة التطوير فقط!
لا تستخدمه في بيئة الإنتاج أبداً!
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import connection
from django.apps import apps
from django.conf import settings

User = get_user_model()


def check_environment():
    """التحقق من أن هذا ليس بيئة إنتاج"""
    # فحص متغير البيئة
    if os.environ.get('DJANGO_ENV', '').lower() == 'production':
        print("❌ خطأ: لا يمكن تشغيل هذا السكريبت في بيئة الإنتاج!")
        sys.exit(1)
    
    # فحص DEBUG
    if not getattr(settings, 'DEBUG', True):
        print("❌ خطأ: DEBUG=False - يبدو أن هذه بيئة إنتاج!")
        print("   إذا كنت متأكداً، عيّن DJANGO_ENV=development")
        sys.exit(1)
    
    # فحص قاعدة البيانات
    db_name = settings.DATABASES.get('default', {}).get('NAME', '')
    if 'production' in str(db_name).lower() or 'prod' in str(db_name).lower():
        print(f"❌ خطأ: اسم قاعدة البيانات يبدو إنتاجياً: {db_name}")
        sys.exit(1)
    
    return True


def get_all_models():
    """الحصول على جميع الموديلات في المشروع"""
    all_models = []
    for app_config in apps.get_app_configs():
        # استثناء تطبيقات Django الأساسية
        if app_config.name.startswith('django.'):
            continue
        for model in app_config.get_models():
            all_models.append(model)
    return all_models

def reset_database():
    """تصفير قاعدة البيانات بالكامل"""
    print("=" * 60)
    print("🗑️  بدء عملية تصفير النظام")
    print("=" * 60)
    
    # الموديلات التي يجب استثناؤها (الأساسية)
    excluded_models = [
        'auth.Permission',
        'auth.Group',
        'contenttypes.ContentType',
        'sessions.Session',
        'admin.LogEntry',
    ]
    
    # حذف جميع البيانات
    all_models = get_all_models()
    deleted_count = 0
    
    # ترتيب الموديلات بحيث نحذف الموديلات التابعة أولاً
    for model in reversed(all_models):
        model_name = f"{model._meta.app_label}.{model._meta.model_name}"
        
        # استثناء المستخدمين حسب الاختيار
        if model == User:
            continue
            
        try:
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
                print(f"✅ تم حذف {count} سجل من {model._meta.verbose_name_plural or model.__name__}")
                deleted_count += count
        except Exception as e:
            print(f"⚠️  خطأ في حذف {model.__name__}: {str(e)[:50]}")
    
    print("\n" + "=" * 60)
    print(f"✅ تم حذف إجمالي {deleted_count} سجل")
    print("=" * 60)
    
    return deleted_count

def reset_users(keep_superuser=True):
    """إعادة تعيين المستخدمين"""
    if keep_superuser:
        # حذف جميع المستخدمين ما عدا السوبر يوزر
        deleted = User.objects.filter(is_superuser=False).delete()
        print(f"✅ تم حذف {deleted[0]} مستخدم (تم الإبقاء على المسؤولين)")
    else:
        # حذف الجميع
        deleted = User.objects.all().delete()
        print(f"✅ تم حذف {deleted[0]} مستخدم")

def reset_sequences():
    """إعادة تعيين الـ auto-increment لـ SQLite"""
    with connection.cursor() as cursor:
        # للـ SQLite
        try:
            cursor.execute("DELETE FROM sqlite_sequence;")
            print("✅ تم إعادة تعيين الـ auto-increment")
        except:
            pass

def main():
    # فحص البيئة أولاً
    check_environment()
    
    # عرض معلومات قاعدة البيانات
    db_name = settings.DATABASES.get('default', {}).get('NAME', 'unknown')
    print(f"\n📁 قاعدة البيانات: {db_name}")
    
    print("\n" + "=" * 60)
    print("⚠️  تحذير: سيتم حذف جميع البيانات من النظام!")
    print("   هذا الإجراء لا يمكن التراجع عنه!")
    print("=" * 60)
    print("\nاختر نوع التصفير:")
    print("1. تصفير كل شيء ما عدا المسؤولين (Superusers)")
    print("2. تصفير كل شيء بالكامل (بما فيهم المستخدمين)")
    print("3. إلغاء")
    
    choice = input("\nاختيارك (1/2/3): ").strip()
    
    if choice == "3":
        print("تم الإلغاء.")
        return
    
    if choice not in ("1", "2"):
        print("اختيار غير صالح.")
        return
    
    # تأكيد إضافي - أقوى من مجرد 'نعم'
    confirm = input("\n⚠️  هل أنت متأكد؟ اكتب 'DELETE ALL' للتأكيد: ").strip()
    if confirm != "DELETE ALL":
        print("تم الإلغاء - لم تكتب 'DELETE ALL' بشكل صحيح.")
        return
    
    # تنفيذ التصفير
    reset_database()
    
    if choice == "1":
        reset_users(keep_superuser=True)
    elif choice == "2":
        reset_users(keep_superuser=False)
    
    reset_sequences()
    
    print("\n" + "=" * 60)
    print("🎉 تم تصفير النظام بنجاح!")
    print("=" * 60)
    print("\n📌 الخطوات التالية:")
    if choice == "2":
        print("1. قم بإنشاء مستخدم مسؤول جديد:")
        print("   python manage.py createsuperuser")
    print("2. ابدأ بإدخال البيانات الفعلية")
    print("")

if __name__ == "__main__":
    main()
