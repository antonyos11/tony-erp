"""
Advanced CRM Views
نظام CRM المتقدم - الواجهات
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from .models import Opportunity, SalesStage, ActivityLog, ForecastRecord
from crm.models import Customer, ContactPerson


@login_required
def dashboard(request):
    """لوحة تحكم CRM المتقدمة"""
    
    # الإحصائيات الأساسية
    total_opportunities = Opportunity.objects.count()
    active_opportunities = Opportunity.objects.exclude(status__in=['won', 'lost']).count()
    won_opportunities = Opportunity.objects.filter(status='won').count()
    lost_opportunities = Opportunity.objects.filter(status='lost').count()
    
    # القيم المالية
    total_pipeline_value = Opportunity.objects.exclude(status__in=['won', 'lost']).aggregate(
        total=Sum('expected_value')
    )['total'] or Decimal('0')
    
    weighted_pipeline = Opportunity.objects.exclude(status__in=['won', 'lost']).aggregate(
        total=Sum('weighted_value')
    )['total'] or Decimal('0')
    
    won_value = Opportunity.objects.filter(status='won').aggregate(
        total=Sum('expected_value')
    )['total'] or Decimal('0')
    
    # معدل التحويل
    conversion_rate = (won_opportunities / total_opportunities * 100) if total_opportunities > 0 else 0
    
    # متوسط قيمة الصفقة
    avg_deal_value_res = Opportunity.objects.filter(status='won').aggregate(
        avg=Avg('expected_value')
    )['avg']
    avg_deal_value = Decimal(str(avg_deal_value_res)) if avg_deal_value_res else Decimal('0')
    
    # الفرص حسب المرحلة
    opportunities_by_stage = Opportunity.objects.exclude(status__in=['won', 'lost']).values(
        'stage__name', 'stage__color'
    ).annotate(
        count=Count('id'),
        total_value=Sum('expected_value')
    ).order_by('stage__sequence')
    
    # أفضل 10 فرص
    top_opportunities = Opportunity.objects.exclude(status__in=['won', 'lost']).order_by('-expected_value')[:10]
    
    # الفرص المعرضة للخطر
    at_risk_opportunities = Opportunity.objects.filter(is_at_risk=True).exclude(status__in=['won', 'lost'])[:5]
    
    # الأنشطة الأخيرة
    recent_activities = ActivityLog.objects.select_related('opportunity', 'performed_by').order_by('-activity_date')[:10]
    
    # الفرص التي تحتاج متابعة
    follow_up_needed = Opportunity.objects.filter(
        activities__follow_up_required=True,
        activities__follow_up_date__lte=timezone.now().date() + timedelta(days=7)
    ).distinct()[:5]
    
    # توزيع الفرص حسب الحالة
    status_distribution = Opportunity.objects.values('status').annotate(
        count=Count('id')
    )
    
    # الأداء الشهري (آخر 6 أشهر)
    six_months_ago = timezone.now().date() - timedelta(days=180)
    monthly_performance = []
    for i in range(6):
        month_start = timezone.now().date().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        won_in_month = Opportunity.objects.filter(
            status='won',
            closed_date__gte=month_start,
            closed_date__lte=month_end
        ).aggregate(
            count=Count('id'),
            value=Sum('expected_value')
        )
        
        monthly_performance.append({
            'month': month_start.strftime('%Y-%m'),
            'count': won_in_month['count'] or 0,
            'value': float(won_in_month['value'] or 0)
        })
    
    monthly_performance.reverse()
    
    # العملاء الأكثر قيمة
    top_customers = Customer.objects.annotate(
        total_value=Sum('advanced_opportunities__expected_value', filter=Q(advanced_opportunities__status='won'))
    ).order_by('-total_value')[:10]
    
    context = {
        'page_title': 'لوحة تحكم CRM المتقدمة',
        'total_opportunities': total_opportunities,
        'active_opportunities': active_opportunities,
        'won_opportunities': won_opportunities,
        'lost_opportunities': lost_opportunities,
        'total_pipeline_value': total_pipeline_value,
        'weighted_pipeline': weighted_pipeline,
        'won_value': won_value,
        'conversion_rate': round(conversion_rate, 2),
        'avg_deal_value': avg_deal_value,
        'opportunities_by_stage': opportunities_by_stage,
        'top_opportunities': top_opportunities,
        'at_risk_opportunities': at_risk_opportunities,
        'recent_activities': recent_activities,
        'follow_up_needed': follow_up_needed,
        'status_distribution': status_distribution,
        'monthly_performance': monthly_performance,
        'top_customers': top_customers,
    }
    
    return render(request, 'advanced_crm/dashboard.html', context)


@login_required
def opportunities_list(request):
    """قائمة الفرص"""
    opportunities = Opportunity.objects.select_related('customer', 'stage', 'owner').order_by('-created_date')
    
    # الفلاتر
    status_filter = request.GET.get('status')
    stage_filter = request.GET.get('stage')
    
    if status_filter:
        opportunities = opportunities.filter(status=status_filter)
    if stage_filter:
        opportunities = opportunities.filter(stage_id=stage_filter)
    
    stages = SalesStage.objects.all()
    
    context = {
        'page_title': 'الفرص التجارية',
        'opportunities': opportunities,
        'stages': stages,
    }
    
    return render(request, 'advanced_crm/opportunities_list.html', context)


@login_required
def opportunity_detail(request, pk):
    """تفاصيل الفرصة"""
    opportunity = get_object_or_404(Opportunity, pk=pk)
    activities = opportunity.activities.all().order_by('-activity_date')
    
    context = {
        'page_title': f'الفرصة: {opportunity.title}',
        'opportunity': opportunity,
        'activities': activities,
    }
    
    return render(request, 'advanced_crm/opportunity_detail.html', context)


@login_required
def customer_analytics(request):
    """تحليلات العملاء"""
    
    # إجمالي العملاء
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(status='active').count()
    
    # العملاء الجدد هذا الشهر
    month_start = timezone.now().date().replace(day=1)
    new_customers_this_month = Customer.objects.filter(created_at__gte=month_start).count()
    
    # توزيع العملاء حسب النوع
    customers_by_type = Customer.objects.values('customer_type__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # توزيع العملاء حسب المصدر
    customers_by_source = Customer.objects.values('source__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # القيمة الدائمة للعميل (CLV)
    customers_with_clv = Customer.objects.annotate(
        clv=Sum('advanced_opportunities__expected_value', filter=Q(advanced_opportunities__status='won'))
    ).order_by('-clv')[:20]
    
    # معدل الاحتفاظ بالعملاء
    # (عملاء نشطين / إجمالي العملاء)
    retention_rate = (active_customers / total_customers * 100) if total_customers > 0 else 0
    
    # توزيع العملاء حسب المدينة
    customers_by_city = Customer.objects.values('city').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    context = {
        'page_title': 'تحليلات العملاء',
        'total_customers': total_customers,
        'active_customers': active_customers,
        'new_customers_this_month': new_customers_this_month,
        'customers_by_type': customers_by_type,
        'customers_by_source': customers_by_source,
        'customers_with_clv': customers_with_clv,
        'retention_rate': round(retention_rate, 2),
        'customers_by_city': customers_by_city,
    }
    
    return render(request, 'advanced_crm/customer_analytics.html', context)


@login_required
def sales_forecast(request):
    """التنبؤ بالمبيعات"""
    
    # الفترات المتاحة
    periods = ['هذا الشهر', 'الشهر القادم', 'هذا الربع', 'الربع القادم']
    
    # التنبؤ الحالي
    current_forecast = ForecastRecord.objects.order_by('-forecast_date').first()
    
    # سجل التنبؤات
    forecast_history = ForecastRecord.objects.order_by('-forecast_date')[:12]
    
    # حساب التنبؤ للشهر القادم
    next_month = timezone.now().date() + timedelta(days=30)
    opportunities_next_month = Opportunity.objects.filter(
        expected_close_date__lte=next_month,
        expected_close_date__gte=timezone.now().date()
    ).exclude(status__in=['won', 'lost'])
    
    total_pipeline = opportunities_next_month.aggregate(Sum('expected_value'))['expected_value__sum'] or Decimal('0')
    weighted_pipeline = opportunities_next_month.aggregate(Sum('weighted_value'))['weighted_value__sum'] or Decimal('0')
    
    # متوسط معدل الإغلاق التاريخي
    historical_close_rate = Opportunity.objects.filter(
        status='won'
    ).count() / Opportunity.objects.count() * 100 if Opportunity.objects.count() > 0 else 0
    
    expected_revenue = weighted_pipeline
    
    context = {
        'page_title': 'التنبؤ بالمبيعات',
        'periods': periods,
        'current_forecast': current_forecast,
        'forecast_history': forecast_history,
        'total_pipeline': total_pipeline,
        'weighted_pipeline': weighted_pipeline,
        'expected_revenue': expected_revenue,
        'historical_close_rate': round(historical_close_rate, 2),
        'opportunities_count': opportunities_next_month.count(),
    }
    
    return render(request, 'advanced_crm/sales_forecast.html', context)


@login_required
def customer_journey(request, customer_id):
    """رحلة العميل"""
    customer = get_object_or_404(Customer, pk=customer_id)
    
    # جميع الفرص المرتبطة بالعميل
    opportunities = customer.advanced_opportunities.all().order_by('-created_date')
    
    # جميع الأنشطة
    activities = ActivityLog.objects.filter(
        opportunity__customer=customer
    ).order_by('-activity_date')
    
    # الإحصائيات
    total_opportunities = opportunities.count()
    won_opportunities = opportunities.filter(status='won').count()
    total_value = opportunities.filter(status='won').aggregate(Sum('expected_value'))['expected_value__sum'] or Decimal('0')
    
    context = {
        'page_title': f'رحلة العميل: {customer.full_name}',
        'customer': customer,
        'opportunities': opportunities,
        'activities': activities,
        'total_opportunities': total_opportunities,
        'won_opportunities': won_opportunities,
        'total_value': total_value,
    }
    
    return render(request, 'advanced_crm/customer_journey.html', context)


# API Endpoints

@login_required
def api_pipeline_data(request):
    """بيانات خط الأنابيب للرسوم البيانية"""
    
    pipeline_data = Opportunity.objects.exclude(status__in=['won', 'lost']).values(
        'stage__name', 'stage__sequence'
    ).annotate(
        count=Count('id'),
        value=Sum('expected_value')
    ).order_by('stage__sequence')
    
    data = {
        'labels': [item['stage__name'] for item in pipeline_data],
        'counts': [item['count'] for item in pipeline_data],
        'values': [float(item['value'] or 0) for item in pipeline_data],
    }
    
    return JsonResponse(data)


@login_required
def api_conversion_funnel(request):
    """قمع التحويل"""
    
    stages = SalesStage.objects.order_by('sequence')
    funnel_data = []
    
    for stage in stages:
        count = Opportunity.objects.filter(stage=stage).exclude(status__in=['won', 'lost']).count()
        funnel_data.append({
            'stage': stage.name,
            'count': count,
            'color': stage.color
        })
    
    return JsonResponse({'funnel': funnel_data})
