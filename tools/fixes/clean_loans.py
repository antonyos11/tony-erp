"""
تنظيف بيانات القروض الخاطئة
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from accounting.models import Loan
from decimal import InvalidOperation, Decimal

print("جاري فحص القروض...")

deleted_count = 0
fixed_count = 0
total_count = Loan.objects.count()

for loan in Loan.objects.all():
    try:
        # محاولة الوصول للحقول
        _ = loan.principal_amount
        _ = loan.interest_rate
        _ = loan.outstanding_balance
        
        # إذا كانت القيم صحيحة، نتحقق منها
        if loan.principal_amount is None or loan.principal_amount < 0:
            print(f"حذف القرض {loan.id}: مبلغ القرض غير صحيح")
            loan.delete()
            deleted_count += 1
        
    except (InvalidOperation, ValueError, TypeError) as e:
        print(f"حذف القرض {loan.id}: خطأ في البيانات - {e}")
        loan.delete()
        deleted_count += 1

print(f"\n{'='*50}")
print(f"إجمالي القروض: {total_count}")
print(f"تم حذف: {deleted_count} قرض")
print(f"القروض المتبقية: {Loan.objects.count()}")
print(f"{'='*50}")
