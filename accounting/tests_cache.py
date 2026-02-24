from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Account, JournalEntry, JournalEntryItem
from .services import get_account_balance_cached, invalidate_account_balance

class BalanceCacheTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u','u@u.com','pw')
        self.asset = Account.objects.create(code='A777', name='أصل كاش', account_type='asset')
        self.rev = Account.objects.create(code='R777', name='إيراد كاش', account_type='revenue')
        self.je = JournalEntry.objects.create(description='قيد', created_by=self.user, is_posted=False)
        JournalEntryItem.objects.create(journal_entry=self.je, account=self.asset, type='debit', amount=Decimal('50.00'))
        JournalEntryItem.objects.create(journal_entry=self.je, account=self.rev, type='credit', amount=Decimal('50.00'))
        self.je.is_posted = True
        self.je.save()

    def test_cached_balance(self):
        b1 = get_account_balance_cached(self.asset.id)
        self.assertEqual(b1, Decimal('50.00'))
        # أضف بند جديد لنفس الحساب (لن ينعكس إلا بعد إبطال الكاش)
        je2 = JournalEntry.objects.create(description='قيد 2', created_by=self.user, is_posted=False)
        JournalEntryItem.objects.create(journal_entry=je2, account=self.asset, type='debit', amount=Decimal('25.00'))
        JournalEntryItem.objects.create(journal_entry=je2, account=self.rev, type='credit', amount=Decimal('25.00'))
        je2.is_posted = True
        je2.save()
        b_after_signal = get_account_balance_cached(self.asset.id)
        # بسبب signal تم إبطال الكاش تلقائياً وتحديثه
        self.assertEqual(b_after_signal, Decimal('75.00'))
