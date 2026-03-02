"""
محرك الميزانيات — RITA ERP Sprint 22B
══════════════════════════════════════
يُدير:
1. إنشاء ميزانية
2. فحص التجاوز
3. تقرير Budget vs Actual
"""
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from apps.accounts.models import Budget, BudgetLine


class BudgetEngine:

    @classmethod
    def check_budget(cls, account_code, amount, branch=None, cost_center=None, month=None):
        """
        فحص هل المبلغ ضمن الميزانية
        Returns: (is_within_budget, budget_amount, actual_spent, remaining)
        """
        if not month:
            month = timezone.now().month
        year = timezone.now().year

        # البحث عن الميزانية المعتمدة
        budget_filter = {
            'status': 'approved',
            'fiscal_year__start_date__year': year,
        }
        if branch:
            budget_filter['branch'] = branch
        if cost_center:
            budget_filter['cost_center'] = cost_center

        budget = Budget.objects.filter(**budget_filter).first()
        if not budget:
            return True, Decimal('0'), Decimal('0'), Decimal('0')  # لا ميزانية = مسموح

        # البحث عن سطر الميزانية
        from apps.accounts.models import Account
        try:
            account = Account.objects.get(code=account_code)
        except Account.DoesNotExist:
            return True, Decimal('0'), Decimal('0'), Decimal('0')

        budget_line = BudgetLine.objects.filter(budget=budget, account=account).first()
        if not budget_line:
            return True, Decimal('0'), Decimal('0'), Decimal('0')

        budget_amount = Decimal(str(budget_line.get_month_amount(month)))

        # حساب الفعلي
        from apps.accounts.models import JournalLine
        actual = JournalLine.objects.filter(
            account=account,
            entry__date__month=month,
            entry__date__year=year,
            entry__status='posted',
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0')

        remaining = budget_amount - actual
        is_within = (actual + Decimal(str(amount))) <= budget_amount

        return is_within, budget_amount, actual, remaining

    @classmethod
    def get_budget_vs_actual(cls, budget_id, month=None):
        """تقرير الميزانية مقابل الفعلي"""
        budget = Budget.objects.get(pk=budget_id)
        year = budget.fiscal_year.start_date.year

        if not month:
            month = timezone.now().month

        result = []
        for line in budget.lines.select_related('account', 'expense_category'):
            budget_amount = Decimal(str(line.get_month_amount(month)))

            from apps.accounts.models import JournalLine
            actual = JournalLine.objects.filter(
                account=line.account,
                entry__date__month=month,
                entry__date__year=year,
                entry__status='posted',
            ).aggregate(total=Sum('debit'))['total'] or Decimal('0')

            variance = budget_amount - actual
            variance_pct = (variance / budget_amount * 100) if budget_amount > 0 else Decimal('0')

            status = 'normal'
            if budget_amount > 0:
                if actual > budget_amount:
                    status = 'over'
                elif actual > budget_amount * Decimal('0.9'):
                    status = 'warning'

            result.append({
                'account': line.account,
                'category': line.expense_category,
                'budget': budget_amount,
                'actual': actual,
                'variance': variance,
                'variance_pct': variance_pct.quantize(Decimal('0.1')) if isinstance(variance_pct, Decimal) else Decimal('0'),
                'status': status,
            })

        return {
            'budget': budget,
            'month': month,
            'year': year,
            'lines': result,
            'total_budget': sum(r['budget'] for r in result),
            'total_actual': sum(r['actual'] for r in result),
            'total_variance': sum(r['variance'] for r in result),
        }

    @classmethod
    def get_annual_summary(cls, budget_id):
        """ملخص سنوي — كل الشهور"""
        budget = Budget.objects.get(pk=budget_id)
        months_data = []

        for month in range(1, 13):
            data = cls.get_budget_vs_actual(budget_id, month)
            months_data.append({
                'month': month,
                'total_budget': data['total_budget'],
                'total_actual': data['total_actual'],
                'total_variance': data['total_variance'],
            })

        return {
            'budget': budget,
            'months': months_data,
        }
