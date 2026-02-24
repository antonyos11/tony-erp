"""
واجهات عرض الجدولة التلقائية للإنتاج
Production Scheduling Views

يوفر:
- لوحة التحكم في الجدولة
- جدولة تلقائية للأوامر
- تحليل السعة والاختناقات
- مخطط جانت للإنتاج
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from production.models import (
    ProductionOrder, ProductionOrderStage, ProductionWorkCenter,
    ProductionStage
)
from production.services.scheduling_service import (
    ProductionScheduler, CapacityAnalyzer
)


@login_required
def scheduling_dashboard(request):
    """
    لوحة التحكم في الجدولة
    
    عرض شامل لحالة الجدولة:
    - أوامر الإنتاج المجدولة
    - معدلات استخدام مراكز العمل
    - الاختناقات
    - إحصائيات الأداء
    """
    # تحديد الفترة الزمنية (افتراضياً الشهر الحالي)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        # الافتراضي: من اليوم لـ 30 يوم قادمة
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)
    
    # الحصول على أوامر الإنتاج في هذه الفترة
    orders = ProductionOrder.objects.filter(
        planned_start_date__gte=start_date.date(),
        planned_end_date__lte=end_date.date(),
        status__in=['confirmed', 'in_progress', 'on_hold']
    ).select_related('product', 'bom', 'supervisor')
    
    # تحليل السعة والاختناقات
    bottlenecks = CapacityAnalyzer.identify_bottlenecks(
        start_date, end_date, threshold=80.0
    )
    
    # معدلات استخدام مراكز العمل
    work_centers = ProductionWorkCenter.objects.filter(is_active=True)
    work_center_utilizations = []
    
    for wc in work_centers:
        utilization = CapacityAnalyzer.get_work_center_utilization(
            wc, start_date, end_date
        )
        work_center_utilizations.append(utilization)
    
    # ترتيب حسب معدل الاستخدام
    work_center_utilizations.sort(
        key=lambda x: x['utilization_rate'],
        reverse=True
    )
    
    # إحصائيات عامة
    stats = {
        'total_orders': orders.count(),
        'total_planned_quantity': orders.aggregate(
            total=Sum('planned_quantity')
        )['total'] or 0,
        'high_priority_orders': orders.filter(
            priority__in=['urgent', 'high']
        ).count(),
        'bottlenecks_count': len(bottlenecks),
        'average_utilization': sum(
            u['utilization_rate'] for u in work_center_utilizations
        ) / len(work_center_utilizations) if work_center_utilizations else 0
    }
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'orders': orders,
        'work_center_utilizations': work_center_utilizations,
        'bottlenecks': bottlenecks,
        'stats': stats,
        'page_title': 'لوحة التحكم في جدولة الإنتاج'
    }
    
    return render(request, 'production/scheduling/dashboard.html', context)


@login_required
def auto_schedule_orders(request):
    """
    جدولة تلقائية للأوامر المحددة
    
    POST:
        - order_ids: قائمة معرفات الأوامر
        - optimization_goal: هدف التحسين (minimize_time, balance_load, minimize_cost)
        - start_date: تاريخ البدء المطلوب
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            
            order_ids = data.getlist('order_ids[]') if hasattr(data, 'getlist') else data.get('order_ids', [])
            optimization_goal = data.get('optimization_goal', 'minimize_time')
            start_date_str = data.get('start_date')
            
            if not order_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'يجب اختيار أمر إنتاج واحد على الأقل'
                }, status=400)
            
            # الحصول على الأوامر
            orders = ProductionOrder.objects.filter(
                id__in=order_ids,
                status__in=['draft', 'confirmed']
            )
            
            if not orders.exists():
                return JsonResponse({
                    'success': False,
                    'message': 'لم يتم العثور على أوامر صالحة للجدولة'
                }, status=400)
            
            # تاريخ البدء
            start_date = None
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            
            # تنفيذ الجدولة
            scheduler = ProductionScheduler()
            results = scheduler.schedule_production_orders(
                list(orders),
                start_date=start_date,
                optimization_goal=optimization_goal
            )
            
            # إعداد النتائج للإرجاع
            scheduled_orders_data = []
            for schedule in results['scheduled_orders']:
                scheduled_orders_data.append({
                    'order_number': schedule['order'].number,
                    'product_name': schedule['order'].product.name,
                    'start_date': schedule['estimated_start_date'].strftime('%Y-%m-%d %H:%M'),
                    'end_date': schedule['estimated_end_date'].strftime('%Y-%m-%d %H:%M'),
                    'duration_hours': float(schedule['total_duration_hours']),
                    'estimated_cost': float(schedule['total_estimated_cost'])
                })
            
            messages.success(
                request,
                f'تم جدولة {len(scheduled_orders_data)} أمر إنتاج بنجاح'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'تمت الجدولة بنجاح',
                'results': {
                    'scheduled_orders': scheduled_orders_data,
                    'statistics': results['statistics'],
                    'warnings': results['warnings']
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ أثناء الجدولة: {str(e)}'
            }, status=500)
    
    # GET: عرض صفحة الجدولة
    orders = ProductionOrder.objects.filter(
        status__in=['draft', 'confirmed']
    ).select_related('product', 'bom').order_by('-priority', 'planned_start_date')
    
    context = {
        'orders': orders,
        'page_title': 'جدولة تلقائية لأوامر الإنتاج'
    }
    
    return render(request, 'production/scheduling/auto_schedule.html', context)


@login_required
def gantt_chart_view(request):
    """
    عرض مخطط جانت للإنتاج
    
    يعرض الجدول الزمني للأوامر والمراحل على شكل مخطط جانت تفاعلي
    """
    # تحديد الفترة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    work_center_id = request.GET.get('work_center')
    
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)
    
    # بناء استعلام المراحل
    stages_query = ProductionOrderStage.objects.filter(
        planned_start_date__isnull=False,
        planned_end_date__isnull=False,
        planned_start_date__gte=start_date,
        planned_end_date__lte=end_date
    ).select_related(
        'production_order',
        'production_order__product',
        'stage'
    )
    
    # تصفية حسب مركز العمل إن وجد
    if work_center_id:
        stages_query = stages_query.filter(stage__work_center__id=work_center_id)
    
    # بناء بيانات مخطط جانت
    gantt_data = []
    
    for stage in stages_query:
        gantt_data.append({
            'id': f'stage_{stage.id}',
            'order_number': stage.production_order.number,
            'product_name': stage.production_order.product.name,
            'stage_name': stage.stage.name,
            'start': stage.planned_start_date.isoformat(),
            'end': stage.planned_end_date.isoformat(),
            'status': stage.get_status_display(),
            'progress': float(
                (stage.completed_quantity / stage.planned_quantity * 100)
                if stage.planned_quantity > 0 else 0
            ),
            'priority': stage.production_order.priority,
            'color': _get_stage_color(stage.status)
        })
    
    # مراكز العمل للتصفية
    work_centers = ProductionWorkCenter.objects.filter(is_active=True)
    
    context = {
        'gantt_data': json.dumps(gantt_data),
        'start_date': start_date,
        'end_date': end_date,
        'work_centers': work_centers,
        'selected_work_center': work_center_id,
        'page_title': 'مخطط جانت للإنتاج'
    }
    
    return render(request, 'production/scheduling/gantt_chart.html', context)


@login_required
def capacity_analysis_view(request):
    """
    تحليل مفصل للسعة
    
    يعرض:
    - معدلات استخدام مراكز العمل
    - الاختناقات
    - توقعات الحمل المستقبلي
    """
    # الفترة الزمنية
    weeks_ahead = int(request.GET.get('weeks', 4))
    start_date = timezone.now()
    end_date = start_date + timedelta(weeks=weeks_ahead)
    
    # تحليل كل مركز عمل
    work_centers_analysis = []
    work_centers = ProductionWorkCenter.objects.filter(is_active=True)
    
    for wc in work_centers:
        utilization = CapacityAnalyzer.get_work_center_utilization(
            wc, start_date, end_date
        )
        
        # تحليل أسبوعي
        weekly_analysis = []
        current_week_start = start_date
        
        for week in range(weeks_ahead):
            week_end = current_week_start + timedelta(days=7)
            week_util = CapacityAnalyzer.get_work_center_utilization(
                wc, current_week_start, week_end
            )
            weekly_analysis.append({
                'week': week + 1,
                'start': current_week_start.date(),
                'end': week_end.date(),
                'utilization': week_util['utilization_rate']
            })
            current_week_start = week_end
        
        work_centers_analysis.append({
            'work_center': wc,
            'overall_utilization': utilization,
            'weekly_analysis': weekly_analysis
        })
    
    # تحديد الاختناقات
    bottlenecks = CapacityAnalyzer.identify_bottlenecks(
        start_date, end_date, threshold=75.0
    )
    
    context = {
        'work_centers_analysis': work_centers_analysis,
        'bottlenecks': bottlenecks,
        'start_date': start_date,
        'end_date': end_date,
        'weeks_ahead': weeks_ahead,
        'page_title': 'تحليل السعة الإنتاجية'
    }
    
    return render(request, 'production/scheduling/capacity_analysis.html', context)


@login_required
def reschedule_order(request, order_id):
    """
    إعادة جدولة أمر إنتاج محدد
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    
    if request.method == 'POST':
        try:
            new_start_date_str = request.POST.get('new_start_date')
            optimization_goal = request.POST.get('optimization_goal', 'minimize_time')
            
            if not new_start_date_str:
                messages.error(request, 'يجب تحديد تاريخ البدء الجديد')
                return redirect('production:scheduling_dashboard')
            
            new_start_date = datetime.strptime(new_start_date_str, '%Y-%m-%d')
            
            # إعادة الجدولة
            scheduler = ProductionScheduler()
            results = scheduler.schedule_production_orders(
                [order],
                start_date=new_start_date,
                optimization_goal=optimization_goal
            )
            
            if results['scheduled_orders']:
                messages.success(
                    request,
                    f'تمت إعادة جدولة أمر الإنتاج {order.number} بنجاح'
                )
            else:
                messages.warning(request, 'لم يتم إعادة الجدولة بشكل كامل')
            
            return redirect('production:production_order_detail', pk=order_id)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
            return redirect('production:scheduling_dashboard')
    
    context = {
        'order': order,
        'page_title': f'إعادة جدولة أمر الإنتاج {order.number}'
    }
    
    return render(request, 'production/scheduling/reschedule_order.html', context)


@login_required
def check_conflicts_ajax(request):
    """
    فحص تعارضات السعة (AJAX)
    
    POST:
        - start_date: تاريخ البدء
        - end_date: تاريخ الانتهاء
        - work_center_id: (اختياري) معرف مركز العمل
    
    Returns:
        JSON: قائمة التعارضات
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
            work_center_id = data.get('work_center_id')
            
            work_center = None
            if work_center_id:
                work_center = ProductionWorkCenter.objects.get(id=work_center_id)
            
            scheduler = ProductionScheduler()
            conflicts = scheduler.check_capacity_conflicts(
                start_date, end_date, work_center
            )
            
            return JsonResponse({
                'success': True,
                'conflicts': conflicts,
                'conflicts_count': len(conflicts)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def _get_stage_color(status: str) -> str:
    """
    الحصول على لون المرحلة حسب الحالة
    """
    colors = {
        'pending': '#6c757d',      # رمادي
        'ready': '#17a2b8',        # أزرق فاتح
        'in_progress': '#ffc107',  # أصفر
        'quality_check': '#fd7e14', # برتقالي
        'completed': '#28a745',    # أخضر
        'on_hold': '#dc3545',      # أحمر
        'cancelled': '#343a40'     # رمادي داكن
    }
    return colors.get(status, '#6c757d')


@login_required
def optimize_schedule_view(request):
    """
    تحسين الجدولة باستخدام خوارزميات متقدمة
    """
    if request.method == 'POST':
        try:
            order_ids = request.POST.getlist('order_ids[]')
            optimization_type = request.POST.get('optimization_type', 'greedy')
            
            if not order_ids:
                messages.error(request, 'يجب اختيار أوامر للتحسين')
                return redirect('production:scheduling_dashboard')
            
            orders = ProductionOrder.objects.filter(id__in=order_ids)
            
            scheduler = ProductionScheduler()
            results = scheduler.optimize_schedule(list(orders), optimization_type)
            
            messages.success(
                request,
                f'تم تحسين جدولة {len(results["scheduled_orders"])} أمر'
            )
            
            return redirect('production:scheduling_dashboard')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
            return redirect('production:scheduling_dashboard')
    
    # GET: عرض خيارات التحسين
    orders = ProductionOrder.objects.filter(
        status__in=['confirmed', 'on_hold']
    ).select_related('product')
    
    context = {
        'orders': orders,
        'page_title': 'تحسين الجدولة'
    }
    
    return render(request, 'production/scheduling/optimize.html', context)
