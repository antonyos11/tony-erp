"""
Unit tests for Accounting models.

Tests cover:
- Account model (balance calculation, hierarchy)
- JournalEntry model (validation, posting)
- JournalEntryItem model
- CostCenter model
- FiscalYear model

Priority: P0 - Critical (Financial Integrity)
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounting.models import (
    Account, JournalEntry, JournalEntryItem, CostCenter, FiscalYear
)
from tests.factories import (
    AccountFactory, JournalEntryFactory, JournalEntryItemFactory,
    CostCenterFactory, FiscalYearFactory, UserFactory,
    create_balanced_journal_entry
)
from tests.utils import assert_decimal_equal, assert_journal_entry_balanced


# ============================================================================
# Account Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.p0
class TestAccountModel:
    """Tests for Account model."""
    
    def test_create_account(self):
        """Test creating a basic account."""
        account = AccountFactory(
            code='1000',
            name='Assets',
            account_type='asset'
        )
        
        assert account.code == '1000'
        assert account.name == 'Assets'
        assert account.account_type == 'asset'
        assert account.is_active is True
    
    def test_account_code_unique(self):
        """Test that account code must be unique."""
        AccountFactory(code='1000')
        
        with pytest.raises(IntegrityError):
            AccountFactory(code='1000')
    
    def test_account_hierarchy(self):
        """Test account parent-child hierarchy."""
        parent = AccountFactory(
            code='1000',
            name='Assets',
            is_group=True,
            parent=None
        )
        
        child = AccountFactory(
            code='1001',
            name='Cash',
            parent=parent,
            is_group=False
        )
        
        assert child.parent == parent
        assert child.level == parent.level + 1
        assert parent.code in child.path
    
    def test_account_balance_calculation_asset(self):
        """Test balance calculation for asset accounts (debit - credit)."""
        account = AccountFactory(
            code='1001',
            name='Cash',
            account_type='asset',
            can_post=True
        )
        
        # Create balanced journal entry
        entry = JournalEntryFactory(is_posted=True)
        
        # Debit cash (increase asset)
        JournalEntryItemFactory(
            journal_entry=entry,
            account=account,
            type='debit',
            amount=Decimal('1000.00')
        )
        
        # Credit revenue
        revenue_account = AccountFactory(account_type='revenue', can_post=True)
        JournalEntryItemFactory(
            journal_entry=entry,
            account=revenue_account,
            type='credit',
            amount=Decimal('1000.00')
        )
        
        # For assets: balance = debits - credits
        assert_decimal_equal(account.balance, Decimal('1000.00'))
    
    def test_account_balance_calculation_liability(self):
        """Test balance calculation for liability accounts (credit - debit)."""
        account = AccountFactory(
            code='2001',
            name='Accounts Payable',
            account_type='liability',
            can_post=True
        )
        
        entry = JournalEntryFactory(is_posted=True)
        
        # Credit liability (increase)
        JournalEntryItemFactory(
            journal_entry=entry,
            account=account,
            type='credit',
            amount=Decimal('5000.00')
        )
        
        # Debit expense
        expense_account = AccountFactory(account_type='expense', can_post=True)
        JournalEntryItemFactory(
            journal_entry=entry,
            account=expense_account,
            type='debit',
            amount=Decimal('5000.00')
        )
        
        # For liabilities: balance = credits - debits
        assert_decimal_equal(account.balance, Decimal('5000.00'))
    
    def test_account_balance_with_multiple_entries(self):
        """Test account balance with multiple journal entries."""
        account = AccountFactory(
            code='1001',
            name='Cash',
            account_type='asset',
            can_post=True
        )
        
        revenue = AccountFactory(account_type='revenue', can_post=True)
        
        # Entry 1: Debit cash 1000
        entry1 = JournalEntryFactory(is_posted=True)
        JournalEntryItemFactory(
            journal_entry=entry1,
            account=account,
            type='debit',
            amount=Decimal('1000.00')
        )
        JournalEntryItemFactory(
            journal_entry=entry1,
            account=revenue,
            type='credit',
            amount=Decimal('1000.00')
        )
        
        # Entry 2: Credit cash 300
        entry2 = JournalEntryFactory(is_posted=True)
        expense = AccountFactory(account_type='expense', can_post=True)
        JournalEntryItemFactory(
            journal_entry=entry2,
            account=expense,
            type='debit',
            amount=Decimal('300.00')
        )
        JournalEntryItemFactory(
            journal_entry=entry2,
            account=account,
            type='credit',
            amount=Decimal('300.00')
        )
        
        # Cash balance = 1000 - 300 = 700
        assert_decimal_equal(account.balance, Decimal('700.00'))
    
    def test_account_str_representation(self):
        """Test string representation of account."""
        account = AccountFactory(code='1001', name='Cash')
        assert '1001' in str(account)
        assert 'Cash' in str(account)


# ============================================================================
# JournalEntry Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.p0
class TestJournalEntryModel:
    """Tests for JournalEntry model."""
    
    def test_create_journal_entry(self, admin_user):
        """Test creating a journal entry."""
        entry = JournalEntryFactory(
            date=date.today(),
            entry_type='manual',
            description='Test entry',
            created_by=admin_user
        )
        
        assert entry.date == date.today()
        assert entry.entry_type == 'manual'
        assert entry.is_posted is False
        assert entry.number is not None  # Auto-generated
    
    def test_journal_entry_number_auto_generation(self):
        """Test that journal entry numbers are auto-generated."""
        entry1 = JournalEntryFactory()
        entry2 = JournalEntryFactory()
        
        assert entry1.number is not None
        assert entry2.number is not None
        assert entry1.number != entry2.number
    
    def test_journal_entry_number_format(self):
        """Test journal entry number format (JE-YYYY-NNNNNN)."""
        entry = JournalEntryFactory()
        
        assert entry.number.startswith('JE-')
        assert str(date.today().year) in entry.number
    
    def test_balanced_journal_entry_validation(self):
        """Test that balanced journal entries pass validation."""
        entry = create_balanced_journal_entry(
            amount=Decimal('1000.00')
        )
        
        # Should not raise ValidationError
        entry.clean()
        assert_journal_entry_balanced(entry)
    
    def test_unbalanced_journal_entry_validation(self):
        """Test that unbalanced journal entries fail validation."""
        debit_account = AccountFactory(account_type='asset', can_post=True)
        credit_account = AccountFactory(account_type='revenue', can_post=True)
        
        entry = JournalEntryFactory()
        
        # Debit 1000
        JournalEntryItemFactory(
            journal_entry=entry,
            account=debit_account,
            type='debit',
            amount=Decimal('1000.00')
        )
        
        # Credit 500 (unbalanced!)
        JournalEntryItemFactory(
            journal_entry=entry,
            account=credit_account,
            type='credit',
            amount=Decimal('500.00')
        )
        
        # Should raise ValidationError
        with pytest.raises(ValidationError, match='balanced'):
            entry.clean()
    
    def test_journal_entry_posting(self):
        """Test posting a journal entry."""
        entry = create_balanced_journal_entry(amount=Decimal('1000.00'))
        
        assert entry.is_posted is False
        
        # Post the entry
        entry.is_posted = True
        entry.save()
        
        assert entry.is_posted is True
    
    def test_journal_entry_total_debit(self):
        """Test calculating total debit of journal entry."""
        entry = JournalEntryFactory()
        
        JournalEntryItemFactory(
            journal_entry=entry,
            type='debit',
            amount=Decimal('500.00')
        )
        JournalEntryItemFactory(
            journal_entry=entry,
            type='debit',
            amount=Decimal('300.00')
        )
        
        total_debit = entry.total_debit
        assert_decimal_equal(total_debit, Decimal('800.00'))
    
    def test_journal_entry_total_credit(self):
        """Test calculating total credit of journal entry."""
        entry = JournalEntryFactory()
        
        JournalEntryItemFactory(
            journal_entry=entry,
            type='credit',
            amount=Decimal('600.00')
        )
        JournalEntryItemFactory(
            journal_entry=entry,
            type='credit',
            amount=Decimal('400.00')
        )
        
        total_credit = entry.total_credit
        assert_decimal_equal(total_credit, Decimal('1000.00'))


# ============================================================================
# JournalEntryItem Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.p0
class TestJournalEntryItemModel:
    """Tests for JournalEntryItem model."""
    
    def test_create_journal_entry_item(self):
        """Test creating a journal entry item."""
        entry = JournalEntryFactory()
        account = AccountFactory(can_post=True)
        
        item = JournalEntryItemFactory(
            journal_entry=entry,
            account=account,
            type='debit',
            amount=Decimal('500.00')
        )
        
        assert item.journal_entry == entry
        assert item.account == account
        assert item.type == 'debit'
        assert_decimal_equal(item.amount, Decimal('500.00'))
    
    def test_journal_entry_item_requires_positive_amount(self):
        """Test that amount must be positive."""
        # This should be validated at the model level
        item = JournalEntryItemFactory.build(amount=Decimal('-100.00'))
        
        with pytest.raises(ValidationError):
            item.full_clean()


# ============================================================================
# CostCenter Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.p0
class TestCostCenterModel:
    """Tests for CostCenter model."""
    
    def test_create_cost_center(self, admin_user):
        """Test creating a cost center."""
        cost_center = CostCenterFactory(
            code='CC001',
            name='Production',
            manager=admin_user
        )
        
        assert cost_center.code == 'CC001'
        assert cost_center.name == 'Production'
        assert cost_center.manager == admin_user
        assert cost_center.is_active is True
    
    def test_cost_center_code_unique(self):
        """Test that cost center code must be unique."""
        CostCenterFactory(code='CC001')
        
        with pytest.raises(IntegrityError):
            CostCenterFactory(code='CC001')
    
    def test_cost_center_hierarchy(self):
        """Test cost center parent-child relationship."""
        parent = CostCenterFactory(code='CC001', name='Operations')
        child = CostCenterFactory(
            code='CC002',
            name='Production',
            parent=parent
        )
        
        assert child.parent == parent


# ============================================================================
# FiscalYear Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.p0
class TestFiscalYearModel:
    """Tests for FiscalYear model."""
    
    def test_create_fiscal_year(self, admin_user):
        """Test creating a fiscal year."""
        fiscal_year = FiscalYearFactory(
            name='2026',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_active=True,
            created_by=admin_user
        )
        
        assert fiscal_year.name == '2026'
        assert fiscal_year.start_date == date(2026, 1, 1)
        assert fiscal_year.end_date == date(2026, 12, 31)
        assert fiscal_year.is_active is True
    
    def test_fiscal_year_date_validation(self):
        """Test that end_date must be after start_date."""
        fiscal_year = FiscalYearFactory.build(
            start_date=date(2026, 12, 31),
            end_date=date(2026, 1, 1)  # Before start!
        )
        
        with pytest.raises(ValidationError):
            fiscal_year.full_clean()
    
    def test_only_one_active_fiscal_year(self):
        """Test that only one fiscal year can be active at a time."""
        FiscalYearFactory(name='2025', is_active=True)
        
        # Creating another active fiscal year should deactivate the first
        fiscal_year_2026 = FiscalYearFactory(name='2026', is_active=True)
        
        # Re-fetch from database
        from accounting.models import FiscalYear
        active_years = FiscalYear.objects.filter(is_active=True)
        
        # Only one should be active
        assert active_years.count() <= 1
