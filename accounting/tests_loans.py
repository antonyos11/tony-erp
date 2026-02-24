from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Account, Loan, Bank, LoanPayment, JournalEntry

class LoanWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u','u@u.com','pw')
        self.bank = Bank.objects.create(name='بنك', code='B1')
        self.loan_acc = Account.objects.create(code='2100', name='قرض بنك', account_type='liability')
        self.loan = Loan.objects.create(loan_number='LN1', bank=self.bank, principal_amount=Decimal('1200.00'), interest_rate=Decimal('12.00'), duration_months=12, disbursement_date='2025-01-01', loan_account=self.loan_acc, created_by=self.user, status='active', outstanding_balance=Decimal('1200.00'))

    def test_monthly_installment_calculation(self):
        inst = self.loan.monthly_installment
        self.assertGreater(inst, 0)

    def test_payment_updates_outstanding(self):
        before = self.loan.outstanding_balance
        LoanPayment.objects.create(loan=self.loan, payment_date='2025-02-01', amount=Decimal('110.00'), principal_portion=Decimal('100.00'), interest_portion=Decimal('10.00'), created_by=self.user)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.outstanding_balance, before - Decimal('100.00'))
