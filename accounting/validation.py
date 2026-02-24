"""
Journal Entry Validation Utilities
Advanced server-side validation for accounting operations
"""

from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from typing import List, Dict, Any, Tuple, Optional
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)


class JournalEntryValidator:
    """
    Comprehensive validation class for journal entries
    Handles all business logic and validation rules
    """
    
    def __init__(self, user=None):
        self.user = user
        self.errors = []
        self.warnings = []
        
    def validate_complete_entry(self, entry_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Complete validation of a journal entry
        Returns (is_valid, validation_result)
        """
        self.errors = []
        self.warnings = []
        
        try:
            # Basic structure validation
            self._validate_basic_structure(entry_data)
            
            # Date validation
            self._validate_entry_date(entry_data.get('date'))
            
            # Description validation
            self._validate_description(entry_data.get('description', ''))
            
            # Items validation
            items = entry_data.get('items', [])
            self._validate_items_structure(items)
            
            # Business rules validation
            self._validate_business_rules(entry_data)
            
            # Balance validation
            balance_result = self._validate_balance(items)
            
            # Account validation
            self._validate_accounts(items)
            
            # Amounts validation
            self._validate_amounts(items)
            
            # Duplicate detection
            self._check_duplicates(entry_data)
            
            # Fiscal year validation
            self._validate_fiscal_year(entry_data.get('date'))
            
            # Permission validation
            if self.user:
                self._validate_permissions(entry_data)
            
            return len(self.errors) == 0, {
                'valid': len(self.errors) == 0,
                'errors': self.errors,
                'warnings': self.warnings,
                'balance': balance_result,
                'summary': self._generate_summary(entry_data, balance_result)
            }
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            self.errors.append(_("حدث خطأ غير متوقع في التحقق من صحة القيد"))
            return False, {
                'valid': False,
                'errors': self.errors,
                'warnings': self.warnings
            }
    
    def _validate_basic_structure(self, entry_data: Dict[str, Any]):
        """Validate basic entry structure"""
        required_fields = ['description', 'date', 'items']
        
        for field in required_fields:
            if field not in entry_data:
                self.errors.append(_(f"حقل {field} مطلوب"))
            elif not entry_data[field]:
                self.errors.append(_(f"لا يمكن أن يكون حقل {field} فارغاً"))
    
    def _validate_entry_date(self, entry_date):
        """Validate entry date"""
        if not entry_date:
            self.errors.append(_("تاريخ القيد مطلوب"))
            return
        
        try:
            if isinstance(entry_date, str):
                parsed_date = datetime.strptime(entry_date, '%Y-%m-%d').date()
            elif isinstance(entry_date, datetime):
                parsed_date = entry_date.date()
            elif isinstance(entry_date, date):
                parsed_date = entry_date
            else:
                raise ValueError("Invalid date format")
            
            # Check if date is in the future
            if parsed_date > date.today():
                self.warnings.append(_("تاريخ القيد في المستقبل"))
            
            # Check if date is too old (more than 5 years)
            if (date.today() - parsed_date).days > 1825:
                self.warnings.append(_("تاريخ القيد قديم جداً (أكثر من 5 سنوات)"))
                
        except (ValueError, TypeError):
            self.errors.append(_("تاريخ القيد غير صحيح"))
    
    def _validate_description(self, description: str):
        """Validate entry description"""
        if not description or not description.strip():
            self.errors.append(_("وصف القيد مطلوب"))
            return
        
        if len(description.strip()) < 3:
            self.errors.append(_("وصف القيد قصير جداً (يجب أن يكون 3 أحرف على الأقل)"))
        
        if len(description) > 500:
            self.errors.append(_("وصف القيد طويل جداً (الحد الأقصى 500 حرف)"))
    
    def _validate_items_structure(self, items: List[Dict[str, Any]]):
        """Validate items structure"""
        if not items:
            self.errors.append(_("القيد يجب أن يحتوي على عناصر"))
            return
        
        if len(items) < 2:
            self.errors.append(_("القيد يجب أن يحتوي على عنصرين على الأقل"))
            return
        
        if len(items) > 50:
            self.errors.append(_("عدد عناصر القيد كبير جداً (الحد الأقصى 50 عنصر)"))
        
        # Validate individual items
        for i, item in enumerate(items):
            self._validate_single_item(item, i + 1)
    
    def _validate_single_item(self, item: Dict[str, Any], row_number: int):
        """Validate a single journal entry item"""
        row_prefix = f"الصف {row_number}: "
        
        # Account validation
        if 'account_id' not in item or not item['account_id']:
            self.errors.append(row_prefix + _("يجب اختيار حساب"))
            return
        
        # Amount validation
        debit = self._parse_amount(item.get('debit', '0'))
        credit = self._parse_amount(item.get('credit', '0'))
        
        if debit is None:
            self.errors.append(row_prefix + _("مبلغ المدين غير صحيح"))
            return
        
        if credit is None:
            self.errors.append(row_prefix + _("مبلغ الدائن غير صحيح"))
            return
        
        # Business logic validation
        if debit == 0 and credit == 0:
            self.errors.append(row_prefix + _("يجب إدخال مبلغ في المدين أو الدائن"))
        
        if debit > 0 and credit > 0:
            self.errors.append(row_prefix + _("لا يمكن إدخال مبلغ في المدين والدائن معاً"))
        
        if debit < 0 or credit < 0:
            self.errors.append(row_prefix + _("المبالغ لا يمكن أن تكون سالبة"))
        
        # Description validation for item
        description = item.get('description', '').strip()
        if description and len(description) > 200:
            self.warnings.append(row_prefix + _("وصف العنصر طويل (الحد المفضل 200 حرف)"))
    
    def _validate_balance(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate journal entry balance"""
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        
        for item in items:
            debit = self._parse_amount(item.get('debit', '0'))
            credit = self._parse_amount(item.get('credit', '0'))
            
            if debit is not None:
                total_debit += debit
            if credit is not None:
                total_credit += credit
        
        difference = abs(total_debit - total_credit)
        is_balanced = difference <= Decimal('0.01')
        
        if not is_balanced:
            self.errors.append(_(f"القيد غير متوازن - المدين: {total_debit:.2f}, الدائن: {total_credit:.2f}, الفرق: {difference:.2f}"))
        
        return {
            'total_debit': float(total_debit),
            'total_credit': float(total_credit),
            'difference': float(difference),
            'balanced': is_balanced
        }
    
    def _validate_accounts(self, items: List[Dict[str, Any]]):
        """Validate accounts existence and permissions"""
        from .models import Account
        
        account_ids = [item.get('account_id') for item in items if item.get('account_id')]
        
        if not account_ids:
            return
        
        # Check for duplicates
        if len(account_ids) != len(set(account_ids)):
            self.errors.append(_("لا يمكن استخدام نفس الحساب أكثر من مرة في نفس القيد"))
        
        # Validate accounts exist
        try:
            existing_accounts = Account.objects.filter(id__in=account_ids).values_list('id', flat=True)
            missing_accounts = set(account_ids) - set(existing_accounts)
            
            if missing_accounts:
                self.errors.append(_(f"الحسابات التالية غير موجودة: {', '.join(map(str, missing_accounts))}"))
            
            # Check for inactive accounts
            inactive_accounts = Account.objects.filter(
                id__in=account_ids, 
                is_active=False
            ).values_list('code', 'name')
            
            for code, name in inactive_accounts:
                self.warnings.append(_(f"الحساب {code} - {name} غير نشط"))
                
        except Exception as e:
            logger.error(f"Account validation error: {str(e)}")
            self.errors.append(_("خطأ في التحقق من الحسابات"))
    
    def _validate_amounts(self, items: List[Dict[str, Any]]):
        """Validate amount formats and ranges"""
        max_amount = Decimal('999999999.99')  # 9 digits + 2 decimals
        
        for i, item in enumerate(items):
            row_prefix = f"الصف {i + 1}: "
            
            debit = self._parse_amount(item.get('debit', '0'))
            credit = self._parse_amount(item.get('credit', '0'))
            
            if debit and debit > max_amount:
                self.errors.append(row_prefix + _(f"مبلغ المدين كبير جداً (الحد الأقصى {max_amount})"))
            
            if credit and credit > max_amount:
                self.errors.append(row_prefix + _(f"مبلغ الدائن كبير جداً (الحد الأقصى {max_amount})"))
            
            # Check for very small amounts
            min_amount = Decimal('0.01')
            if debit and 0 < debit < min_amount:
                self.warnings.append(row_prefix + _("مبلغ المدين صغير جداً"))
            
            if credit and 0 < credit < min_amount:
                self.warnings.append(row_prefix + _("مبلغ الدائن صغير جداً"))
    
    def _check_duplicates(self, entry_data: Dict[str, Any]):
        """Check for potential duplicate entries"""
        from .models import JournalEntry
        
        try:
            entry_date = entry_data.get('date')
            description = entry_data.get('description', '').strip()
            
            if not entry_date or not description:
                return
            
            # Look for similar entries in the last 30 days
            similar_entries = JournalEntry.objects.filter(
                date=entry_date,
                description__icontains=description[:50]
            ).count()
            
            if similar_entries > 0:
                self.warnings.append(_(f"يوجد {similar_entries} قيد مشابه في نفس التاريخ"))
                
        except Exception as e:
            logger.error(f"Duplicate check error: {str(e)}")
    
    def _validate_fiscal_year(self, entry_date):
        """Validate fiscal year status"""
        # This would check if the fiscal year is open/closed
        # Implementation depends on your fiscal year model
        pass
    
    def _validate_permissions(self, entry_data: Dict[str, Any]):
        """Validate user permissions"""
        if not self.user:
            return
            
        if not hasattr(self.user, 'has_perm') or not self.user.has_perm('accounting.add_journalentry'):
            self.errors.append(_("ليس لديك صلاحية لإنشاء قيود محاسبية"))
        
        # Additional permission checks can be added here
        # e.g., date restrictions, amount limits, etc.
    
    def _validate_business_rules(self, entry_data: Dict[str, Any]):
        """Validate custom business rules"""
        # Add custom business validation rules here
        # e.g., specific account combinations, workflow rules, etc.
        
        items = entry_data.get('items', [])
        
        # Example: Check for cash account rules
        cash_accounts = []  # Would be loaded from settings
        
        # Example: Validate cost center requirements
        # This is where you'd add industry-specific rules
        pass
    
    def _parse_amount(self, amount) -> Optional[Decimal]:
        """Parse amount with error handling"""
        if not amount:
            return Decimal('0')
        
        try:
            # Handle string formatting
            if isinstance(amount, str):
                amount = amount.replace(',', '').replace(' ', '')
            
            return Decimal(str(amount))
        except (ValueError, TypeError, InvalidOperation):
            return None
    
    def _generate_summary(self, entry_data: Dict[str, Any], balance_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation summary"""
        items = entry_data.get('items', [])
        
        return {
            'entry_date': entry_data.get('date'),
            'description': entry_data.get('description', ''),
            'items_count': len(items),
            'total_debit': balance_result.get('total_debit', 0),
            'total_credit': balance_result.get('total_credit', 0),
            'is_balanced': balance_result.get('balanced', False),
            'validation_status': 'valid' if len(self.errors) == 0 else 'invalid',
            'has_warnings': len(self.warnings) > 0,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }


class JournalEntryBusinessRules:
    """
    Business rules and workflow validation
    """
    
    @staticmethod
    def validate_account_combination(debit_account_id, credit_account_id):
        """Validate specific account combinations"""
        # Example business rules
        restricted_combinations = [
            # (debit_account_type, credit_account_type)
            # Add your business-specific restrictions
        ]
        
        # Implementation would check against business rules
        return True, []
    
    @staticmethod
    def validate_amount_limits(user, amount):
        """Validate amount limits based on user role"""
        # Implementation based on user permissions and amount
        return True, []
    
    @staticmethod
    def validate_date_restrictions(user, entry_date):
        """Validate date restrictions"""
        # Check if user can post to this date
        return True, []


def validate_journal_entry_data(entry_data: Dict[str, Any], user=None) -> Tuple[bool, Dict[str, Any]]:
    """
    Main validation function - convenience wrapper
    """
    validator = JournalEntryValidator(user)
    return validator.validate_complete_entry(entry_data)


def quick_balance_check(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Quick balance validation for real-time checks
    """
    total_debit = Decimal('0')
    total_credit = Decimal('0')
    
    for item in items:
        try:
            debit = Decimal(str(item.get('debit', '0'))) if item.get('debit') else Decimal('0')
            credit = Decimal(str(item.get('credit', '0'))) if item.get('credit') else Decimal('0')
            total_debit += debit
            total_credit += credit
        except (ValueError, TypeError, InvalidOperation):
            continue
    
    difference = abs(total_debit - total_credit)
    
    return {
        'total_debit': float(total_debit),
        'total_credit': float(total_credit),
        'difference': float(difference),
        'balanced': difference <= Decimal('0.01')
    }