"""
Treasury Management Views
نظام إدارة الخزانة - الواجهات الكاملة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from .models import CashPosition, CashFlow, Investment, TreasuryTarget
from accounting.models import Account, JournalEntry


@login_required
def dashboard(request):
    """لوحة تحكم إدارة الخزانة"""
    
    # الموقف النقدي الحالي
    latest_position = CashPosition.objects.order_by('-position_date').first()
    
    # إحصائيات السيولة
    total_cash = (latest_position.bank_balance + latest_position.cash_on_hand) if latest_position else Decimal('0')
    total_investments = Investment.objects.filter(status='active').aggregate(
        total=Sum('current_value')
    )['total'] or Decimal('0')
    
    total_liquidity = total_cash + total_investments
    
    # الاستثمارات
    active_investments_count = Investment.objects.filter(status='active').count()
    total_investment_value = Investment.objects.filter(status='active').aggregate(
        total=Sum('principal_amount')
    )['total'] or Decimal('0')
    
    # العائد على الاستثمارات
    avg_roi = Investment.objects.filter(status='active').aggregate(
        avg=Avg('expected_return_rate')
    )['avg'] or Decimal('0')
    
    # التدفقات النقدية المتوقعة (30 يوم)
    thirty_days_later = timezone.now().date() + timedelta(days=30)
    upcoming_cashflows = CashFlow.objects.filter(
        forecast_date__lte=thirty_days_later,
        forecast_date__gte=timezone.now().date()
    ).order_by('forecast_date')[:10]
    
    # الاستثمارات القريبة من الاستحقاق
    sixty_days_later = timezone.now().date() + timedelta(days=60)
    maturing_investments = Investment.objects.filter(
        status='active',
        maturity_date__lte=sixty_days_later,
        maturity_date__gte=timezone.now().date()
    ).order_by('maturity_date')[:5]
    
    # الأهداف
    active_targets = TreasuryTarget.objects.filter(status='in_progress')
    
    # توزيع الاستثمارات حسب النوع
    investments_by_type = Investment.objects.filter(status='active').values(
        'investment_type'
    ).annotate(
        count=Count('id'),
        total_value=Sum('current_value')
    )
    
    # التدفقات النقدية (آخر 6 أشهر)
    six_months_ago = timezone.now().date() - timedelta(days=180)
    cashflow_history = CashFlow.objects.filter(
        forecast_date__gte=six_months_ago
    ).order_by('forecast_date')
    
    context = {
        'page_title': 'لوحة تحكم إدارة الخزانة',
        'latest_position': latest_position,
        'total_cash': total_cash,
        'total_investments': total_investments,
        'total_liquidity': total_liquidity,
        'active_investments_count': active_investments_count,
        'total_investment_value': total_investment_value,
        'avg_roi': avg_roi,
        'upcoming_cashflows': upcoming_cashflows,
        'maturing_investments': maturing_investments,
        'active_targets': active_targets,
        'investments_by_type': investments_by_type,
        'cashflow_history': cashflow_history,
    }
    
    return render(request, 'treasury_management/dashboard.html', context)


@login_required
def cash_flow_forecast(request):
    """التنبؤ بالتدفقات النقدية"""
    
    # التنبؤات المستقبلية
    future_forecasts = CashFlow.objects.filter(
        forecast_date__gte=timezone.now().date()
    ).order_by('forecast_date')[:30]
    
    # التنبؤات التاريخية
    historical_forecasts = CashFlow.objects.filter(
        forecast_date__lt=timezone.now().date()
    ).order_by('-forecast_date')[:30]
    
    # الدقة المتوسطة
    avg_accuracy = CashFlow.objects.filter(
        accuracy_score__isnull=False
    ).aggregate(avg=Avg('accuracy_score'))['avg'] or Decimal('0')
    
    context = {
        'page_title': 'التنبؤ بالتدفقات النقدية',
        'future_forecasts': future_forecasts,
        'historical_forecasts': historical_forecasts,
        'avg_accuracy': avg_accuracy,
    }
    
    return render(request, 'treasury_management/cash_flow_forecast.html', context)


@login_required
def investments_list(request):
    """قائمة الاستثمارات"""
    
    investments = Investment.objects.all().order_by('-investment_date')
    
    # الفلاتر
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    
    if status_filter:
        investments = investments.filter(status=status_filter)
    if type_filter:
        investments = investments.filter(investment_type=type_filter)
    
    # الإحصائيات
    total_principal = investments.aggregate(Sum('principal_amount'))['principal_amount__sum'] or Decimal('0')
    total_current_value = investments.aggregate(Sum('current_value'))['current_value__sum'] or Decimal('0')
    total_return = total_current_value - total_principal
    
    context = {
        'page_title': 'الاستثمارات',
        'investments': investments,
        'total_principal': total_principal,
        'total_current_value': total_current_value,
        'total_return': total_return,
    }
    
    return render(request, 'treasury_management/investments_list.html', context)


@login_required
def investment_detail(request, pk):
    """تفاصيل الاستثمار"""
    
    investment = get_object_or_404(Investment, pk=pk)
    roi = investment.get_roi()
    
    context = {
        'page_title': f'الاستثمار: {investment.description}',
        'investment': investment,
        'roi': roi,
    }
    
    return render(request, 'treasury_management/investment_detail.html', context)


@login_required
def liquidity_analysis(request):
    """تحليل السيولة"""
    
    # آخر 12 موقف سيولة
    positions = CashPosition.objects.order_by('-position_date')[:12]
    
    # المتوسطات
    avg_liquidity = CashPosition.objects.aggregate(
        avg=Avg('total_liquidity')
    )['avg'] or Decimal('0')
    
    avg_ratio = CashPosition.objects.aggregate(
        avg=Avg('liquidity_ratio')
    )['avg'] or Decimal('0')
    
    context = {
        'page_title': 'تحليل السيولة',
        'positions': positions,
        'avg_liquidity': avg_liquidity,
        'avg_ratio': avg_ratio,
    }
    
    return render(request, 'treasury_management/liquidity_analysis.html', context)


@login_required
def treasury_targets(request):
    """أهداف الخزانة"""
    
    targets = TreasuryTarget.objects.all().order_by('-start_date')
    
    context = {
        'page_title': 'أهداف الخزانة',
        'targets': targets,
    }
    
    return render(request, 'treasury_management/treasury_targets.html', context)


# API Endpoints

@login_required
def api_cashflow_chart(request):
    """بيانات الرسم البياني للتدفقات النقدية"""
    
    cashflows = CashFlow.objects.order_by('forecast_date')[:30]
    
    data = {
        'dates': [cf.forecast_date.strftime('%Y-%m-%d') for cf in cashflows],
        'inflows': [float(cf.inflows) for cf in cashflows],
        'outflows': [float(cf.outflows) for cf in cashflows],
        'balances': [float(cf.closing_balance) for cf in cashflows],
    }
    
    return JsonResponse(data)


@login_required
def api_investment_performance(request):
    """أداء الاستثمارات"""
    
    investments = Investment.objects.filter(status='active')
    
    data = {
        'labels': [inv.description for inv in investments],
        'values': [float(inv.current_value) for inv in investments],
        'returns': [float(inv.get_roi()) for inv in investments],
    }
    
    return JsonResponse(data)
