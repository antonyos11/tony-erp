"""
سكريبت مسح جميع البيانات التجريبية - Tony ERP
تشغيل: .venv/bin/python scripts/clear_demo_data.py
"""

import os
import sys
import django

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.db import transaction, connection

print("=" * 70)
print("🗑️   بدء مسح البيانات التجريبية - Tony ERP")
print("=" * 70)

errors = []

def safe_delete(model_path, label):
    try:
        parts = model_path.rsplit('.', 1)
        module_path, class_name = parts[0], parts[1]
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        count = cls.objects.count()
        cls.objects.all().delete()
        print(f"  ✅ {label}: تم حذف {count} سجل")
        return count
    except Exception as e:
        msg = f"  ⚠️  {label}: {e}"
        print(msg)
        errors.append(msg)
        return 0

with transaction.atomic():

    print("\n📌 1. المبيعات")
    safe_delete('sales.models.SalesOrderLine',      'بنود أوامر البيع')
    safe_delete('sales.models.SalesOrder',          'أوامر البيع')
    safe_delete('sales.models.InvoiceItem',         'بنود الفواتير')
    safe_delete('sales.models.Payment',             'المدفوعات')
    safe_delete('sales.models.Invoice',             'الفواتير')

    print("\n📌 2. المشتريات")
    safe_delete('purchases.models.PurchaseRequisitionItem', 'بنود طلبات الشراء')
    safe_delete('purchases.models.PurchaseRequisition',     'طلبات الشراء')
    safe_delete('purchases.models.PurchaseOrderLine',       'بنود أوامر الشراء')
    safe_delete('purchases.models.PurchaseOrder',           'أوامر الشراء')
    safe_delete('purchases.models.PurchaseItem',            'بنود الفواتير الشراء')
    safe_delete('purchases.models.PurchaseBill',            'فواتير الشراء')

    print("\n📌 3. المحاسبة (القيود فقط - الحسابات تبقى)")
    safe_delete('accounting.models.JournalEntryItem', 'بنود القيود')
    safe_delete('accounting.models.JournalEntry',     'القيود المحاسبية')

    print("\n📌 4. المخزون - الحركات")
    safe_delete('inventory.models.StockMovement', 'حركات المخزون')
    safe_delete('inventory.models.StockTransfer', 'نقل المخزون')
    safe_delete('inventory.models.Stock',         'أرصدة المخزون')

    print("\n📌 5. نقاط البيع")
    safe_delete('pos.models.POSOrderItem',  'بنود POS')
    safe_delete('pos.models.POSOrder',      'طلبات POS')
    safe_delete('pos.models.POSSession',    'جلسات POS')

    print("\n📌 6. الموارد البشرية")
    safe_delete('hr.models.LoanInstallment', 'أقساط السلف')
    safe_delete('hr.models.EmployeeLoan',    'السلف')
    safe_delete('hr.models.Payroll',         'الرواتب')
    safe_delete('hr.models.Attendance',      'الحضور')
    safe_delete('hr.models.Leave',           'الإجازات')

    print("\n📌 7. العملاء التجريبيون فقط")
    try:
        from partners.models import Customer
        # حذف العملاء التجريبيين فقط
        test_keywords = ['Test', 'TestSprite', 'test', 'TC00', 'Ahmad Ali', 
                         'John Smith', 'Sara Ahmed', 'Mohamed Hassan', 'Fatima Abbas']
        deleted = 0
        for kw in test_keywords:
            count, _ = Customer.objects.filter(name__icontains=kw).delete()
            deleted += count
        print(f"  ✅ العملاء التجريبيون: تم حذف {deleted} سجل")
    except Exception as e:
        print(f"  ⚠️  العملاء: {e}")
        errors.append(str(e))

    print("\n📌 8. الموردون التجريبيون فقط")
    try:
        from partners.models import Supplier, Partner
        test_keywords = ['TestSprite', 'TC006', 'Test Supplier', 'test signal']
        deleted = 0
        for kw in test_keywords:
            count, _ = Supplier.objects.filter(name__icontains=kw).delete()
            deleted += count
        print(f"  ✅ الموردون التجريبيون: تم حذف {deleted} سجل")
        # حذف الشركاء التجريبيين
        deleted2 = 0
        for kw in test_keywords:
            count, _ = Partner.objects.filter(name__icontains=kw).delete()
            deleted2 += count
        print(f"  ✅ الشركاء التجريبيون: تم حذف {deleted2} سجل")
    except Exception as e:
        print(f"  ⚠️  الموردون: {e}")
        errors.append(str(e))

    print("\n📌 9. الحسابات التجريبية فقط")
    try:
        from accounting.models import Account
        test_keywords = ['Test Account', 'TEST-EQUITY', 'TEST-REVENUE', 'Fresh Test']
        deleted = 0
        for kw in test_keywords:
            count, _ = Account.objects.filter(name__icontains=kw).delete()
            deleted += count
        for kw in ['TEST-', '9102', '9104', '9158', '9215', '9300']:
            count, _ = Account.objects.filter(code__icontains=kw).delete()
            deleted += count
        print(f"  ✅ الحسابات التجريبية: تم حذف {deleted} سجل")
    except Exception as e:
        print(f"  ⚠️  الحسابات: {e}")
        errors.append(str(e))

    print("\n📌 10. الإشعارات والسجلات التجريبية")
    safe_delete('notifications.models.Notification', 'الإشعارات')

    print("\n📌 11. المنتجات والإنتاج التجريبيون")
    safe_delete('production.models.ProductionOrderMaterial', 'مواد الإنتاج')
    safe_delete('production.models.ProductionOrder',         'أوامر الإنتاج')
    safe_delete('inventory.models.BOMItem',                  'بنود BOM')
    safe_delete('inventory.models.BOM',                      'قوائم المكونات')

print("\n" + "=" * 70)
if errors:
    print(f"⚠️  اكتمل بـ {len(errors)} تحذير (غير مؤثرة)")
    for e in errors:
        print(f"    {e}")
else:
    print("🎉 تم مسح جميع البيانات التجريبية بنجاح!")
print("=" * 70)

print("""
📋 الخطوات التالية لإدخال البيانات الحقيقية:
  1️⃣  تحقق من إعدادات الشركة
  2️⃣  راجع شجرة الحسابات
  3️⃣  أضف الموظفين
  4️⃣  ابدأ الفواتير والمشتريات الحقيقية
""")
