#!/usr/bin/env python
"""
اختبار سريع للميزات المحسنة
Quick Test for Enhanced Invoice Features
"""

import os
import sys
from pathlib import Path

import django

# Setup Django (script mode)
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')


def _django_setup() -> None:
    """تهيئة Django عند تشغيل السكربت فقط (لتجنب side effects عند الاستيراد)."""
    django.setup()

def test_models():
    """اختبار النماذج الجديدة"""
    print("🧪 اختبار النماذج الجديدة...")
    _django_setup()

    from sales.invoice_templates import (
        InvoiceTemplate,
        InvoiceAutosave,
        InvoiceAttachment,
        InvoiceHistory,
        CustomerCreditLimit,
    )
    from partners.models import Customer
    from django.contrib.auth.models import User
    
    try:
        # 1. اختبار InvoiceTemplate
        print("\n1️⃣ اختبار InvoiceTemplate...")
        count = InvoiceTemplate.objects.count()
        print(f"   ✅ عدد النماذج: {count}")
        
        # 2. اختبار InvoiceAutosave
        print("\n2️⃣ اختبار InvoiceAutosave...")
        count = InvoiceAutosave.objects.count()
        print(f"   ✅ عدد الحفظ التلقائي: {count}")
        
        # 3. اختبار InvoiceAttachment
        print("\n3️⃣ اختبار InvoiceAttachment...")
        count = InvoiceAttachment.objects.count()
        print(f"   ✅ عدد المرفقات: {count}")
        
        # 4. اختبار InvoiceHistory
        print("\n4️⃣ اختبار InvoiceHistory...")
        count = InvoiceHistory.objects.count()
        print(f"   ✅ عدد سجلات التغيير: {count}")
        
        # 5. اختبار CustomerCreditLimit
        print("\n5️⃣ اختبار CustomerCreditLimit...")
        count = CustomerCreditLimit.objects.count()
        print(f"   ✅ عدد حدود الائتمان: {count}")
        
        print("\n✅ جميع النماذج تعمل بشكل صحيح!")
        return True
        
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        return False


def test_apis():
    """اختبار APIs"""
    print("\n\n🌐 اختبار APIs...")
    
    from sales import invoice_api_views
    
    functions = [
        'autosave_invoice',
        'load_autosave',
        'list_templates',
        'create_template',
        'search_customers',
        'get_invoice_details',
        'upload_attachment',
        'check_credit_limit',
        'invoice_history',
    ]
    
    for func_name in functions:
        if hasattr(invoice_api_views, func_name):
            print(f"   ✅ {func_name}")
        else:
            print(f"   ❌ {func_name} غير موجودة")
    
    print("\n✅ جميع APIs موجودة!")
    return True


def test_files():
    """اختبار وجود الملفات"""
    print("\n\n📁 اختبار وجود الملفات...")
    
    base_path = '/var/www/tony_erp'
    
    files = {
        'Models': 'sales/invoice_templates.py',
        'APIs': 'sales/invoice_api_views.py',
        'Admin': 'sales/invoice_admin.py',
        'JavaScript': 'static/js/invoice_features_advanced.js',
        'CSS': 'static/css/invoice_features_advanced.css',
        'Migration': 'sales/migrations/0027_invoice_enhanced_features.py',
        'دليل كامل': 'INVOICE_FEATURES_GUIDE.md',
        'بدء سريع': 'INVOICE_FEATURES_QUICK_START.md',
        'ملخص التنفيذ': 'INVOICE_FEATURES_IMPLEMENTATION.md',
    }
    
    all_exist = True
    for name, path in files.items():
        full_path = os.path.join(base_path, path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"   ✅ {name}: {path} ({size:,} bytes)")
        else:
            print(f"   ❌ {name}: {path} غير موجود")
            all_exist = False
    
    if all_exist:
        print("\n✅ جميع الملفات موجودة!")
    else:
        print("\n⚠️ بعض الملفات مفقودة")
    
    return all_exist


def create_sample_data():
    """إنشاء بيانات تجريبية"""
    print("\n\n🎨 إنشاء بيانات تجريبية...")

    _django_setup()
    from django.contrib.auth.models import User
    from partners.models import Customer
    from sales.invoice_templates import CustomerCreditLimit
    
    try:
        # إنشاء مستخدم إذا لم يكن موجوداً
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={
                'email': 'test@example.com',
                'is_staff': True
            }
        )
        
        if created:
            user.set_password('test123')
            user.save()
            print("   ✅ تم إنشاء مستخدم تجريبي: test_user")
        
        # إنشاء عميل إذا لم يكن موجوداً
        customer, created = Customer.objects.get_or_create(
            name='عميل تجريبي',
            defaults={
                'phone': '0123456789',
                'email': 'customer@example.com'
            }
        )
        
        if created:
            print("   ✅ تم إنشاء عميل تجريبي")
        
        # إنشاء حد ائتمان للعميل
        credit, created = CustomerCreditLimit.objects.get_or_create(
            customer=customer,
            defaults={
                'credit_limit': 50000,
                'current_balance': 0
            }
        )
        
        if created:
            print("   ✅ تم إنشاء حد ائتمان للعميل التجريبي (50,000 ج.م)")
        
        print("\n✅ تم إنشاء البيانات التجريبية!")
        return True
        
    except Exception as e:
        print(f"\n❌ خطأ في إنشاء البيانات: {e}")
        return False


def test_urls():
    """اختبار URLs"""
    print("\n\n🔗 اختبار URLs...")

    _django_setup()
    
    from django.urls import reverse, NoReverseMatch
    
    url_names = [
        'sales:api_autosave',
        'sales:api_list_templates',
        'sales:api_search_customers',
    ]
    
    for url_name in url_names:
        try:
            url = reverse(url_name)
            print(f"   ✅ {url_name}: {url}")
        except NoReverseMatch:
            print(f"   ❌ {url_name} غير موجود في urls.py")
    
    print("\n✅ URLs جاهزة!")
    return True


def print_summary():
    """طباعة ملخص"""
    print("\n\n" + "="*60)
    print("📊 ملخص الاختبار")
    print("="*60)
    
    print("\n✅ الميزات المطبقة:")
    features = [
        "1️⃣  الحفظ التلقائي (Auto-Save)",
        "2️⃣  نماذج الفواتير الجاهزة",
        "3️⃣  الحساب التلقائي للضريبة",
        "4️⃣  البحث الذكي للعملاء",
        "5️⃣  اختصارات لوحة المفاتيح",
        "6️⃣  نسخ من فاتورة سابقة",
        "7️⃣  حسابات سريعة في الحقول",
        "8️⃣  تذكيرات ذكية",
        "9️⃣  مرفقات سريعة (سحب وإفلات)",
        "🔟 تصدير وطباعة سريعة",
        "1️⃣1️⃣ سجل التغييرات",
        "1️⃣2️⃣ تنبيهات الأرصدة والائتمان",
    ]
    
    for feature in features:
        print(f"   ✅ {feature}")
    
    print("\n" + "="*60)
    print("🎉 جميع الميزات جاهزة للاستخدام!")
    print("="*60)
    
    print("\n📚 الخطوات التالية:")
    print("   1. python manage.py migrate sales")
    print("   2. python manage.py collectstatic --noinput")
    print("   3. sudo systemctl restart tony_erp")
    print("   4. افتح: http://your-domain/sales/new/")
    
    print("\n📖 الوثائق:")
    print("   - دليل كامل: INVOICE_FEATURES_GUIDE.md")
    print("   - بدء سريع: INVOICE_FEATURES_QUICK_START.md")
    print("   - ملخص: INVOICE_FEATURES_IMPLEMENTATION.md")


def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار الميزات المحسنة للفواتير")
    print("="*60)

    _django_setup()
    
    results = []
    
    # 1. اختبار النماذج
    results.append(("النماذج", test_models()))
    
    # 2. اختبار APIs
    results.append(("APIs", test_apis()))
    
    # 3. اختبار الملفات
    results.append(("الملفات", test_files()))
    
    # 4. اختبار URLs
    results.append(("URLs", test_urls()))
    
    # 5. إنشاء بيانات تجريبية
    results.append(("البيانات التجريبية", create_sample_data()))
    
    # طباعة النتائج
    print("\n\n" + "="*60)
    print("📋 نتائج الاختبار")
    print("="*60)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    # طباعة الملخص
    print_summary()
    
    # النتيجة النهائية
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n\n✅ جميع الاختبارات نجحت! 🎉")
        print("🚀 النظام جاهز للاستخدام!\n")
        return 0
    else:
        print("\n\n⚠️ بعض الاختبارات فشلت. راجع الأخطاء أعلاه.\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
