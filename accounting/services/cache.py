from functools import lru_cache
from decimal import Decimal
from typing import Optional
from django.db.models import Sum, Q
from ..models import Account, JournalEntryItem

# كاش في الذاكرة على مستوى العملية باستخدام LRU (يمكن استبداله بـ django cache)

@lru_cache(maxsize=2048)
def account_aggregate_balance_cached(account_id: int) -> Decimal:
    try:
        acc = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        return Decimal('0')
    from django.db.models import Sum, Q
    subtree_ids = Account.objects.filter(path__startswith=acc.path).values_list('id', flat=True)
    items = JournalEntryItem.objects.filter(account_id__in=subtree_ids, journal_entry__is_posted=True)
    agg = items.aggregate(
        debits=Sum('amount', filter=Q(type='debit')),
        credits=Sum('amount', filter=Q(type='credit'))
    )
    debits = agg['debits'] or Decimal('0')
    credits = agg['credits'] or Decimal('0')
    return debits - credits if acc.account_type in ['asset', 'expense'] else credits - debits

def invalidate_account_balance(account_id: int):
    # تفريغ إدخال محدد من الكاش (بإعادة تهيئة كامل الكاش البسيط هنا)
    account_aggregate_balance_cached.cache_clear()
