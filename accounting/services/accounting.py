from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from django.db.models import Sum, Q
from ..models import Account, JournalEntryItem
from ..models import FiscalYear, JournalEntry, PeriodYearClose
from django.db import transaction
from django.utils import timezone

class YearCloseError(Exception):
    pass


@dataclass
class TrialBalanceRow:
    code: str
    name: str
    level: int
    debit: Decimal
    credit: Decimal
    balance: Decimal
    is_group: bool


class AccountService:
    """خدمات خاصة بالحسابات لتسهيل بناء التقارير وتجربة المحاسب."""

    @staticmethod
    def build_tree() -> List[Dict[str, Any]]:
        return Account.objects.build_tree()

    @staticmethod
    def recalc_paths():
        """إعادة حساب المستويات والمسارات لجميع الحسابات (عند وجود خلل)."""
        for acc in Account.objects.all().order_by('code'):
            parent = acc.parent
            if parent:
                acc.level = (parent.level or 0) + 1
                parent_path = parent.path or parent.code
                acc.path = f"{parent_path}/{acc.code}"
            else:
                acc.level = 0
                acc.path = acc.code
            # ضبط can_post في حالة العلامة is_group
            if acc.is_group and acc.can_post:
                acc.can_post = False
            acc.save(update_fields=['level', 'path', 'can_post'])

    @staticmethod
    def get_trial_balance(include_groups: bool = True) -> List[TrialBalanceRow]:
        """ميزان المراجعة مبسط."""
        rows: List[TrialBalanceRow] = []
        qs = Account.objects.all().order_by('path')
        for acc in qs:
            # بنود الحساب فقط (وليس الفروع) للرصد المباشر
            items = JournalEntryItem.objects.filter(account=acc, journal_entry__is_posted=True)
            debits = items.aggregate(val=Sum('amount', filter=Q(type='debit')))['val'] or Decimal('0')
            credits = items.aggregate(val=Sum('amount', filter=Q(type='credit')))['val'] or Decimal('0')
            balance = debits - credits if acc.account_type in ['asset', 'expense'] else credits - debits
            if acc.is_group and include_groups:
                balance = acc.aggregate_balance()
            if acc.is_group and not include_groups:
                continue
            rows.append(TrialBalanceRow(
                code=acc.code,
                name=acc.name,
                level=acc.level,
                debit=debits,
                credit=credits,
                balance=balance,
                is_group=acc.is_group
            ))
        return rows

    @staticmethod
    def quick_lookup(code: str) -> Optional[Account]:
        return Account.objects.filter(code=code).first()


def perform_year_close(fiscal_year: FiscalYear, user, retained_earnings_code: str = '3900') -> PeriodYearClose:
    """تنفيذ إقفال سنة مالية.

    المنطق:
      - التأكد من عدم وجود إقفال سابق لتلك السنة.
      - التأكد من عدم وجود قيود غير مرحلة داخل نطاق السنة.
      - تجميع أرصدة حسابات الإيرادات والمصروفات (الحسابات الورقية فقط).
      - حساب صافي الربح = إجمالي الإيرادات - إجمالي المصروفات.
      - إنشاء قيد إقفال: عكس أرصدة الإيرادات والمصروفات إلى حساب الأرباح المبقاة.
      - وسم السنة بأنها مغلقة is_closed=True وتعطيل is_active (يُترك للمستخدم إنشاء السنة التالية).
    """
    if fiscal_year.is_closed:
        raise YearCloseError('السنة مقفلة مسبقاً')
    if PeriodYearClose.objects.filter(fiscal_year=fiscal_year).exists():
        raise YearCloseError('تم تنفيذ الإقفال لهذه السنة سابقاً')

    # قيود ضمن السنة غير مرحلة
    unposted_exists = JournalEntry.objects.filter(
        date__gte=fiscal_year.start_date,
        date__lte=fiscal_year.end_date,
        is_posted=False
    ).exists()
    if unposted_exists:
        raise YearCloseError('هناك قيود غير مرحلة داخل السنة')

    # جمع أرصدة الحسابات
    revenue_accounts = Account.objects.filter(account_type='revenue', is_active=True, can_post=True)
    expense_accounts = Account.objects.filter(account_type='expense', is_active=True, can_post=True)

    from django.db.models import Sum, Q
    def _account_net_in_period(acc: Account) -> Decimal:
        # إجمالي البنود داخل حدود السنة
        items = acc.journal_entries.filter(  # type: ignore[attr-defined]
            journal_entry__is_posted=True,
            journal_entry__date__gte=fiscal_year.start_date,
            journal_entry__date__lte=fiscal_year.end_date,
        )
        debits = items.aggregate(v=Sum('amount', filter=Q(type='debit')))['v'] or Decimal('0')
        credits = items.aggregate(v=Sum('amount', filter=Q(type='credit')))['v'] or Decimal('0')
        # لطبيعة الحساب نحدد الرصيد
        if acc.account_type == 'expense':
            return debits - credits
        else:  # revenue
            return credits - debits

    total_revenue = Decimal('0')
    total_expense = Decimal('0')
    revenue_rows = []
    expense_rows = []
    for acc in revenue_accounts:
        val = _account_net_in_period(acc)
        if val != 0:
            total_revenue += val
            revenue_rows.append({'code': acc.code, 'name': acc.name, 'amount': float(val)})
    for acc in expense_accounts:
        val = _account_net_in_period(acc)
        if val != 0:
            total_expense += val
            expense_rows.append({'code': acc.code, 'name': acc.name, 'amount': float(val)})

    net_income = total_revenue - total_expense

    retained_acc = Account.objects.filter(code=retained_earnings_code).first()
    if not retained_acc:
        # إنشاء حساب أرباح مبقاة مبسط إذا لم يوجد
        retained_acc = Account.objects.create(
            code=retained_earnings_code,
            name='الأرباح المبقاة',
            account_type='equity',
            can_post=True
        )

    # إنشاء القيد داخل معاملة
    with transaction.atomic():
        je = JournalEntry(
            date=fiscal_year.end_date,
            entry_type='adjustment',
            description=f'قيد إقفال السنة {fiscal_year.name}',
            created_by=user,
            is_posted=False,
        )
        je.save()
        # عكس الإيرادات (إيرادات طبيعتها دائن => نجعلها مدينة لإغلاقها)
        from ..models import JournalEntryItem
        for row in revenue_rows:
            JournalEntryItem.objects.create(
                journal_entry=je,
                account=Account.objects.get(code=row['code']),
                type='debit',
                amount=Decimal(str(row['amount'])),
                description='إقفال إيرادات'
            )
        # عكس المصروفات (مصروفات طبيعتها مدين => نجعلها دائنة لإغلاقها)
        for row in expense_rows:
            JournalEntryItem.objects.create(
                journal_entry=je,
                account=Account.objects.get(code=row['code']),
                type='credit',
                amount=Decimal(str(row['amount'])),
                description='إقفال مصروفات'
            )
        # بند صافي الربح إلى حساب الأرباح المبقاة
        if net_income > 0:
            # ربح: نضع دائن (لزيادة حقوق الملكية)
            JournalEntryItem.objects.create(
                journal_entry=je,
                account=retained_acc,
                type='credit',
                amount=net_income,
                description='ترحيل صافي الربح'
            )
        elif net_income < 0:
            JournalEntryItem.objects.create(
                journal_entry=je,
                account=retained_acc,
                type='debit',
                amount=abs(net_income),
                description='ترحيل صافي الخسارة'
            )
        # ترحيل القيد
        je.is_posted = True
        je.save(update_fields=['is_posted'])

        # تحديث السنة
        fiscal_year.is_closed = True
        fiscal_year.is_active = False
        fiscal_year.save(update_fields=['is_closed','is_active'])

        closure = PeriodYearClose.objects.create(
            fiscal_year=fiscal_year,
            closed_by=user,
            journal_entry=je,
            net_income=net_income,
            preview_data={
                'revenue_total': float(total_revenue),
                'expense_total': float(total_expense),
                'revenues': revenue_rows,
                'expenses': expense_rows,
            }
        )
    return closure
