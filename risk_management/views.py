"""
Risk Management Views
نظام إدارة المخاطر - الواجهات الكاملة
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from django.db.models.functions import TruncMonth
from .models import Risk, RiskCategory


@login_required
def dashboard(request):
    """لوحة تحكم إدارة المخاطر"""
    
    # الإحصائيات الأساسية
    total_risks = Risk.objects.count()
    # الحالات النشطة: identified, assessed, mitigating, monitored
    active_statuses = ['identified', 'assessed', 'mitigating', 'monitored']
    active_risks = Risk.objects.filter(status__in=active_statuses).count()
    mitigated_risks = Risk.objects.filter(status='mitigating').count()
    
    # توزيع المخاطر حسب المستوى (بناءً على الدرجة: high >= 12, medium >= 6)
    high_risks = Risk.objects.filter(risk_score__gte=12, status__in=active_statuses).count()
    medium_risks = Risk.objects.filter(risk_score__gte=6, risk_score__lt=12, status__in=active_statuses).count()
    low_risks = Risk.objects.filter(risk_score__lt=6, status__in=active_statuses).count()
    
    # نسبة المخاطر المخففة
    mitigation_rate = (mitigated_risks / total_risks * 100) if total_risks > 0 else 0
    
    # أهم 10 مخاطر
    top_risks = Risk.objects.filter(status__in=active_statuses).order_by('-risk_score')[:10]
    
    # المخاطر حسب الفئة
    risks_by_category = Risk.objects.values('category__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # المخاطر حسب الحالة
    risks_by_department = Risk.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # خطط التخفيف النشطة
    active_mitigation_plans = Risk.objects.exclude(mitigation_plan='').exclude(status='closed').count()
    
    # الاتجاه الشهري
    six_months_ago = timezone.now().date() - timedelta(days=180)
    monthly_trend = Risk.objects.filter(
        identified_date__gte=six_months_ago
    ).annotate(month=TruncMonth('identified_date')).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    context = {
        'page_title': 'لوحة تحكم إدارة المخاطر',
        'total_risks': total_risks,
        'active_risks': active_risks,
        'mitigated_risks': mitigated_risks,
        'high_risks': high_risks,
        'medium_risks': medium_risks,
        'low_risks': low_risks,
        'mitigation_rate': round(mitigation_rate, 2),
        'top_risks': top_risks,
        'risks_by_category': risks_by_category,
        'risks_by_department': risks_by_department,
        'active_mitigation_plans': active_mitigation_plans,
        'monthly_trend': monthly_trend,
    }
    
    return render(request, 'risk_management/dashboard.html', context)


@login_required
def risks_list(request):
    """قائمة المخاطر"""
    risks = Risk.objects.select_related('category', 'owner').order_by('-risk_score')
    
    # الفلاتر
    level_filter = request.GET.get('level')
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    
    if level_filter == 'high':
        risks = risks.filter(risk_score__gte=12)
    elif level_filter == 'medium':
        risks = risks.filter(risk_score__gte=6, risk_score__lt=12)
    elif level_filter == 'low':
        risks = risks.filter(risk_score__lt=6)
    if status_filter:
        risks = risks.filter(status=status_filter)
    if category_filter:
        risks = risks.filter(category_id=category_filter)
    
    categories = RiskCategory.objects.all()
    
    context = {
        'page_title': 'سجل المخاطر',
        'risks': risks,
        'categories': categories,
    }
    
    return render(request, 'risk_management/risks_list.html', context)


@login_required
def risk_detail(request, pk):
    """تفاصيل المخاطر"""
    risk = get_object_or_404(Risk, pk=pk)
    assessments = risk.assessments.all().order_by('-assessment_date')
    mitigation_plans = risk.mitigation_plans.all().order_by('-created_at')
    
    context = {
        'page_title': f'المخاطر: {risk.title}',
        'risk': risk,
        'assessments': assessments,
        'mitigation_plans': mitigation_plans,
    }
    
    return render(request, 'risk_management/risk_detail.html', context)


@login_required
def risk_matrix(request):
    """مصفوفة المخاطر"""
    
    # المخاطر حسب الاحتمالية والتأثير
    risks = Risk.objects.filter(status='active')
    
    # تجميع حسب المستوى
    matrix_data = []
    for risk in risks:
        matrix_data.append({
            'title': risk.title,
            'probability': risk.probability,
            'impact': risk.impact,
            'level': risk.risk_level,
            'score': risk.risk_score,
        })
    
    context = {
        'page_title': 'مصفوفة المخاطر',
        'matrix_data': matrix_data,
    }
    
    return render(request, 'risk_management/risk_matrix.html', context)


@login_required
def mitigation_plans_list(request):
    """قائمة خطط التخفيف"""
    
    plans = Risk.objects.exclude(mitigation_plan='').order_by('-created_at')
    
    context = {
        'page_title': 'خطط التخفيف',
        'plans': plans,
    }
    
    return render(request, 'risk_management/mitigation_plans_list.html', context)


@login_required
def api_risk_heatmap(request):
    """بيانات الخريطة الحرارية للمخاطر"""
    
    risks = Risk.objects.filter(status='active')
    
    data = {
        'risks': [
            {
                'title': risk.title,
                'probability': risk.probability,
                'impact': risk.impact,
                'level': risk.risk_level,
                'score': risk.risk_score,
            }
            for risk in risks
        ]
    }
    
    return JsonResponse(data)


@login_required
def api_risk_trend(request):
    """اتجاه المخاطر"""
    
    six_months_ago = timezone.now().date() - timedelta(days=180)
    trend = Risk.objects.filter(
        identified_date__gte=six_months_ago
    ).annotate(month=TruncMonth('identified_date')).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    data = {
        'trend': list(trend)
    }
    
    return JsonResponse(data)
