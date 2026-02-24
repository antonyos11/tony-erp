"""
Business Intelligence Views
نظام تحليلات الأعمال والذكاء الاصطناعي
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Dashboard, Widget, Forecast, PredictiveAnalysis, Report


@login_required
def dashboard(request):
    """لوحة تحكم تحليلات الأعمال"""
    
    # إحصائيات عامة
    total_dashboards = Dashboard.objects.count()
    total_forecasts = Forecast.objects.count()
    total_reports = Report.objects.filter(is_active=True).count()
    
    # أحدث التنبؤات
    recent_forecasts = Forecast.objects.order_by('-created_at')[:5]
    
    # أحدث لوحات المعلومات
    user_dashboards = Dashboard.objects.filter(
        Q(owner=request.user) | Q(is_public=True)
    ).order_by('-updated_at')[:6]
    
    # متوسط دقة التنبؤات
    avg_accuracy = Forecast.objects.filter(accuracy__isnull=False).aggregate(
        avg=Avg('accuracy')
    )['avg'] or Decimal('0')
    
    # التحليلات التنبؤية الأخيرة
    recent_analyses = PredictiveAnalysis.objects.order_by('-analysis_date')[:5]
    
    # التقارير المجدولة
    scheduled_reports = Report.objects.filter(is_active=True).exclude(
        frequency='on_demand'
    ).order_by('-last_generated')[:5]
    
    # KPIs
    kpis = {
        'total_dashboards': total_dashboards,
        'total_forecasts': total_forecasts,
        'total_reports': total_reports,
        'avg_accuracy': round(avg_accuracy, 2),
    }
    
    context = {
        'page_title': 'تحليلات الأعمال الذكية',
        'kpis': kpis,
        'recent_forecasts': recent_forecasts,
        'user_dashboards': user_dashboards,
        'recent_analyses': recent_analyses,
        'scheduled_reports': scheduled_reports,
    }
    
    return render(request, 'business_intelligence/dashboard.html', context)


@login_required
def dashboard_list(request):
    """قائمة لوحات المعلومات"""
    dashboards = Dashboard.objects.filter(
        Q(owner=request.user) | Q(is_public=True)
    ).order_by('-updated_at')
    
    context = {
        'page_title': 'لوحات المعلومات',
        'dashboards': dashboards,
    }
    
    return render(request, 'business_intelligence/dashboard_list.html', context)


@login_required
def dashboard_create(request):
    """إنشاء لوحة معلومات جديدة"""
    if request.method == 'POST':
        dashboard = Dashboard.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            owner=request.user,
            layout=request.POST.get('layout', 'grid'),
            theme=request.POST.get('theme', 'auto'),
        )
        return redirect('business_intelligence:dashboard_detail', pk=dashboard.pk)
    
    context = {
        'page_title': 'إنشاء لوحة معلومات',
    }
    
    return render(request, 'business_intelligence/dashboard_form.html', context)


@login_required
def dashboard_detail(request, pk):
    """عرض لوحة معلومات"""
    dashboard = get_object_or_404(Dashboard, pk=pk)
    widgets = dashboard.widgets.all()
    
    context = {
        'page_title': dashboard.name,
        'dashboard': dashboard,
        'widgets': widgets,
    }
    
    return render(request, 'business_intelligence/dashboard_detail.html', context)


@login_required
def forecast_list(request):
    """قائمة التنبؤات"""
    forecasts = Forecast.objects.order_by('-created_at')
    
    # الفلاتر
    forecast_type = request.GET.get('type')
    if forecast_type:
        forecasts = forecasts.filter(forecast_type=forecast_type)
    
    context = {
        'page_title': 'التنبؤات الذكية',
        'forecasts': forecasts,
        'forecast_types': Forecast.FORECAST_TYPE_CHOICES,
    }
    
    return render(request, 'business_intelligence/forecast_list.html', context)


@login_required
def report_list(request):
    """قائمة التقارير"""
    reports = Report.objects.filter(is_active=True).order_by('-updated_at')
    
    context = {
        'page_title': 'التقارير المجدولة',
        'reports': reports,
    }
    
    return render(request, 'business_intelligence/report_list.html', context)


@login_required
def api_kpis(request):
    """API للحصول على مؤشرات الأداء"""
    
    kpis = {
        'forecasts_count': Forecast.objects.count(),
        'avg_accuracy': float(Forecast.objects.filter(accuracy__isnull=False).aggregate(
            avg=Avg('accuracy')
        )['avg'] or 0),
        'active_reports': Report.objects.filter(is_active=True).count(),
        'dashboards_count': Dashboard.objects.count(),
    }
    
    return JsonResponse(kpis)
