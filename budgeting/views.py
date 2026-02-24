from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum, F
from django.utils import timezone
from .models import FiscalYear, Budget, BudgetLine, BudgetAlert, BudgetTransfer
from .forms import FiscalYearForm, BudgetForm, BudgetLineForm

@login_required
def dashboard(request):
    """Budget dashboard with overview"""
    current_fiscal_year = FiscalYear.objects.filter(is_current=True).first()
    budgets = Budget.objects.filter(fiscal_year=current_fiscal_year) if current_fiscal_year else Budget.objects.none()
    
    total_budgeted = budgets.aggregate(total=Sum('total_amount'))['total'] or 0
    total_spent = BudgetLine.objects.filter(budget__in=budgets).aggregate(total=Sum('actual_amount'))['total'] or 0
    
    alerts = BudgetAlert.objects.filter(is_read=False).order_by('-created_at')[:10]
    
    context = {
        'current_fiscal_year': current_fiscal_year,
        'budgets': budgets,
        'total_budgeted': total_budgeted,
        'total_spent': total_spent,
        'remaining': total_budgeted - total_spent,
        'alerts': alerts,
    }
    return render(request, 'budgeting/dashboard.html', context)

@login_required
def fiscal_year_list(request):
    """List all fiscal years"""
    fiscal_years = FiscalYear.objects.all().order_by('-start_date')
    return render(request, 'budgeting/fiscal_year_list.html', {'fiscal_years': fiscal_years})

@login_required
@permission_required('budgeting.add_fiscalyear')
def fiscal_year_create(request):
    """Create new fiscal year"""
    if request.method == 'POST':
        form = FiscalYearForm(request.POST)
        if form.is_valid():
            fiscal_year = form.save(commit=False)
            fiscal_year.created_by = request.user
            fiscal_year.save()
            messages.success(request, 'تم إنشاء السنة المالية بنجاح')
            return redirect('budgeting:fiscal_year_list')
    else:
        form = FiscalYearForm()
    return render(request, 'budgeting/fiscal_year_form.html', {'form': form, 'title': 'إنشاء سنة مالية'})

@login_required
def budget_list(request):
    """List all budgets"""
    budgets = Budget.objects.all().select_related('fiscal_year').order_by('-created_at')
    return render(request, 'budgeting/budget_list.html', {'budgets': budgets})

@login_required
def budget_detail(request, pk):
    """Budget detail with lines"""
    budget = get_object_or_404(Budget, pk=pk)
    lines = budget.lines.all().select_related('account')
    
    total_planned = lines.aggregate(total=Sum('planned_amount'))['total'] or 0
    total_actual = lines.aggregate(total=Sum('actual_amount'))['total'] or 0
    
    context = {
        'budget': budget,
        'lines': lines,
        'total_planned': total_planned,
        'total_actual': total_actual,
        'variance': total_planned - total_actual,
    }
    return render(request, 'budgeting/budget_detail.html', context)

@login_required
@permission_required('budgeting.add_budget')
def budget_create(request):
    """Create new budget"""
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.created_by = request.user
            budget.save()
            messages.success(request, 'تم إنشاء الميزانية بنجاح')
            return redirect('budgeting:budget_detail', pk=budget.pk)
    else:
        form = BudgetForm()
    return render(request, 'budgeting/budget_form.html', {'form': form, 'title': 'إنشاء ميزانية'})

@login_required
@permission_required('budgeting.change_budget')
def budget_edit(request, pk):
    """Edit budget"""
    budget = get_object_or_404(Budget, pk=pk)
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.updated_by = request.user
            budget.save()
            messages.success(request, 'تم تحديث الميزانية بنجاح')
            return redirect('budgeting:budget_detail', pk=budget.pk)
    else:
        form = BudgetForm(instance=budget)
    return render(request, 'budgeting/budget_form.html', {'form': form, 'budget': budget, 'title': 'تعديل ميزانية'})

@login_required
def variance_report(request):
    """Budget variance report"""
    fiscal_year_id = request.GET.get('fiscal_year')
    if fiscal_year_id:
        fiscal_year = get_object_or_404(FiscalYear, pk=fiscal_year_id)
    else:
        fiscal_year = FiscalYear.objects.filter(is_current=True).first()
    
    budgets = Budget.objects.filter(fiscal_year=fiscal_year) if fiscal_year else Budget.objects.none()
    
    report_data = []
    for budget in budgets:
        lines = budget.lines.all()
        total_planned = lines.aggregate(total=Sum('planned_amount'))['total'] or 0
        total_actual = lines.aggregate(total=Sum('actual_amount'))['total'] or 0
        variance = total_planned - total_actual
        variance_pct = (variance / total_planned * 100) if total_planned else 0
        
        report_data.append({
            'budget': budget,
            'total_planned': total_planned,
            'total_actual': total_actual,
            'variance': variance,
            'variance_pct': variance_pct,
        })
    
    context = {
        'fiscal_year': fiscal_year,
        'fiscal_years': FiscalYear.objects.all(),
        'report_data': report_data,
    }
    return render(request, 'budgeting/variance_report.html', context)

@login_required
def alert_list(request):
    """List budget alerts"""
    alerts = BudgetAlert.objects.all().select_related('budget').order_by('-created_at')
    return render(request, 'budgeting/alert_list.html', {'alerts': alerts})

@login_required
def mark_alert_read(request, pk):
    """Mark alert as read"""
    alert = get_object_or_404(BudgetAlert, pk=pk)
    alert.is_read = True
    alert.save()
    messages.success(request, 'تم تحديد التنبيه كمقروء')
    return redirect('budgeting:alert_list')
