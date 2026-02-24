"""
سكربت اختبار شامل لنظام ERP المصنع الكامل
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'الشامل.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

# Models
from hr.models import Employee, Department, Position
from inventory.models import Product, Location
from production.models import (
    WorkerProductionEntry, BillOfMaterials, BOMItem, 
    ProductionOrder, ProductionWorkCenter
)
from production.services.costing_service import (
    ProductCostingService, WorkerProductivityService
)

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def test_worker_production_system():
    """اختبار نظام تسجيل إنتاج العمال"""
    print_header("اختبار نظام تسجيل إنتاج العمال")
    
    # 1. التحقق من وجود عامل
    try:
        employee = Employee.objects.filter(is_active=True).first()
        if not employee:
            print("❌ لا يوجد موظفين في النظام")
            print("   قم بإنشاء موظف أولاً من لوحة الموارد البشرية")
            return False
        
        print(f"✅ تم العثور على عامل: {employee.arabic_name}")
        
        # 2. التحقق من وجود منتج
        product = Product.objects.filter(is_active=True).first()
        if not product:
            print("❌ لا توجد منتجات في النظام")
            return False
        
        print(f"✅ تم العثور على منتج: {product.name}")
        
        # 3. إنشاء تسجيل إنتاج تجريبي
        entry = WorkerProductionEntry.objects.create(
            employee=employee,
            date=date.today(),
            shift='صباحي',
            product=product,
            quantity=Decimal('100'),
            unit_of_measure='متر',
            hours_worked=Decimal('8'),
            status='submitted'
        )
        
        print(f"✅ تم إنشاء تسجيل إنتاج: {entry.id}")
        print(f"   العامل: {entry.employee.arabic_name}")
        print(f"   المنتج: {entry.product.name}")
        print(f"   الكمية: {entry.quantity} {entry.unit_of_measure}")
        print(f"   الحالة: {entry.get_status_display()}")
        
        # 4. حساب تكلفة العمالة
        entry.calculate_labor_cost()
        print(f"   تكلفة العمالة: {entry.labor_cost_calculated} ج.م")
        
        # 5. محاكاة الموافقة
        user = User.objects.filter(is_superuser=True).first()
        if user:
            entry.approve(user)
            print(f"✅ تمت الموافقة على التسجيل")
            print(f"   تم إنشاء حركة مخزون: {entry.inventory_transaction_created}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_costing_service():
    """اختبار خدمات محاسبة التكاليف"""
    print_header("اختبار خدمات محاسبة التكاليف")
    
    try:
        # البحث عن منتج له BOM
        bom = BillOfMaterials.objects.filter(is_active=True).first()
        if not bom:
            print("⚠️  لا توجد BOM في النظام")
            print("   قم بإنشاء BOM من لوحة الإنتاج")
            return False
        
        product = bom.product
        print(f"✅ تم العثور على منتج مع BOM: {product.name}")
        
        # 1. حساب التكلفة الكاملة
        cost_data = ProductCostingService.calculate_full_product_cost(
            product, Decimal('1')
        )
        
        print(f"\n📊 تفاصيل التكلفة لـ {product.name}:")
        print(f"   تكلفة المواد: {cost_data['material_cost']} ج.م")
        print(f"   تكلفة الأجور: {cost_data['labor_cost']} ج.م")
        print(f"   التكاليف غير المباشرة: {cost_data['overhead_cost']} ج.م")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━")
        print(f"   التكلفة الإجمالية: {cost_data['total_cost']} ج.م")
        print(f"   سعر البيع: {cost_data['selling_price']} ج.م")
        print(f"   هامش الربح: {cost_data['profit_margin']} ج.م ({cost_data['profit_percentage']:.1f}%)")
        
        # 2. تفاصيل المواد
        materials = cost_data['details']['materials']['materials']
        if materials:
            print(f"\n📦 تفاصيل المواد:")
            for mat in materials:
                print(f"   - {mat['material_name']}: {mat['quantity']} {mat['uom']} × {mat['unit_cost']} = {mat['total_cost']} ج.م")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_worker_productivity():
    """اختبار حساب إنتاجية العمال"""
    print_header("اختبار حساب إنتاجية العمال")
    
    try:
        employee = Employee.objects.filter(is_active=True).first()
        if not employee:
            print("❌ لا يوجد موظفين")
            return False
        
        # حساب إنتاجية آخر 30 يوم
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        productivity = WorkerProductivityService.calculate_worker_production(
            employee, start_date, end_date
        )
        
        print(f"✅ إنتاجية العامل: {employee.arabic_name}")
        print(f"   الفترة: {start_date} إلى {end_date}")
        print(f"   إجمالي الكمية: {productivity['total_units']}")
        print(f"   إجمالي ساعات العمل: {productivity['total_hours']}")
        print(f"   الإنتاجية (وحدة/ساعة): {productivity['units_per_hour']:.2f}")
        print(f"   أيام العمل: {productivity['days_worked']}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_system_readiness():
    """فحص جاهزية النظام"""
    print_header("فحص جاهزية النظام الشامل")
    
    checks = [
        ("الموظفين", Employee.objects.filter(is_active=True).count()),
        ("المنتجات", Product.objects.filter(is_active=True).count()),
        ("BOM", BillOfMaterials.objects.filter(is_active=True).count()),
        ("تسجيلات الإنتاج", WorkerProductionEntry.objects.count()),
        ("المستودعات", Location.objects.filter(is_active=True).count()),
    ]
    
    all_ready = True
    for name, count in checks:
        if count > 0:
            print(f"✅ {name}: {count}")
        else:
            print(f"⚠️  {name}: 0 (يحتاج إعداد)")
            all_ready = False
    
    return all_ready

def main():
    """تشغيل جميع الاختبارات"""
    print("\n" + "🚀"*35)
    print("  اختبار شامل لنظام ERP المصنع الكامل")
    print("🚀"*35)
    
    results = {
        "جاهزية النظام": test_system_readiness(),
        "تسجيل إنتاج العمال": test_worker_production_system(),
        "محاسبة التكاليف": test_costing_service(),
        "إنتاجية العمال": test_worker_productivity(),
    }
    
    print_header("ملخص النتائج")
    for test_name, result in results.items():
        status = "✅ نجح" if result else "❌ فشل أو يحتاج إعداد"
        print(f"{test_name}: {status}")
    
    success_rate = sum(1 for r in results.values() if r) / len(results) * 100
    print(f"\nنسبة النجاح: {success_rate:.0f}%")
    
    if success_rate == 100:
        print("\n🎉 جميع الاختبارات نجحت! النظام جاهز للعمل.")
    else:
        print("\n⚠️  بعض الاختبارات تحتاج إعداد البيانات الأساسية.")
        print("   قم بإنشاء موظفين، منتجات، وBOM من لوحة التحكم.")

if __name__ == '__main__':
    main()

