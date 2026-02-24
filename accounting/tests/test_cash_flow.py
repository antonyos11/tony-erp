from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from datetime import date
from accounting.models import Account, JournalEntry, JournalEntryItem


class CashFlowStatementTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user('u','u@example.com','pw')
		self.user.is_staff = True
		self.user.is_superuser = True
		self.user.save()
		# تعطيل إلزام تغيير كلمة المرور
		try:
			from users.models import UserProfile
			profile = UserProfile.objects.get(user=self.user)
			profile.must_change_password = False
			profile.is_approved = True
			profile.save()
		except Exception:
			pass
		self.client = Client()
		self.client.force_login(self.user)
		# Create some accounts
		self.rev = Account.objects.create(code='4001', name='مبيعات', account_type='revenue')
		self.exp = Account.objects.create(code='5001', name='مصروفات', account_type='expense')
		self.bank = Account.objects.create(code='1001', name='بنك', account_type='asset')
		# Simple journal (sale: bank debit, revenue credit)
		j = JournalEntry.objects.create(description='بيع', entry_type='sales', is_posted=False)
		JournalEntryItem.objects.create(journal_entry=j, account=self.bank, type='debit', amount=Decimal('100.00'))
		JournalEntryItem.objects.create(journal_entry=j, account=self.rev, type='credit', amount=Decimal('100.00'))
		j.is_posted = True
		j.save()
		# Expense (expense debit, bank credit)
		e = JournalEntry.objects.create(description='مصروف', entry_type='adjustment', is_posted=False)
		JournalEntryItem.objects.create(journal_entry=e, account=self.exp, type='debit', amount=Decimal('30.00'))
		JournalEntryItem.objects.create(journal_entry=e, account=self.bank, type='credit', amount=Decimal('30.00'))
		e.is_posted = True
		e.save()

	def test_cash_flow_basic(self):
		self.client.force_login(self.user)
		url = reverse('accounting:cash_flow_statement') + '?format=json'
		r = self.client.get(url)
		self.assertEqual(r.status_code,200)
		self.assertIn('operating', r.json())

	def test_cash_flow_compare(self):
		url = reverse('accounting:cash_flow_statement') + '?compare=1&format=json'
		r = self.client.get(url)
		self.assertEqual(r.status_code,200)
		self.assertIn('prev_period', r.json())

	def test_cash_flow_json(self):
		url = reverse('accounting:cash_flow_statement') + '?format=json'
		r = self.client.get(url)
		self.assertEqual(r.status_code,200)
		self.assertIn('operating', r.json())

	def test_cash_flow_xlsx_export(self):
		url = reverse('accounting:cash_flow_statement') + '?export=xlsx'
		r = self.client.get(url)
		self.assertEqual(r.status_code,200)
		self.assertIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', r.headers.get('Content-Type',''))

	def test_cash_flow_csv_export(self):
		url = reverse('accounting:cash_flow_statement') + '?export=csv'
		r = self.client.get(url)
		self.assertEqual(r.status_code,200)
		self.assertIn('text/csv', r.headers.get('Content-Type',''))
