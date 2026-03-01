"""
اختبارات Sprint 8 — الخزينة والبنوك والأقساط
RITA ERP
"""
from decimal import Decimal
from datetime import date

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.models import Account, FiscalYear
from apps.core.models import Branch, Warehouse
from apps.treasury.models import BankAccount, CashBox, Check, MoneyTransfer
from apps.treasury.services.treasury_engine import TreasuryEngine
from apps.treasury.services.check_engine import CheckEngine
from apps.sales.models import Customer, SalesInvoice
from apps.installments.models import InstallmentPlan, Installment
from apps.installments.services.installment_engine import InstallmentEngine

User = get_user_model()


# ══════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════

def _make_account(code, name, atype, nature):
    acc, _ = Account.objects.get_or_create(
        code=code,
        defaults=dict(name=name, account_type=atype, nature=nature,
                      is_detail=True, is_system=True),
    )
    return acc


def _make_fiscal_year():
    fy, _ = FiscalYear.objects.get_or_create(
        name='FY-TEST',
        defaults=dict(
            start_date='2025-01-01', end_date='2026-12-31',
            is_active=True, is_closed=False,
        ),
    )
    return fy


def _base_setup():
    """إعداد مشترك: فرع، مخزن، سنة مالية، حسابات"""
    branch = Branch.objects.create(name='فرع اختبار', branch_type='owned')
    warehouse = Warehouse.objects.create(name='مخزن اختبار', branch=branch)
    fy     = _make_fiscal_year()
    cash_acc = _make_account('1110', 'الخزنة',   'asset', 'debit')
    bank_acc = _make_account('1120', 'البنك',    'asset', 'debit')
    return branch, warehouse, fy, cash_acc, bank_acc


# ══════════════════════════════════════════════════════
# Test: عمليات الخزنة
# ══════════════════════════════════════════════════════

class CashBoxOperationsTest(TestCase):
    """اختبار إيداع وسحب من خزنة"""

    def setUp(self):
        self.branch, _, self.fy, self.cash_acc, _ = _base_setup()
        self.user = User.objects.create_user(username='treas_user', password='x')
        self.cashbox = CashBox.objects.create(
            name='خزنة رئيسية',
            branch=self.branch,
            account=self.cash_acc,
            responsible=self.user,
        )

    def test_deposit_increases_balance(self):
        """الإيداع يزيد رصيد الخزنة"""
        TreasuryEngine.deposit_to_cashbox(
            self.cashbox, amount=500, description='إيداع اختبار',
            branch=self.branch, user=self.user,
        )
        self.cashbox.refresh_from_db()
        self.assertEqual(self.cashbox.current_balance, Decimal('500'))

    def test_withdraw_decreases_balance(self):
        """السحب يخفض رصيد الخزنة"""
        # إيداع أولاً
        TreasuryEngine.deposit_to_cashbox(
            self.cashbox, amount=1000, description='إيداع',
            branch=self.branch, user=self.user,
        )
        TreasuryEngine.withdraw_from_cashbox(
            self.cashbox, amount=300, description='سحب اختبار',
            branch=self.branch, user=self.user,
        )
        self.cashbox.refresh_from_db()
        self.assertEqual(self.cashbox.current_balance, Decimal('700'))

    def test_withdraw_insufficient_funds_raises(self):
        """السحب بمبلغ أكبر من الرصيد يرفع استثناء"""
        with self.assertRaises(ValueError):
            TreasuryEngine.withdraw_from_cashbox(
                self.cashbox, amount=999999, description='سحب فاشل',
                branch=self.branch, user=self.user,
            )

    def test_zero_amount_raises(self):
        """مبلغ صفر يرفع استثناء"""
        with self.assertRaises(ValueError):
            TreasuryEngine.deposit_to_cashbox(
                self.cashbox, amount=0, description='اختبار',
                branch=self.branch, user=self.user,
            )


# ══════════════════════════════════════════════════════
# Test: تحويل بين بنوك
# ══════════════════════════════════════════════════════

class BankTransferTest(TestCase):
    """اختبار التحويل بين حسابات بنكية"""

    def setUp(self):
        self.branch, _, self.fy, _, self.bank_acc = _base_setup()
        self.user = User.objects.create_user(username='bank_user', password='x')

        bank_acc_2 = _make_account('1121', 'البنك 2', 'asset', 'debit')

        self.bank_a = BankAccount.objects.create(
            name='بنك أ', account_number='001',
            branch=self.branch, account=self.bank_acc,
            current_balance=Decimal('5000'),
        )
        self.bank_b = BankAccount.objects.create(
            name='بنك ب', account_number='002',
            branch=self.branch, account=bank_acc_2,
            current_balance=Decimal('1000'),
        )

    def test_bank_to_bank_transfer(self):
        """التحويل من بنك إلى بنك يعدّل الأرصدة بشكل صحيح"""
        TreasuryEngine.transfer(
            from_obj=self.bank_a, from_type='bank',
            to_obj=self.bank_b,   to_type='bank',
            amount=Decimal('2000'), notes='تحويل اختبار',
            branch=self.branch, user=self.user,
        )
        self.bank_a.refresh_from_db()
        self.bank_b.refresh_from_db()
        self.assertEqual(self.bank_a.current_balance, Decimal('3000'))
        self.assertEqual(self.bank_b.current_balance, Decimal('3000'))

    def test_transfer_creates_money_transfer_record(self):
        """التحويل ينشئ سجل MoneyTransfer"""
        count_before = MoneyTransfer.objects.count()
        TreasuryEngine.transfer(
            from_obj=self.bank_a, from_type='bank',
            to_obj=self.bank_b,   to_type='bank',
            amount=Decimal('500'), notes='',
            branch=self.branch, user=self.user,
        )
        self.assertEqual(MoneyTransfer.objects.count(), count_before + 1)


# ══════════════════════════════════════════════════════
# Test: الشيكات
# ══════════════════════════════════════════════════════

class CheckEngineTest(TestCase):
    """اختبار شيكات وارد وصادر"""

    def setUp(self):
        self.branch, _, self.fy, _, self.bank_acc = _base_setup()
        self.user = User.objects.create_user(username='check_user', password='x')
        self.bank = BankAccount.objects.create(
            name='بنك الشيكات', account_number='555',
            branch=self.branch, account=self.bank_acc,
            current_balance=Decimal('10000'),
        )

    def _make_check(self, check_type='incoming'):
        return CheckEngine.create_check(
            check_number='CHK-001', check_type=check_type,
            bank=self.bank, amount=Decimal('1500'),
            issue_date=date(2026, 1, 1), due_date=date(2026, 3, 1),
            partner_name='عميل اختبار', user=self.user,
        )

    def test_create_incoming_check(self):
        """إنشاء شيك وارد بحالة pending"""
        check = self._make_check('incoming')
        self.assertEqual(check.check_type, 'incoming')
        self.assertEqual(check.status, 'pending')

    def test_create_outgoing_check(self):
        """إنشاء شيك صادر"""
        check = self._make_check('outgoing')
        self.assertEqual(check.check_type, 'outgoing')

    def test_deposit_check(self):
        """إيداع شيك يغير حالته إلى deposited"""
        check = self._make_check()
        CheckEngine.deposit_check(check, branch=self.branch, user=self.user)
        check.refresh_from_db()
        self.assertEqual(check.status, 'deposited')

    def test_clear_incoming_check_increases_bank_balance(self):
        """تحصيل شيك وارد يزيد رصيد البنك"""
        check = self._make_check('incoming')
        balance_before = self.bank.current_balance
        CheckEngine.clear_check(check, branch=self.branch, user=self.user)
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.current_balance, balance_before + Decimal('1500'))

    def test_bounce_check(self):
        """ارتجاع شيك يغير حالته إلى bounced"""
        check = self._make_check()
        CheckEngine.bounce_check(check, branch=self.branch, notes='مرتجع', user=self.user)
        check.refresh_from_db()
        self.assertEqual(check.status, 'bounced')

    def test_cannot_deposit_cleared_check(self):
        """لا يمكن إيداع شيك تم تحصيله"""
        check = self._make_check()
        CheckEngine.clear_check(check, branch=self.branch, user=self.user)
        with self.assertRaises(ValueError):
            CheckEngine.deposit_check(check, branch=self.branch, user=self.user)


# ══════════════════════════════════════════════════════
# Test: خطة الأقساط
# ══════════════════════════════════════════════════════

class InstallmentEngineTest(TestCase):
    """اختبار إنشاء خطة أقساط وتسجيل دفعة"""

    def setUp(self):
        self.branch, self.warehouse, self.fy, _, _ = _base_setup()
        self.user = User.objects.create_user(username='inst_user', password='x')
        self.customer = Customer.objects.create(
            code='CUST-01', name='عميل الأقساط', customer_type='retail',
        )
        self.invoice = SalesInvoice.objects.create(
            invoice_number='INV-TEST-001',
            date='2026-01-01 00:00:00',
            customer=self.customer,
            branch=self.branch,
            warehouse=self.warehouse,
            status='confirmed',
            subtotal=Decimal('10000'),
            discount_amount=Decimal('0'),
            tax_amount=Decimal('0'),
            total=Decimal('10000'),
        )

    def test_create_plan_generates_installments(self):
        """إنشاء خطة أقساط يولّد عدد الأقساط الصحيح"""
        plan = InstallmentEngine.create_plan(
            invoice=self.invoice,
            customer=self.customer,
            total_amount=Decimal('10000'),
            down_payment=Decimal('2000'),
            number_of_installments=4,
            interest_rate=Decimal('0'),
            start_date=date(2026, 2, 1),
            user=self.user,
        )
        self.assertEqual(plan.number_of_installments, 4)
        self.assertEqual(plan.installments.count(), 4)

    def test_installment_due_dates_are_monthly(self):
        """تواريخ الأقساط شهرية بالتسلسل"""
        plan = InstallmentEngine.create_plan(
            invoice=self.invoice,
            customer=self.customer,
            total_amount=Decimal('6000'),
            down_payment=Decimal('0'),
            number_of_installments=3,
            interest_rate=Decimal('0'),
            start_date=date(2026, 1, 1),
            user=self.user,
        )
        dates = list(plan.installments.values_list('due_date', flat=True).order_by('installment_number'))
        self.assertEqual(dates[0], date(2026, 1, 1))
        self.assertEqual(dates[1], date(2026, 2, 1))
        self.assertEqual(dates[2], date(2026, 3, 1))

    def test_pay_installment_full(self):
        """تسجيل دفعة كاملة يغير الحالة إلى paid"""
        plan = InstallmentEngine.create_plan(
            invoice=self.invoice,
            customer=self.customer,
            total_amount=Decimal('4000'),
            down_payment=Decimal('0'),
            number_of_installments=2,
            interest_rate=Decimal('0'),
            start_date=date(2026, 1, 1),
            user=self.user,
        )
        first = plan.installments.first()
        InstallmentEngine.pay_installment(
            installment=first,
            paid_amount=first.amount,
            user=self.user,
        )
        first.refresh_from_db()
        self.assertEqual(first.status, 'paid')

    def test_pay_installment_partial(self):
        """دفعة جزئية تضع الحالة partial"""
        plan = InstallmentEngine.create_plan(
            invoice=self.invoice,
            customer=self.customer,
            total_amount=Decimal('2000'),
            down_payment=Decimal('0'),
            number_of_installments=1,
            interest_rate=Decimal('0'),
            start_date=date(2026, 1, 1),
            user=self.user,
        )
        inst = plan.installments.first()
        InstallmentEngine.pay_installment(
            installment=inst, paid_amount=Decimal('500'), user=self.user,
        )
        inst.refresh_from_db()
        self.assertEqual(inst.status, 'partial')
        self.assertEqual(inst.paid_amount, Decimal('500'))

    def test_all_paid_completes_plan(self):
        """دفع جميع الأقساط يضع الخطة بحالة completed"""
        plan = InstallmentEngine.create_plan(
            invoice=self.invoice,
            customer=self.customer,
            total_amount=Decimal('2000'),
            down_payment=Decimal('0'),
            number_of_installments=2,
            interest_rate=Decimal('0'),
            start_date=date(2026, 1, 1),
            user=self.user,
        )
        for inst in plan.installments.all():
            InstallmentEngine.pay_installment(
                installment=inst, paid_amount=inst.amount, user=self.user,
            )
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'completed')

    def test_down_payment_greater_than_total_raises(self):
        """مقدم أكبر من الإجمالي يرفع خطأ"""
        with self.assertRaises(ValueError):
            InstallmentEngine.create_plan(
                invoice=self.invoice,
                customer=self.customer,
                total_amount=Decimal('1000'),
                down_payment=Decimal('2000'),
                number_of_installments=3,
                interest_rate=Decimal('0'),
                start_date=date(2026, 1, 1),
            )


# ══════════════════════════════════════════════════════
# Test: الصفحات (HTTP 200)
# ══════════════════════════════════════════════════════

class TreasuryViewsTest(TestCase):
    """اختبار أن صفحات الخزينة تعيد 200"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='view_user', password='pw')
        self.client.login(username='view_user', password='pw')

    def test_bank_account_list_200(self):
        r = self.client.get(reverse('treasury:bank_account_list'))
        self.assertEqual(r.status_code, 200)

    def test_cashbox_list_200(self):
        r = self.client.get(reverse('treasury:cashbox_list'))
        self.assertEqual(r.status_code, 200)

    def test_check_list_200(self):
        r = self.client.get(reverse('treasury:check_list'))
        self.assertEqual(r.status_code, 200)

    def test_transfer_list_200(self):
        r = self.client.get(reverse('treasury:transfer_list'))
        self.assertEqual(r.status_code, 200)

    def test_transfer_create_200(self):
        r = self.client.get(reverse('treasury:transfer_create'))
        self.assertEqual(r.status_code, 200)

    def test_bank_reconciliation_200(self):
        r = self.client.get(reverse('treasury:bank_reconciliation'))
        self.assertEqual(r.status_code, 200)

    def test_bank_account_create_200(self):
        r = self.client.get(reverse('treasury:bank_account_create'))
        self.assertEqual(r.status_code, 200)

    def test_check_create_200(self):
        r = self.client.get(reverse('treasury:check_create'))
        self.assertEqual(r.status_code, 200)


class InstallmentsViewsTest(TestCase):
    """اختبار أن صفحات الأقساط تعيد 200"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='inst_view', password='pw')
        self.client.login(username='inst_view', password='pw')

    def test_plan_list_200(self):
        r = self.client.get(reverse('installments:plan_list'))
        self.assertEqual(r.status_code, 200)

    def test_plan_create_200(self):
        r = self.client.get(reverse('installments:plan_create'))
        self.assertEqual(r.status_code, 200)

    def test_overdue_list_200(self):
        r = self.client.get(reverse('installments:overdue_list'))
        self.assertEqual(r.status_code, 200)
