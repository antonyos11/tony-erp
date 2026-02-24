# -*- coding: utf-8 -*-
"""
🧪 اختبار دورة الضمان الكاملة - من الإنتاج إلى تفعيل الضمان
============================================================
هذا السكريبت يختبر:
1. إنشاء سياسة ضمان 10 سنوات
2. إنشاء منتج تجريبي
3. إنشاء أمر إنتاج
4. توليد وحدات المنتجات مع الباركود و QR Code
5. تفعيل الضمان للعميل
6. طباعة الملصق
"""

import os
import sys
import django

# إعداد Django
sys.path.insert(0, r'H:\برمجة\الشامل\الشامل\الشامل\app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import json

# استيراد النماذج
from inventory.models import Product, Category, Location
from production.models import ProductionOrder, FinishedGoodUnit, BillOfMaterials
from ecommerce.models import ProductWarranty, WarrantyCard
from partners.models import Partner

def print_header(title):
    print("\n" + "="*70)
    print(f"🔷 {title}")
    print("="*70)

def print_success(msg):
    print(f"✅ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

def print_warning(msg):
    print(f"⚠️  {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def main():
    print("\n" + "🏭"*35)
    print("     اختبار دورة الضمان الكاملة - Tony ERP")
    print("🏭"*35)
    
    # ==========================================
    # الخطوة 1: إنشاء سياسة ضمان 10 سنوات
    # ==========================================
    print_header("الخطوة 1: إنشاء سياسة ضمان 10 سنوات")
    
    warranty_policy, created = ProductWarranty.objects.get_or_create(
        name="ضمان ذهبي 10 سنوات",
        defaults={
            'duration': 10,
            'duration_unit': 'years',
            'description': 'ضمان شامل لمدة 10 سنوات يغطي جميع عيوب الصناعة والتركيب',
            'terms_and_conditions': '''
            شروط الضمان:
            1. يغطي الضمان عيوب الصناعة والمواد الخام
            2. لا يشمل الضمان سوء الاستخدام أو الحوادث
            3. يجب تقديم فاتورة الشراء عند المطالبة
            4. الضمان ساري من تاريخ الشراء أو تاريخ التفعيل
            5. الصيانة مجانية خلال فترة الضمان
            ''',
            'coverage': 'يغطي جميع عيوب التصنيع والمواد الخام والتركيب',
            'exclusions': 'لا يشمل سوء الاستخدام، الحوادث، الكوارث الطبيعية',
            'is_active': True,
            'requires_registration': True,
        }
    )
    
    if created:
        print_success(f"تم إنشاء سياسة الضمان: {warranty_policy.name}")
    else:
        print_info(f"سياسة الضمان موجودة: {warranty_policy.name}")
    
    print_info(f"   📅 مدة الضمان: {warranty_policy.duration} {warranty_policy.get_duration_unit_display()}")
    
    # ==========================================
    # الخطوة 2: إنشاء تصنيف ومنتج تجريبي
    # ==========================================
    print_header("الخطوة 2: إنشاء منتج تجريبي")
    
    # إنشاء تصنيف
    category, _ = Category.objects.get_or_create(
        name="أجهزة منزلية",
        defaults={'description': 'أجهزة كهربائية منزلية'}
    )
    
    # إنشاء موقع/مخزن
    location, _ = Location.objects.get_or_create(
        code="WH-MAIN",
        defaults={
            'name': 'المخزن الرئيسي',
            'type': 'finished',
            'is_active': True
        }
    )
    
    # إنشاء المنتج
    product, created = Product.objects.get_or_create(
        sku="WASHER-PRO-2025",
        defaults={
            'name': "غسالة أوتوماتيك برو 2025",
            'description': "غسالة أوتوماتيك بسعة 10 كجم مع تقنية البخار",
            'category': category,
            'price': Decimal('15000.00'),
            'cost': Decimal('10000.00'),
        }
    )
    
    if created:
        print_success(f"تم إنشاء المنتج: {product.name}")
    else:
        print_info(f"المنتج موجود: {product.name}")
    
    print_info(f"   🏷️ SKU: {product.sku}")
    print_info(f"   💰 السعر: {product.price} ج.م")
    
    # ==========================================
    # الخطوة 3: إنشاء قائمة مواد (BOM) وأمر إنتاج
    # ==========================================
    print_header("الخطوة 3: إنشاء أمر إنتاج")
    
    # إنشاء BOM بسيط
    bom, bom_created = BillOfMaterials.objects.get_or_create(
        product=product,
        name=f"BOM - {product.name}",
        defaults={
            'is_active': True,
            'version': '1.0',
        }
    )
    
    if bom_created:
        print_success(f"تم إنشاء قائمة المواد: {bom.name}")
    
    # إنشاء أمر إنتاج
    order_number = f"PO-TEST-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    
    production_order = ProductionOrder.objects.create(
        number=order_number,
        product=product,
        bom=bom,
        planned_quantity=5,  # إنتاج 5 وحدات
        produced_quantity=5,
        planned_start_date=date.today(),
        planned_end_date=date.today() + timedelta(days=1),
        actual_start_date=date.today(),
        actual_end_date=date.today(),
        status='completed',
        notes='أمر إنتاج تجريبي لاختبار نظام الضمان',
    )
    
    print_success(f"تم إنشاء أمر الإنتاج: {production_order.number}")
    print_info(f"   📦 الكمية المطلوبة: {production_order.planned_quantity}")
    print_info(f"   ✅ الكمية المنتجة: {production_order.produced_quantity}")
    
    # ==========================================
    # الخطوة 4: توليد وحدات المنتجات مع الباركود و QR
    # ==========================================
    print_header("الخطوة 4: توليد وحدات المنتجات (الباركود و QR Code)")
    
    units_created = []
    
    for i in range(1, 6):  # إنشاء 5 وحدات
        unit_serial = f"{production_order.number}-{i:04d}"
        barcode = f"8800{production_order.id:06d}{i:04d}"
        
        # التحقق من عدم وجود الوحدة
        if FinishedGoodUnit.objects.filter(unit_serial=unit_serial).exists():
            print_warning(f"الوحدة موجودة بالفعل: {unit_serial}")
            continue
        
        unit = FinishedGoodUnit.objects.create(
            product=product,
            production_order=production_order,
            unit_serial=unit_serial,
            barcode=barcode,
            manufacture_date=date.today(),
            warranty_policy=warranty_policy,
            status='produced',
            size_text='60x85x55 سم',
            notes=f'وحدة تجريبية رقم {i}',
        )
        
        # توليد QR Code
        unit.generate_qr_data()
        try:
            unit.generate_qr_image()
        except Exception as e:
            print_warning(f"   تعذر توليد صورة QR: {e}")
        unit.save()
        
        units_created.append(unit)
        print_success(f"تم إنشاء الوحدة: {unit.unit_serial}")
        print_info(f"   🔢 الباركود: {unit.barcode}")
        print_info(f"   📱 بيانات QR: {unit.qr_code_data[:50]}...")
    
    if not units_created:
        # استخدام وحدة موجودة
        unit = FinishedGoodUnit.objects.filter(production_order=production_order).first()
        if unit:
            units_created = [unit]
    
    # ==========================================
    # الخطوة 5: محاكاة بيع الوحدة وتفعيل الضمان
    # ==========================================
    print_header("الخطوة 5: تفعيل الضمان للعميل")
    
    if units_created:
        test_unit = units_created[0]
        
        # بيانات العميل التجريبي
        customer_data = {
            'name': 'أحمد محمد علي',
            'phone': '01012345678',
            'email': 'ahmed@example.com',
            'address': '123 شارع التحرير، القاهرة',
            'national_id': '29001011234567',
        }
        
        # تفعيل الضمان
        test_unit.activate_warranty(customer_data)
        
        print_success(f"تم تفعيل الضمان للوحدة: {test_unit.unit_serial}")
        print_info(f"   👤 العميل: {test_unit.customer_name}")
        print_info(f"   📞 الهاتف: {test_unit.customer_phone}")
        print_info(f"   📅 بداية الضمان: {test_unit.warranty_start_date}")
        print_info(f"   📅 نهاية الضمان: {test_unit.warranty_end_date}")
        print_info(f"   ⏰ المتبقي: {test_unit.warranty_remaining_days} يوم")
        print_info(f"   ✅ الضمان ساري: {'نعم' if test_unit.is_warranty_valid else 'لا'}")
    
    # ==========================================
    # الخطوة 6: عرض روابط الطباعة والتحقق
    # ==========================================
    print_header("الخطوة 6: روابط النظام")
    
    base_url = "http://127.0.0.1:8000"
    
    print("\n📋 روابط الإدارة:")
    print(f"   • قائمة الوحدات: {base_url}/production/units/")
    print(f"   • أمر الإنتاج: {base_url}/production/orders/{production_order.id}/")
    
    if units_created:
        test_unit = units_created[0]
        print(f"\n🏷️ روابط الطباعة:")
        print(f"   • طباعة ملصق واحد: {base_url}/production/units/{test_unit.id}/print/")
        print(f"   • طباعة كل الوحدات: {base_url}/production/orders/{production_order.id}/print-units/")
        
        print(f"\n🔍 روابط التحقق من الضمان:")
        print(f"   • التحقق بالسيج.م: {base_url}/production/warranty/verify/?code={test_unit.unit_serial}")
        print(f"   • التحقق بالباركود: {base_url}/production/warranty/verify/?code={test_unit.barcode}")
        print(f"   • صفحة الضمان (المتجر): {base_url}/store/warranty/check/")
    
    # ==========================================
    # ملخص النتائج
    # ==========================================
    print_header("📊 ملخص الاختبار")
    
    print(f"""
    ┌─────────────────────────────────────────────────────────────┐
    │                    نتائج الاختبار                           │
    ├─────────────────────────────────────────────────────────────┤
    │  ✅ سياسة الضمان: {warranty_policy.name:<35} │
    │  ✅ المنتج: {product.name:<43} │
    │  ✅ أمر الإنتاج: {production_order.number:<37} │
    │  ✅ عدد الوحدات: {len(units_created):<43} │
    │  ✅ مدة الضمان: {warranty_policy.duration} {warranty_policy.get_duration_unit_display():<40} │
    └─────────────────────────────────────────────────────────────┘
    """)
    
    if units_created:
        print("\n📦 الوحدات المنشأة:")
        print("─" * 70)
        print(f"{'الرقم التسلسلي':<25} {'الباركود':<20} {'الحالة':<15}")
        print("─" * 70)
        for unit in units_created:
            status = "✅ ضمان مفعّل" if unit.warranty_registered else "⏳ في المخزن"
            print(f"{unit.unit_serial:<25} {unit.barcode:<20} {status:<15}")
        print("─" * 70)
    
    print("\n" + "🎉"*35)
    print("      تم اكتمال الاختبار بنجاح!")
    print("🎉"*35)
    
    print("""
    
    📌 الخطوات التالية:
    ─────────────────────
    1. افتح رابط طباعة الملصق في المتصفح
    2. اضغط Ctrl+P للطباعة
    3. اختر الطابعة الموصلة
    4. تأكد من إعدادات حجم الملصق
    5. اطبع الملصق وألصقه على المنتج
    
    🔗 للتحقق من الضمان:
    ─────────────────────
    1. امسح QR Code بالجوال
    2. أو أدخل الرقم التسلسلي في صفحة التحقق
    
    """)
    
    return {
        'warranty_policy': warranty_policy,
        'product': product,
        'production_order': production_order,
        'units': units_created,
    }

if __name__ == '__main__':
    result = main()
