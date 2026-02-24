"""
Monitoring Module - Django ل Views
View functions for anomaly detection and monitoring dashboards
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from . import anomaly_detection as anomaly_module


@login_required
def anomaly_dashboard(request):
    """
    لوحة تحكم كشف الشذوذات
    Main dashboard for anomaly detection system
    """
    # Get recent alerts
    alerts = anomaly_module.AnomalyAlert.objects.all().order_by('-detected_at')[:20]
    
    # Statistics
    stats = {
        'total_alerts': anomaly_module.AnomalyAlert.objects.count(),
        'critical_alerts': anomaly_module.AnomalyAlert.objects.filter(severity='critical', status='new').count(),
        'high_alerts': anomaly_module.AnomalyAlert.objects.filter(severity='high', status='new').count(),
        'resolved_today': anomaly_module.AnomalyAlert.objects.filter(
            status='resolved',
            resolved_at__date=anomaly_module.timezone.now().date()
        ).count(),
    }
    
    context = {
        'title': 'كشف الشذوذات',
        'alerts': alerts,
        'stats': stats,
    }
    return render(request, 'monitoring/anomaly_dashboard.html', context)


@login_required
def anomaly_alerts(request):
    """عرض جميع التنبيهات"""
    status = request.GET.get('status', '')
    severity = request.GET.get('severity', '')
    category = request.GET.get('category', '')
    
    alerts = anomaly_module.AnomalyAlert.objects.all()
    
    if status:
        alerts = alerts.filter(status=status)
    if severity:
        alerts = alerts.filter(severity=severity)  
    if category:
        alerts = alerts.filter(category=category)
    
    alerts = alerts.order_by('-detected_at')
    
    context = {
        'title': 'جميع التنبيهات',
        'alerts': alerts,
        'status_filter': status,
        'severity_filter': severity,
        'category_filter': category,
    }
    return render(request, 'monitoring/anomaly_alerts.html', context)


@login_required
def anomaly_config(request):
    """إعدادات نظام كشف الشذوذات"""
    context = {
        'title': 'إعدادات كشف الشذوذات',
        'threshold': 2.5,  # عدد الانحرافات المعيارية
    }
    return render(request, 'monitoring/anomaly_config.html', context)


@login_required
def anomaly_history(request):
    """سجل الشذوذات"""
    alerts = anomaly_module.AnomalyAlert.objects.filter(
        status__in=['resolved', 'false_positive']
    ).order_by('-detected_at')[:100]
    
    context = {
        'title': 'سجل الشذوذات',
        'alerts': alerts,
    }
    return render(request, 'monitoring/anomaly_history.html', context)


@login_required
def run_anomaly_check(request):
    """تشغيل فحص الشذوذات يدوياً (API)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    detector = anomaly_module.AnomalyDetectionService()
    results = detector.run_all_detections()
    
    total_alerts = sum(len(alerts) for alerts in results.values())
    
    return JsonResponse({
        'success': True,
        'total_alerts': total_alerts,
        'breakdown': {
            cat: len(alerts) for cat, alerts in results.items()
        }
    })
