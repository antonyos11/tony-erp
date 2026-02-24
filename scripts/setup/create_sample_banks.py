"""
إنشاء بنوك نموذجية في النظام
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from accounting.models import Bank

# قائمة البنوك المصرية الشهيرة
banks_data = [
    {
        'name': 'البنك الأهلي المصري',
        'code': 'NBE',
        'swift_code': 'NBEGEGCX',
        'phone': '19623',
        'is_active': True
    },
    {
        'name': 'بنك مصر',
        'code': 'BME',
        'swift_code': 'BMISEGCX',
        'phone': '19888',
        'is_active': True
    },
    {
        'name': 'بنك القاهرة',
        'code': 'BOC',
        'swift_code': 'BOCAEGCX',
        'phone': '16822',
        'is_active': True
    },
    {
        'name': 'البنك التجاري الدولي - CIB',
        'code': 'CIB',
        'swift_code': 'CIBEEGCX',
        'phone': '19666',
        'is_active': True
    },
    {
        'name': 'بنك الإسكندرية',
        'code': 'ALEX',
        'swift_code': 'ALEXEGCX',
        'phone': '19777',
        'is_active': True
    },
    {
        'name': 'بنك فيصل الإسلامي',
        'code': 'FIB',
        'swift_code': 'FIBKEGCX',
        'phone': '16700',
        'is_active': True
    },
    {
        'name': 'بنك HSBC مصر',
        'code': 'HSBC',
        'swift_code': 'HBEGEGCX',
        'phone': '16722',
        'is_active': True
    },
    {
        'name': 'بنك قطر الوطني الأهلي - QNB',
        'code': 'QNB',
        'swift_code': 'QNBAEGCX',
        'phone': '19405',
        'is_active': True
    }
]

created_count = 0
updated_count = 0

for bank_data in banks_data:
    bank, created = Bank.objects.get_or_create(
        code=bank_data['code'],
        defaults=bank_data
    )
    
    if created:
        created_count += 1
        print(f"✓ تم إنشاء: {bank.name}")
    else:
        # تحديث البيانات إذا كان البنك موجود
        for key, value in bank_data.items():
            setattr(bank, key, value)
        bank.save()
        updated_count += 1
        print(f"→ تم تحديث: {bank.name}")

print(f"\n{'='*50}")
print(f"تم إنشاء {created_count} بنك جديد")
print(f"تم تحديث {updated_count} بنك موجود")
print(f"إجمالي البنوك في النظام: {Bank.objects.count()}")
print(f"{'='*50}")
