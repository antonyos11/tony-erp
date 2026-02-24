from accounting.models import Account,CostDriver,CostPool,CostPoolSourceAccount,CostPoolConsumption,CostCenter
from decimal import Decimal
cc = CostCenter.objects.first() or CostCenter.objects.create(code='CC1', name='مركز1')
drv = CostDriver.objects.first() or CostDriver.objects.create(code='HRS', name='ساعات')
# الحصول على حسابين مصروفات
accs = list(Account.objects.filter(account_type='expense', can_post=True)[:2])
if len(accs) < 2:
    print('لا يوجد حسابان مصروفات كافيان للاختبار')
else:
    debit_acc, credit_acc = accs[0], accs[1]
    pool = CostPool.objects.first() or CostPool.objects.create(code='POOL1', name='مجمع خدمات', driver=drv, debit_account=debit_acc, credit_account=credit_acc)
    CostPoolSourceAccount.objects.get_or_create(pool=pool, account=credit_acc)
    CostPoolConsumption.objects.get_or_create(pool=pool, cost_center=cc, period='2025-09', defaults={'driver_quantity': Decimal('100')})
    print('تم تجهيز بيانات الاختبار')
