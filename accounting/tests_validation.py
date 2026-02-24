from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.exceptions import ValidationError
from .models import Account, JournalEntry, JournalEntryItem, CostCenter

class AccountingEnhancementsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('admin','a@a.com','pw')
        self.asset = Account.objects.create(code='A100', name='أصل', account_type='asset')
        self.rev = Account.objects.create(code='R100', name='إيراد', account_type='revenue')
        self.exp_parent = Account.objects.create(code='E000', name='مصروف رئيسي', account_type='expense', requires_cost_center=True)
        self.cost_center = CostCenter.objects.create(code='CC1', name='مركز 1')
        self.exp_with_default = Account.objects.create(code='E001', name='مصروف تلقائي', account_type='expense', requires_cost_center=True, default_cost_center=self.cost_center)

    def test_balance_property(self):
        je = JournalEntry.objects.create(description='قيد', created_by=self.user)
        JournalEntryItem.objects.create(journal_entry=je, account=self.asset, type='debit', amount=Decimal('150.00'))
        JournalEntryItem.objects.create(journal_entry=je, account=self.rev, type='credit', amount=Decimal('150.00'))
        self.assertEqual(self.asset.balance, Decimal('150.00'))
        self.assertEqual(self.rev.balance, Decimal('150.00'))

    def test_cost_center_required_raises(self):
        je = JournalEntry.objects.create(description='قيد 2', created_by=self.user)
        with self.assertRaises(ValidationError):
            JournalEntryItem.objects.create(journal_entry=je, account=self.exp_parent, type='debit', amount=Decimal('10.00'))

    def test_cost_center_auto_fill(self):
        je = JournalEntry.objects.create(description='قيد 3', created_by=self.user)
        item = JournalEntryItem.objects.create(journal_entry=je, account=self.exp_with_default, type='debit', amount=Decimal('20.00'))
        self.assertIsNotNone(item.cost_center)
        self.assertEqual(item.cost_center, self.cost_center)

    def test_cannot_post_unbalanced(self):
        je = JournalEntry.objects.create(description='قيد 4', created_by=self.user)
        JournalEntryItem.objects.create(journal_entry=je, account=self.asset, type='debit', amount=Decimal('50.00'))
        # محاولة ترحيل قبل التوازن
        je.is_posted = True
        with self.assertRaises(ValidationError):
            je.save()
        # موازنة
        JournalEntryItem.objects.create(journal_entry=je, account=self.rev, type='credit', amount=Decimal('50.00'))
        je.is_posted = True
        je.save()  # لا استثناء الآن
        self.assertTrue(je.is_posted)
