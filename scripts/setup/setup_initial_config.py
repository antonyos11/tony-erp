"""
سكريبت الإعدادات الأولية للنظام الجديد
يقوم بإنشاء:
1. سياسة غياب افتراضية
2. أيام العمل (عطلة نهاية الأسبوع)
3. طابعة Zebra افتراضية (اختبارية)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from hr.models import AbsencePolicy, WeekendDay
from inventory.models import PrinterConfiguration
from decimal import Decimal

print("=" * 70)
print("بدء الإعدادات الأولية للنظام...")
print("=" * 70)

# 1. إنشاء سياسة غياب افتراضية
print("\n1. إنشاء سياسة الغياب الافتراضية...")
policy, created = AbsencePolicy.objects.get_or_create(
    is_default=True,
    defaults={
        'name': 'السياسة الافتراضية',
        'description': 'سياسة خصم الغياب الافتراضية للموظفين',
        'deduct_from_leave_first': True,
        'salary_deduction_per_day': Decimal('0'),
        'salary_deduction_percentage': Decimal('10'),  # 10% من الراتب اليومي
        'warning_days': 0,
        'unauthorized_absence_multiplier': Decimal('2.0'),  # مضاعفة العقوبة
        'is_active': True,
    }
)
if created:
    print("   ✅ تم إنشاء سياسة الغياب الافتراضية")
else:
    print("   ℹ️  سياسة الغياب موجودة مسبقاً")

# 2. إعداد أيام العمل
print("\n2. إعداد أيام العمل (عطلة نهاية الأسبوع)...")

# الجمعة (day_of_week = 4)
friday, created = WeekendDay.objects.get_or_create(
    day_of_week=4,
    defaults={
        'is_active': True  # True يعني عطلة
    }
)
if created:
    print("   ✅ تم تعيين الجمعة كعطلة")
else:
    print("   ℹ️  الجمعة معينة كعطلة مسبقاً")

# السبت (day_of_week = 5)
saturday, created = WeekendDay.objects.get_or_create(
    day_of_week=5,
    defaults={
        'is_active': True  # True يعني عطلة
    }
)
if created:
    print("   ✅ تم تعيين السبت كعطلة")
else:
    print("   ℹ️  السبت معين كعطلة مسبقاً")

# 3. إنشاء طابعة Zebra افتراضية (للاختبار)
print("\n3. إنشاء طابعة Zebra افتراضية...")
print("   ⚠️  تنبيه: عدّل عنوان IP حسب طابعتك الفعلية")

zebra_printer, created = PrinterConfiguration.objects.get_or_create(
    printer_type='zebra',
    document_type='barcode',
    defaults={
        'name': 'Zebra Barcode Printer',
        'connection_type': 'network',
        'ip_address': '192.168.1.100',  # عدّل هذا العنوان
        'port': 9100,
        'paper_size': '100x100mm',
        'dpi': 203,
        'label_width_mm': 100,
        'label_height_mm': 100,
        'is_default': True,
        'is_active': False,  # معطلة حتى تعديل الإعدادات
    }
)
if created:
    print("   ✅ تم إنشاء طابعة Zebra (معطلة حالياً)")
    print(f"   📝 عنوان IP: {zebra_printer.ip_address}:{zebra_printer.port}")
    print("   📝 لتفعيلها: افتح Admin > Inventory > Printer Configurations")
    print("      وعدّل عنوان IP ثم فعّل 'is_active'")
else:
    print("   ℹ️  طابعة Zebra موجودة مسبقاً")

print("\n" + "=" * 70)
print("✅ تمت الإعدادات الأولية بنجاح!")
print("=" * 70)

print("\n📋 الخطوات التالية:")
print("1. افتح Admin Panel: http://localhost:8000/admin/")
print("2. عدّل إعدادات طابعة Zebra (عنوان IP)")
print("3. جرّب بوابة الموظفين: http://localhost:8000/hr/employee-portal/")
print("4. جرّب لوحة الموافقات: http://localhost:8000/hr/leave-approval/")
print("\n📚 راجع التوثيق: docs/QUICK_START_BARCODE_HR.md")
print("=" * 70)
