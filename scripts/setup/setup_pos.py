#!/usr/bin/env python
"""
سكربت إعداد نظام نقاط البيع (POS)
====================================
يقوم هذا السكربت بإنشاء البيانات الأساسية المطلوبة لتشغيل نظام POS:
- طرق الدفع (نقدي، فيزا، ماستر كارد، إلخ)
- موقع/معرض افتراضي للـ POS
- التحقق من وجود المتطلبات الأخرى

الاستخدام:
    python setup_pos.py
    
أو عبر أمر الإدارة:
    python manage.py setup_pos
"""

import os
import sys
from pathlib import Path

import django

# إعداد Django
# عند تشغيل السكربت مباشرةً نضمن إضافة جذر المشروع إلى sys.path
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.db import transaction
from payments.models import PaymentMethod
from inventory.models import Location
from accounting.models import Account


def create_payment_methods():
    """إنشاء طرق الدفع الأساسية"""
    
    payment_methods_data = [
        {
            'name': 'نقدي',
            'type': 'cash',
            'display_order': 1,
            'is_active': True,
        },
        {
            'name': 'فيزا',
            'type': 'credit_card',
            'display_order': 2,
            'is_active': True,
        },
        {
            'name': 'ماستر كارد',
            'type': 'credit_card',
            'display_order': 3,
            'is_active': True,
        },
        {
            'name': 'حوالة بنكية',
            'type': 'bank_transfer',
            'display_order': 4,
            'is_active': True,
        },
        {
            'name': 'فودافون كاش',
            'type': 'vodafone_cash',
            'display_order': 5,
            'is_active': True,
        },
        {
            'name': 'إنستا باي',
            'type': 'instapay',
            'display_order': 6,
            'is_active': True,
        },
        {
            'name': 'شيك',
            'type': 'check',
            'display_order': 7,
            'is_active': True,
        },
    ]
    
    created_count = 0
    updated_count = 0
    
    for method_data in payment_methods_data:
        method, created = PaymentMethod.objects.get_or_create(
            name=method_data['name'],
            defaults=method_data
        )
        if created:
            created_count += 1
            print(f"  ✅ تم إنشاء طريقة الدفع: {method.name}")
        else:
            # تحديث البيانات إذا موجودة
            for key, value in method_data.items():
                setattr(method, key, value)
            method.save()
            updated_count += 1
            print(f"  ✔️ تم تحديث طريقة الدفع: {method.name}")
    
    return created_count, updated_count


def create_pos_location():
    """إنشاء موقع/معرض افتراضي للـ POS"""
    
    pos_location, created = Location.objects.get_or_create(
        code='POS-MAIN',
        defaults={
            'name': 'المعرض الرئيسي - نقطة البيع',
            'type': 'store',
            'address': 'المتجر الرئيسي',
            'is_active': True,
            'is_default': True,
        }
    )
    
    if created:
        print(f"  ✅ تم إنشاء موقع POS: {pos_location.name}")
        return True
    else:
        print(f"  ✔️ موقع POS موجود مسبقاً: {pos_location.name}")
        return False


def verify_cash_account():
    """التحقق من وجود حساب الصندوق وربطه بطريقة الدفع النقدي"""
    
    # البحث عن حساب الصندوق
    cash_account = Account.objects.filter(
        name__icontains='صندوق'
    ).first()
    
    if not cash_account:
        # محاولة إنشاء حساب صندوق بسيط
        cash_account = Account.objects.filter(
            account_type='asset'
        ).first()
    
    if cash_account:
        # ربط حساب الصندوق بطريقة الدفع النقدي
        cash_method = PaymentMethod.objects.filter(type='cash').first()
        if cash_method and not cash_method.account:
            cash_method.account = cash_account
            cash_method.save()
            print(f"  ✅ تم ربط حساب '{cash_account.name}' بطريقة الدفع النقدي")
            return True
        else:
            print(f"  ✔️ حساب الصندوق مرتبط مسبقاً بطريقة الدفع النقدي")
    else:
        print("  ⚠️ لم يتم العثور على حساب صندوق - يرجى إنشاؤه يدوياً")
    
    return False


def verify_requirements():
    """التحقق من المتطلبات الأخرى"""
    
    issues = []
    
    # التحقق من وجود مستخدم
    from django.contrib.auth.models import User
    if not User.objects.filter(is_active=True).exists():
        issues.append("لا يوجد مستخدمين نشطين - يجب إنشاء مستخدم أولاً")
    
    # التحقق من وجود منتجات
    from inventory.models import Product
    product_count = Product.objects.count()
    if product_count == 0:
        issues.append("لا توجد منتجات - يجب إضافة منتجات للبيع")
    else:
        print(f"  ✅ يوجد {product_count} منتج")
    
    return issues


def run_setup(verbose=True):
    """تشغيل إعداد POS الكامل"""
    
    print("\n" + "=" * 60)
    print("🏪  إعداد نظام نقاط البيع (POS)")
    print("=" * 60 + "\n")
    
    with transaction.atomic():
        # 1. إنشاء طرق الدفع
        print("📋 1. إعداد طرق الدفع...")
        created, updated = create_payment_methods()
        print(f"   → تم إنشاء {created} طريقة جديدة، تحديث {updated} موجودة\n")
        
        # 2. إنشاء موقع POS
        print("📍 2. إعداد موقع نقطة البيع...")
        create_pos_location()
        print()
        
        # 3. ربط حساب الصندوق
        print("💰 3. ربط الحسابات المحاسبية...")
        verify_cash_account()
        print()
        
        # 4. التحقق من المتطلبات
        print("✅ 4. التحقق من المتطلبات...")
        issues = verify_requirements()
        
        if issues:
            print("\n⚠️  تحذيرات:")
            for issue in issues:
                print(f"   - {issue}")
        
        print("\n" + "=" * 60)
        print("🎉  تم إعداد نظام POS بنجاح!")
        print("=" * 60)
        
        # إحصائيات نهائية
        print("\n📊 الإحصائيات:")
        print(f"   - طرق الدفع: {PaymentMethod.objects.count()}")
        print(f"   - مواقع POS: {Location.objects.filter(type='store').count()}")
        
        print("\n💡 الخطوات التالية:")
        print("   1. افتح نظام POS من: /pos/")
        print("   2. ابدأ جلسة جديدة لنقطة البيع")
        print("   3. أضف منتجات للسلة وأتم عملية البيع")
        print()
    
    return len(issues) == 0


if __name__ == '__main__':
    success = run_setup()
    sys.exit(0 if success else 1)
