"""
مثال عملي: استخدام رقم الفاتورة التالي في معاملة محاسبية

هذا المثال يوضح كيفية استخدام رقم الفاتورة المتوقع في قيد محاسبي
قبل إنشاء الفاتورة الفعلية
"""

# إعداد Django
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from sales.next_invoice_number import get_next_invoice_number, get_next_tax_invoice_number
from decimal import Decimal


def example_1_accounting_entry():
    """
    مثال 1: تسجيل قيد محاسبي متوقع باستخدام رقم الفاتورة التالي
    """
    print("\n" + "="*60)
    print("مثال 1: تسجيل قيد محاسبي متوقع")
    print("="*60)
    
    # الحصول على رقم الفاتورة التالي
    next_invoice = get_next_invoice_number()
    print(f"\n✓ رقم الفاتورة المتوقع: {next_invoice}")
    
    # بيانات القيد المحاسبي
    amount = Decimal('5000.00')
    vat = Decimal('750.00')  # 15%
    total = amount + vat
    
    print(f"\n📝 القيد المحاسبي:")
    print(f"   التاريخ: اليوم")
    print(f"   المرجع: {next_invoice}")
    print(f"   الوصف: فاتورة مبيعات متوقعة")
    print(f"\n   من حـ/ العملاء          {total:,.2f}")
    print(f"        إلى حـ/ المبيعات         {amount:,.2f}")
    print(f"        إلى حـ/ ضريبة القيمة المضافة  {vat:,.2f}")
    
    print(f"\n💡 ملاحظة: هذا قيد متوقع، يتم تأكيده عند إصدار الفاتورة {next_invoice}")


def example_2_tax_invoice_planning():
    """
    مثال 2: التخطيط لفاتورة ضريبية
    """
    print("\n" + "="*60)
    print("مثال 2: التخطيط لفاتورة ضريبية")
    print("="*60)
    
    # الحصول على أرقام الفواتير الضريبية
    sales_tax = get_next_tax_invoice_number('sales')
    purchase_tax = get_next_tax_invoice_number('purchase')
    
    print(f"\n✓ الفاتورة الضريبية التالية - مبيعات: {sales_tax}")
    print(f"✓ الفاتورة الضريبية التالية - مشتريات: {purchase_tax}")
    
    print("\n📋 خطة العمل:")
    print(f"   1. تحضير فاتورة مبيعات ضريبية رقم: {sales_tax}")
    print(f"   2. تسجيل في دفتر المبيعات")
    print(f"   3. إعداد التقرير الضريبي الشهري")
    

def example_3_excel_report():
    """
    مثال 3: تحضير تقرير Excel بأرقام الفواتير المتوقعة
    """
    print("\n" + "="*60)
    print("مثال 3: تحضير تقرير Excel")
    print("="*60)
    
    from sales.next_invoice_number import preview_invoice_numbers
    
    numbers = preview_invoice_numbers()
    
    print("\n📊 أرقام الفواتير للتقرير:")
    print("\n| النوع | الرقم التالي |")
    print("|-------|-------------|")
    for key, value in numbers.items():
        print(f"| {key.replace('_', ' ').title()} | {value} |")
    
    print("\n💡 يمكن نسخ هذه الأرقام ولصقها في Excel مباشرة")


def example_4_api_usage():
    """
    مثال 4: استخدام الأرقام في API خارجي
    """
    print("\n" + "="*60)
    print("مثال 4: التكامل مع API خارجي")
    print("="*60)
    
    import json
    from sales.next_invoice_number import preview_invoice_numbers
    
    numbers = preview_invoice_numbers()
    
    # محاكاة إرسال البيانات لـ API خارجي
    api_payload = {
        'expected_invoices': numbers,
        'company': 'شركة مثال',
        'date': '2026-01-17',
        'status': 'planned'
    }
    
    print("\n📤 البيانات المرسلة للـ API:")
    print(json.dumps(api_payload, ensure_ascii=False, indent=2))
    
    print("\n✓ يمكن استخدام هذه البيانات في:")
    print("  - أنظمة ERP خارجية")
    print("  - تطبيقات المحاسبة السحابية")
    print("  - أدوات التقارير")


def example_5_batch_planning():
    """
    مثال 5: التخطيط لدفعة من الفواتير
    """
    print("\n" + "="*60)
    print("مثال 5: التخطيط لدفعة فواتير")
    print("="*60)
    
    next_invoice = get_next_invoice_number()
    
    # استخراج الجزء الرقمي
    try:
        prefix, year_month, seq = next_invoice.rsplit('-', 2)
        base = int(seq)
    except:
        print("خطأ في استخراج الرقم")
        return
    
    print(f"\n📦 تخطيط لـ 5 فواتير متتالية:")
    print(f"   الفاتورة الأساسية: {next_invoice}")
    
    for i in range(5):
        invoice_num = f"{prefix}-{year_month}-{str(base + i).zfill(6)}"
        print(f"   {i+1}. {invoice_num}")
    
    print("\n💡 ملاحظة: هذه أرقام متوقعة فقط")


def main():
    """
    تشغيل جميع الأمثلة
    """
    print("\n" + "🎓 "+"="*58 + " 🎓")
    print("    أمثلة عملية لاستخدام أرقام الفواتير المتوقعة")
    print("🎓 " + "="*58 + " 🎓")
    
    example_1_accounting_entry()
    example_2_tax_invoice_planning()
    example_3_excel_report()
    example_4_api_usage()
    example_5_batch_planning()
    
    print("\n" + "="*60)
    print("✨ انتهت الأمثلة")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
