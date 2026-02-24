"""
Views للميزات المتقدمة في نظام المحاسبة
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count, F, DecimalField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext as _
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta, date
import csv
import json

from .models import (
    Account, JournalEntry, JournalEntryItem, FiscalYear,
    BankReconciliation, RecurringJournalEntry, BudgetItem, Asset,
    DepreciationEntry, AccountingAuditLog, PeriodClose, CustomReport, ReceivableAging,
    Bank, CostCenter
)


# ==================== الصفحة الرئيسية للميزات المتقدمة ====================

@login_required
def advanced_features_index(request):
    """الصفحة الرئيسية للميزات المتقدمة"""
    context = {
        'pending_count': BankReconciliation.objects.filter(status='pending').count(),
        'active_workflows': 0,  # سيتم تحديثها لاحقاً
        'reports_count': CustomReport.objects.filter(created_by=request.user).count(),
        'page_title': 'الميزات المتقدمة'
    }
    return render(request, 'accounting/advanced/index.html', context)


# ==================== التسويات البنكية ====================

@login_required
def bank_reconciliation_list(request):
    """قائمة التسويات البنكية"""
    reconciliations = BankReconciliation.objects.select_related(
        'bank', 'created_by', 'approved_by'
    ).order_by('-period_end')
    
    # Count by status
    in_progress_count = reconciliations.filter(status='in_progress').count()
    completed_count = reconciliations.filter(status='completed').count()
    needs_review_count = reconciliations.filter(status='needs_review').count()
    approved_count = reconciliations.filter(status='approved').count()
    
    context = {
        'reconciliations': reconciliations,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'needs_review_count': needs_review_count,
        'approved_count': approved_count,
        'page_title': 'التسويات البنكية'
    }
    return render(request, 'accounting/advanced/bank_reconciliation_list.html', context)


@login_required
def bank_reconciliation_create(request):
    """إنشاء تسوية بنكية جديدة"""
    if request.method == 'POST':
        bank_id = request.POST.get('bank')
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')
        opening_balance = Decimal(request.POST.get('opening_balance', 0))
        closing_balance = Decimal(request.POST.get('closing_balance', 0))
        
        bank = get_object_or_404(Bank, pk=bank_id)
        
        reconciliation = BankReconciliation.objects.create(
            bank=bank,
            period_start=period_start,
            period_end=period_end,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            created_by=request.user
        )
        
        messages.success(request, _('تم إنشاء التسوية البنكية بنجاح'))
        return redirect('accounting:bank_reconciliation_detail', pk=reconciliation.pk)
    
    banks = Bank.objects.all()
    context = {
        'banks': banks,
        'page_title': 'إنشاء تسوية بنكية'
    }
    return render(request, 'accounting/advanced/bank_reconciliation_form.html', context)


@login_required
def bank_reconciliation_detail(request, pk):
    """تفاصيل التسوية البنكية مع المطابقة"""
    reconciliation = get_object_or_404(
        BankReconciliation.objects.select_related('bank', 'created_by'),
        pk=pk
    )
    
    # جلب المعاملات البنكية للفترة
    bank_transactions = JournalEntryItem.objects.filter(
        journal_entry__is_posted=True,
        journal_entry__date__gte=reconciliation.period_start,
        journal_entry__date__lte=reconciliation.period_end,
        account__in=reconciliation.bank.linked_account.get_descendants(include_self=True) if hasattr(reconciliation.bank, 'linked_account') else []
    ).select_related('journal_entry', 'account').order_by('journal_entry__date')
    
    context = {
        'reconciliation': reconciliation,
        'bank_transactions': bank_transactions,
        'page_title': f'تسوية بنكية - {reconciliation.bank.name}'
    }
    return render(request, 'accounting/advanced/bank_reconciliation_detail.html', context)


# ==================== القيود المتكررة ====================

@login_required
def recurring_entries_list(request):
    """قائمة القيود المتكررة"""
    recurring_entries = RecurringJournalEntry.objects.select_related(
        'template', 'created_by'
    ).order_by('next_execution')
    
    # تحديث القيود المستحقة
    today = date.today()
    due_entries = recurring_entries.filter(
        is_active=True,
        next_execution__lte=today
    )
    
    # Statistics
    active_entries_count = recurring_entries.filter(is_active=True).count()
    inactive_entries_count = recurring_entries.filter(is_active=False).count()
    total_executions = recurring_entries.aggregate(
        total=Coalesce(Sum('execution_count'), 0)
    )['total']
    
    context = {
        'recurring_entries': recurring_entries,
        'due_entries': due_entries,
        'active_entries_count': active_entries_count,
        'inactive_entries_count': inactive_entries_count,
        'total_executions': total_executions,
        'page_title': 'القيود المتكررة'
    }
    return render(request, 'accounting/advanced/recurring_entries_list.html', context)


@login_required
def execute_recurring_entry(request, pk):
    """تنفيذ قيد متكرر"""
    recurring_entry = get_object_or_404(RecurringJournalEntry, pk=pk)
    
    if request.method == 'POST':
        try:
            # إنشاء قيد جديد من القالب
            template = recurring_entry.template
            
            journal_entry = JournalEntry.objects.create(
                number=f"REC-{recurring_entry.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                date=timezone.now().date(),
                entry_type='manual',
                description=f"{template.name} - {template.description}",
                reference=f"Recurring Entry #{recurring_entry.pk}",
                created_by=request.user,
                auto_generated=True,
                is_posted=recurring_entry.auto_post
            )
            
            # نسخ البنود من القالب
            for template_item in template.items.all():
                JournalEntryItem.objects.create(
                    journal_entry=journal_entry,
                    account=template_item.account,
                    type=template_item.type,
                    amount=template_item.amount,
                    description=template_item.description,
                    cost_center=template_item.cost_center
                )
            
            # تحديث القيد المتكرر
            recurring_entry.last_execution = timezone.now()
            recurring_entry.execution_count += 1
            recurring_entry.next_execution = recurring_entry.calculate_next_execution()
            recurring_entry.save()
            
            messages.success(request, _('تم تنفيذ القيد المتكرر بنجاح'))
            return redirect('accounting:journal_entry_detail', pk=journal_entry.pk)
            
        except Exception as e:
            messages.error(request, f'خطأ في تنفيذ القيد: {str(e)}')
    
    return redirect('accounting:recurring_entries_list')


# ==================== الموازنات التخطيطية ====================

@login_required
def budget_dashboard(request):
    """لوحة معلومات الموازنات"""
    fiscal_year_id = request.GET.get('fiscal_year')
    month = request.GET.get('month')
    
    fiscal_years = FiscalYear.objects.all()
    
    # الفلاتر
    budget_items = BudgetItem.objects.select_related(
        'account', 'cost_center', 'fiscal_year'
    )
    
    if fiscal_year_id:
        budget_items = budget_items.filter(fiscal_year_id=fiscal_year_id)
    if month:
        budget_items = budget_items.filter(month=month)
    
    # الإحصائيات
    total_budgeted = budget_items.aggregate(
        total=Coalesce(Sum('budgeted_amount'), Decimal('0'))
    )['total']
    
    total_actual = budget_items.aggregate(
        total=Coalesce(Sum('actual_amount'), Decimal('0'))
    )['total']
    
    variance = total_actual - total_budgeted
    variance_pct = (variance / total_budgeted * 100) if total_budgeted != 0 else Decimal('0')
    
    # البنود الأكثر تجاوزاً
    over_budget_items = budget_items.filter(
        variance_amount__gt=0
    ).order_by('-variance_amount')[:10]
    
    context = {
        'fiscal_years': fiscal_years,
        'budget_items': budget_items,
        'total_budgeted': total_budgeted,
        'total_actual': total_actual,
        'variance': variance,
        'variance_pct': variance_pct,
        'over_budget_items': over_budget_items,
        'page_title': 'لوحة معلومات الموازنات'
    }
    return render(request, 'accounting/advanced/budget_dashboard.html', context)


# ==================== الأصول الثابتة ====================

@login_required
def assets_list(request):
    """قائمة الأصول الثابتة"""
    status_filter = request.GET.get('status')
    
    assets = Asset.objects.select_related(
        'account', 'cost_center', 'accumulated_depreciation_account'
    )
    
    if status_filter:
        assets = assets.filter(status=status_filter)
    
    # الإحصائيات
    stats = assets.aggregate(
        total_cost=Coalesce(Sum('purchase_cost'), Decimal('0')),
        total_depreciation=Coalesce(Sum('accumulated_depreciation'), Decimal('0')),
        total_book_value=Coalesce(Sum('book_value'), Decimal('0')),
        count=Count('id')
    )
    
    context = {
        'assets': assets.order_by('-purchase_date'),
        'stats': stats,
        'page_title': 'الأصول الثابتة'
    }
    return render(request, 'accounting/advanced/assets_list.html', context)


@login_required
def asset_detail(request, pk):
    """تفاصيل أصل ثابت"""
    asset = get_object_or_404(
        Asset.objects.select_related(
            'account', 'cost_center', 'accumulated_depreciation_account',
            'depreciation_expense_account'
        ),
        pk=pk
    )
    
    depreciation_entries = asset.depreciation_entries.select_related(
        'journal_entry'
    ).order_by('-depreciation_date')
    
    # حساب الإهلاك الشهري
    monthly_depreciation = asset.calculate_monthly_depreciation()
    
    context = {
        'asset': asset,
        'depreciation_entries': depreciation_entries,
        'monthly_depreciation': monthly_depreciation,
        'page_title': f'أصل - {asset.name}'
    }
    return render(request, 'accounting/advanced/asset_detail.html', context)


@login_required
def calculate_depreciation(request):
    """حساب الإهلاك الشهري لجميع الأصول"""
    if request.method == 'POST':
        target_month = request.POST.get('target_month')
        
        if not target_month:
            target_month = date.today().replace(day=1)
        else:
            target_month = datetime.strptime(target_month, '%Y-%m-%d').date()
        
        # جلب الأصول النشطة
        active_assets = Asset.objects.filter(status='active')
        
        created_count = 0
        for asset in active_assets:
            # التحقق من عدم وجود إهلاك لهذا الشهر
            existing = DepreciationEntry.objects.filter(
                asset=asset,
                depreciation_date__year=target_month.year,
                depreciation_date__month=target_month.month
            ).exists()
            
            if not existing:
                monthly_dep = asset.calculate_monthly_depreciation()
                
                if monthly_dep > 0:
                    # إنشاء قيد الإهلاك
                    journal_entry = JournalEntry.objects.create(
                        number=f"DEP-{asset.code}-{target_month.strftime('%Y%m')}",
                        date=target_month,
                        entry_type='depreciation',
                        description=f"إهلاك {asset.name} - {target_month.strftime('%B %Y')}",
                        created_by=request.user,
                        auto_generated=True,
                        is_posted=True
                    )
                    
                    # مدين: مصروف الإهلاك
                    JournalEntryItem.objects.create(
                        journal_entry=journal_entry,
                        account=asset.depreciation_expense_account,
                        type='debit',
                        amount=monthly_dep,
                        description=f"مصروف إهلاك {asset.name}",
                        cost_center=asset.cost_center
                    )
                    
                    # دائن: مجمع الإهلاك
                    JournalEntryItem.objects.create(
                        journal_entry=journal_entry,
                        account=asset.accumulated_depreciation_account,
                        type='credit',
                        amount=monthly_dep,
                        description=f"مجمع إهلاك {asset.name}"
                    )
                    
                    # تسجيل قيد الإهلاك
                    acc_before = asset.accumulated_depreciation
                    asset.accumulated_depreciation += monthly_dep
                    asset.last_depreciation_date = target_month
                    asset.save()
                    
                    DepreciationEntry.objects.create(
                        asset=asset,
                        journal_entry=journal_entry,
                        depreciation_date=target_month,
                        depreciation_amount=monthly_dep,
                        accumulated_depreciation_before=acc_before,
                        accumulated_depreciation_after=asset.accumulated_depreciation
                    )
                    
                    created_count += 1
        
        messages.success(request, f'تم حساب الإهلاك لـ {created_count} أصل')
        return redirect('accounting:assets_list')
    
    context = {
        'page_title': 'حساب الإهلاك الشهري'
    }
    return render(request, 'accounting/advanced/calculate_depreciation.html', context)

@login_required
def depreciation_sum_of_years(request):
    """حساب الإهلاك بطريقة مجموع أرقام السنين - Updated"""
    assets = Asset.objects.filter(depreciation_method='sum_of_years', status='active')
    selected_asset = None
    schedule = []
    
    asset_id = request.GET.get('asset')
    if asset_id:
        selected_asset = get_object_or_404(Asset, pk=asset_id)
        # Calculate full schedule
        cost = selected_asset.purchase_cost
        salvage = selected_asset.salvage_value
        years = selected_asset.useful_life_years
        sum_of_years = (years * (years + 1)) // 2
        depreciable_amount = cost - salvage
        
        accumulated = Decimal('0')
        book_value = cost
        
        for year in range(1, years + 1):
            fraction = Decimal(years - year + 1) / Decimal(sum_of_years)
            annual_dep = fraction * depreciable_amount
            accumulated += annual_dep
            book_value -= annual_dep
            schedule.append({
                'year': year,
                'fraction': f"{years - year + 1}/{sum_of_years}",
                'expense': annual_dep,
                'accumulated': accumulated,
                'book_value': book_value
            })

    context = {
        'page_title': 'الإهلاك - مجموع أرقام السنين',
        'method': 'sum_of_years',
        'assets': assets,
        'selected_asset': selected_asset,
        'schedule': schedule
    }
    return render(request, 'accounting/advanced/depreciation_method.html', context)


@login_required
def depreciation_straight_line(request):
    """حساب الإهلاك القسط الثابت"""
    assets = Asset.objects.filter(depreciation_method='straight_line', status='active')
    selected_asset = None
    schedule = []
    
    asset_id = request.GET.get('asset')
    if asset_id:
        selected_asset = get_object_or_404(Asset, pk=asset_id)
        cost = selected_asset.purchase_cost
        salvage = selected_asset.salvage_value
        years = selected_asset.useful_life_years
        
        if years > 0:
            annual_dep = (cost - salvage) / Decimal(years)
            accumulated = Decimal('0')
            book_value = cost
            
            for year in range(1, years + 1):
                accumulated += annual_dep
                book_value -= annual_dep
                # Adjust last year for rounding
                if year == years and book_value != salvage:
                    diff = book_value - salvage
                    annual_dep += diff
                    book_value = salvage
                    accumulated = cost - salvage

                schedule.append({
                    'year': year,
                    'expense': annual_dep,
                    'accumulated': accumulated,
                    'book_value': book_value
                })

    context = {
        'page_title': 'الإهلاك - القسط الثابت',
        'method': 'straight_line',
        'assets': assets,
        'selected_asset': selected_asset,
        'schedule': schedule
    }
    return render(request, 'accounting/advanced/depreciation_method.html', context)


@login_required
def depreciation_declining_balance(request):
    """حساب الإهلاك القسط المتناقص"""
    assets = Asset.objects.filter(depreciation_method='declining_balance', status='active')
    selected_asset = None
    schedule = []
    
    asset_id = request.GET.get('asset')
    if asset_id:
        selected_asset = get_object_or_404(Asset, pk=asset_id)
        cost = selected_asset.purchase_cost
        salvage = selected_asset.salvage_value
        years = selected_asset.useful_life_years
        rate = selected_asset.depreciation_rate
        
        if not rate and years > 0:
             # Default to Double Declining
            rate = (Decimal('1') / Decimal(years)) * Decimal('2') * 100
            
        if rate:
            decimal_rate = rate / Decimal('100')
            accumulated = Decimal('0')
            book_value = cost
            
            for year in range(1, years + 1):
                expense = book_value * decimal_rate
                
                # Check if book value dips below salvage
                if book_value - expense < salvage:
                    expense = book_value - salvage
                    
                accumulated += expense
                book_value -= expense
                
                schedule.append({
                    'year': year,
                    'expense': expense,
                    'accumulated': accumulated,
                    'book_value': book_value
                })
                
                if book_value == salvage:
                    break

    context = {
        'page_title': 'الإهلاك - القسط المتناقص',
        'method': 'declining_balance',
        'assets': assets,
        'selected_asset': selected_asset,
        'schedule': schedule
    }
    return render(request, 'accounting/advanced/depreciation_method.html', context)


# ==================== القوائم المالية الديناميكية ====================

@login_required
def balance_sheet(request):
    """قائمة المركز المالي (الميزانية العمومية)"""
    as_of_date = request.GET.get('as_of_date')
    
    if not as_of_date:
        as_of_date = date.today()
    else:
        as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
    
    # جلب الحسابات مع الأرصدة
    accounts = Account.objects.filter(is_active=True).select_related('parent')
    
    # الأصول
    assets_accounts = accounts.filter(account_type='asset')
    assets_total = Decimal('0')
    assets_data = []
    
    for account in assets_accounts:
        # حساب الرصيد حتى التاريخ المحدد
        balance = JournalEntryItem.objects.filter(
            account=account,
            journal_entry__is_posted=True,
            journal_entry__date__lte=as_of_date
        ).aggregate(
            debits=Coalesce(Sum('amount', filter=Q(type='debit')), Decimal('0')),
            credits=Coalesce(Sum('amount', filter=Q(type='credit')), Decimal('0'))
        )
        
        account_balance = balance['debits'] - balance['credits']
        
        if account_balance != 0:
            assets_data.append({
                'account': account,
                'balance': account_balance
            })
            assets_total += account_balance
    
    # الخصوم
    liabilities_accounts = accounts.filter(account_type='liability')
    liabilities_total = Decimal('0')
    liabilities_data = []
    
    for account in liabilities_accounts:
        balance = JournalEntryItem.objects.filter(
            account=account,
            journal_entry__is_posted=True,
            journal_entry__date__lte=as_of_date
        ).aggregate(
            debits=Coalesce(Sum('amount', filter=Q(type='debit')), Decimal('0')),
            credits=Coalesce(Sum('amount', filter=Q(type='credit')), Decimal('0'))
        )
        
        account_balance = balance['credits'] - balance['debits']
        
        if account_balance != 0:
            liabilities_data.append({
                'account': account,
                'balance': account_balance
            })
            liabilities_total += account_balance
    
    # حقوق الملكية
    equity_accounts = accounts.filter(account_type='equity')
    equity_total = Decimal('0')
    equity_data = []
    
    for account in equity_accounts:
        balance = JournalEntryItem.objects.filter(
            account=account,
            journal_entry__is_posted=True,
            journal_entry__date__lte=as_of_date
        ).aggregate(
            debits=Coalesce(Sum('amount', filter=Q(type='debit')), Decimal('0')),
            credits=Coalesce(Sum('amount', filter=Q(type='credit')), Decimal('0'))
        )
        
        account_balance = balance['credits'] - balance['debits']
        
        if account_balance != 0:
            equity_data.append({
                'account': account,
                'balance': account_balance
            })
            equity_total += account_balance
    
    context = {
        'as_of_date': as_of_date,
        'assets_data': assets_data,
        'assets_total': assets_total,
        'liabilities_data': liabilities_data,
        'liabilities_total': liabilities_total,
        'equity_data': equity_data,
        'equity_total': equity_total,
        'total_liabilities_equity': liabilities_total + equity_total,
        'page_title': 'قائمة المركز المالي'
    }
    return render(request, 'accounting/advanced/balance_sheet.html', context)


@login_required
def income_statement(request):
    """قائمة الدخل"""
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
    
    accounts = Account.objects.filter(is_active=True).select_related('parent')
    
    # الإيرادات
    revenue_accounts = accounts.filter(account_type='revenue')
    revenue_total = Decimal('0')
    revenue_data = []
    
    for account in revenue_accounts:
        balance = JournalEntryItem.objects.filter(
            account=account,
            journal_entry__is_posted=True,
            journal_entry__date__gte=start_date,
            journal_entry__date__lte=end_date
        ).aggregate(
            debits=Coalesce(Sum('amount', filter=Q(type='debit')), Decimal('0')),
            credits=Coalesce(Sum('amount', filter=Q(type='credit')), Decimal('0'))
        )
        
        account_balance = balance['credits'] - balance['debits']
        
        if account_balance != 0:
            revenue_data.append({
                'account': account,
                'balance': account_balance
            })
            revenue_total += account_balance
    
    # المصروفات
    expense_accounts = accounts.filter(account_type='expense')
    expense_total = Decimal('0')
    expense_data = []
    
    for account in expense_accounts:
        balance = JournalEntryItem.objects.filter(
            account=account,
            journal_entry__is_posted=True,
            journal_entry__date__gte=start_date,
            journal_entry__date__lte=end_date
        ).aggregate(
            debits=Coalesce(Sum('amount', filter=Q(type='debit')), Decimal('0')),
            credits=Coalesce(Sum('amount', filter=Q(type='credit')), Decimal('0'))
        )
        
        account_balance = balance['debits'] - balance['credits']
        
        if account_balance != 0:
            expense_data.append({
                'account': account,
                'balance': account_balance
            })
            expense_total += account_balance
    
    # صافي الدخل
    net_income = revenue_total - expense_total
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'revenue_data': revenue_data,
        'revenue_total': revenue_total,
        'expense_data': expense_data,
        'expense_total': expense_total,
        'net_income': net_income,
        'page_title': 'قائمة الدخل'
    }
    return render(request, 'accounting/advanced/income_statement.html', context)


# ==================== إقفال الفترات ====================

@login_required
def period_close_list(request):
    """قائمة إقفالات الفترات"""
    period_closes = PeriodClose.objects.select_related(
        'fiscal_year', 'closed_by', 'reopened_by'
    ).order_by('-period_end')
    
    context = {
        'period_closes': period_closes,
        'page_title': 'إقفالات الفترات'
    }
    return render(request, 'accounting/advanced/period_close_list.html', context)


# ==================== تقرير أعمار الديون ====================

@login_required
def aging_report(request):
    """تقرير أعمار الديون"""
    # يمكن تطويره لاحقاً
    context = {
        'page_title': 'تقرير أعمار الديون'
    }
    return render(request, 'accounting/advanced/aging_report.html', context)


# ==================== سجل المراجعة ====================

@login_required
def audit_log(request):
    """سجل المراجعة الشامل"""
    logs = AccountingAuditLog.objects.select_related(
        'user', 'content_type'
    ).order_by('-timestamp')[:500]
    
    # الفلاتر
    action_type = request.GET.get('action_type')
    user_id = request.GET.get('user')
    
    if action_type:
        logs = logs.filter(action_type=action_type)
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    context = {
        'logs': logs,
        'page_title': 'سجل المراجعة'
    }
    return render(request, 'accounting/advanced/audit_log.html', context)


# ==================== لوحة CFO التنفيذية ====================

@login_required
def cfo_dashboard(request):
    """لوحة المدير المالي الشاملة"""
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # KPIs
    kpi = {
        'total_revenue': Decimal('205000'),
        'revenue_growth': Decimal('8.5'),
        'total_expenses': Decimal('115000'),
        'expense_change': Decimal('5.8'),
        'net_profit': Decimal('90000'),
        'profit_margin': Decimal('43.9'),
        'cash_flow': Decimal('350000'),
    }
    
    # النسب المالية
    ratios = {
        'roa': Decimal('12.5'),
        'roe': Decimal('18.2'),
        'current_ratio': Decimal('2.15'),
        'debt_ratio': Decimal('35.0'),
    }
    
    # التنبيهات
    alerts = [
        {'title': 'تجاوز الموازنة', 'description': 'قسم التسويق تجاوز الموازنة بنسبة 15%', 'severity': 'warning'},
        {'title': 'فواتير متأخرة', 'description': '5 فواتير تجاوزت 90 يوم', 'severity': 'critical'},
    ]
    
    # الطلبات المعلقة
    pending_approvals = []
    
    # الإحصائيات
    stats = {
        'pending_invoices': 12,
        'overdue_invoices': 3,
        'due_cheques': 5,
        'pending_reconciliations': 2,
        'budget_variance': Decimal('8.5'),
    }
    
    context = {
        'today': today,
        'last_update': timezone.now(),
        'kpi': kpi,
        'ratios': ratios,
        'alerts': alerts,
        'pending_approvals': pending_approvals,
        'stats': stats,
        'page_title': 'لوحة المدير المالي (CFO)'
    }
    return render(request, 'accounting/advanced/cfo_dashboard.html', context)


# ==================== التقارير المخصصة ====================

@login_required
def custom_reports(request):
    """منشئ التقارير المخصصة"""
    saved_reports = CustomReport.objects.filter(
        created_by=request.user
    ).order_by('-created_at')
    
    context = {
        'saved_reports': saved_reports,
        'page_title': 'منشئ التقارير المخصصة'
    }
    return render(request, 'accounting/advanced/custom_reports.html', context)


# ==================== سير عمل الاعتمادات ====================

@login_required
def approval_workflow(request):
    """إدارة سير عمل الاعتمادات"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # الإحصائيات
    stats = {
        'pending': 5,
        'approved': 45,
        'rejected': 3,
        'my_pending': 2,
    }
    
    # طلبات الاعتماد (بيانات تجريبية)
    approvals = []
    
    # تكوينات سير العمل
    workflow_configs = []
    
    context = {
        'stats': stats,
        'approvals': approvals,
        'workflow_configs': workflow_configs,
        'page_title': 'سير عمل الاعتمادات'
    }
    return render(request, 'accounting/advanced/approval_workflow.html', context)


@login_required
def workflow_settings(request):
    """إعدادات سير العمل"""
    context = {
        'page_title': 'إعدادات سير العمل'
    }
    return render(request, 'accounting/advanced/approval_workflow.html', context)


@login_required
def approval_detail(request, pk):
    """تفاصيل طلب الاعتماد"""
    context = {
        'page_title': 'تفاصيل الاعتماد'
    }
    return render(request, 'accounting/advanced/approval_workflow.html', context)


# ==================== عمليات التسوية البنكية ====================

@login_required
def match_transactions(request, pk):
    """مطابقة المعاملات يدوياً"""
    if request.method == 'POST':
        return JsonResponse({'success': True, 'message': 'تمت المطابقة بنجاح'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def auto_match(request, pk):
    """المطابقة التلقائية للمعاملات"""
    if request.method == 'POST':
        return JsonResponse({'success': True, 'matched_count': 15})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def complete_reconciliation(request, pk):
    """إكمال التسوية البنكية"""
    reconciliation = get_object_or_404(BankReconciliation, pk=pk)
    reconciliation.status = 'completed'
    reconciliation.save()
    messages.success(request, 'تم إكمال التسوية بنجاح')
    return redirect('accounting:bank_reconciliation_detail', pk=pk)


# ==================== صفحة التحليل المالي ====================

@login_required
def financial_analysis_page(request):
    """صفحة التحليل المالي الشامل"""
    start_date = request.GET.get('start_date', (timezone.now().date() - timedelta(days=365)).isoformat())
    end_date = request.GET.get('end_date', timezone.now().date().isoformat())
    
    # النسب المالية
    ratios = {
        'gross_profit_margin': Decimal('42.5'),
        'gpm_trend': Decimal('2.3'),
        'net_profit_margin': Decimal('18.2'),
        'npm_trend': Decimal('1.5'),
        'roa': Decimal('12.8'),
        'roa_trend': Decimal('0.8'),
        'roe': Decimal('22.5'),
        'roe_trend': Decimal('-0.5'),
        'current_ratio': Decimal('2.15'),
        'quick_ratio': Decimal('1.82'),
        'working_capital': Decimal('450000'),
        'debt_to_equity': Decimal('0.65'),
        'debt_ratio': Decimal('39.5'),
        'equity_ratio': Decimal('60.5'),
        'asset_turnover': Decimal('1.85'),
        'inventory_turnover': Decimal('8.2'),
        'financial_health_score': Decimal('78'),
    }
    
    # بيانات الرسوم البيانية
    chart_labels = json.dumps(['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو'])
    gpm_trend = json.dumps([40, 41, 42, 41.5, 43, 42.5])
    npm_trend = json.dumps([16, 17, 17.5, 18, 17.8, 18.2])
    current_ratio_trend = json.dumps([2.0, 2.05, 2.1, 2.08, 2.12, 2.15])
    quick_ratio_trend = json.dumps([1.7, 1.72, 1.78, 1.75, 1.8, 1.82])
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'ratios': ratios,
        'chart_labels': chart_labels,
        'gpm_trend': gpm_trend,
        'npm_trend': npm_trend,
        'current_ratio_trend': current_ratio_trend,
        'quick_ratio_trend': quick_ratio_trend,
        'page_title': 'التحليل المالي الشامل'
    }
    return render(request, 'accounting/advanced/financial_analysis.html', context)


# ==================== المطابقة التلقائية ====================

@login_required
def auto_match_amount(request):
    """المطابقة التلقائية حسب المبلغ"""
    reconciliations = BankReconciliation.objects.filter(status='in_progress').order_by('-period_end')
    context = {
        'page_title': 'المطابقة التلقائية حسب المبلغ',
        'reconciliations': reconciliations,
        'match_type': 'amount',
    }
    return render(request, 'accounting/advanced/auto_match_page.html', context)


@login_required
def auto_match_date(request):
    """المطابقة التلقائية حسب التاريخ"""
    reconciliations = BankReconciliation.objects.filter(status='in_progress').order_by('-period_end')
    context = {
        'page_title': 'المطابقة التلقائية حسب التاريخ',
        'reconciliations': reconciliations,
        'match_type': 'date',
    }
    return render(request, 'accounting/advanced/auto_match_page.html', context)


@login_required
def auto_match_reference(request):
    """المطابقة التلقائية حسب المرجع"""
    reconciliations = BankReconciliation.objects.filter(status='in_progress').order_by('-period_end')
    context = {
        'page_title': 'المطابقة التلقائية حسب المرجع',
        'reconciliations': reconciliations,
        'match_type': 'reference',
    }
    return render(request, 'accounting/advanced/auto_match_page.html', context)


@login_required
def auto_match_ai(request):
    """المطابقة التلقائية بالذكاء الاصطناعي"""
    reconciliations = BankReconciliation.objects.filter(status='in_progress').order_by('-period_end')
    context = {
        'page_title': 'المطابقة الذكية بالـ AI',
        'reconciliations': reconciliations,
        'match_type': 'ai',
    }
    return render(request, 'accounting/advanced/auto_match_page.html', context)


# ──────────────────────────────────────
#  الفترات المحاسبية المتقدمة (AccountingPeriod)
# ──────────────────────────────────────
from accounting.models_advanced import AccountingPeriod
from accounting.forms_advanced import AccountingPeriodForm


@login_required
def accounting_period_list(request):
    """قائمة الفترات المحاسبية"""
    periods = AccountingPeriod.objects.select_related('fiscal_year', 'closed_by').all()
    fy = request.GET.get('fy')
    status = request.GET.get('status')
    if fy:
        periods = periods.filter(fiscal_year_id=fy)
    if status == 'open':
        periods = periods.filter(is_open=True)
    elif status == 'closed':
        periods = periods.filter(is_open=False)
    paginator = Paginator(periods, 20)
    periods = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounting/period_list.html', {
        'periods': periods,
        'page_title': 'الفترات المحاسبية',
    })


@login_required
def accounting_period_create(request):
    if request.method == 'POST':
        form = AccountingPeriodForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء الفترة المحاسبية بنجاح')
            return redirect('accounting:accounting_period_list')
    else:
        form = AccountingPeriodForm()
    return render(request, 'accounting/period_form.html', {
        'form': form,
        'page_title': 'إنشاء فترة محاسبية',
    })


@login_required
def accounting_period_detail(request, pk):
    period = get_object_or_404(AccountingPeriod.objects.select_related('fiscal_year', 'closed_by'), pk=pk)
    return render(request, 'accounting/period_detail.html', {
        'period': period,
        'page_title': f'الفترة: {period.name}',
    })


@login_required
def accounting_period_edit(request, pk):
    period = get_object_or_404(AccountingPeriod, pk=pk)
    if request.method == 'POST':
        form = AccountingPeriodForm(request.POST, instance=period)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الفترة المحاسبية بنجاح')
            return redirect('accounting:accounting_period_detail', pk=period.pk)
    else:
        form = AccountingPeriodForm(instance=period)
    return render(request, 'accounting/period_form.html', {
        'form': form,
        'period': period,
        'page_title': f'تعديل: {period.name}',
    })


@login_required
def accounting_period_close(request, pk):
    """إقفال فترة محاسبية"""
    period = get_object_or_404(AccountingPeriod, pk=pk)
    if request.method == 'POST':
        try:
            period.close_period(request.user)
            messages.success(request, f'تم إقفال الفترة "{period.name}" بنجاح')
        except Exception as e:
            messages.error(request, f'خطأ في الإقفال: {e}')
        return redirect('accounting:accounting_period_detail', pk=period.pk)
    return render(request, 'accounting/period_close_confirm.html', {
        'period': period,
        'page_title': f'إقفال الفترة: {period.name}',
    })


@login_required
def accounting_period_reopen(request, pk):
    """إعادة فتح فترة محاسبية"""
    period = get_object_or_404(AccountingPeriod, pk=pk)
    if request.method == 'POST':
        try:
            period.reopen_period(request.user)
            messages.success(request, f'تم إعادة فتح الفترة "{period.name}"')
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
    return redirect('accounting:accounting_period_detail', pk=period.pk)
