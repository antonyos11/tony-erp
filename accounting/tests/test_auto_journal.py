"""
اختبارات ميزة القيد المحاسبي التلقائي للإيرادات والمصروفات
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from accounting.models import (
    Account, AccountEntry, JournalEntry, 
    AccountingSettings, Treasury
)
from core.integration_services import AccountingIntegrationService

User = get_user_model()


class AutoJournalEntryTest(TestCase):
    """اختبار القيود المحاسبية التلقائية"""
    
    def setUp(self):
        """إعداد بيئة الاختبار"""
        self.user = User.objects.create_user('testuser', 'test@test.com', 'password123')
        
        # إنشاء الحسابات المطلوبة
        self.revenue_account = Account.objects.create(
            code='4000',
            name='إيرادات متنوعة',
            account_type='revenue',
            is_active=True,
            can_post=True
        )
        
        self.expense_account = Account.objects.create(
            code='5000',
            name='مصروفات متنوعة',
            account_type='expense',
            is_active=True,
            can_post=True
        )
        
        self.cash_account = Account.objects.create(
            code='1001',
            name='الخزينة الرئيسية',
            account_type='asset',
            is_active=True,
            can_post=True
        )
        
        # إعداد إعدادات المحاسبة
        settings = AccountingSettings.get()
        settings.auto_create_journal_entries = True
        settings.misc_revenue_account = self.revenue_account
        settings.misc_expense_account = self.expense_account
        settings.default_treasury_account = self.cash_account
        settings.save()
        
        # إنشاء خزينة
        self.treasury = Treasury.objects.create(
            name='الخزينة الرئيسية',
            code='TR001',
            is_active=True
        )
        # ربط الخزينة بالحساب (إذا كان النموذج يدعم ذلك)
        if hasattr(self.treasury, 'account'):
            self.treasury.account = self.cash_account
            self.treasury.save()
    
    def test_auto_journal_for_revenue(self):
        """اختبار إنشاء قيد تلقائي للإيراد"""
        # إنشاء إيراد
        entry = AccountEntry.objects.create(
            entry_type='revenue',
            date='2026-01-18',
            amount=Decimal('1000.00'),
            description='إيراد اختباري',
            ledger_account=self.revenue_account,
            destination_type='treasury',
            treasury=self.treasury,
            created_by=self.user
        )
        
        # إنشاء القيد التلقائي
        journal_entry = AccountingIntegrationService.create_revenue_expense_journal_entry(
            entry, self.user
        )
        
        # التحقق من إنشاء القيد
        self.assertIsNotNone(journal_entry, "يجب إنشاء قيد محاسبي")
        self.assertEqual(journal_entry.entry_type, 'revenue', "نوع القيد يجب أن يكون إيراد")
        self.assertTrue(journal_entry.is_posted, "القيد يجب أن يكون مرحّلاً")
        
        # التحقق من البنود
        items = journal_entry.items.all()
        self.assertEqual(items.count(), 2, "يجب وجود بندين في القيد")
        
        debit_item = items.filter(type='debit').first()
        credit_item = items.filter(type='credit').first()
        
        self.assertIsNotNone(debit_item, "يجب وجود بند مدين")
        self.assertIsNotNone(credit_item, "يجب وجود بند دائن")
        
        self.assertEqual(debit_item.account, self.cash_account, "البند المدين يجب أن يكون الخزينة")
        self.assertEqual(debit_item.amount, Decimal('1000.00'), "المبلغ المدين يجب أن يكون 1000")
        
        self.assertEqual(credit_item.account, self.revenue_account, "البند الدائن يجب أن يكون الإيراد")
        self.assertEqual(credit_item.amount, Decimal('1000.00'), "المبلغ الدائن يجب أن يكون 1000")
        
        # التحقق من ربط القيد بالإيراد
        entry.refresh_from_db()
        self.assertEqual(entry.journal_entry, journal_entry, "يجب ربط القيد بسجل الإيراد")
    
    def test_auto_journal_for_expense(self):
        """اختبار إنشاء قيد تلقائي للمصروف"""
        # إنشاء مصروف
        entry = AccountEntry.objects.create(
            entry_type='expense',
            date='2026-01-18',
            amount=Decimal('500.00'),
            description='مصروف اختباري',
            ledger_account=self.expense_account,
            destination_type='treasury',
            treasury=self.treasury,
            created_by=self.user
        )
        
        # إنشاء القيد التلقائي
        journal_entry = AccountingIntegrationService.create_revenue_expense_journal_entry(
            entry, self.user
        )
        
        # التحقق من إنشاء القيد
        self.assertIsNotNone(journal_entry, "يجب إنشاء قيد محاسبي")
        self.assertEqual(journal_entry.entry_type, 'expense', "نوع القيد يجب أن يكون مصروف")
        
        # التحقق من البنود
        items = journal_entry.items.all()
        debit_item = items.filter(type='debit').first()
        credit_item = items.filter(type='credit').first()
        
        self.assertEqual(debit_item.account, self.expense_account, "البند المدين يجب أن يكون المصروف")
        self.assertEqual(debit_item.amount, Decimal('500.00'))
        
        self.assertEqual(credit_item.account, self.cash_account, "البند الدائن يجب أن يكون الخزينة")
        self.assertEqual(credit_item.amount, Decimal('500.00'))
    
    def test_disabled_auto_journal(self):
        """اختبار عدم إنشاء قيد عند تعطيل الميزة"""
        # تعطيل الميزة
        settings = AccountingSettings.get()
        settings.auto_create_journal_entries = False
        settings.save()
        
        # إنشاء إيراد
        entry = AccountEntry.objects.create(
            entry_type='revenue',
            amount=Decimal('1000.00'),
            description='إيراد اختباري',
            created_by=self.user
        )
        
        # محاولة إنشاء القيد
        journal_entry = AccountingIntegrationService.create_revenue_expense_journal_entry(
            entry, self.user
        )
        
        # التحقق من عدم إنشاء القيد
        self.assertIsNone(journal_entry, "يجب عدم إنشاء قيد عند تعطيل الميزة")
    
    def test_journal_balance(self):
        """اختبار توازن القيد المحاسبي"""
        entry = AccountEntry.objects.create(
            entry_type='revenue',
            amount=Decimal('1500.00'),
            description='إيراد للتحقق من التوازن',
            ledger_account=self.revenue_account,
            destination_type='treasury',
            treasury=self.treasury,
            created_by=self.user
        )
        
        journal_entry = AccountingIntegrationService.create_revenue_expense_journal_entry(
            entry, self.user
        )
        
        # حساب إجمالي المدين والدائن
        total_debit = sum(item.amount for item in journal_entry.items.filter(type='debit'))
        total_credit = sum(item.amount for item in journal_entry.items.filter(type='credit'))
        
        self.assertEqual(total_debit, total_credit, "القيد يجب أن يكون متوازناً")
        self.assertEqual(total_debit, Decimal('1500.00'))
