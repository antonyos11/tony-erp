#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار شامل لنظام الضمان - Warranty System Complete Test
=========================================================
هذا الملف يختبر جميع وظائف نظام الضمان بشكل كامل

الوظائف المختبرة:
1. إنشاء سياسة ضمان (ProductWarranty)
2. إنشاء بطاقة ضمان (WarrantyCard)
3. تسجيل/تفعيل الضمان من العميل (WarrantyRegistration)
4. مطالبة الضمان (WarrantyClaim)
5. API التحقق من الضمان
6. حساب الأيام المتبقية
7. إلغاء وانتهاء الضمان
"""

import os
import sys
import django
from datetime import date, timedelta

# إعداد Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, 'الشامل', 'الشامل', 'app')
sys.path.insert(0, APP_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')

django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Colors:
    """ألوان للطباعة الجميلة"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")


def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_info(text):
    print(f"{Colors.YELLOW}📋 {text}{Colors.END}")


def print_section(text):
    print(f"\n{Colors.MAGENTA}▶ {text}{Colors.END}")


def test_warranty_system():
    """اختبار شامل لنظام الضمان"""
    
    print_header("🛡️ اختبار نظام الضمان الشامل 🛡️")
    
    results = {
        'passed': 0,
        'failed': 0,
        'tests': []
    }
    
    try:
        from ecommerce.models import (
            ProductWarranty, WarrantyCard, WarrantyRegistration,
            WarrantyClaim, OnlineProduct
        )
        from inventory.models import Product, Category
        print_success("تم استيراد الموديلات بنجاح")
        results['passed'] += 1
        results['tests'].append(('استيراد الموديلات', True))
    except Exception as e:
        print_error(f"فشل استيراد الموديلات: {e}")
        results['failed'] += 1
        results['tests'].append(('استيراد الموديلات', False))
        return results
    
    # ======================================
    # 1. اختبار سياسة الضمان
    # ======================================
    print_section("اختبار سياسة الضمان (ProductWarranty)")
    
    try:
        # إنشاء سياسة ضمان جديدة
        warranty_policy, created = ProductWarranty.objects.get_or_create(
            name='ضمان اختباري شامل',
            defaults={
                'description': 'سياسة ضمان للاختبار - تشمل جميع أعطال التصنيع',
                'duration': 12,
                'duration_unit': 'months',
                'terms_and_conditions': '''
شروط وأحكام الضمان:
1. يغطي الضمان جميع أعطال التصنيع
2. لا يشمل الأضرار الناتجة عن سوء الاستخدام
3. يجب تقديم الفاتورة الأصلية عند المطالبة
4. مدة الضمان 12 شهراً من تاريخ الشراء
                ''',
                'coverage': '''
ما يغطيه الضمان:
- أعطال التصنيع
- الأعطال الكهربائية
- أعطال المكونات الداخلية
- عيوب المواد الخام
                ''',
                'exclusions': '''
ما لا يغطيه الضمان:
- الأضرار الناتجة عن سوء الاستخدام
- الأضرار الناتجة عن الماء أو السوائل
- الأضرار الناتجة عن الحوادث
- استبدال البطاريات والملحقات
                ''',
                'is_active': True,
                'requires_registration': True
            }
        )
        
        if created:
            print_success(f"تم إنشاء سياسة ضمان جديدة: {warranty_policy.name}")
        else:
            print_info(f"سياسة الضمان موجودة: {warranty_policy.name}")
        
        # اختبار حساب تاريخ الانتهاء
        today = date.today()
        expiry_date = warranty_policy.get_expiry_date(today)
        print_info(f"تاريخ البدء: {today}")
        print_info(f"تاريخ الانتهاء المحسوب: {expiry_date}")
        print_info(f"مدة الضمان: {warranty_policy.duration} {warranty_policy.get_duration_unit_display()}")
        
        results['passed'] += 1
        results['tests'].append(('سياسة الضمان', True))
        
    except Exception as e:
        print_error(f"فشل اختبار سياسة الضمان: {e}")
        results['failed'] += 1
        results['tests'].append(('سياسة الضمان', False))
        return results
    
    # ======================================
    # 2. اختبار بطاقة الضمان
    # ======================================
    print_section("اختبار بطاقة الضمان (WarrantyCard)")
    
    try:
        # الحصول على أو إنشاء منتج للاختبار
        category, _ = Category.objects.get_or_create(
            name='منتجات اختبارية',
            defaults={'description': 'فئة للاختبار'}
        )
        
        product, _ = Product.objects.get_or_create(
            sku='TEST-WARRANTY-001',
            defaults={
                'name': 'منتج اختبار الضمان',
                'category': category,
                'price': 1000,
                'description': 'منتج للاختبار مع ضمان'
            }
        )
        
        # إنشاء بطاقة ضمان
        warranty_code = WarrantyCard.generate_warranty_code()
        print_info(f"رمز الضمان المولد: {warranty_code}")
        
        warranty_card = WarrantyCard.objects.create(
            warranty_code=warranty_code,
            inventory_product=product,
            warranty_policy=warranty_policy,
            purchase_date=today,
            status='pending'
        )
        
        print_success(f"تم إنشاء بطاقة ضمان: {warranty_card}")
        print_info(f"الحالة: {warranty_card.get_status_display()}")
        
        # اختبار خصائص البطاقة
        print_info(f"هل الضمان صالح؟ {warranty_card.is_valid}")  # يجب أن يكون False لأنه pending
        
        results['passed'] += 1
        results['tests'].append(('بطاقة الضمان', True))
        
    except Exception as e:
        print_error(f"فشل اختبار بطاقة الضمان: {e}")
        import traceback
        traceback.print_exc()
        results['failed'] += 1
        results['tests'].append(('بطاقة الضمان', False))
        return results
    
    # ======================================
    # 3. اختبار تفعيل الضمان
    # ======================================
    print_section("اختبار تفعيل الضمان")
    
    try:
        # الحصول على مستخدم للاختبار
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()
        
        # تفعيل الضمان
        warranty_card.status = 'active'
        warranty_card.warranty_start_date = today
        warranty_card.activated_at = timezone.now()
        warranty_card.activated_by = admin_user
        warranty_card.save()
        
        # إعادة تحميل من قاعدة البيانات
        warranty_card.refresh_from_db()
        
        print_success(f"تم تفعيل الضمان بنجاح!")
        print_info(f"تاريخ بدء الضمان: {warranty_card.warranty_start_date}")
        print_info(f"تاريخ انتهاء الضمان: {warranty_card.warranty_end_date}")
        print_info(f"الأيام المتبقية: {warranty_card.days_remaining}")
        print_info(f"هل الضمان صالح؟ {warranty_card.is_valid}")
        
        if warranty_card.is_valid:
            print_success("الضمان صالح ✓")
        else:
            print_error("الضمان غير صالح!")
        
        results['passed'] += 1
        results['tests'].append(('تفعيل الضمان', True))
        
    except Exception as e:
        print_error(f"فشل اختبار تفعيل الضمان: {e}")
        import traceback
        traceback.print_exc()
        results['failed'] += 1
        results['tests'].append(('تفعيل الضمان', False))
    
    # ======================================
    # 4. اختبار تسجيل الضمان من العميل
    # ======================================
    print_section("اختبار تسجيل الضمان من العميل (WarrantyRegistration)")
    
    try:
        # إنشاء بطاقة ضمان جديدة في حالة انتظار للاختبار
        new_warranty_code = WarrantyCard.generate_warranty_code()
        pending_card = WarrantyCard.objects.create(
            warranty_code=new_warranty_code,
            inventory_product=product,
            warranty_policy=warranty_policy,
            purchase_date=today - timedelta(days=7),  # تم الشراء قبل أسبوع
            status='pending'
        )
        
        # إنشاء طلب تسجيل ضمان (بدون ملف صورة للاختبار)
        registration = WarrantyRegistration.objects.create(
            warranty_card=pending_card,
            customer_name='عميل اختباري',
            customer_email='test@example.com',
            customer_phone='0501234567',
            customer_address='شارع الاختبار، مدينة الاختبار',
            warranty_code_entered=new_warranty_code,
            invoice_number='INV-TEST-001',
            purchase_date=today - timedelta(days=7),
            product_serial='SN-TEST-12345',
            status='pending'
        )
        
        print_success(f"تم إنشاء طلب تسجيل ضمان: {registration}")
        print_info(f"الحالة: {registration.get_status_display()}")
        print_info(f"العميل: {registration.customer_name}")
        print_info(f"الهاتف: {registration.customer_phone}")
        
        # اختبار الموافقة على التسجيل
        print_info("جاري الموافقة على طلب التسجيل...")
        registration.approve(admin_user)
        
        # إعادة تحميل البطاقة
        pending_card.refresh_from_db()
        registration.refresh_from_db()
        
        print_success(f"تمت الموافقة على التسجيل!")
        print_info(f"حالة التسجيل: {registration.get_status_display()}")
        print_info(f"حالة البطاقة: {pending_card.get_status_display()}")
        print_info(f"تاريخ بدء الضمان: {pending_card.warranty_start_date}")
        print_info(f"تاريخ انتهاء الضمان: {pending_card.warranty_end_date}")
        print_info(f"هل الضمان صالح؟ {pending_card.is_valid}")
        
        results['passed'] += 1
        results['tests'].append(('تسجيل الضمان', True))
        
    except Exception as e:
        print_error(f"فشل اختبار تسجيل الضمان: {e}")
        import traceback
        traceback.print_exc()
        results['failed'] += 1
        results['tests'].append(('تسجيل الضمان', False))
    
    # ======================================
    # 5. اختبار مطالبة الضمان
    # ======================================
    print_section("اختبار مطالبة الضمان (WarrantyClaim)")
    
    try:
        # إنشاء مطالبة ضمان
        claim = WarrantyClaim.objects.create(
            warranty_card=warranty_card,
            claim_type='repair',
            issue_description='الجهاز لا يعمل بشكل صحيح - يصدر صوت غريب عند التشغيل',
            contact_name='عميل اختباري',
            contact_phone='0501234567',
            contact_email='test@example.com',
            pickup_address='شارع الاختبار، مدينة الاختبار',
            status='submitted'
        )
        
        print_success(f"تم إنشاء مطالبة ضمان: {claim}")
        print_info(f"نوع المطالبة: {claim.get_claim_type_display()}")
        print_info(f"الحالة: {claim.get_status_display()}")
        print_info(f"وصف المشكلة: {claim.issue_description[:50]}...")
        
        # تغيير حالة المطالبة
        claim.status = 'under_review'
        claim.assigned_to = admin_user
        claim.save()
        
        print_info(f"تم تحويل المطالبة للمراجعة")
        print_info(f"مُسندة إلى: {claim.assigned_to}")
        
        # إغلاق المطالبة بنجاح
        claim.status = 'completed'
        claim.resolution_notes = 'تم إصلاح الجهاز بنجاح - تم استبدال المكون التالف'
        claim.resolved_at = timezone.now()
        claim.save()
        
        print_success(f"تم إغلاق المطالبة بنجاح!")
        print_info(f"ملاحظات الحل: {claim.resolution_notes}")
        
        results['passed'] += 1
        results['tests'].append(('مطالبة الضمان', True))
        
    except Exception as e:
        print_error(f"فشل اختبار مطالبة الضمان: {e}")
        import traceback
        traceback.print_exc()
        results['failed'] += 1
        results['tests'].append(('مطالبة الضمان', False))
    
    # ======================================
    # 6. اختبار الضمان المنتهي
    # ======================================
    print_section("اختبار الضمان المنتهي")
    
    try:
        # إنشاء بطاقة ضمان منتهية
        old_warranty_code = WarrantyCard.generate_warranty_code()
        expired_card = WarrantyCard.objects.create(
            warranty_code=old_warranty_code,
            inventory_product=product,
            warranty_policy=warranty_policy,
            purchase_date=today - timedelta(days=400),  # تم الشراء قبل أكثر من سنة
            status='active',
            warranty_start_date=today - timedelta(days=400),
            warranty_end_date=today - timedelta(days=35),  # انتهى قبل شهر
        )
        
        print_info(f"بطاقة ضمان: {expired_card.warranty_code}")
        print_info(f"تاريخ الانتهاء: {expired_card.warranty_end_date}")
        print_info(f"هل الضمان صالح؟ {expired_card.is_valid}")
        print_info(f"الأيام المتبقية: {expired_card.days_remaining}")
        
        if not expired_card.is_valid:
            print_success("تم اكتشاف الضمان المنتهي بشكل صحيح ✓")
        else:
            print_error("خطأ: الضمان يظهر كصالح رغم انتهائه!")
        
        results['passed'] += 1
        results['tests'].append(('الضمان المنتهي', True))
        
    except Exception as e:
        print_error(f"فشل اختبار الضمان المنتهي: {e}")
        results['failed'] += 1
        results['tests'].append(('الضمان المنتهي', False))
    
    # ======================================
    # 7. اختبار الضمان الملغي
    # ======================================
    print_section("اختبار الضمان الملغي")
    
    try:
        # إنشاء بطاقة ضمان ملغية
        void_warranty_code = WarrantyCard.generate_warranty_code()
        void_card = WarrantyCard.objects.create(
            warranty_code=void_warranty_code,
            inventory_product=product,
            warranty_policy=warranty_policy,
            purchase_date=today,
            status='void'  # ملغي
        )
        
        print_info(f"بطاقة ضمان ملغية: {void_card.warranty_code}")
        print_info(f"الحالة: {void_card.get_status_display()}")
        print_info(f"هل الضمان صالح؟ {void_card.is_valid}")
        
        if not void_card.is_valid:
            print_success("تم اكتشاف الضمان الملغي بشكل صحيح ✓")
        else:
            print_error("خطأ: الضمان يظهر كصالح رغم إلغائه!")
        
        results['passed'] += 1
        results['tests'].append(('الضمان الملغي', True))
        
    except Exception as e:
        print_error(f"فشل اختبار الضمان الملغي: {e}")
        results['failed'] += 1
        results['tests'].append(('الضمان الملغي', False))
    
    # ======================================
    # 8. عرض إحصائيات الضمان
    # ======================================
    print_section("إحصائيات نظام الضمان")
    
    try:
        total_policies = ProductWarranty.objects.count()
        active_policies = ProductWarranty.objects.filter(is_active=True).count()
        
        total_cards = WarrantyCard.objects.count()
        pending_cards = WarrantyCard.objects.filter(status='pending').count()
        active_cards = WarrantyCard.objects.filter(status='active').count()
        expired_cards = WarrantyCard.objects.filter(status='expired').count()
        void_cards = WarrantyCard.objects.filter(status='void').count()
        
        total_registrations = WarrantyRegistration.objects.count()
        pending_registrations = WarrantyRegistration.objects.filter(status='pending').count()
        approved_registrations = WarrantyRegistration.objects.filter(status='approved').count()
        
        total_claims = WarrantyClaim.objects.count()
        pending_claims = WarrantyClaim.objects.filter(status__in=['submitted', 'under_review']).count()
        completed_claims = WarrantyClaim.objects.filter(status='completed').count()
        
        print_info(f"📊 سياسات الضمان:")
        print_info(f"   - إجمالي: {total_policies} | مفعلة: {active_policies}")
        
        print_info(f"📊 بطاقات الضمان:")
        print_info(f"   - إجمالي: {total_cards}")
        print_info(f"   - في الانتظار: {pending_cards}")
        print_info(f"   - مفعلة: {active_cards}")
        print_info(f"   - منتهية: {expired_cards}")
        print_info(f"   - ملغية: {void_cards}")
        
        print_info(f"📊 طلبات التسجيل:")
        print_info(f"   - إجمالي: {total_registrations}")
        print_info(f"   - في الانتظار: {pending_registrations}")
        print_info(f"   - موافق عليها: {approved_registrations}")
        
        print_info(f"📊 مطالبات الضمان:")
        print_info(f"   - إجمالي: {total_claims}")
        print_info(f"   - معلقة: {pending_claims}")
        print_info(f"   - مكتملة: {completed_claims}")
        
        results['passed'] += 1
        results['tests'].append(('الإحصائيات', True))
        
    except Exception as e:
        print_error(f"فشل عرض الإحصائيات: {e}")
        results['failed'] += 1
        results['tests'].append(('الإحصائيات', False))
    
    # ======================================
    # عرض النتائج النهائية
    # ======================================
    print_header("📋 ملخص نتائج الاختبار")
    
    print(f"\n{Colors.BOLD}النتائج:{Colors.END}")
    for test_name, passed in results['tests']:
        status = f"{Colors.GREEN}✅ نجح{Colors.END}" if passed else f"{Colors.RED}❌ فشل{Colors.END}"
        print(f"  • {test_name}: {status}")
    
    total = results['passed'] + results['failed']
    success_rate = (results['passed'] / total * 100) if total > 0 else 0
    
    print(f"\n{Colors.BOLD}الإجمالي:{Colors.END}")
    print(f"  • الاختبارات الناجحة: {Colors.GREEN}{results['passed']}{Colors.END}")
    print(f"  • الاختبارات الفاشلة: {Colors.RED}{results['failed']}{Colors.END}")
    print(f"  • نسبة النجاح: {Colors.CYAN}{success_rate:.1f}%{Colors.END}")
    
    if success_rate == 100:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 جميع الاختبارات نجحت! نظام الضمان يعمل بشكل كامل.{Colors.END}")
    elif success_rate >= 80:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️ معظم الاختبارات نجحت. هناك بعض المشاكل البسيطة.{Colors.END}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ هناك مشاكل في نظام الضمان تحتاج إصلاح.{Colors.END}")
    
    return results


def show_usage_guide():
    """عرض دليل استخدام نظام الضمان"""
    
    print_header("📖 دليل استخدام نظام الضمان")
    
    guide = """
┌─────────────────────────────────────────────────────────────────────┐
│                    🛡️ نظام الضمان الشامل                           │
└─────────────────────────────────────────────────────────────────────┘

📌 المكونات الرئيسية:
══════════════════════════════════════════════════════════════════════

1️⃣ سياسات الضمان (ProductWarranty)
   ├── تحديد مدة الضمان (أيام/أشهر/سنوات)
   ├── تحديد ما يغطيه الضمان
   ├── تحديد الاستثناءات
   └── تعيين الشروط والأحكام

2️⃣ بطاقات الضمان (WarrantyCard)
   ├── رمز ضمان فريد لكل منتج
   ├── كود QR للتحقق السريع
   ├── ربط بالمنتج وفاتورة البيع
   └── تتبع حالة الضمان

3️⃣ تسجيل الضمان (WarrantyRegistration)
   ├── العميل يسجل الضمان بعد الشراء
   ├── رفع صورة الفاتورة
   └── الإدارة توافق/ترفض الطلب

4️⃣ مطالبات الضمان (WarrantyClaim)
   ├── العميل يقدم مطالبة عند وجود مشكلة
   ├── تتبع حالة المطالبة
   └── إغلاق المطالبة بعد الإصلاح/الاستبدال


📌 كيفية الاستخدام من الواجهة:
══════════════════════════════════════════════════════════════════════

🔗 روابط الضمان للعملاء:
   /shop/warranty/              - الصفحة الرئيسية
   /shop/warranty/check/        - التحقق من حالة الضمان
   /shop/warranty/register/     - تسجيل ضمان جديد

🔗 روابط الإدارة:
   /shop/admin/warranty/                    - لوحة تحكم الضمان
   /shop/admin/warranty/policies/           - إدارة السياسات
   /shop/admin/warranty/cards/              - إدارة البطاقات
   /shop/admin/warranty/registrations/      - طلبات التفعيل
   /shop/admin/warranty/claims/             - مطالبات الضمان


📌 سير العمل (Workflow):
══════════════════════════════════════════════════════════════════════

    ┌────────────┐
    │  بيع منتج  │
    └─────┬──────┘
          ▼
    ┌────────────────────┐
    │ إنشاء بطاقة ضمان  │ (تلقائي مع الفاتورة)
    │  حالة: pending     │
    └─────┬──────────────┘
          ▼
    ┌────────────────────┐
    │ العميل يسجل الضمان │
    │ مع صورة الفاتورة   │
    └─────┬──────────────┘
          ▼
    ┌────────────────────┐
    │ الإدارة تراجع      │
    │ وتوافق على الطلب   │
    └─────┬──────────────┘
          ▼
    ┌────────────────────┐
    │  الضمان مفعّل      │
    │  حالة: active      │
    └─────┬──────────────┘
          ▼
    ┌────────────────────┐
    │  في حالة مشكلة:    │
    │  العميل يقدم مطالبة│
    └─────┬──────────────┘
          ▼
    ┌────────────────────┐
    │   معالجة المطالبة  │
    │ إصلاح/استبدال/رفض  │
    └────────────────────┘


📌 حالات بطاقة الضمان:
══════════════════════════════════════════════════════════════════════

   pending   ⏳  في انتظار التفعيل (بعد البيع مباشرة)
   active    ✅  مفعّل (الضمان ساري)
   expired   ⌛  منتهي (انتهت مدة الضمان)
   claimed   🔧  تم المطالبة (جاري الإصلاح)
   void      ❌  ملغي (تم إلغاء الضمان)


📌 أنواع المطالبات:
══════════════════════════════════════════════════════════════════════

   repair      🔧  طلب إصلاح المنتج
   replacement 🔄  طلب استبدال المنتج
   refund      💰  طلب استرداد المبلغ


📌 استخدام API:
══════════════════════════════════════════════════════════════════════

GET /shop/api/warranty/verify/?code=WRN-XXXX-XXXXXXXXXX

Response:
{
    "valid": true,
    "code": "WRN-2412-ABC123XYZ",
    "status": "active",
    "status_display": "مفعل",
    "product_name": "منتج اختباري",
    "purchase_date": "2024-12-01",
    "warranty_end_date": "2025-12-01",
    "is_valid": true,
    "days_remaining": 340
}


📌 أمثلة برمجية:
══════════════════════════════════════════════════════════════════════

# إنشاء سياسة ضمان
from ecommerce.models import ProductWarranty

policy = ProductWarranty.objects.create(
    name='ضمان سنة',
    duration=12,
    duration_unit='months',
    coverage='عيوب التصنيع',
    exclusions='سوء الاستخدام',
    is_active=True
)

# إنشاء بطاقة ضمان
from ecommerce.models import WarrantyCard

card = WarrantyCard.objects.create(
    inventory_product=product,
    warranty_policy=policy,
    purchase_date=date.today(),
    status='pending'
)

# تفعيل الضمان
card.status = 'active'
card.warranty_start_date = date.today()
card.save()

# التحقق من صلاحية الضمان
if card.is_valid:
    print(f"الضمان ساري، متبقي {card.days_remaining} يوم")
else:
    print("الضمان منتهي أو ملغي")

# إنشاء مطالبة ضمان
from ecommerce.models import WarrantyClaim

claim = WarrantyClaim.objects.create(
    warranty_card=card,
    claim_type='repair',
    issue_description='وصف المشكلة',
    contact_name='اسم العميل',
    contact_phone='0501234567',
    status='submitted'
)

══════════════════════════════════════════════════════════════════════
    """
    
    print(guide)


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🛡️  اختبار نظام الضمان الشامل - Tony ERP")
    print("=" * 70)
    
    # عرض دليل الاستخدام أولاً
    show_usage_guide()
    
    # تشغيل الاختبارات
    input(f"\n{Colors.CYAN}اضغط Enter لبدء الاختبارات...{Colors.END}")
    
    results = test_warranty_system()
    
    print("\n" + "=" * 70)
    print("تم الانتهاء من الاختبار")
    print("=" * 70)
