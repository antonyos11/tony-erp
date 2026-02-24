from django.core.management.base import BaseCommand
from decimal import Decimal
from accounting.models import Account, CostDriver, CostPool, CostPoolSourceAccount, CostPoolConsumption, CostCenter

class Command(BaseCommand):
    help = 'تهيئة بيانات اختبار للتوزيع'

    def handle(self, *a, **kw):
        cc = CostCenter.objects.first() or CostCenter.objects.create(code='CC1', name='مركز1')
        drv = CostDriver.objects.first() or CostDriver.objects.create(code='HRS', name='ساعات')
        accs = list(Account.objects.filter(account_type='expense', can_post=True)[:2])
        if len(accs) < 2:
            self.stdout.write('يلزم حسابان مصروفات على الأقل')
            return
        debit_acc, credit_acc = accs[0], accs[1]
        pool = CostPool.objects.first() or CostPool.objects.create(code='POOL1', name='مجمع خدمات', driver=drv, debit_account=debit_acc, credit_account=credit_acc)
        CostPoolSourceAccount.objects.get_or_create(pool=pool, account=credit_acc)
        CostPoolConsumption.objects.get_or_create(pool=pool, cost_center=cc, period='2025-09', defaults={'driver_quantity': Decimal('100')})
        self.stdout.write('تم تجهيز بيانات التوزيع للاختبار')
