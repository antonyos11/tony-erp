from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from .models import Account, JournalEntry, JournalEntryItem

class TrialBalanceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tbuser','tb@example.com','pw')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client = Client(); self.client.login(username='tbuser', password='pw')
        # Create sample accounts
        self.cash = Account.objects.create(code='1000', name='صندوق', account_type='asset')
        self.rev = Account.objects.create(code='4000', name='إيراد', account_type='revenue')
        # Create a posted journal entry (cash debit, revenue credit)
        je = JournalEntry.objects.create(description='عملية اختبار', is_posted=False, entry_type='sales')
        JournalEntryItem.objects.create(journal_entry=je, account=self.cash, type='debit', amount=Decimal('150.00'))
        JournalEntryItem.objects.create(journal_entry=je, account=self.rev, type='credit', amount=Decimal('150.00'))
        je.is_posted = True
        je.save()

    def test_trial_balance_json(self):
        url = reverse('accounting:trial_balance') + '?format=json&page=1&page_size=50'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for key in ['rows','total_debit','total_credit','page','total_pages']:
            self.assertIn(key, data)
        # Totals should be balanced in this simple case
        self.assertEqual(data['total_debit'], data['total_credit'])
