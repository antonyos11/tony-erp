"""
اختبارات تطبيق المصروفات والسندات — RITA ERP
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Account, FiscalYear
from apps.core.models import Branch
from apps.expenses.models import (
    ExpenseCategory, Expense, RecurringExpense,
    PaymentVoucher, ReceiptVoucher,
    PettyCash, PettyCashTransaction,
)
from apps.expenses.services.expense_engine import ExpenseEngine, VoucherEngine, PettyCashEngine

User = get_user_model()


def _create_accounts():
    """إنشاء الحسابات اللازمة للاختبارات"""
    data = [
        ('1111', 'الخزينة',               'asset',     'debit'),
        ('115',  'ضريبة مشتريات',          'asset',     'debit'),
        ('61',   'مصروفات إدارية',         'expense',   'debit'),
        ('611',  'رواتب وأجور إدارية',     'expense',   'debit'),
        ('612',  'إيجارات',                'expense',   'debit'),
        ('613',  'كهرباء ومياه',           'expense',   'debit'),
        ('619',  'مصروفات متنوعة',         'expense',   'debit'),
        ('1121', 'ذمم العملاء',            'asset',     'debit'),
        ('211',  'ذمم الموردين',           'liability', 'credit'),
    ]
    for code, name, atype, nature in data:
        Account.objects.get_or_create(
            code=code,
            defaults=dict(name=name, account_type=atype, nature=nature,
                          is_detail=True, is_system=True),
        )


def _setup_base(self):
    """إعداد الكائنات الأساسية للاختبارات"""
    self.user = User.objects.create_user(username='expense_tester', password='test123')

    self.branch = Branch.objects.create(
        name='فرع تجريبي المصروفات', branch_type='owned', governorate='القاهرة',
    )

    FiscalYear.objects.create(
        name='2026', start_date='2026-01-01', end_date='2026-12-31',
        is_active=True, is_closed=False,
    )
    _create_accounts()

    expense_account = Account.objects.get(code='612')
    self.category = ExpenseCategory.objects.create(
        name='إيجارات', account=expense_account, is_active=True,
    )


# ══════════════════════════════════════════════════════
# اختبارات محرك المصروفات
# ══════════════════════════════════════════════════════

class ExpenseEngineTest(TestCase):
    """اختبار ExpenseEngine"""

    def setUp(self):
        _setup_base(self)

    def test_create_expense(self):
        """إنشاء مصروف مسودة"""
        expense = ExpenseEngine.create_expense(
            category=self.category,
            branch=self.branch,
            description='إيجار شهر يناير',
            amount=Decimal('1000.00'),
            user=self.user,
        )
        self.assertIsNotNone(expense.pk)
        self.assertEqual(expense.status, 'draft')
        self.assertEqual(expense.amount, Decimal('1000.00'))
        self.assertEqual(expense.total, Decimal('1000.00'))
        self.assertTrue(expense.expense_number.startswith('EXP-'))

    def test_create_expense_with_tax(self):
        """إنشاء مصروف خاضع للضريبة"""
        expense = ExpenseEngine.create_expense(
            category=self.category,
            branch=self.branch,
            description='مصروف خاضع للضريبة',
            amount=Decimal('1000.00'),
            is_taxable=True,
            user=self.user,
        )
        self.assertTrue(expense.is_taxable)
        self.assertGreater(expense.tax_amount, 0)
        self.assertEqual(expense.total, expense.amount + expense.tax_amount)

    def test_approve_and_pay_expense(self):
        """اعتماد وصرف مصروف — يجب أن ينشئ قيداً"""
        expense = ExpenseEngine.create_expense(
            category=self.category,
            branch=self.branch,
            description='إيجار اختبار',
            amount=Decimal('500.00'),
            user=self.user,
        )
        expense = ExpenseEngine.approve_and_pay_expense(expense, user=self.user)
        self.assertEqual(expense.status, 'paid')
        self.assertIsNotNone(expense.journal_entry)
        self.assertIsNotNone(expense.approved_by)
        self.assertIsNotNone(expense.approved_at)
        # التحقق من القيد
        lines = expense.journal_entry.lines.all()
        self.assertGreaterEqual(lines.count(), 2)
        total_debit = sum(l.debit for l in lines)
        total_credit = sum(l.credit for l in lines)
        self.assertEqual(total_debit, total_credit)

    def test_approve_already_paid_raises(self):
        """محاولة اعتماد مصروف مدفوع يجب أن ترفع استثناء"""
        expense = ExpenseEngine.create_expense(
            category=self.category,
            branch=self.branch,
            description='اختبار رفع استثناء',
            amount=Decimal('200.00'),
            user=self.user,
        )
        ExpenseEngine.approve_and_pay_expense(expense, user=self.user)
        expense.refresh_from_db()
        with self.assertRaises(ValueError):
            ExpenseEngine.approve_and_pay_expense(expense, user=self.user)


# ══════════════════════════════════════════════════════
# اختبارات محرك السندات
# ══════════════════════════════════════════════════════

class VoucherEngineTest(TestCase):
    """اختبار VoucherEngine"""

    def setUp(self):
        _setup_base(self)
        self.debit_account = Account.objects.get(code='619')
        self.credit_account = Account.objects.get(code='1111')

    def test_create_payment_voucher(self):
        """إنشاء سند صرف"""
        voucher = VoucherEngine.create_payment_voucher(
            branch=self.branch,
            beneficiary_type='other',
            amount=Decimal('300.00'),
            description='سند صرف اختبار',
            debit_account=self.debit_account,
            credit_account=self.credit_account,
            beneficiary_name='مستفيد تجريبي',
            user=self.user,
        )
        self.assertIsNotNone(voucher.pk)
        self.assertEqual(voucher.status, 'draft')
        self.assertTrue(voucher.voucher_number.startswith('PV-'))

    def test_approve_payment_voucher(self):
        """اعتماد سند صرف — ينشئ قيداً"""
        voucher = VoucherEngine.create_payment_voucher(
            branch=self.branch,
            beneficiary_type='other',
            amount=Decimal('300.00'),
            description='سند صرف للاعتماد',
            debit_account=self.debit_account,
            credit_account=self.credit_account,
            user=self.user,
        )
        voucher = VoucherEngine.approve_payment_voucher(voucher, user=self.user)
        self.assertEqual(voucher.status, 'paid')
        self.assertIsNotNone(voucher.journal_entry)
        lines = voucher.journal_entry.lines.all()
        self.assertEqual(lines.count(), 2)

    def test_approve_already_approved_raises(self):
        """اعتماد سند مكرر يجب أن يرفع استثناء"""
        voucher = VoucherEngine.create_payment_voucher(
            branch=self.branch,
            beneficiary_type='other',
            amount=Decimal('100.00'),
            description='اختبار',
            debit_account=self.debit_account,
            credit_account=self.credit_account,
            user=self.user,
        )
        VoucherEngine.approve_payment_voucher(voucher, user=self.user)
        voucher.refresh_from_db()
        with self.assertRaises(ValueError):
            VoucherEngine.approve_payment_voucher(voucher, user=self.user)

    def test_create_receipt_voucher(self):
        """إنشاء سند قبض"""
        voucher = VoucherEngine.create_receipt_voucher(
            branch=self.branch,
            payer_type='other',
            amount=Decimal('500.00'),
            description='سند قبض اختبار',
            debit_account=self.credit_account,
            credit_account=Account.objects.get(code='1121'),
            user=self.user,
        )
        self.assertIsNotNone(voucher.pk)
        self.assertEqual(voucher.status, 'draft')
        self.assertTrue(voucher.voucher_number.startswith('RV-'))

    def test_approve_receipt_voucher(self):
        """اعتماد سند قبض — ينشئ قيداً"""
        voucher = VoucherEngine.create_receipt_voucher(
            branch=self.branch,
            payer_type='other',
            amount=Decimal('500.00'),
            description='سند قبض للاعتماد',
            debit_account=self.credit_account,
            credit_account=Account.objects.get(code='1121'),
            user=self.user,
        )
        voucher = VoucherEngine.approve_receipt_voucher(voucher, user=self.user)
        self.assertEqual(voucher.status, 'received')
        self.assertIsNotNone(voucher.journal_entry)


# ══════════════════════════════════════════════════════
# اختبارات العهدة النثرية
# ══════════════════════════════════════════════════════

class PettyCashEngineTest(TestCase):
    """اختبار PettyCashEngine"""

    def setUp(self):
        _setup_base(self)
        self.petty_account = Account.objects.get(code='1111')
        self.petty_cash = PettyCash.objects.create(
            name='عهدة تجريبية',
            branch=self.branch,
            custodian=User.objects.get(username='expense_tester'),
            limit_amount=Decimal('1000.00'),
            current_balance=Decimal('0'),
            account=self.petty_account,
            is_active=True,
        )

    def test_replenish(self):
        """تعبئة العهدة"""
        PettyCashEngine.replenish(self.petty_cash, Decimal('500.00'), user=self.user)
        self.petty_cash.refresh_from_db()
        self.assertEqual(self.petty_cash.current_balance, Decimal('500.00'))
        txn = PettyCashTransaction.objects.filter(petty_cash=self.petty_cash).last()
        self.assertEqual(txn.transaction_type, 'in')

    def test_spend(self):
        """صرف من العهدة"""
        PettyCashEngine.replenish(self.petty_cash, Decimal('500.00'), user=self.user)
        self.petty_cash.refresh_from_db()
        PettyCashEngine.spend(
            self.petty_cash,
            Decimal('200.00'),
            description='شراء أدوات مكتبية',
            category=self.category,
            user=self.user,
        )
        self.petty_cash.refresh_from_db()
        self.assertEqual(self.petty_cash.current_balance, Decimal('300.00'))

    def test_spend_insufficient_balance_raises(self):
        """الصرف بأكثر من الرصيد يجب أن يرفع استثناء"""
        with self.assertRaises(ValueError):
            PettyCashEngine.spend(
                self.petty_cash,
                Decimal('100.00'),
                description='صرف بدون رصيد',
                user=self.user,
            )


# ══════════════════════════════════════════════════════
# اختبارات المصروفات الدورية
# ══════════════════════════════════════════════════════

class RecurringExpenseTest(TestCase):
    """اختبار توليد المصروفات الدورية"""

    def setUp(self):
        _setup_base(self)

    def test_generate_recurring_expenses(self):
        """توليد مصروفات دورية مستحقة"""
        today = timezone.now().date()
        RecurringExpense.objects.create(
            name='إيجار شهري',
            category=self.category,
            branch=self.branch,
            amount=Decimal('1000.00'),
            frequency='monthly',
            start_date=today,
            next_due_date=today,
            auto_approve=False,
            is_active=True,
        )
        generated = ExpenseEngine.generate_recurring_expenses(user=self.user)
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated[0].amount, Decimal('1000.00'))
        self.assertEqual(generated[0].status, 'draft')

    def test_generate_recurring_auto_approve(self):
        """توليد مصروف دوري مع الاعتماد التلقائي"""
        today = timezone.now().date()
        RecurringExpense.objects.create(
            name='كهرباء',
            category=self.category,
            branch=self.branch,
            amount=Decimal('200.00'),
            frequency='monthly',
            start_date=today,
            next_due_date=today,
            auto_approve=True,
            is_active=True,
        )
        generated = ExpenseEngine.generate_recurring_expenses(user=self.user)
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated[0].status, 'paid')


# ══════════════════════════════════════════════════════
# اختبارات الصفحات
# ══════════════════════════════════════════════════════

class ExpensesViewsTest(TestCase):
    """اختبار أن الصفحات ترجع 200"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='view_tester', password='test123',
        )
        self.client.force_login(self.user)

        self.branch = Branch.objects.create(
            name='فرع اختبار الصفحات', branch_type='owned', governorate='القاهرة',
        )
        FiscalYear.objects.create(
            name='2026_views', start_date='2026-01-01', end_date='2026-12-31',
            is_active=True, is_closed=False,
        )
        _create_accounts()

        expense_account = Account.objects.get(code='612')
        self.category = ExpenseCategory.objects.create(
            name='إيجارات اختبار', account=expense_account, is_active=True,
        )
        self.expense = ExpenseEngine.create_expense(
            category=self.category,
            branch=self.branch,
            description='اختبار صفحات',
            amount=Decimal('100.00'),
            user=self.user,
        )

        debit_acc = Account.objects.get(code='619')
        credit_acc = Account.objects.get(code='1111')
        self.pv = VoucherEngine.create_payment_voucher(
            branch=self.branch,
            beneficiary_type='other',
            amount=Decimal('100.00'),
            description='سند صرف اختبار',
            debit_account=debit_acc,
            credit_account=credit_acc,
            user=self.user,
        )
        self.rv = VoucherEngine.create_receipt_voucher(
            branch=self.branch,
            payer_type='other',
            amount=Decimal('100.00'),
            description='سند قبض اختبار',
            debit_account=credit_acc,
            credit_account=Account.objects.get(code='1121'),
            user=self.user,
        )
        petty_account = Account.objects.get(code='1111')
        self.petty_cash = PettyCash.objects.create(
            name='عهدة اختبار الصفحات',
            branch=self.branch,
            custodian=self.user,
            limit_amount=Decimal('500.00'),
            current_balance=Decimal('0'),
            account=petty_account,
            is_active=True,
        )

    def _get_200(self, url):
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302],
                      msg=f'URL {url} returned {response.status_code}')

    def test_expense_list(self):
        self._get_200('/expenses/')

    def test_expense_create(self):
        self._get_200('/expenses/create/')

    def test_expense_detail(self):
        self._get_200(f'/expenses/{self.expense.pk}/')

    def test_pv_list(self):
        self._get_200('/expenses/payment-vouchers/')

    def test_pv_create(self):
        self._get_200('/expenses/payment-vouchers/create/')

    def test_pv_detail(self):
        self._get_200(f'/expenses/payment-vouchers/{self.pv.pk}/')

    def test_pv_print(self):
        self._get_200(f'/expenses/payment-vouchers/{self.pv.pk}/print/')

    def test_rv_list(self):
        self._get_200('/expenses/receipt-vouchers/')

    def test_rv_create(self):
        self._get_200('/expenses/receipt-vouchers/create/')

    def test_rv_detail(self):
        self._get_200(f'/expenses/receipt-vouchers/{self.rv.pk}/')

    def test_rv_print(self):
        self._get_200(f'/expenses/receipt-vouchers/{self.rv.pk}/print/')

    def test_petty_cash_list(self):
        self._get_200('/expenses/petty-cash/')

    def test_petty_cash_detail(self):
        self._get_200(f'/expenses/petty-cash/{self.petty_cash.pk}/')

    def test_petty_cash_replenish(self):
        self._get_200(f'/expenses/petty-cash/{self.petty_cash.pk}/replenish/')

    def test_petty_cash_spend(self):
        self._get_200(f'/expenses/petty-cash/{self.petty_cash.pk}/spend/')

    def test_recurring_list(self):
        self._get_200('/expenses/recurring/')

    def test_recurring_create(self):
        self._get_200('/expenses/recurring/create/')

    def test_budget_report(self):
        self._get_200('/expenses/budget/')


# ══════════════════════════════════════════════════════
# اختبار تقرير الميزانية
# ══════════════════════════════════════════════════════

class BudgetReportTest(TestCase):
    """اختبار تقرير الميزانية"""

    def setUp(self):
        _setup_base(self)
        self.category.budget_monthly = Decimal('1000.00')
        self.category.save()

    def test_budget_vs_actual(self):
        """اختبار حساب الوفر"""
        ExpenseEngine.create_expense(
            category=self.category,
            branch=self.branch,
            description='مصروف اختبار الميزانية',
            amount=Decimal('400.00'),
            user=self.user,
        )
        # المبلغ الفعلي 400 من ميزانية 1000 — الوفر 600
        today = timezone.now().date()
        from django.db.models import Sum
        actual = Expense.objects.filter(
            category=self.category,
            date__year=today.year,
            date__month=today.month,
            status__in=['approved', 'paid'],
        ).aggregate(s=Sum('total'))['s'] or Decimal('0')
        # المصروف في حالة draft لا يُحسب في الوفر
        self.assertEqual(actual, Decimal('0'))
