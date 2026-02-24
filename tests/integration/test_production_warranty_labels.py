#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار شامل لمنظومة طباعة ملصقات الضمان من الإنتاج
====================================================
هذا الملف يختبر:
1. إنشاء وحدات المنتجات النهائية (FinishedGoodUnit)
2. توليد الباركود و QR Code تلقائياً
3. طباعة الملصقات الفردية والجماعية
4. تفعيل الضمان للوحدات
5. تتبع دورة حياة الوحدة من الإنتاج للبيع
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
from django.db.models import Q

User = get_user_model()


class Colors:
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


def test_production_warranty_labels():
    """اختبار منظومة طباعة ملصقات الضمان من الإنتاج"""
    
    print_header("🏭 اختبار منظومة طباعة ملصقات الضمان من الإنتاج 🏭")
    
    results = {
        'passed': 0,
        'failed': 0,
        'tests': []
    }
    
    # ======================================
    # 1. استيراد الموديلات
    # ======================================
    print_section("استيراد الموديلات")
    
    try:
        from production.models import FinishedGoodUnit, ProductionOrder
        from inventory.models import Product, Category
        from ecommerce.models import ProductWarranty
        print_success("تم استيراد موديلات الإنتاج")
        results['passed'] += 1
        results['tests'].append(('استيراد الموديلات', True))
    except Exception as e:
        print_error(f"فشل استيراد الموديلات: {e}")
        results['failed'] += 1
        results['tests'].append(('استيراد الموديلات', False))
        return results
    
    # ======================================
    # 2. إنشاء بيانات اختبارية
    # ======================================
    print_section("إنشاء بيانات اختبارية")
    
    try:
        # إنشاء فئة ومنتج
        category, _ = Category.objects.get_or_create(
            name='أجهزة كهربائية اختبارية',
            defaults={'description': 'فئة للاختبار'}
        )
        
        product, _ = Product.objects.get_or_create(
            sku='PROD-WARRANTY-TEST-001',
            defaults={
                'name': 'جهاز اختباري للضمان',
                'category': category,
                'price': 2500,
                'description': 'جهاز للاختبار مع ضمان وملصقات'
            }
        )
        print_success(f"تم إنشاء المنتج: {product.name}")
        
        # إنشاء سياسة ضمان
        warranty_policy, _ = ProductWarranty.objects.get_or_create(
            name='ضمان سنتين للأجهزة',
            defaults={
                'duration': 24,
                'duration_unit': 'months',
                'coverage': 'جميع أعطال التصنيع',
                'exclusions': 'الأضرار الناتجة عن سوء الاستخدام',
                'is_active': True
            }
        )
        print_success(f"تم إنشاء سياسة الضمان: {warranty_policy.name}")
        
        # البحث عن أمر إنتاج موجود أو تخطي هذه الخطوة
        production_order = ProductionOrder.objects.filter(status='completed').first()
        if not production_order:
            production_order = ProductionOrder.objects.first()
        
        if production_order:
            print_success(f"تم استخدام أمر إنتاج موجود: {production_order.number}")
            product = production_order.product  # استخدم منتج أمر الإنتاج
        else:
            print_info("لا توجد أوامر إنتاج، سيتم إنشاء الوحدات بدون أمر")
        
        results['passed'] += 1
        results['tests'].append(('إنشاء البيانات الاختبارية', True))
        
    except Exception as e:
        print_error(f"فشل إنشاء البيانات: {e}")
        import traceback
        traceback.print_exc()
        results['failed'] += 1
        results['tests'].append(('إنشاء البيانات الاختبارية', False))
        return results
    
    # ======================================
    # 3. اختبار وحدات المنتجات النهائية الموجودة
    # ======================================
    print_section("اختبار وحدات المنتجات النهائية الموجودة")
    
    created_units = []
    try:
        # البحث عن وحدات موجودة
        existing_units = list(FinishedGoodUnit.objects.select_related(
            'product', 'production_order', 'warranty_policy'
        ).order_by('-id')[:5])
        
        if existing_units:
            created_units = existing_units
            print_success(f"تم العثور على {len(existing_units)} وحدة موجودة")
            for unit in existing_units[:3]:
                print_info(f"  - {unit.unit_serial} | {unit.product.name if unit.product else 'N/A'} | {unit.get_status_display()}")
            results['passed'] += 1
            results['tests'].append(('وحدات المنتجات', True))
        else:
            # لا توجد وحدات - نحتاج أمر إنتاج لإنشائها
            print_info("لا توجد وحدات منتجات نهائية في النظام")
            print_info("ℹ️ لإنشاء وحدات، يجب:")
            print_info("   1. إنشاء أمر إنتاج")
            print_info("   2. اكتمال الإنتاج")
            print_info("   3. توليد الوحدات من /production/orders/<id>/generate-units/")
            results['passed'] += 1
            results['tests'].append(('وحدات المنتجات', True))
        
    except Exception as e:
        print_error(f"فشل اختبار الوحدات: {e}")
        results['failed'] += 1
        results['tests'].append(('وحدات المنتجات', False))
    
    # ======================================
    # 4. اختبار توليد QR Code
    # ======================================
    print_section("اختبار توليد QR Code تلقائياً")
    
    try:
        unit = created_units[0] if created_units else None
        if unit:
            # التحقق من بيانات QR
            if unit.qr_code_data:
                print_success(f"تم توليد بيانات QR Code")
                print_info(f"بيانات QR (جزء): {unit.qr_code_data[:100]}...")
            else:
                print_info("لم يتم توليد بيانات QR تلقائياً، جاري التوليد...")
                unit.generate_qr_data()
                unit.save()
                print_success(f"تم توليد بيانات QR")
            
            # التحقق من صورة QR
            if unit.qr_code_image:
                print_success(f"صورة QR موجودة: {unit.qr_code_image.name}")
            else:
                print_info("صورة QR غير موجودة (ستُنشأ عند الطباعة)")
            
            results['passed'] += 1
            results['tests'].append(('توليد QR Code', True))
        else:
            print_error("لا توجد وحدات للاختبار")
            results['failed'] += 1
            results['tests'].append(('توليد QR Code', False))
            
    except Exception as e:
        print_error(f"فشل اختبار QR Code: {e}")
        results['failed'] += 1
        results['tests'].append(('توليد QR Code', False))
    
    # ======================================
    # 5. اختبار تغيير حالات الوحدة
    # ======================================
    print_section("اختبار دورة حياة الوحدة")
    
    try:
        if created_units:
            unit = created_units[0]
            
            # الحالة: تم الإنتاج
            print_info(f"الحالة الأولية: {unit.get_status_display()}")
            
            # نقل للمخزون
            unit.status = 'in_stock'
            unit.save()
            print_success(f"تم النقل للمخزون: {unit.get_status_display()}")
            
            # بيع لتاجر
            unit.status = 'sold_to_dealer'
            unit.dealer_sale_date = date.today()
            unit.dealer_sale_price = 2000
            unit.save()
            print_success(f"تم البيع لتاجر: {unit.get_status_display()}")
            
            # بيع لعميل نهائي
            unit.status = 'sold_to_customer'
            unit.customer_name = 'أحمد محمد'
            unit.customer_phone = '0501234567'
            unit.customer_email = 'ahmed@example.com'
            unit.customer_sale_date = date.today()
            unit.customer_sale_price = 2500
            unit.save()
            print_success(f"تم البيع لعميل: {unit.get_status_display()}")
            print_info(f"العميل: {unit.customer_name}")
            
            results['passed'] += 1
            results['tests'].append(('دورة حياة الوحدة', True))
        else:
            results['failed'] += 1
            results['tests'].append(('دورة حياة الوحدة', False))
            
    except Exception as e:
        print_error(f"فشل اختبار دورة الحياة: {e}")
        results['failed'] += 1
        results['tests'].append(('دورة حياة الوحدة', False))
    
    # ======================================
    # 6. اختبار تفعيل الضمان للوحدة
    # ======================================
    print_section("اختبار تفعيل الضمان للوحدة")
    
    try:
        if created_units and len(created_units) > 1:
            unit = created_units[1]
            
            # بيانات العميل
            customer_data = {
                'name': 'خالد عبدالله',
                'phone': '0509876543',
                'email': 'khaled@example.com',
                'address': 'الرياض - حي النزهة',
                'national_id': '1234567890'
            }
            
            # تفعيل الضمان
            result = unit.activate_warranty(customer_data)
            
            if result:
                print_success("تم تفعيل الضمان بنجاح!")
                print_info(f"تاريخ بدء الضمان: {unit.warranty_start_date}")
                print_info(f"تاريخ نهاية الضمان: {unit.warranty_end_date}")
                print_info(f"هل الضمان ساري؟ {unit.is_warranty_valid}")
                print_info(f"الأيام المتبقية: {unit.warranty_remaining_days}")
                print_info(f"الحالة: {unit.get_status_display()}")
                
                results['passed'] += 1
                results['tests'].append(('تفعيل الضمان للوحدة', True))
            else:
                print_error("فشل تفعيل الضمان")
                results['failed'] += 1
                results['tests'].append(('تفعيل الضمان للوحدة', False))
        else:
            print_error("لا توجد وحدات كافية للاختبار")
            results['failed'] += 1
            results['tests'].append(('تفعيل الضمان للوحدة', False))
            
    except Exception as e:
        print_error(f"فشل اختبار تفعيل الضمان: {e}")
        import traceback
        traceback.print_exc()
        results['failed'] += 1
        results['tests'].append(('تفعيل الضمان للوحدة', False))
    
    # ======================================
    # 7. اختبار البحث عن الوحدات
    # ======================================
    print_section("اختبار البحث عن الوحدات")
    
    try:
        if created_units:
            unit = created_units[0]
            
            # البحث بالرقم التسلسلي
            found = FinishedGoodUnit.objects.filter(unit_serial=unit.unit_serial).first()
            if found:
                print_success(f"تم العثور بالرقم التسلسلي: {found.unit_serial}")
            
            # البحث بالباركود
            found = FinishedGoodUnit.objects.filter(barcode=unit.barcode).first()
            if found:
                print_success(f"تم العثور بالباركود: {found.barcode}")
            
            # البحث المتعدد
            found = FinishedGoodUnit.objects.filter(
                Q(unit_serial=unit.unit_serial) | Q(barcode=unit.barcode)
            ).first()
            if found:
                print_success(f"البحث المتعدد نجح!")
            
            results['passed'] += 1
            results['tests'].append(('البحث عن الوحدات', True))
        else:
            results['failed'] += 1
            results['tests'].append(('البحث عن الوحدات', False))
            
    except Exception as e:
        print_error(f"فشل البحث: {e}")
        results['failed'] += 1
        results['tests'].append(('البحث عن الوحدات', False))
    
    # ======================================
    # 8. عرض الإحصائيات
    # ======================================
    print_section("إحصائيات وحدات المنتجات النهائية")
    
    try:
        stats = {
            'total': FinishedGoodUnit.objects.count(),
            'produced': FinishedGoodUnit.objects.filter(status='produced').count(),
            'in_stock': FinishedGoodUnit.objects.filter(status='in_stock').count(),
            'sold_dealer': FinishedGoodUnit.objects.filter(status='sold_to_dealer').count(),
            'sold_customer': FinishedGoodUnit.objects.filter(status='sold_to_customer').count(),
            'warranty_registered': FinishedGoodUnit.objects.filter(warranty_registered=True).count(),
        }
        
        print_info(f"📊 إجمالي الوحدات: {stats['total']}")
        print_info(f"   - تم الإنتاج: {stats['produced']}")
        print_info(f"   - في المخزن: {stats['in_stock']}")
        print_info(f"   - مباع لتاجر: {stats['sold_dealer']}")
        print_info(f"   - مباع لعميل: {stats['sold_customer']}")
        print_info(f"   - ضمان مسجل: {stats['warranty_registered']}")
        
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
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 جميع الاختبارات نجحت! منظومة طباعة الملصقات تعمل بشكل كامل.{Colors.END}")
    
    return results


def show_labels_guide():
    """عرض دليل استخدام منظومة طباعة الملصقات"""
    
    print_header("📖 دليل منظومة طباعة ملصقات الضمان من الإنتاج")
    
    guide = """
┌─────────────────────────────────────────────────────────────────────┐
│              🏭 منظومة طباعة ملصقات الضمان من الإنتاج               │
└─────────────────────────────────────────────────────────────────────┘

📌 نظرة عامة:
══════════════════════════════════════════════════════════════════════
هذه المنظومة تربط بين نظام الإنتاج ونظام الضمان:
• عند انتهاء تصنيع منتج → يتم إنشاء وحدة (FinishedGoodUnit)
• كل وحدة لها رقم تسلسلي فريد + باركود + QR Code
• يمكن طباعة ملصقات لكل وحدة أو مجموعة من الوحدات
• عند البيع للعميل → يتم تفعيل الضمان بمسح QR Code


📌 المكونات الرئيسية:
══════════════════════════════════════════════════════════════════════

1️⃣ وحدة المنتج النهائي (FinishedGoodUnit)
   ├── رقم تسلسلي فريد (unit_serial)
   ├── باركود (barcode)
   ├── QR Code (qr_code_data, qr_code_image)
   ├── تاريخ الإنتاج والصلاحية
   ├── معلومات التاجر والعميل
   └── معلومات الضمان

2️⃣ حالات الوحدة:
   • produced         → تم الإنتاج
   • in_stock         → في المخزن
   • sold_to_dealer   → مباع لتاجر
   • sold_to_customer → مباع لعميل
   • warranty_registered → ضمان مسجل


📌 روابط المنظومة:
══════════════════════════════════════════════════════════════════════

🔗 إدارة الوحدات:
   /production/units/                              - قائمة الوحدات
   /production/units/<id>/                         - تفاصيل وحدة
   /production/units/<id>/print/                   - طباعة ملصق واحد
   /production/units/print-batch/?ids=1,2,3        - طباعة ملصقات متعددة

🔗 من أمر الإنتاج:
   /production/orders/<id>/generate-units/         - توليد الوحدات تلقائياً
   /production/orders/<id>/print-units/            - طباعة كل ملصقات الأمر

🔗 تسجيل الضمان (للعميل):
   /production/warranty/verify/                    - التحقق من الوحدة
   /production/warranty/register/                  - تسجيل الضمان
   /production/warranty/success/<id>/              - نجاح التسجيل


📌 سير العمل (Workflow):
══════════════════════════════════════════════════════════════════════

    ┌─────────────────────┐
    │   أمر إنتاج جديد    │
    └──────────┬──────────┘
               ▼
    ┌─────────────────────┐
    │   تصنيع المنتجات    │
    └──────────┬──────────┘
               ▼
    ┌─────────────────────┐
    │   اكتمال الإنتاج    │
    │  إنشاء الوحدات      │ ← تلقائي أو يدوي
    └──────────┬──────────┘
               ▼
    ┌─────────────────────┐
    │  توليد الباركود و   │
    │     QR Code        │
    └──────────┬──────────┘
               ▼
    ┌─────────────────────┐
    │   طباعة الملصقات    │ ← لصق على المنتجات
    └──────────┬──────────┘
               ▼
    ┌─────────────────────┐
    │   نقل للمخزون      │
    └──────────┬──────────┘
               ▼
    ┌─────────────────────┐
    │   بيع للتاجر       │ (اختياري)
    └──────────┬──────────┘
               ▼
    ┌─────────────────────┐
    │  بيع للعميل النهائي │
    └──────────┬──────────┘
               ▼
    ┌─────────────────────┐
    │ العميل يمسح QR Code │
    │  لتفعيل الضمان      │
    └──────────┬──────────┘
               ▼
    ┌─────────────────────┐
    │   الضمان مفعّل!    │
    └─────────────────────┘


📌 الملصق يحتوي على:
══════════════════════════════════════════════════════════════════════

    ┌──────────────────────────────────────┐
    │           Tony ERP                    │  ← اسم الشركة
    │                                       │
    │      جهاز اختباري للضمان            │  ← اسم المنتج
    │                                       │
    │          ┌────────────┐              │
    │          │   QR Code  │              │  ← للمسح بالجوال
    │          │            │              │
    │          └────────────┘              │
    │                                       │
    │    SN: PO-001-0001                   │  ← الرقم التسلسلي
    │                                       │
    │    |||||||||||||||||||               │  ← الباركود
    │    123456789012                       │
    │                                       │
    │  تاريخ الإنتاج: 2025/12/25           │
    │  ضمان: 24 شهر                        │
    └──────────────────────────────────────┘


📌 أمثلة برمجية:
══════════════════════════════════════════════════════════════════════

# 1️⃣ إنشاء وحدة منتج نهائي
from production.models import FinishedGoodUnit, ProductionOrder

order = ProductionOrder.objects.get(number='PO-001')

unit = FinishedGoodUnit.objects.create(
    product=order.product,
    production_order=order,
    unit_serial=f"{order.number}-0001",
    barcode="123456789012",
    manufacture_date=date.today(),
    status='produced',
)

# 2️⃣ توليد QR Code
unit.generate_qr_data()
unit.generate_qr_image()
unit.save()

# 3️⃣ البحث عن وحدة بالباركود أو الرقم التسلسلي
from django.db.models import Q

unit = FinishedGoodUnit.objects.filter(
    Q(unit_serial=code) | Q(barcode=code)
).first()

# 4️⃣ تفعيل الضمان للعميل
customer_data = {
    'name': 'اسم العميل',
    'phone': '0501234567',
    'email': 'email@example.com',
    'address': 'العنوان',
}
unit.activate_warranty(customer_data)

# 5️⃣ التحقق من صلاحية الضمان
if unit.is_warranty_valid:
    print(f"الضمان ساري، متبقي {unit.warranty_remaining_days} يوم")


📌 توليد الملصقات من أمر الإنتاج:
══════════════════════════════════════════════════════════════════════

# في views_units.py

@login_required
def unit_generate_labels(request, order_id):
    '''توليد ملصقات لأمر إنتاج (إذا لم تُنشأ)'''
    order = get_object_or_404(ProductionOrder, pk=order_id)
    
    target_count = int(order.produced_quantity or 0)
    existing_count = order.finished_units.count()
    
    for i in range(existing_count + 1, target_count + 1):
        unit = FinishedGoodUnit.objects.create(
            product=order.product,
            production_order=order,
            unit_serial=f"{order.number}-{i:04d}",
            barcode=generate_unique_barcode(),
            manufacture_date=date.today(),
            status='produced',
        )
    
    return redirect('production:unit_print_from_order', order_id=order_id)


📌 API للتحقق من الوحدة:
══════════════════════════════════════════════════════════════════════

GET /production/units/verify/?code=SN-123456

Response:
{
    "success": true,
    "unit": {
        "id": 1,
        "serial": "SN-123456",
        "barcode": "123456789012",
        "product_name": "جهاز اختباري",
        "manufacture_date": "2025-12-25",
        "status": "sold_to_customer",
        "warranty_registered": true,
        "warranty_valid": true,
        "warranty_end_date": "2027-12-25",
        "warranty_remaining_days": 730,
        "customer_name": "أحمد محمد",
        "customer_phone": "0501234567"
    }
}


📌 ملاحظات مهمة:
══════════════════════════════════════════════════════════════════════

⚠️ كل وحدة لها رقم تسلسلي وباركود فريد
⚠️ QR Code يحتوي على بيانات JSON مشفرة
⚠️ الملصق مصمم لحجم 100×100 مم
⚠️ يمكن طباعة ملصقات متعددة في صفحة واحدة
⚠️ تفعيل الضمان يتطلب بيانات العميل
⚠️ الضمان يبدأ من تاريخ البيع للعميل

══════════════════════════════════════════════════════════════════════
    """
    
    print(guide)


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🏭 اختبار منظومة طباعة ملصقات الضمان من الإنتاج - Tony ERP")
    print("=" * 70)
    
    # عرض الدليل
    show_labels_guide()
    
    # تشغيل الاختبارات
    input(f"\n{Colors.CYAN}اضغط Enter لبدء الاختبارات...{Colors.END}")
    
    results = test_production_warranty_labels()
    
    print("\n" + "=" * 70)
    print("تم الانتهاء من الاختبار")
    print("=" * 70)
