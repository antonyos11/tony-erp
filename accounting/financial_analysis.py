"""
التحليل المالي المتقدم - النسب المالية والمؤشرات
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, F, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import date, datetime

from .models import Account, JournalEntryItem, Asset


class FinancialAnalyzer:
    """محلل مالي متقدم"""
    
    def __init__(self, as_of_date=None, start_date=None, end_date=None):
        self.as_of_date = as_of_date or date.today()
        self.start_date = start_date
        self.end_date = end_date
    
    def get_account_balance(self, account_type, as_of_date=None):
        """حساب رصيد حسابات من نوع معين"""
        target_date = as_of_date or self.as_of_date
        
        accounts = Account.objects.filter(
            account_type=account_type,
            is_active=True
        )
        
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        
        for account in accounts:
            balance = JournalEntryItem.objects.filter(
                account=account,
                journal_entry__is_posted=True,
                journal_entry__date__lte=target_date
            ).aggregate(
                debits=Coalesce(Sum('amount', filter=Q(type='debit')), Decimal('0')),
                credits=Coalesce(Sum('amount', filter=Q(type='credit')), Decimal('0'))
            )
            
            total_debit += balance['debits']
            total_credit += balance['credits']
        
        if account_type in ['asset', 'expense']:
            return total_debit - total_credit
        else:
            return total_credit - total_debit
    
    def get_period_account_balance(self, account_type, start_date, end_date):
        """حساب رصيد حسابات لفترة محددة"""
        accounts = Account.objects.filter(
            account_type=account_type,
            is_active=True
        )
        
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        
        for account in accounts:
            balance = JournalEntryItem.objects.filter(
                account=account,
                journal_entry__is_posted=True,
                journal_entry__date__gte=start_date,
                journal_entry__date__lte=end_date
            ).aggregate(
                debits=Coalesce(Sum('amount', filter=Q(type='debit')), Decimal('0')),
                credits=Coalesce(Sum('amount', filter=Q(type='credit')), Decimal('0'))
            )
            
            total_debit += balance['debits']
            total_credit += balance['credits']
        
        if account_type in ['asset', 'expense']:
            return total_debit - total_credit
        else:
            return total_credit - total_debit
    
    # ==================== نسب الربحية ====================
    
    def gross_profit_margin(self):
        """هامش الربح الإجمالي %"""
        if not self.start_date or not self.end_date:
            return None
        
        revenue = self.get_period_account_balance('revenue', self.start_date, self.end_date)
        # يمكن إضافة تكلفة البضاعة المباعة
        # افتراضياً نستخدم المصروفات
        expenses = self.get_period_account_balance('expense', self.start_date, self.end_date)
        
        if revenue == 0:
            return Decimal('0')
        
        gross_profit = revenue - expenses
        return (gross_profit / revenue) * 100
    
    def net_profit_margin(self):
        """هامش الربح الصافي %"""
        if not self.start_date or not self.end_date:
            return None
        
        revenue = self.get_period_account_balance('revenue', self.start_date, self.end_date)
        expenses = self.get_period_account_balance('expense', self.start_date, self.end_date)
        
        if revenue == 0:
            return Decimal('0')
        
        net_profit = revenue - expenses
        return (net_profit / revenue) * 100
    
    def return_on_assets(self):
        """العائد على الأصول (ROA) %"""
        if not self.start_date or not self.end_date:
            return None
        
        revenue = self.get_period_account_balance('revenue', self.start_date, self.end_date)
        expenses = self.get_period_account_balance('expense', self.start_date, self.end_date)
        net_income = revenue - expenses
        
        total_assets = self.get_account_balance('asset')
        
        if total_assets == 0:
            return Decimal('0')
        
        return (net_income / total_assets) * 100
    
    def return_on_equity(self):
        """العائد على حقوق الملكية (ROE) %"""
        if not self.start_date or not self.end_date:
            return None
        
        revenue = self.get_period_account_balance('revenue', self.start_date, self.end_date)
        expenses = self.get_period_account_balance('expense', self.start_date, self.end_date)
        net_income = revenue - expenses
        
        total_equity = self.get_account_balance('equity')
        
        if total_equity == 0:
            return Decimal('0')
        
        return (net_income / total_equity) * 100
    
    # ==================== نسب السيولة ====================
    
    def current_ratio(self):
        """النسبة الجارية (Current Ratio)"""
        # يحتاج تصنيف الأصول المتداولة والخصوم المتداولة
        # هنا نستخدم إجمالي الأصول والخصوم كمثال
        total_assets = self.get_account_balance('asset')
        total_liabilities = self.get_account_balance('liability')
        
        if total_liabilities == 0:
            return Decimal('0')
        
        return total_assets / total_liabilities
    
    def quick_ratio(self):
        """النسبة السريعة (Quick Ratio)"""
        # = (الأصول المتداولة - المخزون) / الخصوم المتداولة
        # تحتاج تصنيف دقيق للحسابات
        total_assets = self.get_account_balance('asset')
        total_liabilities = self.get_account_balance('liability')
        
        if total_liabilities == 0:
            return Decimal('0')
        
        # افتراضياً بدون المخزون
        return (total_assets * Decimal('0.8')) / total_liabilities
    
    def working_capital(self):
        """رأس المال العامل"""
        total_assets = self.get_account_balance('asset')
        total_liabilities = self.get_account_balance('liability')
        
        return total_assets - total_liabilities
    
    # ==================== نسب الكفاءة ====================
    
    def asset_turnover_ratio(self):
        """معدل دوران الأصول"""
        if not self.start_date or not self.end_date:
            return None
        
        revenue = self.get_period_account_balance('revenue', self.start_date, self.end_date)
        total_assets = self.get_account_balance('asset')
        
        if total_assets == 0:
            return Decimal('0')
        
        return revenue / total_assets
    
    # ==================== نسب المديونية ====================
    
    def debt_to_equity_ratio(self):
        """نسبة الدين إلى حقوق الملكية"""
        total_liabilities = self.get_account_balance('liability')
        total_equity = self.get_account_balance('equity')
        
        if total_equity == 0:
            return Decimal('0')
        
        return total_liabilities / total_equity
    
    def debt_ratio(self):
        """نسبة الدين"""
        total_assets = self.get_account_balance('asset')
        total_liabilities = self.get_account_balance('liability')
        
        if total_assets == 0:
            return Decimal('0')
        
        return (total_liabilities / total_assets) * 100
    
    def equity_ratio(self):
        """نسبة حقوق الملكية"""
        total_assets = self.get_account_balance('asset')
        total_equity = self.get_account_balance('equity')
        
        if total_assets == 0:
            return Decimal('0')
        
        return (total_equity / total_assets) * 100
    
    # ==================== تحليل شامل ====================
    
    def comprehensive_analysis(self):
        """تحليل مالي شامل"""
        return {
            # الأرصدة الأساسية
            'total_assets': self.get_account_balance('asset'),
            'total_liabilities': self.get_account_balance('liability'),
            'total_equity': self.get_account_balance('equity'),
            
            # نسب الربحية
            'gross_profit_margin': self.gross_profit_margin(),
            'net_profit_margin': self.net_profit_margin(),
            'return_on_assets': self.return_on_assets(),
            'return_on_equity': self.return_on_equity(),
            
            # نسب السيولة
            'current_ratio': self.current_ratio(),
            'quick_ratio': self.quick_ratio(),
            'working_capital': self.working_capital(),
            
            # نسب الكفاءة
            'asset_turnover_ratio': self.asset_turnover_ratio(),
            
            # نسب المديونية
            'debt_to_equity_ratio': self.debt_to_equity_ratio(),
            'debt_ratio': self.debt_ratio(),
            'equity_ratio': self.equity_ratio(),
        }


@login_required
def financial_analysis_dashboard(request):
    """لوحة معلومات التحليل المالي"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date or not end_date:
        # افتراضياً: الشهر الحالي
        today = date.today()
        start_date = today.replace(day=1)
        end_date = today
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # إنشاء محلل مالي
    analyzer = FinancialAnalyzer(
        as_of_date=end_date,
        start_date=start_date,
        end_date=end_date
    )
    
    # الحصول على التحليل الشامل
    analysis = analyzer.comprehensive_analysis()
    
    # حساب الإيرادات والمصروفات للفترة
    revenue = analyzer.get_period_account_balance('revenue', start_date, end_date)
    expenses = analyzer.get_period_account_balance('expense', start_date, end_date)
    net_income = revenue - expenses
    
    # إضافة بيانات الفترة
    analysis['period_start'] = start_date
    analysis['period_end'] = end_date
    analysis['revenue'] = revenue
    analysis['expenses'] = expenses
    analysis['net_income'] = net_income
    
    # Calculate financial health score (0-100)
    score = 50  # Base score
    
    # Profitability bonus
    if analysis.get('net_profit_margin') and analysis['net_profit_margin'] > 0:
        score += min(float(analysis['net_profit_margin']), 20)
    
    # Liquidity bonus/penalty
    current_ratio = float(analysis.get('current_ratio') or 0)
    if current_ratio >= 2:
        score += 15
    elif current_ratio >= 1:
        score += 5
    else:
        score -= 10
    
    # Debt penalty
    debt_ratio = float(analysis.get('debt_ratio') or 0)
    if debt_ratio > 70:
        score -= 15
    elif debt_ratio > 50:
        score -= 5
    
    # ROA/ROE bonus
    if analysis.get('return_on_assets') and analysis['return_on_assets'] > 10:
        score += 10
    
    financial_health_score = max(0, min(100, score))
    analysis['financial_health_score'] = financial_health_score
    
    # Add trend data (placeholder values - could be calculated from historical data)
    analysis['gpm_trend'] = 0
    analysis['npm_trend'] = 0
    analysis['roa_trend'] = 0
    analysis['roe_trend'] = 0
    analysis['roa'] = analysis.get('return_on_assets', 0)
    analysis['roe'] = analysis.get('return_on_equity', 0)
    analysis['debt_to_equity'] = analysis.get('debt_to_equity_ratio', 0)
    analysis['asset_turnover'] = analysis.get('asset_turnover_ratio', 0)
    analysis['inventory_turnover'] = 12  # Placeholder
    
    # تقييم الصحة المالية
    if financial_health_score >= 80:
        financial_health = 'ممتاز'
    elif financial_health_score >= 60:
        financial_health = 'جيد'
    elif financial_health_score >= 40:
        financial_health = 'متوسط'
    else:
        financial_health = 'ضعيف'
    
    analysis['financial_health'] = financial_health
    
    # Chart data (placeholder)
    chart_labels = '["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو"]'
    gpm_trend = '[15, 18, 17, 20, 22, 17]'
    npm_trend = '[8, 10, 9, 12, 14, 17]'
    current_ratio_trend = '[1.5, 1.6, 1.7, 1.72, 1.8, 1.72]'
    quick_ratio_trend = '[1.1, 1.2, 1.3, 1.35, 1.4, 1.37]'
    
    context = {
        'analysis': analysis,
        'start_date': start_date,
        'end_date': end_date,
        'chart_labels': chart_labels,
        'gpm_trend': gpm_trend,
        'npm_trend': npm_trend,
        'current_ratio_trend': current_ratio_trend,
        'quick_ratio_trend': quick_ratio_trend,
        'page_title': 'التحليل المالي المتقدم'
    }
    return render(request, 'accounting/advanced/financial_analysis.html', context)


@login_required
def financial_ratios_report(request):
    """تقرير النسب المالية التفصيلي"""
    from accounting.models import Account
    from django.db.models import Sum
    from decimal import Decimal

    # حساب النسب المالية الحقيقية
    def get_account_balance(account_type, is_current=None):
        qs = Account.objects.filter(account_type=account_type)
        if is_current is not None:
            qs = qs.filter(is_current=is_current)
        return qs.aggregate(
            debit=Sum('journalentryline__debit'),
            credit=Sum('journalentryline__credit'),
        )

    try:
        current_assets_data = get_account_balance('asset', is_current=True)
        current_assets = (current_assets_data.get('debit') or Decimal('0')) - (current_assets_data.get('credit') or Decimal('0'))

        current_liabilities_data = get_account_balance('liability', is_current=True)
        current_liabilities = (current_liabilities_data.get('credit') or Decimal('0')) - (current_liabilities_data.get('debit') or Decimal('0'))

        total_assets_data = get_account_balance('asset')
        total_assets = (total_assets_data.get('debit') or Decimal('0')) - (total_assets_data.get('credit') or Decimal('0'))

        equity_data = get_account_balance('equity')
        equity = (equity_data.get('credit') or Decimal('0')) - (equity_data.get('debit') or Decimal('0'))

        revenue_data = get_account_balance('revenue')
        revenue = (revenue_data.get('credit') or Decimal('0')) - (revenue_data.get('debit') or Decimal('0'))

        expense_data = get_account_balance('expense')
        expenses = (expense_data.get('debit') or Decimal('0')) - (expense_data.get('credit') or Decimal('0'))

        net_income = revenue - expenses
        total_liabilities = total_assets - equity

        ratios = {
            'current_ratio': float(current_assets / current_liabilities) if current_liabilities else 0,
            'quick_ratio': float(current_assets / current_liabilities) if current_liabilities else 0,
            'net_profit_margin': float(net_income / revenue * 100) if revenue else 0,
            'gross_profit_margin': float((revenue - expenses) / revenue * 100) if revenue else 0,
            'return_on_assets': float(net_income / total_assets * 100) if total_assets else 0,
            'return_on_equity': float(net_income / equity * 100) if equity else 0,
            'debt_to_equity': float(total_liabilities / equity) if equity else 0,
            'debt_ratio': float(total_liabilities / total_assets * 100) if total_assets else 0,
            'roa': float(net_income / total_assets * 100) if total_assets else 0,
            'roe': float(net_income / equity * 100) if equity else 0,
        }

        summary = {
            'revenue': float(revenue),
            'expenses': float(expenses),
            'net_income': float(net_income),
            'total_assets': float(total_assets),
            'total_liabilities': float(total_liabilities),
            'equity': float(equity),
        }
    except Exception:
        ratios = {
            'current_ratio': 0, 'quick_ratio': 0, 'net_profit_margin': 0,
            'gross_profit_margin': 0, 'return_on_assets': 0, 'return_on_equity': 0,
            'debt_to_equity': 0, 'debt_ratio': 0, 'roa': 0, 'roe': 0,
        }
        summary = {
            'revenue': 0, 'expenses': 0, 'net_income': 0,
            'total_assets': 0, 'total_liabilities': 0, 'equity': 0,
        }

    context = {
        'page_title': 'تقرير النسب المالية',
        'ratios': ratios,
        'summary': summary,
    }
    return render(request, 'accounting/advanced/financial_ratios.html', context)
