import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','accountant_pro.settings')
django.setup()
from accounting.models import Account, CostDriver, CostPool, CostPoolConsumption, CostPoolSourceAccount, CostCenter
from decimal import Decimal

acc_exp1,_=Account.objects.get_or_create(code='9100', defaults={'name':'مصروفات إدارية عامة','account_type':'expense','can_post':True})
acc_exp2,_=Account.objects.get_or_create(code='9101', defaults={'name':'مصروفات خدمات مساندة','account_type':'expense','can_post':True})
acc_debit,_=Account.objects.get_or_create(code='9200', defaults={'name':'تكلفة محملة','account_type':'expense','can_post':True})
acc_credit,_=Account.objects.get_or_create(code='9300', defaults={'name':'مجمع تكاليف خدمات','account_type':'expense','can_post':True})
cc1,_=CostCenter.objects.get_or_create(code='CC-ADM', defaults={'name':'إدارة'})
cc2,_=CostCenter.objects.get_or_create(code='CC-SLS', defaults={'name':'مبيعات'})
cc3,_=CostCenter.objects.get_or_create(code='CC-PRD', defaults={'name':'إنتاج'})
drv,_=CostDriver.objects.get_or_create(code='HRS', defaults={'name':'ساعات عمل','driver_type':'hours','unit':'hr'})
pool,_=CostPool.objects.get_or_create(code='SUPPORT', defaults={'name':'دعم إداري','driver':drv,'debit_account':acc_debit,'credit_account':acc_credit})
CostPoolSourceAccount.objects.get_or_create(pool=pool, account=acc_exp1, defaults={'percentage':0})
CostPoolSourceAccount.objects.get_or_create(pool=pool, account=acc_exp2, defaults={'percentage':0})
for cc,qty in [(cc1,Decimal('100')), (cc2,Decimal('300')), (cc3,Decimal('600'))]:
    CostPoolConsumption.objects.get_or_create(pool=pool, cost_center=cc, period='2025-09', defaults={'driver_quantity':qty})
print('Seed allocation data ready.')
