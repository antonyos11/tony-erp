from decimal import Decimal
from datetime import date

from accounting.models import Account, JournalEntry, JournalEntryItem
from django.contrib.auth.models import User

# احصل على حساب قابل للقيد أو أنشئ واحدًا للاختبار
acc = Account.objects.filter(can_post=True, is_active=True).first()
if not acc:
    acc = Account.objects.create(code='9999', name='Test Account', account_type='asset', can_post=True, is_active=True)

# مستخدم للاختبارات
user = User.objects.filter(is_superuser=True).first() or User.objects.first()

# أنشئ قيد تجريبي
je = JournalEntry.objects.create(
    description='Test JE for analytics fields',
    reference='ref-test',
    entry_type='manual',
    date=date(2025,9,15),
    created_by=user
)

# بنود متوازنة
it1 = JournalEntryItem.objects.create(
    journal_entry=je,
    account=acc,
    type='debit',
    amount=Decimal('150.00'),
    description='test debit',
    master_account='MA1',
    analytics='A1',
    analytics_2='A2',
    analytics_3='A3'
)
it2 = JournalEntryItem.objects.create(
    journal_entry=je,
    account=acc,
    type='credit',
    amount=Decimal('150.00'),
    description='test credit',
    master_account='MA2',
    analytics='B1',
    analytics_2='B2',
    analytics_3='B3'
)

print('Created JournalEntry:', je.pk, je.number)
for it in je.items.all():
    print('Item:', it.pk, it.type, float(it.amount), it.master_account, it.analytics, it.analytics_2, it.analytics_3)
print('Done')
