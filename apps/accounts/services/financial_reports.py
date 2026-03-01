"""
التقارير المالية الأساسية
ميزان المراجعة + قائمة الدخل + المركز المالي
"""
from decimal import Decimal
from django.db.models import Sum, Q
from apps.accounts.models import Account, JournalLine, JournalEntry


class FinancialReports:
    """التقارير المالية"""

    @classmethod
    def trial_balance(cls, start_date=None, end_date=None, branch=None):
        """
        ميزان المراجعة
        """
        filters = Q(entry__status='posted')
        if start_date:
            filters &= Q(entry__date__gte=start_date)
        if end_date:
            filters &= Q(entry__date__lte=end_date)
        if branch:
            filters &= Q(entry__branch=branch)

        accounts = Account.objects.filter(is_detail=True, is_active=True).order_by('code')

        result = []
        total_debit  = Decimal('0')
        total_credit = Decimal('0')

        for account in accounts:
            totals = JournalLine.objects.filter(
                filters,
                account=account,
            ).aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit'),
            )

            debit  = totals['total_debit']  or Decimal('0')
            credit = totals['total_credit'] or Decimal('0')

            if debit == 0 and credit == 0:
                continue

            balance = debit - credit

            result.append({
                'code':         account.code,
                'name':         account.name,
                'account_type': account.get_account_type_display(),
                'debit':        debit,
                'credit':       credit,
                'balance':      abs(balance),
                'balance_type': 'مدين' if balance > 0 else ('دائن' if balance < 0 else 'صفر'),
            })

            total_debit  += debit
            total_credit += credit

        return {
            'accounts':     result,
            'total_debit':  total_debit,
            'total_credit': total_credit,
            'is_balanced':  total_debit == total_credit,
        }

    @classmethod
    def income_statement(cls, start_date, end_date, branch=None):
        """
        قائمة الدخل
        """
        filters = Q(
            entry__status='posted',
            entry__date__gte=start_date,
            entry__date__lte=end_date,
        )
        if branch:
            filters &= Q(entry__branch=branch)

        def get_total(account_type):
            totals = JournalLine.objects.filter(
                filters,
                account__account_type=account_type,
            ).aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit'),
            )
            debit  = totals['total_debit']  or Decimal('0')
            credit = totals['total_credit'] or Decimal('0')
            return credit - debit  # الإيرادات دائنة، المصروفات مدينة

        revenue  = get_total('revenue')
        cogs     = get_total('cogs')
        expenses = get_total('expense')

        gross_profit = revenue + cogs   # cogs سالب (مدين)
        net_profit   = gross_profit + expenses  # expenses سالب

        gross_margin = (gross_profit / revenue * 100) if revenue > 0 else Decimal('0')
        net_margin   = (net_profit   / revenue * 100) if revenue > 0 else Decimal('0')

        return {
            'period':       f'{start_date} إلى {end_date}',
            'revenue':      abs(revenue),
            'cogs':         abs(cogs),
            'gross_profit': gross_profit,
            'gross_margin': gross_margin.quantize(Decimal('0.01')),
            'expenses':     abs(expenses),
            'net_profit':   net_profit,
            'net_margin':   net_margin.quantize(Decimal('0.01')),
        }

    @classmethod
    def balance_sheet(cls, date, branch=None):
        """
        قائمة المركز المالي (الميزانية العمومية)
        """
        filters = Q(entry__status='posted', entry__date__lte=date)
        if branch:
            filters &= Q(entry__branch=branch)

        def get_balance(account_type):
            totals = JournalLine.objects.filter(
                filters,
                account__account_type=account_type,
            ).aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit'),
            )
            debit  = totals['total_debit']  or Decimal('0')
            credit = totals['total_credit'] or Decimal('0')
            return debit - credit

        assets      = get_balance('asset')
        liabilities = get_balance('liability')
        equity      = get_balance('equity')

        # الأرباح المحتجزة (إيرادات - مصروفات - تكلفة مبيعات)
        revenue_balance  = get_balance('revenue')
        cogs_balance     = get_balance('cogs')
        expense_balance  = get_balance('expense')
        retained_earnings = -(revenue_balance + cogs_balance + expense_balance)

        return {
            'date': str(date),
            'assets': abs(assets),
            'liabilities': abs(liabilities),
            'equity': abs(equity) + retained_earnings,
            'retained_earnings': retained_earnings,
            'is_balanced': abs(
                assets - (abs(liabilities) + abs(equity) + retained_earnings)
            ) < Decimal('0.01'),
        }

    @classmethod
    def account_statement(cls, account_code, start_date=None, end_date=None):
        """
        كشف حساب تفصيلي
        """
        account = Account.objects.get(code=account_code)

        filters = Q(account=account, entry__status='posted')
        if start_date:
            filters &= Q(entry__date__gte=start_date)
        if end_date:
            filters &= Q(entry__date__lte=end_date)

        lines = JournalLine.objects.filter(filters).select_related(
            'entry', 'entry__branch'
        ).order_by('entry__date', 'entry__entry_number')

        result = []
        running_balance = Decimal('0')

        for line in lines:
            running_balance += line.debit - line.credit
            result.append({
                'date':         line.entry.date,
                'entry_number': line.entry.entry_number,
                'description':  line.description or line.entry.description,
                'debit':        line.debit,
                'credit':       line.credit,
                'balance':      abs(running_balance),
                'balance_type': 'مدين' if running_balance > 0 else 'دائن',
                'branch':       line.entry.branch.name if line.entry.branch else '',
                'source':       line.entry.get_source_display(),
            })

        return {
            'account_code': account.code,
            'account_name': account.name,
            'movements':    result,
            'total_debit':  sum(l['debit']  for l in result),
            'total_credit': sum(l['credit'] for l in result),
            'closing_balance':      abs(running_balance),
            'closing_balance_type': 'مدين' if running_balance > 0 else 'دائن',
        }
