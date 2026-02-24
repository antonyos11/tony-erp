from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SalesForecast, ForecastPeriod, DemandPattern, InventoryRecommendation

@login_required
def dashboard(request):
    """لوحة التحكم الرئيسية للتنبؤ بالمبيعات"""
    forecasts = SalesForecast.objects.select_related('period', 'product').order_by('-created_at')[:10]
    periods = ForecastPeriod.objects.filter(is_active=True).order_by('-start_date')
    
    context = {
        'forecasts': forecasts,
        'periods': periods,
        'page_title': 'التنبؤ بالمبيعات AI',
    }
    return render(request, 'sales_forecasting/dashboard.html', context)

@login_required
def forecast_list(request):
    """قائمة جميع التنبؤات"""
    forecasts = SalesForecast.objects.select_related('period', 'product').order_by('-created_at')
    context = {
        'forecasts': forecasts,
        'page_title': 'قائمة التنبؤات',
    }
    return render(request, 'sales_forecasting/forecast_list.html', context)

@login_required
def forecast_create(request):
    """إنشاء تنبؤ جديد"""
    if request.method == 'POST':
        # Logic for creating forecast
        messages.success(request, 'تم إنشاء التنبؤ بنجاح!')
        return redirect('sales_forecasting:dashboard')
    
    context = {
        'page_title': 'إنشاء تنبؤ جديد',
    }
    return render(request, 'sales_forecasting/forecast_create.html', context)

@login_required
def demand_patterns(request):
    """أنماط الطلب"""
    patterns = DemandPattern.objects.select_related('product').order_by('-created_at')
    context = {
        'patterns': patterns,
        'page_title': 'أنماط الطلب',
    }
    return render(request, 'sales_forecasting/demand_patterns.html', context)

@login_required
def recommendations(request):
    """توصيات المخزون"""
    recommendations = InventoryRecommendation.objects.select_related('product').order_by('-created_at')
    context = {
        'recommendations': recommendations,
        'page_title': 'توصيات المخزون',
    }
    return render(request, 'sales_forecasting/recommendations.html', context)
