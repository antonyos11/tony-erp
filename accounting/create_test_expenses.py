from accounting.models import Account
accs = list(Account.objects.filter(account_type='expense', can_post=True)[:2])
need = 2 - len(accs)
for i in range(need):
    code = f'9EXP{i+1:02d}'
    Account.objects.get_or_create(code=code, defaults={'name': f'مصروف اختبار {i+1}', 'account_type': 'expense', 'can_post': True})
print('تم تجهيز حسابات المصروفات (العدد الحالي):', Account.objects.filter(account_type='expense', can_post=True).count())
