"""
تقارير الإنتاج اليومية والشهرية
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q, F, Avg, Min, Max
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json


@login_required
def production_daily_report(request):
    """تقرير الإنتاج اليومي"""
    from production.models import ProductionOrder
    from inventory.models import Product
    
    # التاريخ المحدد أو اليوم
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()
    
    # أوامر الإنتاج لهذا اليوم
    orders = ProductionOrder.objects.filter(
        order_date=report_date
    ).select_related('product', 'bom', 'supervisor')
    
    # الإحصائيات
    total_orders = orders.count()
    completed_orders = orders.filter(status='completed').count()
    in_progress_orders = orders.filter(status='in_progress').count()
    
    # الكميات
    planned_qty = orders.aggregate(total=Sum('planned_quantity'))['total'] or Decimal('0')
    produced_qty = orders.aggregate(total=Sum('produced_quantity'))['total'] or Decimal('0')
    scrap_qty = orders.aggregate(total=Sum('scrap_quantity'))['total'] or Decimal('0')
    
    # التكاليف
    total_material_cost = orders.aggregate(total=Sum('actual_material_cost'))['total'] or Decimal('0')
    total_labor_cost = orders.aggregate(total=Sum('actual_labor_cost'))['total'] or Decimal('0')
    total_overhead_cost = orders.aggregate(total=Sum('actual_overhead_cost'))['total'] or Decimal('0')
    
    # أفضل 10 منتجات إنتاجاً
    top_products = orders.values(
        'product__name',
        'product__sku'
    ).annotate(
        total_qty=Sum('produced_quantity'),
        orders_count=Count('id')
    ).order_by('-total_qty')[:10]
    
    context = {
        'title': f'تقرير الإنتاج اليومي - {report_date}',
        'report_date': report_date,
        'orders': orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'in_progress_orders': in_progress_orders,
        'planned_qty': planned_qty,
        'produced_qty': produced_qty,
        'scrap_qty': scrap_qty,
        'total_material_cost': total_material_cost,
        'total_labor_cost': total_labor_cost,
        'total_overhead_cost': total_overhead_cost,
        'total_cost': total_material_cost + total_labor_cost + total_overhead_cost,
        'top_products': top_products,
        'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
        'production_rate': (produced_qty / planned_qty * 100) if planned_qty > 0 else 0,
    }
    
    return render(request, 'production/reports/daily_report.html', context)


@login_required
def production_monthly_report(request):
    """تقرير الإنتاج الشهري"""
    from production.models import ProductionOrder
    
    # الشهر المحدد أو الشهر الحالي
    year = request.GET.get('year', timezone.now().year)
    month = request.GET.get('month', timezone.now().month)
    
    try:
        year = int(year)
        month = int(month)
    except:
        year = timezone.now().year
        month = timezone.now().month
    
    # أوامر الإنتاج للشهر
    orders = ProductionOrder.objects.filter(
        order_date__year=year,
        order_date__month=month
    ).select_related('product', 'bom')
    
    # الإحصائيات الشهرية
    total_orders = orders.count()
    completed_orders = orders.filter(status='completed').count()
    
    # الكميات
    planned_qty = orders.aggregate(total=Sum('planned_quantity'))['total'] or Decimal('0')
    produced_qty = orders.aggregate(total=Sum('produced_quantity'))['total'] or Decimal('0')
    scrap_qty = orders.aggregate(total=Sum('scrap_quantity'))['total'] or Decimal('0')
    
    # التكاليف
    total_material_cost = orders.aggregate(total=Sum('actual_material_cost'))['total'] or Decimal('0')
    total_labor_cost = orders.aggregate(total=Sum('actual_labor_cost'))['total'] or Decimal('0')
    total_overhead_cost = orders.aggregate(total=Sum('actual_overhead_cost'))['total'] or Decimal('0')
    
    # الإنتاج اليومي (لرسم بياني)
    daily_production = []
    first_day = datetime(year, month, 1).date()
    last_day = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    
    current_date = first_day
    while current_date <= last_day:
        day_orders = orders.filter(order_date=current_date)
        daily_qty = day_orders.aggregate(total=Sum('produced_quantity'))['total'] or 0
        daily_production.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'quantity': float(daily_qty)
        })
        current_date += timedelta(days=1)
    
    # أكثر المنتجات إنتاجاً
    top_products = orders.values(
        'product__name',
        'product__sku'
    ).annotate(
        total_qty=Sum('produced_quantity'),
        orders_count=Count('id'),
        avg_cost=Avg('actual_material_cost')
    ).order_by('-total_qty')[:15]
    
    context = {
        'title': f'تقرير الإنتاج الشهري - {month}/{year}',
        'year': year,
        'month': month,
        'month_name': datetime(year, month, 1).strftime('%B'),
        'orders': orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'planned_qty': planned_qty,
        'produced_qty': produced_qty,
        'scrap_qty': scrap_qty,
        'total_material_cost': total_material_cost,
        'total_labor_cost': total_labor_cost,
        'total_overhead_cost': total_overhead_cost,
        'total_cost': total_material_cost + total_labor_cost + total_overhead_cost,
        'top_products': top_products,
        'daily_production': daily_production,
        'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
        'production_rate': (produced_qty / planned_qty * 100) if planned_qty > 0 else 0,
    }
    
    return render(request, 'production/reports/monthly_report.html', context)


@login_required
def production_material_consumption_report(request):
    """تقرير استهلاك المواد الخام"""
    from production.models import ProductionOrder, BOMItem
    from inventory.models import Product, Issue, IssueItem
    
    # الفترة
    start_date = request.GET.get('start_date', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except:
        start_date = (timezone.now() - timedelta(days=30)).date()
        end_date = timezone.now().date()
    
    # استهلاك المواد من أوامر الصرف للإنتاج
    issues = Issue.objects.filter(
        status='confirmed',
        to_department='production',
        issue_date__gte=start_date,
        issue_date__lte=end_date
    ).select_related('location')
    
    # تجميع الاستهلاك حسب المادة
    material_consumption = {}
    for issue in issues:
        for item in issue.items.all():
            material_key = item.product.id
            if material_key not in material_consumption:
                material_consumption[material_key] = {
                    'product': item.product,
                    'quantity': 0,
                    'cost': Decimal('0'),
                }
            material_consumption[material_key]['quantity'] += item.quantity
            material_consumption[material_key]['cost'] += item.quantity * item.product.cost
    
    # ترتيب حسب التكلفة
    consumption_list = sorted(
        material_consumption.values(),
        key=lambda x: x['cost'],
        reverse=True
    )
    
    context = {
        'title': 'تقرير استهلاك المواد الخام',
        'start_date': start_date,
        'end_date': end_date,
        'issues': issues,
        'consumption_list': consumption_list,
        'total_cost': sum(item['cost'] for item in consumption_list),
        'total_items': len(consumption_list),
    }
    
    return render(request, 'production/reports/material_consumption.html', context)


@login_required
def production_efficiency_report(request):
    """تقرير كفاءة الإنتاج"""
    from production.models import ProductionOrder
    
    # الفترة
    start_date = request.GET.get('start_date', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except:
        start_date = (timezone.now() - timedelta(days=30)).date()
        end_date = timezone.now().date()
    
    # أوامر الإنتاج المكتملة
    orders = ProductionOrder.objects.filter(
        status='completed',
        actual_end_date__gte=start_date,
        actual_end_date__lte=end_date
    ).select_related('product', 'supervisor')
    
    efficiency_data = []
    for order in orders:
        # حساب مدة الإنتاج
        if order.actual_start_date and order.actual_end_date:
            duration = (order.actual_end_date - order.actual_start_date).days
            planned_duration = (order.planned_end_date - order.planned_start_date).days
            time_efficiency = (planned_duration / duration * 100) if duration > 0 else 0
        else:
            duration = 0
            time_efficiency = 0
        
        # حساب كفاءة الكمية
        qty_efficiency = (order.produced_quantity / order.planned_quantity * 100) if order.planned_quantity > 0 else 0
        
        # حساب نسبة التالف
        scrap_rate = (order.scrap_quantity / order.planned_quantity * 100) if order.planned_quantity > 0 else 0
        
        # حساب كفاءة التكلفة
        estimated_cost = order.estimated_material_cost + order.estimated_labor_cost
        actual_cost = order.actual_material_cost + order.actual_labor_cost
        cost_efficiency = (estimated_cost / actual_cost * 100) if actual_cost > 0 else 0
        
        efficiency_data.append({
            'order': order,
            'duration': duration,
            'time_efficiency': time_efficiency,
            'qty_efficiency': qty_efficiency,
            'scrap_rate': scrap_rate,
            'cost_efficiency': cost_efficiency,
            'overall_efficiency': (time_efficiency + qty_efficiency + cost_efficiency) / 3
        })
    
    # ترتيب حسب الكفاءة الكلية
    efficiency_data.sort(key=lambda x: x['overall_efficiency'], reverse=True)
    
    context = {
        'title': 'تقرير كفاءة الإنتاج',
        'start_date': start_date,
        'end_date': end_date,
        'efficiency_data': efficiency_data,
        'avg_time_efficiency': sum(e['time_efficiency'] for e in efficiency_data) / len(efficiency_data) if efficiency_data else 0,
        'avg_qty_efficiency': sum(e['qty_efficiency'] for e in efficiency_data) / len(efficiency_data) if efficiency_data else 0,
        'avg_cost_efficiency': sum(e['cost_efficiency'] for e in efficiency_data) / len(efficiency_data) if efficiency_data else 0,
    }
    
    return render(request, 'production/reports/efficiency_report.html', context)
