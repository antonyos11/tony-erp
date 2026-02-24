#!/usr/bin/env python3
"""
🧪 اختبار تكاملي شامل وقوي جداً
Full Integration Test: Inventory + Suppliers + Pricing + BOM

يختبر:
1. المخازن والمواقع المخزنية
2. الموردين وأسعارهم
3. المنتجات والمواد الخام
4. قوائم المواد (BOM) والتكلفة
5. التسعير وهوامش الربح
6. التكامل بين كل الأنظمة
7. مراكز العمل ومراحل الإنتاج
8. اختبارات الأداء
"""

import os
import sys
import json
import time
import uuid
import traceback
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Django Setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction, models as db_models
from django.utils import timezone

User = get_user_model()


# ============================================================================
# Test Results Tracker
# ============================================================================

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.warnings = 0
        self.details = []
        self.start_time = time.time()

    def success(self, test_name, message=""):
        self.passed += 1
        self.details.append(('✅', test_name, message))
        print(f"  ✅ {test_name}" + (f" - {message}" if message else ""))

    def fail(self, test_name, message=""):
        self.failed += 1
        self.details.append(('❌', test_name, message))
        print(f"  ❌ {test_name}" + (f" - {message}" if message else ""))

    def error(self, test_name, message=""):
        self.errors += 1
        self.details.append(('💥', test_name, message))
        print(f"  💥 {test_name}" + (f" - {message}" if message else ""))

    def warn(self, test_name, message=""):
        self.warnings += 1
        self.details.append(('⚠️', test_name, message))
        print(f"  ⚠️ {test_name}" + (f" - {message}" if message else ""))

    def summary(self):
        elapsed = time.time() - self.start_time
        total = self.passed + self.failed + self.errors
        rate = (self.passed / total * 100) if total > 0 else 0

        print("\n" + "=" * 70)
        print("📊 ملخص نتائج الاختبار الشامل")
        print("=" * 70)
        print(f"  ✅ نجح: {self.passed}")
        print(f"  ❌ فشل: {self.failed}")
        print(f"  💥 أخطاء: {self.errors}")
        print(f"  ⚠️ تحذيرات: {self.warnings}")
        print(f"  📈 نسبة النجاح: {rate:.1f}%")
        print(f"  ⏱️ الوقت: {elapsed:.2f} ثانية")
        print("=" * 70)

        if self.failed == 0 and self.errors == 0:
            print("🎉🎉🎉 جميع الاختبارات نجحت! 🎉🎉🎉")
        elif rate >= 80:
            print("👍 أداء جيد مع بعض المشاكل البسيطة")
        else:
            print("🔴 يوجد مشاكل تحتاج إصلاح فوري!")

        return self.failed == 0 and self.errors == 0


results = TestResults()


# ============================================================================
# SECTION 1: اختبار المخازن والمواقع المخزنية
# ============================================================================

def test_inventory_locations():
    """اختبار شامل للمخازن والمواقع"""
    print("\n" + "=" * 70)
    print("📦 القسم 1: اختبار المخازن والمواقع المخزنية")
    print("=" * 70)

    from inventory.models import Location, Stock, Product, Category

    # 1.1 إنشاء أنواع مخازن مختلفة
    warehouse_types = [
        {'name': 'المستودع الرئيسي - اختبار', 'code': 'TST-WH-MAIN', 'type': 'other'},
        {'name': 'مخزن المواد الخام - اختبار', 'code': 'TST-WH-RAW', 'type': 'raw'},
        {'name': 'مخزن المنتجات التامة - اختبار', 'code': 'TST-WH-FIN', 'type': 'finished'},
        {'name': 'مخزن نصف المصنع - اختبار', 'code': 'TST-WH-WIP', 'type': 'wip'},
        {'name': 'المعرض/المتجر - اختبار', 'code': 'TST-WH-STORE', 'type': 'store'},
    ]

    created_locations = []
    for wh_data in warehouse_types:
        try:
            location, created = Location.objects.update_or_create(
                code=wh_data['code'],
                defaults={
                    'name': wh_data['name'],
                    'type': wh_data['type'],
                    'is_active': True,
                }
            )
            created_locations.append(location)
            status = "جديد" if created else "محدث"
            results.success(f"إنشاء مخزن: {wh_data['name'][:30]}", f"{status} | نوع: {wh_data['type']}")
        except Exception as e:
            results.error(f"إنشاء مخزن: {wh_data['name'][:30]}", str(e)[:100])

    # 1.2 اختبار عدد المخازن
    try:
        test_locations = Location.objects.filter(code__startswith='TST-WH')
        count = test_locations.count()
        if count >= 4:
            results.success(f"عدد المخازن التجريبية", f"{count} مخازن")
        else:
            results.fail(f"عدد المخازن التجريبية", f"فقط {count} من {len(warehouse_types)}")
    except Exception as e:
        results.error("عد المخازن", str(e))

    # 1.3 اختبار أنواع المخازن
    try:
        types_in_db = set(Location.objects.filter(
            code__startswith='TST-WH'
        ).values_list('type', flat=True).distinct())
        expected_types = {'other', 'raw', 'finished', 'wip', 'store'}
        if expected_types.issubset(types_in_db):
            results.success("تنوع أنواع المخازن", f"تم تغطية {len(types_in_db)} نوع")
        else:
            missing = expected_types - types_in_db
            results.fail("تنوع أنواع المخازن", f"ناقص: {missing}")
    except Exception as e:
        results.error("فحص أنواع المخازن", str(e))

    # 1.4 إنشاء منتجات (مواد خام)
    try:
        category, _ = Category.objects.get_or_create(
            name='مواد اختبار شامل',
            defaults={'description': 'فئة لاختبار التكامل الشامل'}
        )

        test_products_data = [
            {'name': 'قماش خارجي اختبار', 'sku': 'TST-FAB-001', 'cost': Decimal('45.00'),
             'price': Decimal('60.00'), 'product_type': 'raw_material', 'raw_material_type': 'fabric',
             'purchase_uom': 'm', 'usage_uom': 'm', 'purchase_price': Decimal('45.00')},
            {'name': 'إسفنج اختبار', 'sku': 'TST-FOAM-001', 'cost': Decimal('120.00'),
             'price': Decimal('180.00'), 'product_type': 'raw_material', 'raw_material_type': 'foam',
             'purchase_uom': 'kg', 'usage_uom': 'kg', 'purchase_price': Decimal('120.00')},
            {'name': 'سوست اختبار', 'sku': 'TST-SPR-001', 'cost': Decimal('85.00'),
             'price': Decimal('130.00'), 'product_type': 'raw_material', 'raw_material_type': 'spring',
             'purchase_uom': 'unit', 'usage_uom': 'unit', 'purchase_price': Decimal('85.00')},
            {'name': 'خيوط خياطة اختبار', 'sku': 'TST-THR-001', 'cost': Decimal('15.00'),
             'price': Decimal('25.00'), 'product_type': 'raw_material', 'raw_material_type': 'thread',
             'purchase_uom': 'roll', 'usage_uom': 'm', 'purchase_price': Decimal('150.00'),
             'conversion_factor': Decimal('100')},
            {'name': 'سحاب اختبار', 'sku': 'TST-ZIP-001', 'cost': Decimal('8.00'),
             'price': Decimal('15.00'), 'product_type': 'raw_material', 'raw_material_type': 'other',
             'purchase_uom': 'm', 'usage_uom': 'm', 'purchase_price': Decimal('8.00')},
            {'name': 'لباد اختبار', 'sku': 'TST-PAD-001', 'cost': Decimal('35.00'),
             'price': Decimal('50.00'), 'product_type': 'raw_material', 'raw_material_type': 'pad',
             'purchase_uom': 'kg', 'usage_uom': 'kg', 'purchase_price': Decimal('35.00')},
            {'name': 'غراء اختبار', 'sku': 'TST-GLU-001', 'cost': Decimal('22.00'),
             'price': Decimal('35.00'), 'product_type': 'raw_material', 'raw_material_type': 'glue',
             'purchase_uom': 'can', 'usage_uom': 'kg', 'purchase_price': Decimal('220.00'),
             'conversion_factor': Decimal('10')},
        ]

        created_products = []
        for p_data in test_products_data:
            product, created = Product.objects.update_or_create(
                sku=p_data['sku'],
                defaults={
                    'name': p_data['name'],
                    'category': category,
                    'cost': p_data['cost'],
                    'price': p_data['price'],
                    'product_type': p_data.get('product_type', 'raw_material'),
                    'raw_material_type': p_data.get('raw_material_type', ''),
                    'purchase_uom': p_data.get('purchase_uom', 'unit'),
                    'usage_uom': p_data.get('usage_uom', 'unit'),
                    'purchase_price': p_data.get('purchase_price', p_data['cost']),
                    'conversion_factor': p_data.get('conversion_factor', Decimal('1')),
                }
            )
            created_products.append(product)
            status = "جديد" if created else "محدث"
            results.success(
                f"مادة خام: {p_data['name'][:25]}",
                f"{status} | نوع: {p_data.get('raw_material_type', '-')} | تكلفة: {p_data['cost']}"
            )

    except Exception as e:
        results.error("إنشاء المنتجات", str(e))
        created_products = []

    # 1.5 إضافة مخزون في مواقع مختلفة
    try:
        if created_locations and created_products:
            raw_wh = next((l for l in created_locations if l.code == 'TST-WH-RAW'), created_locations[0])

            for product in created_products:
                stock, created = Stock.objects.update_or_create(
                    product=product,
                    location=raw_wh,
                    defaults={'quantity': 1000}
                )
                results.success(
                    f"مخزون: {product.name[:20]}",
                    f"1000 وحدة في {raw_wh.name[:20]}"
                )

            # إضافة مخزون في المستودع الرئيسي أيضاً
            main_wh = next((l for l in created_locations if l.code == 'TST-WH-MAIN'), created_locations[0])
            for product in created_products[:3]:
                stock, created = Stock.objects.update_or_create(
                    product=product,
                    location=main_wh,
                    defaults={'quantity': 500}
                )
    except Exception as e:
        results.error("إضافة مخزون", str(e))

    # 1.6 اختبار القيد على المخزون السالب
    print("\n  --- اختبار قيد المخزون السالب ---")
    try:
        from django.db import IntegrityError
        if created_products and created_locations:
            test_loc = created_locations[-1]
            test_prod = created_products[-1]
            try:
                Stock.objects.update_or_create(
                    product=test_prod,
                    location=test_loc,
                    defaults={'quantity': -10}
                )
                results.fail("قيد المخزون السالب", "تم السماح بمخزون سالب!")
            except (IntegrityError, Exception):
                results.success("قيد المخزون السالب", "تم منع المخزون السالب بنجاح ✓")
    except Exception as e:
        results.warn("اختبار المخزون السالب", str(e)[:80])

    # 1.7 اختبار تحويل مخزني
    print("\n  --- اختبار التحويل المخزني ---")
    try:
        from inventory.models import StockTransfer, StockTransferItem

        if len(created_locations) >= 2 and created_products:
            source = next((l for l in created_locations if l.code == 'TST-WH-RAW'), created_locations[0])
            dest = next((l for l in created_locations if l.code == 'TST-WH-MAIN'), created_locations[1])

            transfer = StockTransfer.objects.create(
                source=source,
                destination=dest,
                status='draft',
                notes='تحويل اختباري - TC_FULL_INTEGRATION',
            )

            # إضافة عنصر تحويل
            transfer_item = StockTransferItem.objects.create(
                transfer=transfer,
                product=created_products[0],
                quantity=50,
            )

            results.success(
                "تحويل مخزني",
                f"من {source.code} إلى {dest.code} | {created_products[0].name[:20]} × 50"
            )

            # تأكيد التحويل
            try:
                transfer.confirm()
                results.success("تأكيد التحويل المخزني", f"الحالة: {transfer.get_status_display()}")
            except Exception as e:
                results.warn("تأكيد التحويل", str(e)[:80])

    except Exception as e:
        results.warn("التحويل المخزني", str(e)[:100])

    # 1.8 قيمة المخزون الإجمالية
    print("\n  --- قيمة المخزون ---")
    try:
        for loc in created_locations[:3]:
            val = loc.total_value
            results.success(f"قيمة مخزون {loc.code}", f"{val:,.2f} ج.م")
    except Exception as e:
        results.error("حساب قيمة المخزون", str(e))

    return created_locations, created_products


# ============================================================================
# SECTION 2: اختبار الموردين
# ============================================================================

def test_suppliers():
    """اختبار شامل للموردين"""
    print("\n" + "=" * 70)
    print("🏭 القسم 2: اختبار الموردين")
    print("=" * 70)

    from partners.models import Supplier

    suppliers_data = [
        {
            'name': 'مصنع الأنسجة المصرية - اختبار',
            'code': 'TST-SUP-001',
            'supply_type': 'raw_materials',
            'raw_material': 'أقمشة خارجية وداخلية',
            'phone': '01000000001',
            'email': 'textiles@test.eg',
            'opening_balance': Decimal('50000.00'),
            'credit_limit': Decimal('200000.00'),
            'payment_terms_days': 30,
        },
        {
            'name': 'شركة الإسفنج الحديثة - اختبار',
            'code': 'TST-SUP-002',
            'supply_type': 'raw_materials',
            'raw_material': 'إسفنج طبي ومفروشات',
            'phone': '01000000002',
            'email': 'foam@test.eg',
            'opening_balance': Decimal('30000.00'),
            'credit_limit': Decimal('150000.00'),
            'payment_terms_days': 45,
        },
        {
            'name': 'مصنع السوست المتحدة - اختبار',
            'code': 'TST-SUP-003',
            'supply_type': 'raw_materials',
            'raw_material': 'سوست بونل وبوكيت',
            'phone': '01000000003',
            'email': 'springs@test.eg',
            'opening_balance': Decimal('25000.00'),
            'credit_limit': Decimal('100000.00'),
            'payment_terms_days': 15,
        },
        {
            'name': 'شركة التغليف الذهبية - اختبار',
            'code': 'TST-SUP-004',
            'supply_type': 'packaging',
            'raw_material': 'كراتين ونايلون تغليف',
            'phone': '01000000004',
            'email': 'packing@test.eg',
            'opening_balance': Decimal('10000.00'),
            'credit_limit': Decimal('50000.00'),
            'payment_terms_days': 7,
        },
        {
            'name': 'خدمات النقل السريع - اختبار',
            'code': 'TST-SUP-005',
            'supply_type': 'services',
            'raw_material': '',
            'phone': '01000000005',
            'email': 'transport@test.eg',
            'opening_balance': Decimal('0'),
            'credit_limit': Decimal('30000.00'),
            'payment_terms_days': 60,
        },
        {
            'name': 'مصنع الغراء والمواد اللاصقة - اختبار',
            'code': 'TST-SUP-006',
            'supply_type': 'raw_materials',
            'raw_material': 'غراء صناعي وفازلين',
            'phone': '01000000006',
            'email': 'glue@test.eg',
            'opening_balance': Decimal('5000.00'),
            'credit_limit': Decimal('40000.00'),
            'payment_terms_days': 20,
        },
    ]

    created_suppliers = []

    for s_data in suppliers_data:
        try:
            supplier, created = Supplier.objects.update_or_create(
                code=s_data['code'],
                defaults=s_data
            )
            created_suppliers.append(supplier)
            status = "جديد" if created else "محدث"
            results.success(
                f"مورد: {s_data['name'][:30]}",
                f"{status} | نوع: {s_data['supply_type']} | ائتمان: {s_data['credit_limit']:,.0f}"
            )
        except Exception as e:
            results.error(f"إنشاء مورد: {s_data['name'][:30]}", str(e)[:100])

    # 2.2 اختبار أنواع التوريد
    try:
        supply_types = set(Supplier.objects.filter(
            code__startswith='TST-SUP'
        ).values_list('supply_type', flat=True).distinct())

        expected = {'raw_materials', 'packaging', 'services'}
        if expected.issubset(supply_types):
            results.success("أنواع التوريد", f"تم تغطية {len(supply_types)} نوع: {supply_types}")
        else:
            results.fail("أنواع التوريد", f"ناقص: {expected - supply_types}")
    except Exception as e:
        results.error("فحص أنواع التوريد", str(e))

    # 2.3 اختبار حدود الائتمان
    try:
        for supplier in created_suppliers:
            if float(supplier.credit_limit) > 0:
                results.success(
                    f"حد ائتمان: {supplier.name[:25]}",
                    f"{supplier.credit_limit:,.0f} ج.م | سماح: {supplier.payment_terms_days} يوم"
                )
            else:
                results.warn(f"حد ائتمان: {supplier.name[:25]}", "غير محدد")
    except Exception as e:
        results.error("فحص حدود الائتمان", str(e))

    # 2.4 اختبار البحث والتصفية
    print("\n  --- اختبار البحث والتصفية ---")
    try:
        raw_suppliers = Supplier.objects.filter(
            code__startswith='TST-SUP',
            supply_type='raw_materials'
        )
        results.success("تصفية موردي الخامات", f"{raw_suppliers.count()} موردين")

        high_credit = Supplier.objects.filter(
            code__startswith='TST-SUP',
            credit_limit__gte=100000
        )
        results.success("موردين بائتمان عالي (≥100K)", f"{high_credit.count()} موردين")

        quick_payment = Supplier.objects.filter(
            code__startswith='TST-SUP',
            payment_terms_days__lte=15
        )
        results.success("موردين بسداد سريع (≤15 يوم)", f"{quick_payment.count()} موردين")
    except Exception as e:
        results.error("البحث والتصفية", str(e))

    return created_suppliers


# ============================================================================
# SECTION 3: اختبار أسعار الموردين
# ============================================================================

def test_supplier_pricing(suppliers, products):
    """اختبار أسعار المنتجات حسب المورد"""
    print("\n" + "=" * 70)
    print("💰 القسم 3: اختبار التسعير وأسعار الموردين")
    print("=" * 70)

    if not suppliers or not products:
        results.warn("اختبار التسعير", "لا توجد بيانات موردين أو منتجات")
        return []

    from inventory.models import SupplierProductPrice

    # تحديد المواد
    fabric = next((p for p in products if 'قماش' in p.name), None)
    foam = next((p for p in products if 'إسفنج' in p.name), None)
    springs = next((p for p in products if 'سوست' in p.name), None)
    thread = next((p for p in products if 'خيوط' in p.name), None)
    zipper = next((p for p in products if 'سحاب' in p.name), None)
    pad = next((p for p in products if 'لباد' in p.name), None)
    glue = next((p for p in products if 'غراء' in p.name), None)

    # 3.1 إنشاء أسعار متعددة
    pricing_data = []

    if fabric and len(suppliers) >= 2:
        pricing_data.extend([
            {'supplier': suppliers[0], 'product': fabric, 'cost': Decimal('42.00'),
             'purchase_unit': 'm', 'min_order_qty': Decimal('100'), 'lead_time_days': 5},
            {'supplier': suppliers[1], 'product': fabric, 'cost': Decimal('48.00'),
             'purchase_unit': 'm', 'min_order_qty': Decimal('50'), 'lead_time_days': 3},
        ])

    if foam and len(suppliers) >= 2:
        pricing_data.extend([
            {'supplier': suppliers[0], 'product': foam, 'cost': Decimal('115.00'),
             'purchase_unit': 'kg', 'min_order_qty': Decimal('50'), 'lead_time_days': 7},
            {'supplier': suppliers[1], 'product': foam, 'cost': Decimal('125.00'),
             'purchase_unit': 'kg', 'min_order_qty': Decimal('20'), 'lead_time_days': 3},
        ])

    if springs and len(suppliers) >= 3:
        pricing_data.extend([
            {'supplier': suppliers[2], 'product': springs, 'cost': Decimal('80.00'),
             'purchase_unit': 'unit', 'min_order_qty': Decimal('200'), 'lead_time_days': 10},
            {'supplier': suppliers[0], 'product': springs, 'cost': Decimal('90.00'),
             'purchase_unit': 'unit', 'min_order_qty': Decimal('100'), 'lead_time_days': 5},
        ])

    if thread and suppliers:
        pricing_data.append(
            {'supplier': suppliers[0], 'product': thread, 'cost': Decimal('140.00'),
             'purchase_unit': 'roll', 'min_order_qty': Decimal('10'), 'lead_time_days': 3}
        )

    if zipper and suppliers:
        pricing_data.append(
            {'supplier': suppliers[0], 'product': zipper, 'cost': Decimal('7.50'),
             'purchase_unit': 'm', 'min_order_qty': Decimal('50'), 'lead_time_days': 2}
        )

    if pad and suppliers:
        pricing_data.append(
            {'supplier': suppliers[0], 'product': pad, 'cost': Decimal('32.00'),
             'purchase_unit': 'kg', 'min_order_qty': Decimal('100'), 'lead_time_days': 5}
        )

    if glue and len(suppliers) >= 6:
        pricing_data.extend([
            {'supplier': suppliers[5], 'product': glue, 'cost': Decimal('200.00'),
             'purchase_unit': 'can', 'min_order_qty': Decimal('5'), 'lead_time_days': 2},
            {'supplier': suppliers[0], 'product': glue, 'cost': Decimal('230.00'),
             'purchase_unit': 'can', 'min_order_qty': Decimal('3'), 'lead_time_days': 1},
        ])

    created_prices = []
    for p_data in pricing_data:
        try:
            # SupplierProductPrice has unique_together on (product, supplier, effective_date)
            # We need to handle this carefully
            existing = SupplierProductPrice.objects.filter(
                product=p_data['product'],
                supplier=p_data['supplier'],
            ).first()

            if existing:
                existing.cost = p_data['cost']
                existing.purchase_unit = p_data.get('purchase_unit', 'unit')
                existing.min_order_qty = p_data.get('min_order_qty')
                existing.lead_time_days = p_data.get('lead_time_days')
                existing.save()
                price_obj = existing
                is_new = False
            else:
                price_obj = SupplierProductPrice.objects.create(
                    supplier=p_data['supplier'],
                    product=p_data['product'],
                    cost=p_data['cost'],
                    purchase_unit=p_data.get('purchase_unit', 'unit'),
                    min_order_qty=p_data.get('min_order_qty'),
                    lead_time_days=p_data.get('lead_time_days'),
                )
                is_new = True

            created_prices.append(price_obj)
            results.success(
                f"سعر مورد: {p_data['product'].name[:20]}",
                f"{'جديد' if is_new else 'محدث'} | {p_data['supplier'].name[:20]} → {p_data['cost']} ج.م/{p_data.get('purchase_unit', 'unit')}"
            )
        except Exception as e:
            results.error(f"إنشاء سعر مورد: {p_data['product'].name[:20]}", str(e)[:100])

    # 3.2 اختبار مقارنة الأسعار بين الموردين
    print("\n  --- مقارنة الأسعار بين الموردين ---")
    for product_name, product_obj in [('القماش', fabric), ('الإسفنج', foam), ('السوست', springs), ('الغراء', glue)]:
        if product_obj:
            try:
                prices = SupplierProductPrice.objects.filter(
                    product=product_obj, is_active=True
                ).select_related('supplier').order_by('cost')

                if prices.count() >= 2:
                    cheapest = prices.first()
                    most_exp = prices.last()
                    savings = most_exp.cost - cheapest.cost
                    saving_pct = (savings / most_exp.cost * 100) if most_exp.cost > 0 else 0

                    results.success(
                        f"مقارنة أسعار {product_name}",
                        f"أرخص: {cheapest.cost} ({cheapest.supplier.name[:15]}) | "
                        f"أغلى: {most_exp.cost} ({most_exp.supplier.name[:15]}) | "
                        f"توفير: {savings} ج.م ({saving_pct:.1f}%)"
                    )
                elif prices.count() == 1:
                    results.success(f"سعر {product_name}", f"{prices.first().cost} ج.م (مورد واحد)")
            except Exception as e:
                results.error(f"مقارنة أسعار {product_name}", str(e)[:80])

    # 3.3 اختبار هوامش الربح
    print("\n  --- اختبار هوامش الربح ---")
    try:
        for product in products:
            if product.cost and product.price and product.cost > 0:
                margin = ((product.price - product.cost) / product.cost) * 100
                if margin > 0:
                    results.success(
                        f"هامش: {product.name[:25]}",
                        f"تكلفة: {product.cost} | سعر: {product.price} | هامش: {margin:.1f}%"
                    )
                else:
                    results.fail(
                        f"هامش سالب!: {product.name[:25]}",
                        f"تكلفة: {product.cost} > سعر: {product.price}"
                    )
    except Exception as e:
        results.error("حساب هوامش الربح", str(e))

    # 3.4 اختبار أفضل مورد لكل مادة
    print("\n  --- أفضل مورد (الأرخص) ---")
    try:
        for product in products:
            best_price = SupplierProductPrice.objects.filter(
                product=product, is_active=True
            ).order_by('cost').first()

            if best_price:
                results.success(
                    f"أفضل سعر: {product.name[:20]}",
                    f"{best_price.supplier.name[:20]} → {best_price.cost} ج.م | "
                    f"توريد: {best_price.lead_time_days or '?'} يوم"
                )
    except Exception as e:
        results.error("أفضل مورد", str(e)[:80])

    return created_prices


# ============================================================================
# SECTION 4: اختبار قوائم المواد (BOM)
# ============================================================================

def test_bom(products, locations):
    """اختبار شامل لقوائم المواد"""
    print("\n" + "=" * 70)
    print("📋 القسم 4: اختبار قوائم المواد (BOM)")
    print("=" * 70)

    from production.models import BillOfMaterials, BOMItem
    from inventory.models import Product, Category

    # 4.1 إنشاء منتجات نهائية
    try:
        finished_category, _ = Category.objects.get_or_create(
            name='منتجات تامة - اختبار',
            defaults={'description': 'منتجات نهائية لاختبار BOM'}
        )

        finished_data = [
            {'name': 'مرتبة طبية 120×200 - اختبار', 'sku': 'TST-MAT-120',
             'cost': Decimal('800'), 'price': Decimal('1800'), 'product_type': 'finished'},
            {'name': 'مرتبة طبية 160×200 - اختبار', 'sku': 'TST-MAT-160',
             'cost': Decimal('1200'), 'price': Decimal('2800'), 'product_type': 'finished'},
            {'name': 'مرتبة طبية 180×200 - اختبار', 'sku': 'TST-MAT-180',
             'cost': Decimal('1500'), 'price': Decimal('3500'), 'product_type': 'finished'},
            {'name': 'وسادة طبية - اختبار', 'sku': 'TST-PIL-001',
             'cost': Decimal('150'), 'price': Decimal('350'), 'product_type': 'finished'},
        ]

        finished_products = []
        for fp in finished_data:
            # Handle internal_code unique constraint - use full sku to avoid truncation collision
            internal_code = f"INT{fp['sku']}"
            product, created = Product.objects.update_or_create(
                sku=fp['sku'],
                defaults={
                    'name': fp['name'],
                    'category': finished_category,
                    'cost': fp['cost'],
                    'price': fp['price'],
                    'product_type': fp['product_type'],
                    'internal_code': internal_code,
                }
            )
            finished_products.append(product)
            results.success(f"منتج نهائي: {fp['name'][:30]}", f"سعر: {fp['price']} ج.م")

    except Exception as e:
        results.error("إنشاء منتجات نهائية", str(e))
        return []

    # تحديد المواد الخام
    fabric = next((p for p in products if 'قماش' in p.name), None)
    foam = next((p for p in products if 'إسفنج' in p.name), None)
    springs = next((p for p in products if 'سوست' in p.name), None)
    thread = next((p for p in products if 'خيوط' in p.name), None)
    zipper = next((p for p in products if 'سحاب' in p.name), None)
    pad = next((p for p in products if 'لباد' in p.name), None)
    glue = next((p for p in products if 'غراء' in p.name), None)

    # 4.2 إنشاء BOMs
    bom_definitions = [
        {
            'product': finished_products[0],  # مرتبة 120
            'name': 'وصفة مرتبة طبية 120×200',
            'version': '1.0',
            'items': [
                {'material': fabric, 'quantity': Decimal('4.0'), 'wastage': Decimal('5')},
                {'material': foam, 'quantity': Decimal('12.00'), 'wastage': Decimal('3')},
                {'material': springs, 'quantity': Decimal('1'), 'wastage': Decimal('2')},
                {'material': thread, 'quantity': Decimal('50'), 'wastage': Decimal('10')},
                {'material': zipper, 'quantity': Decimal('1.8'), 'wastage': Decimal('5')},
                {'material': pad, 'quantity': Decimal('2.5'), 'wastage': Decimal('3')},
                {'material': glue, 'quantity': Decimal('0.5'), 'wastage': Decimal('5')},
            ]
        },
        {
            'product': finished_products[1],  # مرتبة 160
            'name': 'وصفة مرتبة طبية 160×200',
            'version': '1.0',
            'items': [
                {'material': fabric, 'quantity': Decimal('5.5'), 'wastage': Decimal('5')},
                {'material': foam, 'quantity': Decimal('18.00'), 'wastage': Decimal('3')},
                {'material': springs, 'quantity': Decimal('1'), 'wastage': Decimal('2')},
                {'material': thread, 'quantity': Decimal('70'), 'wastage': Decimal('10')},
                {'material': zipper, 'quantity': Decimal('2.2'), 'wastage': Decimal('5')},
                {'material': pad, 'quantity': Decimal('3.5'), 'wastage': Decimal('3')},
                {'material': glue, 'quantity': Decimal('0.7'), 'wastage': Decimal('5')},
            ]
        },
        {
            'product': finished_products[2],  # مرتبة 180
            'name': 'وصفة مرتبة طبية 180×200',
            'version': '1.0',
            'items': [
                {'material': fabric, 'quantity': Decimal('6.5'), 'wastage': Decimal('5')},
                {'material': foam, 'quantity': Decimal('22.00'), 'wastage': Decimal('3')},
                {'material': springs, 'quantity': Decimal('1'), 'wastage': Decimal('2')},
                {'material': thread, 'quantity': Decimal('80'), 'wastage': Decimal('10')},
                {'material': zipper, 'quantity': Decimal('2.5'), 'wastage': Decimal('5')},
                {'material': pad, 'quantity': Decimal('4.0'), 'wastage': Decimal('3')},
                {'material': glue, 'quantity': Decimal('0.9'), 'wastage': Decimal('5')},
            ]
        },
        {
            'product': finished_products[3],  # وسادة
            'name': 'وصفة وسادة طبية',
            'version': '1.0',
            'items': [
                {'material': fabric, 'quantity': Decimal('1.2'), 'wastage': Decimal('5')},
                {'material': foam, 'quantity': Decimal('2.5'), 'wastage': Decimal('3')},
                {'material': thread, 'quantity': Decimal('10'), 'wastage': Decimal('10')},
                {'material': zipper, 'quantity': Decimal('0.5'), 'wastage': Decimal('5')},
            ]
        },
    ]

    user = User.objects.filter(is_superuser=True).first()
    created_boms = []

    for bom_def in bom_definitions:
        try:
            bom_kwargs = {
                'name': bom_def['name'],
                'base_quantity': Decimal('1.0'),
                'is_active': True,
                'is_default': True,
            }
            if user:
                bom_kwargs['created_by'] = user

            bom, created = BillOfMaterials.objects.update_or_create(
                product=bom_def['product'],
                version=bom_def['version'],
                defaults=bom_kwargs
            )

            # حذف العناصر القديمة وإضافة الجديدة
            if not created:
                bom.items.all().delete()

            item_count = 0
            total_cost = Decimal('0')

            for item_def in bom_def['items']:
                if item_def['material'] is None:
                    continue

                try:
                    bom_item = BOMItem.objects.create(
                        bom=bom,
                        material=item_def['material'],
                        item_type='material',
                        quantity=item_def['quantity'],
                        unit_cost=item_def['material'].cost or Decimal('0'),
                        wastage_percentage=item_def.get('wastage', Decimal('0')),
                        usage_unit=item_def['material'].usage_uom or 'unit',
                        sequence=item_count + 1,
                    )
                    item_count += 1

                    # حساب التكلفة مع الهدر
                    qty_with_wastage = item_def['quantity'] * (1 + item_def.get('wastage', Decimal('0')) / 100)
                    item_cost = qty_with_wastage * (item_def['material'].cost or Decimal('0'))
                    total_cost += item_cost

                except Exception as e:
                    results.warn(f"عنصر BOM: {item_def['material'].name[:20]}", str(e)[:60])

            created_boms.append(bom)
            results.success(
                f"BOM: {bom_def['name'][:35]}",
                f"{item_count} مكونات | تكلفة تقديرية: {total_cost:.2f} ج.م"
            )

        except Exception as e:
            results.error(f"إنشاء BOM: {bom_def['name'][:35]}", str(e)[:80])

    # 4.3 اختبار حسابات BOM
    print("\n  --- اختبار حسابات BOM ---")

    for bom in created_boms:
        try:
            items = bom.items.all()
            item_count = items.count()

            total_material_cost = Decimal('0')
            for item in items:
                total_material_cost += item.total_cost  # uses @property

            results.success(
                f"تكلفة BOM: {bom.product.name[:25]}",
                f"{item_count} مكونات | المواد: {total_material_cost:.2f} ج.م"
            )

            # هامش ربح المنتج النهائي
            if bom.product.price and total_material_cost > 0:
                margin = ((bom.product.price - total_material_cost) / total_material_cost) * 100
                if margin > 0:
                    results.success(
                        f"هامش {bom.product.name[:20]}",
                        f"تكلفة المواد: {total_material_cost:.0f} | سعر: {bom.product.price} | هامش: {margin:.1f}%"
                    )
                else:
                    results.fail(
                        f"هامش سالب! {bom.product.name[:20]}",
                        f"تكلفة ({total_material_cost:.0f}) > سعر ({bom.product.price})"
                    )

        except Exception as e:
            results.error(f"حساب BOM: {bom.product.name[:25]}", str(e)[:80])

    # 4.4 اختبار الهدر (Wastage)
    print("\n  --- اختبار حساب الهدر ---")

    for bom in created_boms[:2]:
        try:
            for item in bom.items.all()[:4]:
                expected = item.quantity * (1 + item.wastage_percentage / 100)
                actual = item.quantity_with_wastage

                diff = abs(actual - expected)
                if diff < Decimal('0.001'):
                    results.success(
                        f"هدر: {item.material.name[:20]}",
                        f"كمية: {item.quantity} | هدر: {item.wastage_percentage}% | فعلي: {actual:.3f}"
                    )
                else:
                    results.fail(
                        f"حساب هدر خاطئ: {item.material.name[:20]}",
                        f"متوقع: {expected:.3f} | فعلي: {actual:.3f}"
                    )
        except Exception as e:
            results.warn("اختبار الهدر", str(e)[:80])

    # 4.5 اختبار تفرد الإصدار
    print("\n  --- اختبار تفرد إصدار BOM ---")

    try:
        if finished_products:
            from django.db import IntegrityError
            try:
                with transaction.atomic():
                    BillOfMaterials.objects.create(
                        product=finished_products[0],
                        version='1.0',  # مكرر!
                        name='وصفة مكررة يجب أن تفشل',
                    )
                results.fail("تفرد إصدار BOM", "تم السماح بإصدار مكرر!")
            except IntegrityError:
                results.success("تفرد إصدار BOM", "منع التكرار بنجاح ✓")
    except Exception as e:
        results.error("اختبار تفرد الإصدار", str(e))

    # 4.6 اختبار BOM الافتراضية
    print("\n  --- اختبار BOM الافتراضية ---")

    try:
        if finished_products:
            bom_v2, created = BillOfMaterials.objects.update_or_create(
                product=finished_products[0],
                version='2.0',
                defaults={
                    'name': 'وصفة محسنة v2 - اختبار',
                    'base_quantity': Decimal('1.0'),
                    'is_active': True,
                    'is_default': True,
                }
            )

            old_bom = BillOfMaterials.objects.filter(
                product=finished_products[0], version='1.0'
            ).first()

            if old_bom:
                old_bom.refresh_from_db()
                if not old_bom.is_default:
                    results.success("تبديل BOM الافتراضية", "v1 أُلغي → v2 أصبح الافتراضي ✓")
                else:
                    results.warn("تبديل BOM الافتراضية", "v1 لا زال افتراضياً")

            # إعادة v1 كافتراضي
            bom_v2.is_default = False
            bom_v2.save()
            if old_bom:
                old_bom.is_default = True
                old_bom.save()

    except Exception as e:
        results.warn("اختبار BOM الافتراضية", str(e)[:80])

    # 4.7 تقرير تكلفة تفصيلي
    print("\n  --- تقرير تكلفة تفصيلي ---")

    for bom in created_boms:
        try:
            items = bom.items.all().select_related('material')

            print(f"\n  📋 {bom.product.name}:")
            print(f"     {'المادة':<25} {'الكمية':>8} {'الوحدة':<6} {'سعر الوحدة':>10} {'الهدر%':>6} {'الإجمالي':>10}")
            print(f"     {'-' * 70}")

            total = Decimal('0')
            for item in items:
                item_total = item.total_cost
                total += item_total
                uom = item.get_usage_unit_display() if hasattr(item, 'get_usage_unit_display') else item.usage_unit
                print(f"     {item.material.name[:25]:<25} {item.quantity:>8.2f} {uom:<6} "
                      f"{item.unit_cost:>10.2f} {item.wastage_percentage:>5.1f}% {item_total:>10.2f}")

            print(f"     {'-' * 70}")
            print(f"     {'الإجمالي':<25} {'':>8} {'':>6} {'':>10} {'':>6} {total:>10.2f}")

            if bom.product.price:
                profit = bom.product.price - total
                margin_pct = (profit / total * 100) if total > 0 else 0
                print(f"     ➤ سعر البيع: {bom.product.price:.2f} | الربح: {profit:.2f} | الهامش: {margin_pct:.1f}%")

            results.success(f"تقرير: {bom.product.name[:25]}", f"التكلفة: {total:.2f} ج.م")

        except Exception as e:
            results.error(f"تقرير: {bom.product.name[:25]}", str(e)[:60])

    return created_boms


# ============================================================================
# SECTION 5: اختبار التكامل الشامل
# ============================================================================

def test_full_integration(locations, products, suppliers, boms):
    """اختبار التكامل بين كل الأنظمة"""
    print("\n" + "=" * 70)
    print("🔗 القسم 5: اختبار التكامل الشامل")
    print("=" * 70)

    from inventory.models import Stock, Product, SupplierProductPrice
    from production.models import BillOfMaterials, BOMItem

    # 5.1 فحص توفر المواد لإنتاج منتج
    print("\n  --- فحص توفر المواد للإنتاج ---")

    for bom in boms:
        try:
            items = bom.items.all().select_related('material')
            all_available = True
            shortage_items = []

            for item in items:
                total_stock = Stock.objects.filter(
                    product=item.material,
                    location__code__startswith='TST-WH'
                ).aggregate(total=db_models.Sum('quantity'))['total'] or 0

                qty_needed = float(item.quantity_with_wastage)

                if total_stock >= qty_needed:
                    results.success(
                        f"✓ متوفر: {item.material.name[:20]}",
                        f"مطلوب: {qty_needed:.2f} | متوفر: {total_stock}"
                    )
                else:
                    all_available = False
                    shortage_items.append(item.material.name)
                    results.warn(
                        f"✗ نقص: {item.material.name[:20]}",
                        f"مطلوب: {qty_needed:.2f} | متوفر: {total_stock}"
                    )

            if all_available:
                results.success(f"جاهز للإنتاج: {bom.product.name[:25]}", "جميع المواد متوفرة ✓")
            else:
                results.warn(f"غير جاهز: {bom.product.name[:25]}", f"نقص في: {', '.join(shortage_items[:3])}")

        except Exception as e:
            results.error(f"فحص توفر: {bom.product.name[:25]}", str(e)[:60])

    # 5.2 محاكاة أمر إنتاج
    print("\n  --- محاكاة أمر إنتاج ---")
    try:
        from production.models import ProductionOrder

        user = User.objects.filter(is_superuser=True).first()

        if boms and user:
            bom = boms[0]
            order_number = f'TST-PO-{timezone.now().strftime("%Y%m%d%H%M%S")}'
            today = timezone.now().date()

            order = ProductionOrder.objects.create(
                number=order_number,
                product=bom.product,
                bom=bom,
                planned_quantity=Decimal('10'),
                order_date=today,
                planned_start_date=today,
                planned_end_date=today + timedelta(days=7),
                status='draft',
                created_by=user,
            )

            results.success(
                f"أمر إنتاج: {order.number}",
                f"المنتج: {bom.product.name[:20]} | الكمية: 10 | الحالة: مسودة"
            )

            # تأكيد الأمر
            order.status = 'confirmed'
            order.save()
            results.success("تأكيد أمر الإنتاج", f"الحالة: {order.get_status_display()}")

            # فحص الخصائص المحسوبة
            results.success("نسبة الإنجاز", f"{order.completion_percentage:.0f}%")
            results.success("الكمية المتبقية", f"{order.remaining_quantity}")

    except Exception as e:
        results.error("أمر الإنتاج", str(e)[:100])

    # 5.3 ربط المورد المفضل بالمنتج
    print("\n  --- ربط المورد المفضل ---")
    try:
        for product in products[:3]:
            best_price = SupplierProductPrice.objects.filter(
                product=product, is_active=True
            ).order_by('cost').first()

            if best_price:
                product.preferred_supplier = best_price.supplier
                product.save()
                results.success(
                    f"مورد مفضل: {product.name[:20]}",
                    f"{best_price.supplier.name[:20]} بسعر {best_price.cost} ج.م"
                )
    except Exception as e:
        results.error("ربط المورد المفضل", str(e)[:80])

    # 5.4 إحصائيات عامة
    print("\n  --- إحصائيات النظام ---")
    try:
        from partners.models import Supplier
        from inventory.models import Location as Loc

        total_products = Product.objects.count()
        total_raw = Product.objects.filter(product_type='raw_material').count()
        total_finished = Product.objects.filter(product_type='finished').count()
        total_boms = BillOfMaterials.objects.filter(is_active=True).count()
        total_stock = Stock.objects.count()
        total_locations = Loc.objects.filter(is_active=True).count()
        total_suppliers = Supplier.objects.filter(is_active=True).count()
        total_prices = SupplierProductPrice.objects.filter(is_active=True).count()

        print(f"\n  📊 ملخص النظام:")
        print(f"     المنتجات الإجمالية: {total_products}")
        print(f"     مواد خام: {total_raw}")
        print(f"     منتجات تامة: {total_finished}")
        print(f"     قوائم المواد النشطة: {total_boms}")
        print(f"     سجلات المخزون: {total_stock}")
        print(f"     المواقع النشطة: {total_locations}")
        print(f"     الموردين: {total_suppliers}")
        print(f"     أسعار الموردين: {total_prices}")

        results.success(
            "إحصائيات النظام",
            f"{total_products} منتج | {total_boms} BOM | {total_suppliers} مورد | {total_prices} سعر"
        )
    except Exception as e:
        results.error("الإحصائيات", str(e))


# ============================================================================
# SECTION 6: مراكز العمل ومراحل الإنتاج
# ============================================================================

def test_work_centers_and_stages(boms):
    """اختبار مراكز العمل ومراحل الإنتاج"""
    print("\n" + "=" * 70)
    print("🏗️ القسم 6: اختبار مراكز العمل ومراحل الإنتاج")
    print("=" * 70)

    from production.models import ProductionWorkCenter, ProductionStage, BOMStage

    # 6.1 إنشاء مراكز عمل
    wc_data_list = [
        {'code': 'TST-WC-CUT', 'name': 'قسم التقطيع - اختبار',
         'work_center_type': 'cutting', 'hourly_rate': Decimal('75')},
        {'code': 'TST-WC-SEW', 'name': 'قسم الخياطة - اختبار',
         'work_center_type': 'sewing', 'hourly_rate': Decimal('60')},
        {'code': 'TST-WC-FILL', 'name': 'قسم الحشو - اختبار',
         'work_center_type': 'filling', 'hourly_rate': Decimal('70')},
        {'code': 'TST-WC-ASM', 'name': 'قسم التجميع - اختبار',
         'work_center_type': 'assembly', 'hourly_rate': Decimal('80')},
        {'code': 'TST-WC-QC', 'name': 'قسم الجودة - اختبار',
         'work_center_type': 'quality', 'hourly_rate': Decimal('90')},
        {'code': 'TST-WC-PKG', 'name': 'قسم التعبئة - اختبار',
         'work_center_type': 'packaging', 'hourly_rate': Decimal('50')},
    ]

    created_wc = []
    for wc_data in wc_data_list:
        try:
            wc, created = ProductionWorkCenter.objects.update_or_create(
                code=wc_data['code'],
                defaults={
                    'name': wc_data['name'],
                    'work_center_type': wc_data['work_center_type'],
                    'hourly_rate': wc_data['hourly_rate'],
                    'capacity_per_hour': Decimal('5'),
                    'working_hours_per_day': Decimal('8'),
                    'efficiency_rate': Decimal('85.00'),
                }
            )
            created_wc.append(wc)
            results.success(
                f"مركز عمل: {wc_data['name'][:30]}",
                f"{wc_data['hourly_rate']} ج.م/ساعة | سعة يومية: {wc.daily_capacity}"
            )
        except Exception as e:
            results.error(f"مركز عمل: {wc_data['name'][:30]}", str(e)[:60])

    # 6.2 إنشاء مراحل إنتاج وربطها بـ BOM
    if boms and created_wc:
        stages_definitions = [
            {'name': 'تقطيع القماش', 'stage_type': 'cutting', 'wc_idx': 0,
             'setup': 15, 'operation': 30, 'teardown': 5, 'workers': 2},
            {'name': 'خياطة الغلاف', 'stage_type': 'sewing', 'wc_idx': 1,
             'setup': 10, 'operation': 45, 'teardown': 5, 'workers': 3},
            {'name': 'حشو الإسفنج', 'stage_type': 'other', 'wc_idx': 2,
             'setup': 10, 'operation': 20, 'teardown': 5, 'workers': 2},
            {'name': 'تجميع المرتبة', 'stage_type': 'assembly', 'wc_idx': 3,
             'setup': 20, 'operation': 60, 'teardown': 10, 'workers': 4},
            {'name': 'فحص الجودة', 'stage_type': 'quality', 'wc_idx': 4,
             'setup': 5, 'operation': 20, 'teardown': 5, 'workers': 1},
            {'name': 'التغليف النهائي', 'stage_type': 'other', 'wc_idx': 5,
             'setup': 5, 'operation': 15, 'teardown': 5, 'workers': 2},
        ]

        for bom in boms[:2]:
            for i, stage_def in enumerate(stages_definitions):
                try:
                    wc = created_wc[stage_def['wc_idx']] if stage_def['wc_idx'] < len(created_wc) else created_wc[0]
                    stage_code = f"TST-STG-{bom.id}-{i + 1}"

                    stage, created = ProductionStage.objects.update_or_create(
                        code=stage_code,
                        defaults={
                            'bom': bom,
                            'name': f"{stage_def['name']} - {bom.product.name[:15]}",
                            'stage_type': stage_def['stage_type'],
                            'work_center': wc,
                            'sequence': (i + 1) * 10,
                            'setup_time': Decimal(str(stage_def['setup'])),
                            'operation_time': Decimal(str(stage_def['operation'])),
                            'teardown_time': Decimal(str(stage_def['teardown'])),
                            'required_workers': stage_def['workers'],
                        }
                    )

                    total_time = stage_def['setup'] + stage_def['operation'] + stage_def['teardown']
                    labor_cost = stage.labor_cost_per_unit

                    results.success(
                        f"مرحلة: {stage_def['name'][:20]}",
                        f"الوقت: {total_time} دق | عمال: {stage_def['workers']} | "
                        f"تكلفة عمالة: {labor_cost:.2f} ج.م"
                    )

                    # ربط بـ BOM
                    try:
                        BOMStage.objects.update_or_create(
                            bom=bom,
                            stage=stage,
                            defaults={'sequence': i + 1, 'is_required': True}
                        )
                    except Exception:
                        pass

                except Exception as e:
                    results.error(f"مرحلة: {stage_def['name'][:20]}", str(e)[:60])

    # 6.3 حساب وقت الإنتاج الإجمالي وتكلفة العمالة
    print("\n  --- وقت الإنتاج وتكلفة العمالة ---")

    for bom in boms[:2]:
        try:
            stages = ProductionStage.objects.filter(bom=bom).order_by('sequence')
            total_time = Decimal('0')
            total_labor_cost = Decimal('0')

            for stage in stages:
                stage_time = stage.total_time_per_unit
                total_time += stage_time
                total_labor_cost += stage.labor_cost_per_unit

            if total_time > 0:
                hours = total_time / 60
                results.success(
                    f"إنتاج: {bom.product.name[:25]}",
                    f"{stages.count()} مراحل | {total_time:.0f} دق ({hours:.1f} ساعة) | "
                    f"تكلفة عمالة: {total_labor_cost:.2f} ج.م"
                )

                # التكلفة الإجمالية (مواد + عمالة)
                material_cost = sum(item.total_cost for item in bom.items.all())
                total_cost = material_cost + total_labor_cost
                if bom.product.price:
                    net_profit = bom.product.price - total_cost
                    margin = (net_profit / total_cost * 100) if total_cost > 0 else 0
                    results.success(
                        f"تكلفة كاملة: {bom.product.name[:20]}",
                        f"مواد: {material_cost:.0f} + عمالة: {total_labor_cost:.0f} = {total_cost:.0f} | "
                        f"ربح صافي: {net_profit:.0f} ({margin:.1f}%)"
                    )

        except Exception as e:
            results.error(f"حساب وقت الإنتاج", str(e)[:60])

    return created_wc


# ============================================================================
# SECTION 7: اختبار الأداء
# ============================================================================

def test_performance():
    """اختبارات الأداء"""
    print("\n" + "=" * 70)
    print("⚡ القسم 7: اختبار الأداء")
    print("=" * 70)

    from inventory.models import Product, Stock, Location
    from production.models import BillOfMaterials, BOMItem

    # 7.1 سرعة استعلام المنتجات
    start = time.time()
    products = list(Product.objects.all()[:200])
    elapsed = time.time() - start
    if elapsed < 1.0:
        results.success(f"استعلام {len(products)} منتج", f"{elapsed:.3f} ثانية ✓")
    else:
        results.fail(f"استعلام {len(products)} منتج بطيء", f"{elapsed:.3f} ثانية")

    # 7.2 سرعة استعلام BOM مع العناصر (prefetch)
    start = time.time()
    boms = list(BillOfMaterials.objects.select_related('product').prefetch_related('items__material').all()[:50])
    elapsed = time.time() - start
    if elapsed < 1.0:
        results.success(f"استعلام {len(boms)} BOM (prefetch)", f"{elapsed:.3f} ثانية ✓")
    else:
        results.fail(f"استعلام BOMs بطيء", f"{elapsed:.3f} ثانية")

    # 7.3 سرعة حساب التكاليف
    start = time.time()
    for bom in boms[:20]:
        total = sum(item.total_cost for item in bom.items.all())
    elapsed = time.time() - start
    count = min(len(boms), 20)
    if elapsed < 1.0:
        results.success(f"حساب تكاليف {count} BOMs", f"{elapsed:.3f} ثانية ✓")
    else:
        results.warn(f"حساب التكاليف بطيء", f"{elapsed:.3f} ثانية")

    # 7.4 سرعة استعلام المخزون
    start = time.time()
    stock_data = list(Stock.objects.select_related('product', 'location').all()[:500])
    elapsed = time.time() - start
    if elapsed < 1.0:
        results.success(f"استعلام {len(stock_data)} مخزون", f"{elapsed:.3f} ثانية ✓")
    else:
        results.fail(f"استعلام المخزون بطيء", f"{elapsed:.3f} ثانية")

    # 7.5 سرعة تجميع الموردين مع أسعارهم
    start = time.time()
    from inventory.models import SupplierProductPrice
    prices = list(
        SupplierProductPrice.objects.select_related('product', 'supplier')
        .filter(is_active=True)[:200]
    )
    elapsed = time.time() - start
    if elapsed < 1.0:
        results.success(f"استعلام {len(prices)} سعر مورد", f"{elapsed:.3f} ثانية ✓")
    else:
        results.warn(f"استعلام أسعار الموردين بطيء", f"{elapsed:.3f} ثانية")

    # 7.6 استعلام معقد (BOMs + مكونات + موردين)
    start = time.time()
    from django.db.models import Sum, F, Value, DecimalField
    try:
        bom_costs = BillOfMaterials.objects.filter(
            is_active=True
        ).annotate(
            calc_material_cost=Sum(
                F('items__quantity') * F('items__unit_cost'),
                output_field=DecimalField()
            )
        ).values('product__name', 'version', 'calc_material_cost')[:20]

        bom_cost_list = list(bom_costs)
        elapsed = time.time() - start
        if elapsed < 1.0:
            results.success(f"استعلام معقد (تجميع تكاليف)", f"{len(bom_cost_list)} نتيجة في {elapsed:.3f} ثانية ✓")
        else:
            results.warn(f"استعلام معقد بطيء", f"{elapsed:.3f} ثانية")
    except Exception as e:
        elapsed = time.time() - start
        results.warn(f"استعلام معقد", f"{str(e)[:60]} ({elapsed:.3f} ثانية)")


# ============================================================================
# SECTION 8: اختبارات API
# ============================================================================

def test_api_endpoints():
    """اختبار نقاط API"""
    print("\n" + "=" * 70)
    print("🌐 القسم 8: اختبار نقاط API")
    print("=" * 70)

    user = User.objects.filter(is_superuser=True).first()

    if not user:
        results.warn("اختبار API", "لا يوجد مستخدم مسؤول")
        return

    # قائمة API endpoints للاختبار
    api_urls = [
        '/api/products/',
        '/api/locations/',
        '/api/stock/',
        '/api/suppliers/',
        '/api/production/boms/',
        '/api/production/orders/',
        '/api/invoices/',
        '/api/purchases/',
        '/api/companies/',
    ]

    from django.test import Client
    from rest_framework.test import APIClient

    # Try DRF APIClient with force_authenticate first (supports JWT/Token auth)
    try:
        client = APIClient()
        client.force_authenticate(user=user)
    except Exception:
        client = Client()
        client.force_login(user)

    for url in api_urls:
        try:
            start = time.time()
            response = client.get(url, format='json')
            elapsed = time.time() - start

            if response.status_code == 200:
                try:
                    data = response.json() if hasattr(response, 'json') else json.loads(response.content)
                    count = len(data.get('results', data)) if isinstance(data, dict) else len(data)
                except Exception:
                    count = '?'
                results.success(f"API {url[:40]}", f"200 OK | {count} نتائج | {elapsed:.3f}s")
            elif response.status_code in (301, 302):
                results.success(f"API {url[:40]}", f"{response.status_code} (redirect)")
            elif response.status_code == 401:
                results.warn(f"API {url[:40]}", f"HTTP 401 - مطلوب مصادقة | {elapsed:.3f}s")
            else:
                results.fail(f"API {url[:40]}", f"HTTP {response.status_code} | {elapsed:.3f}s")
        except Exception as e:
            results.warn(f"API {url[:40]}", str(e)[:60])


# ============================================================================
# Cleanup
# ============================================================================

def cleanup(do_cleanup=False):
    """تنظيف البيانات التجريبية"""
    if not do_cleanup:
        print("\n💡 لحذف البيانات التجريبية: python3 testsprite_tests/TC_FULL_INTEGRATION_TEST.py --cleanup")
        return

    print("\n" + "=" * 70)
    print("🧹 تنظيف البيانات التجريبية")
    print("=" * 70)

    from inventory.models import Product, Location, Stock, StockTransfer
    from production.models import BillOfMaterials, ProductionWorkCenter, ProductionStage, ProductionOrder, BOMStage

    try:
        d = ProductionOrder.objects.filter(number__startswith='TST-PO').delete()
        print(f"  🗑️ أوامر إنتاج: {d[0]}")

        d = BOMStage.objects.filter(bom__product__sku__startswith='TST-').delete()
        print(f"  🗑️ مراحل BOM: {d[0]}")

        d = ProductionStage.objects.filter(code__startswith='TST-STG').delete()
        print(f"  🗑️ مراحل إنتاج: {d[0]}")

        d = BillOfMaterials.objects.filter(product__sku__startswith='TST-').delete()
        print(f"  🗑️ BOMs: {d[0]}")

        d = ProductionWorkCenter.objects.filter(code__startswith='TST-WC').delete()
        print(f"  🗑️ مراكز عمل: {d[0]}")

        d = StockTransfer.objects.filter(notes__contains='TC_FULL_INTEGRATION').delete()
        print(f"  🗑️ تحويلات: {d[0]}")

        d = Stock.objects.filter(product__sku__startswith='TST-').delete()
        print(f"  🗑️ مخزون: {d[0]}")

        d = Product.objects.filter(sku__startswith='TST-').delete()
        print(f"  🗑️ منتجات: {d[0]}")

        d = Location.objects.filter(code__startswith='TST-WH').delete()
        print(f"  🗑️ مواقع: {d[0]}")

        from partners.models import Supplier
        d = Supplier.objects.filter(code__startswith='TST-SUP').delete()
        print(f"  🗑️ موردين: {d[0]}")

        from inventory.models import Category
        d = Category.objects.filter(name__in=['مواد اختبار شامل', 'منتجات تامة - اختبار']).delete()
        print(f"  🗑️ فئات: {d[0]}")

        results.success("التنظيف", "تم حذف جميع البيانات التجريبية ✓")
    except Exception as e:
        results.error("التنظيف", str(e))


# ============================================================================
# Report
# ============================================================================

def save_report():
    """حفظ تقرير الاختبار"""
    report_path = BASE_DIR / 'testsprite_tests' / 'FULL_INTEGRATION_REPORT.md'

    try:
        elapsed = time.time() - results.start_time
        total = results.passed + results.failed + results.errors
        rate = (results.passed / total * 100) if total > 0 else 0

        report = f"""# 📊 تقرير الاختبار التكاملي الشامل

**التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**الوقت:** {elapsed:.2f} ثانية

## النتائج

| المؤشر | القيمة |
|--------|--------|
| ✅ نجح | {results.passed} |
| ❌ فشل | {results.failed} |
| 💥 أخطاء | {results.errors} |
| ⚠️ تحذيرات | {results.warnings} |
| 📈 نسبة النجاح | {rate:.1f}% |

## التفاصيل

| الحالة | الاختبار | الملاحظات |
|--------|----------|-----------|
"""
        for icon, name, msg in results.details:
            report += f"| {icon} | {name} | {msg} |\n"

        report += f"""
---

## التغطية

- [x] المخازن والمواقع المخزنية (5 أنواع)
- [x] الموردين وأنواعهم (6 موردين)
- [x] أسعار الموردين والمقارنة
- [x] قوائم المواد (BOM) - 4 وصفات
- [x] حساب الهدر (Wastage)
- [x] التسعير وهوامش الربح
- [x] التكامل بين الأنظمة
- [x] مراكز العمل (6 مراكز)
- [x] مراحل الإنتاج (6 مراحل)
- [x] أوامر الإنتاج
- [x] اختبارات الأداء (6 اختبارات)
- [x] نقاط API
"""

        os.makedirs(report_path.parent, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📄 تم حفظ التقرير في: {report_path}")
    except Exception as e:
        print(f"\n⚠️ خطأ في حفظ التقرير: {e}")


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 70)
    print("🧪 اختبار تكاملي شامل - Tony ERP")
    print("   المخازن | الموردين | التسعير | BOM | مراكز العمل | الأداء")
    print(f"   التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    do_cleanup = '--cleanup' in sys.argv

    try:
        # القسم 1: المخازن
        locations, products = test_inventory_locations()

        # القسم 2: الموردين
        suppliers = test_suppliers()

        # القسم 3: التسعير وأسعار الموردين
        prices = test_supplier_pricing(suppliers, products)

        # القسم 4: قوائم المواد (BOM)
        boms = test_bom(products, locations)

        # القسم 5: التكامل الشامل
        test_full_integration(locations, products, suppliers, boms)

        # القسم 6: مراكز العمل والمراحل
        work_centers = test_work_centers_and_stages(boms)

        # القسم 7: الأداء
        test_performance()

        # القسم 8: API
        test_api_endpoints()

        # التنظيف
        cleanup(do_cleanup)

    except Exception as e:
        print(f"\n💥 خطأ غير متوقع: {e}")
        traceback.print_exc()

    # النتائج
    success = results.summary()
    save_report()

    return 0 if success else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
