"""
محرك الخزينة — إيداع، سحب، تحويل بين بنوك/خزائن + قيود تلقائية
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.accounts.services.journal_engine import JournalEngine


class TreasuryEngine:
    """محرك عمليات الخزينة والبنوك"""

    # ── إيداع في خزنة ──────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def deposit_to_cashbox(cls, cashbox, amount, description, branch, user=None):
        """إيداع نقدي في خزنة"""
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر")

        entry = JournalEngine.create_entry(
            source='manual',
            description=description,
            branch=branch,
            lines_data=[
                {'account_code': cashbox.account.code, 'debit': amount,  'credit': 0, 'description': description},
                {'account_code': cashbox.account.code, 'debit': 0,       'credit': amount, 'description': 'إيداع — مقابلة مؤقتة'},
            ],
            source_document=f'CASH-DEP-{cashbox.pk}',
            user=user,
            auto_post=True,
        )

        cashbox.current_balance += amount
        cashbox.save(update_fields=['current_balance', 'updated_at'])
        return entry

    # ── سحب من خزنة ────────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def withdraw_from_cashbox(cls, cashbox, amount, description, branch, user=None):
        """سحب نقدي من خزنة"""
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر")
        if cashbox.current_balance < amount:
            raise ValueError(f"رصيد الخزنة غير كافٍ ({cashbox.current_balance})")

        entry = JournalEngine.create_entry(
            source='manual',
            description=description,
            branch=branch,
            lines_data=[
                {'account_code': cashbox.account.code, 'debit': 0,      'credit': amount, 'description': description},
                {'account_code': cashbox.account.code, 'debit': amount, 'credit': 0,      'description': 'سحب — مقابلة مؤقتة'},
            ],
            source_document=f'CASH-WTH-{cashbox.pk}',
            user=user,
            auto_post=True,
        )

        cashbox.current_balance -= amount
        cashbox.save(update_fields=['current_balance', 'updated_at'])
        return entry

    # ── تحويل مالي ─────────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def transfer(cls, from_obj, from_type, to_obj, to_type, amount,
                 notes, branch, user=None):
        """
        تحويل مالي بين بنوك/خزائن
        from_type / to_type: 'cash' | 'bank'
        """
        from apps.treasury.models import MoneyTransfer

        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر")

        from_account_code = from_obj.account.code
        to_account_code   = to_obj.account.code

        description = f"تحويل {amount} من {from_obj} إلى {to_obj}"

        entry = JournalEngine.create_entry(
            source='manual',
            description=description,
            branch=branch,
            lines_data=[
                {'account_code': to_account_code,   'debit': amount, 'credit': 0,      'description': description},
                {'account_code': from_account_code, 'debit': 0,      'credit': amount, 'description': description},
            ],
            source_document='TRANSFER',
            user=user,
            auto_post=True,
        )

        # تحديث أرصدة المصدر
        from_obj.current_balance -= amount
        from_obj.save(update_fields=['current_balance', 'updated_at'])

        # تحديث أرصدة الوجهة
        to_obj.current_balance += amount
        to_obj.save(update_fields=['current_balance', 'updated_at'])

        # إنشاء سجل التحويل
        transfer_kwargs = {
            'from_account_type': from_type,
            'to_account_type': to_type,
            'amount': amount,
            'date': timezone.now(),
            'notes': notes,
            'journal_entry': entry,
            'created_by': user,
            'updated_by': user,
        }
        if from_type == 'cash':
            transfer_kwargs['from_cash'] = from_obj
        else:
            transfer_kwargs['from_bank'] = from_obj

        if to_type == 'cash':
            transfer_kwargs['to_cash'] = to_obj
        else:
            transfer_kwargs['to_bank'] = to_obj

        transfer = MoneyTransfer.objects.create(**transfer_kwargs)
        return transfer

    # ── إيداع في بنك ───────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def deposit_to_bank(cls, bank_account, amount, description, branch, user=None):
        """إيداع في بنك"""
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر")

        entry = JournalEngine.create_entry(
            source='manual',
            description=description,
            branch=branch,
            lines_data=[
                {'account_code': bank_account.account.code, 'debit': amount, 'credit': 0,      'description': description},
                {'account_code': bank_account.account.code, 'debit': 0,      'credit': amount, 'description': 'مقابلة إيداع'},
            ],
            source_document=f'BANK-DEP-{bank_account.pk}',
            user=user,
            auto_post=True,
        )

        bank_account.current_balance += amount
        bank_account.save(update_fields=['current_balance', 'updated_at'])
        return entry

    # ── سحب من بنك ─────────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def withdraw_from_bank(cls, bank_account, amount, description, branch, user=None):
        """سحب من بنك"""
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر")
        if bank_account.current_balance < amount:
            raise ValueError(f"رصيد البنك غير كافٍ ({bank_account.current_balance})")

        entry = JournalEngine.create_entry(
            source='manual',
            description=description,
            branch=branch,
            lines_data=[
                {'account_code': bank_account.account.code, 'debit': 0,      'credit': amount, 'description': description},
                {'account_code': bank_account.account.code, 'debit': amount, 'credit': 0,      'description': 'مقابلة سحب'},
            ],
            source_document=f'BANK-WTH-{bank_account.pk}',
            user=user,
            auto_post=True,
        )

        bank_account.current_balance -= amount
        bank_account.save(update_fields=['current_balance', 'updated_at'])
        return entry
