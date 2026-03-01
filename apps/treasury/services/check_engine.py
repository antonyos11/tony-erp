"""
محرك الشيكات — إنشاء، إيداع، تحصيل، ارتجاع + قيود تلقائية
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.accounts.services.journal_engine import JournalEngine
from apps.treasury.models import Check


class CheckEngine:
    """محرك إدارة الشيكات"""

    @staticmethod
    def _generate_check_ref():
        count = Check.objects.count() + 1
        return f"CHK-{timezone.now().strftime('%Y%m')}-{count:04d}"

    # ── إنشاء شيك ──────────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def create_check(cls, check_number, check_type, bank, amount,
                     issue_date, due_date, partner_name, notes='', user=None):
        """إنشاء شيك جديد (وارد أو صادر)"""
        check = Check.objects.create(
            check_number=check_number,
            check_type=check_type,
            status='pending',
            bank=bank,
            amount=Decimal(str(amount)),
            issue_date=issue_date,
            due_date=due_date,
            partner_name=partner_name,
            notes=notes,
            created_by=user,
            updated_by=user,
        )
        return check

    # ── إيداع شيك ──────────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def deposit_check(cls, check, branch, user=None):
        """إيداع شيك في البنك"""
        if check.status != 'pending':
            raise ValueError(f"لا يمكن إيداع شيك بحالة: {check.get_status_display()}")

        if not check.bank:
            raise ValueError("يجب تحديد بنك للشيك قبل الإيداع")

        description = f"إيداع شيك {check.check_number} — {check.partner_name}"

        entry = JournalEngine.create_entry(
            source='manual',
            description=description,
            branch=branch,
            lines_data=[
                {'account_code': check.bank.account.code, 'debit': check.amount, 'credit': 0,             'description': description},
                {'account_code': check.bank.account.code, 'debit': 0,            'credit': check.amount, 'description': 'شيك في التحصيل'},
            ],
            source_document=f'CHK-{check.pk}',
            user=user,
            auto_post=True,
        )

        check.status = 'deposited'
        check.journal_entry = entry
        check.updated_by = user
        check.save(update_fields=['status', 'journal_entry', 'updated_at', 'updated_by'])
        return check

    # ── تحصيل شيك ──────────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def clear_check(cls, check, branch, user=None):
        """تحصيل شيك (تم الصرف / القبض)"""
        if check.status not in ('pending', 'deposited'):
            raise ValueError(f"لا يمكن تحصيل شيك بحالة: {check.get_status_display()}")

        if check.bank:
            # تحديث رصيد البنك عند التحصيل
            if check.check_type == 'incoming':
                check.bank.current_balance += check.amount
            else:
                if check.bank.current_balance < check.amount:
                    raise ValueError("رصيد البنك غير كافٍ لصرف الشيك")
                check.bank.current_balance -= check.amount
            check.bank.save(update_fields=['current_balance', 'updated_at'])

        check.status = 'cleared'
        check.updated_by = user
        check.save(update_fields=['status', 'updated_at', 'updated_by'])
        return check

    # ── ارتجاع شيك ─────────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def bounce_check(cls, check, branch, notes='', user=None):
        """ارتجاع شيك مرتجع"""
        if check.status not in ('pending', 'deposited'):
            raise ValueError(f"لا يمكن ارتجاع شيك بحالة: {check.get_status_display()}")

        description = f"ارتجاع شيك {check.check_number} — {check.partner_name}"

        if check.bank:
            entry = JournalEngine.create_entry(
                source='manual',
                description=description,
                branch=branch,
                lines_data=[
                    {'account_code': check.bank.account.code, 'debit': 0,            'credit': check.amount, 'description': description},
                    {'account_code': check.bank.account.code, 'debit': check.amount, 'credit': 0,            'description': 'شيك مرتجع'},
                ],
                source_document=f'CHK-BNC-{check.pk}',
                user=user,
                auto_post=True,
            )
            check.journal_entry = entry

        if notes:
            check.notes = (check.notes + '\n' + notes).strip()

        check.status = 'bounced'
        check.updated_by = user
        check.save(update_fields=['status', 'notes', 'journal_entry', 'updated_at', 'updated_by'])
        return check

    # ── إلغاء شيك ──────────────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def cancel_check(cls, check, user=None):
        """إلغاء شيك"""
        if check.status in ('cleared', 'cancelled'):
            raise ValueError(f"لا يمكن إلغاء شيك بحالة: {check.get_status_display()}")

        check.status = 'cancelled'
        check.updated_by = user
        check.save(update_fields=['status', 'updated_at', 'updated_by'])
        return check
