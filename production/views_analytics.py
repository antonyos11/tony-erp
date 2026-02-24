"""
واجهات التحليلات المتقدمة للإنتاج
Production Analytics Views
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .services import ProductionAnalyticsService


@login_required
@permission_required('production.view_productionorder', raise_exception=True)
def production_analytics_dashboard(request):
    """
    لوحة التحليلات المتقدمة للإنتاج
    """
    # الحصول على فترة التقرير
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # الحصول على KPIs
    kpis = ProductionAnalyticsService.get_production_kpis(start_date, end_date)
    
    # تحديد الاختناقات
    bottlenecks = ProductionAnalyticsService.identify_bottlenecks(start_date, end_date)
    
    # اقتراحات التحسين
    suggestions = ProductionAnalyticsService.get_optimization_suggestions()
    
    context = {
        'kpis': kpis,
        'bottlenecks': bottlenecks,
        'suggestions': suggestions,
        'selected_days': days,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'production/analytics_dashboard.html', context)


@login_required
@require_GET
def production_kpis_api(request):
    """
    API للحصول على مؤشرات الأداء
    """
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    kpis = ProductionAnalyticsService.get_production_kpis(start_date, end_date)
    
    return JsonResponse(kpis)


@login_required
@require_GET
def demand_prediction_api(request, product_id):
    """
    API لتوقع الطلب
    """
    periods = int(request.GET.get('periods', 4))
    period_type = request.GET.get('period_type', 'week')
    
    prediction = ProductionAnalyticsService.predict_demand(
        product_id=product_id,
        periods=periods,
        period_type=period_type
    )
    
    return JsonResponse(prediction)


@login_required
@require_GET
def bottlenecks_api(request):
    """
    API لتحديد الاختناقات
    """
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    bottlenecks = ProductionAnalyticsService.identify_bottlenecks(start_date, end_date)
    
    return JsonResponse({'bottlenecks': bottlenecks})


@login_required
@require_GET
def optimization_suggestions_api(request):
    """
    API للحصول على اقتراحات التحسين
    """
    order_id = request.GET.get('order_id')
    
    if order_id:
        order_id = int(order_id)
    
    suggestions = ProductionAnalyticsService.get_optimization_suggestions(order_id)
    
    return JsonResponse({'suggestions': suggestions})


@login_required
def oee_dashboard(request):
    """
    لوحة OEE (كفاءة المعدات الشاملة)
    """
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    kpis = ProductionAnalyticsService.get_production_kpis(start_date, end_date)
    oee = kpis.get('oee', {})
    
    context = {
        'oee': oee,
        'selected_days': days,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'production/oee_dashboard.html', context)


@login_required
def worker_performance_report(request):
    """
    تقرير أداء العمال المتقدم
    """
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    kpis = ProductionAnalyticsService.get_production_kpis(start_date, end_date)
    worker_productivity = kpis.get('worker_productivity', {})
    
    context = {
        'worker_productivity': worker_productivity,
        'selected_days': days,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'production/worker_performance_report.html', context)


@login_required
def material_efficiency_report(request):
    """
    تقرير كفاءة استخدام المواد
    """
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    kpis = ProductionAnalyticsService.get_production_kpis(start_date, end_date)
    material_efficiency = kpis.get('material_efficiency', {})
    
    context = {
        'material_efficiency': material_efficiency,
        'selected_days': days,
    }
    
    return render(request, 'production/material_efficiency_report.html', context)
