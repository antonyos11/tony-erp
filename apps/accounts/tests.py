"""
اختبارات تطبيق المحاسبة — RITA ERP
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from decimal import Decimal
from apps.accounts.models import Account, FiscalYear, JournalEntry, CostCenter
from apps.accounts.services.journal_engine import JournalEngine
from apps.accounts.services.vat_engine import VATEngine
from apps.core.models import Branch

User = get_user_model()


class ChartOfAccountsTest(TestCase):
    """اختبار دليل الحسابات"""

    def test_account_creation(self):
        """إنشاء حساب تجريبي"""
        account = Account.objects.create(
            code='9999', name='حساب تجريبي', account_type='asset',
            nature='debit', is_detail=True
        )
        self.assertEqual(account.code, '9999')

    def test_parent_child_relationship(self):
        """علاقة الأب والابن بين الحسابات"""
        parent = Account.objects.create(
            code='8000', name='حساب رئيسي', account_type='asset',
            nature='debit', is_detail=False
        )
        child = Account.objects.create(
            code='8001', name='حساب فرعي', account_type='asset',
            nature='debit', is_detail=True, parent=parent
        )
        self.assertEqual(child.parent, parent)


class JournalEngineTest(TestCase):
    """اختبار محرك القيود"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.branch = Branch.objects.create(
            name='فرع تجريبي', branch_type='owned', governorate='القاهرة'
        )
        self.fiscal_year = FiscalYear.objects.create(
            name='2026', start_date='2026-01-01', end_date='2026-12-31',
            is_active=True, is_closed=False
        )
        # إنشاء حسابات تجريبية
        Account.objects.create(code='1111', name='الخزينة', account_type='asset',
                               nature='debit', is_detail=True, is_system=True)
        Account.objects.create(code='411', name='مبيعات قطاعي', account_type='revenue',
                               nature='credit', is_detail=True, is_system=True)
        Account.objects.create(code='213', name='ضريبة مبيعات', account_type='liability',
                               nature='credit', is_detail=True, is_system=True)

    def test_balanced_entry_creation(self):
        """قيد متوازن يُنشأ بنجاح"""
        entry = JournalEngine.create_entry(
            source='manual',
            description='قيد تجريبي',
            branch=self.branch,
            lines_data=[
                {'account_code': '1111', 'debit': 1000, 'credit': 0},
                {'account_code': '411',  'debit': 0,    'credit': 877.19},
                {'account_code': '213',  'debit': 0,    'credit': 122.81},
            ],
            user=self.user,
        )
        self.assertEqual(entry.total_debit, Decimal('1000'))
        self.assertEqual(entry.total_credit, Decimal('1000'))
        self.assertEqual(entry.lines.count(), 3)

    def test_unbalanced_entry_fails(self):
        """قيد غير متوازن يفشل"""
        with self.assertRaises(ValueError):
            JournalEngine.create_entry(
                source='manual',
                description='قيد غير متوازن',
                branch=self.branch,
                lines_data=[
                    {'account_code': '1111', 'debit': 1000, 'credit': 0},
                    {'account_code': '411',  'debit': 0,    'credit': 500},
                ],
                user=self.user,
            )

    def test_zero_entry_fails(self):
        """قيد بقيمة صفر يفشل"""
        with self.assertRaises(ValueError):
            JournalEngine.create_entry(
                source='manual',
                description='قيد صفري',
                branch=self.branch,
                lines_data=[
                    {'account_code': '1111', 'debit': 0, 'credit': 0},
                ],
                user=self.user,
            )


class VATEngineTest(TestCase):
    """اختبار محرك الضريبة"""

    def test_calculate_tax_exclusive(self):
        """حساب ضريبة على مبلغ غير شامل الضريبة"""
        result = VATEngine.calculate_tax(1000)
        self.assertEqual(result['amount_before_tax'], Decimal('1000'))
        self.assertEqual(result['tax_amount'], Decimal('140'))
        self.assertEqual(result['total'], Decimal('1140'))

    def test_calculate_tax_inclusive(self):
        """حساب ضريبة على مبلغ شامل الضريبة"""
        result = VATEngine.calculate_tax(1140, price_includes_tax=True)
        self.assertEqual(result['amount_before_tax'], Decimal('1000'))
        self.assertEqual(result['tax_amount'], Decimal('140'))


class AccountsViewsTest(TestCase):
    """اختبار صفحات المحاسبة"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='testuser', password='test123'
        )
        self.client.login(username='testuser', password='test123')

    def test_chart_of_accounts_page(self):
        """صفحة دليل الحسابات تستجيب 200"""
        response = self.client.get('/accounts/')
        self.assertEqual(response.status_code, 200)

    def test_journal_list_page(self):
        """صفحة قائمة القيود تستجيب 200"""
        response = self.client.get('/accounts/journals/')
        self.assertEqual(response.status_code, 200)

    def test_trial_balance_page(self):
        """صفحة ميزان المراجعة تستجيب 200"""
        response = self.client.get('/accounts/reports/trial-balance/')
        self.assertEqual(response.status_code, 200)

    def test_income_statement_page(self):
        """صفحة قائمة الدخل تستجيب 200"""
        response = self.client.get('/accounts/reports/income-statement/')
        self.assertEqual(response.status_code, 200)

    def test_balance_sheet_page(self):
        """صفحة المركز المالي تستجيب 200"""
        response = self.client.get('/accounts/reports/balance-sheet/')
        self.assertEqual(response.status_code, 200)
