"""
تقارير متقدمة للإنتاج
تتضمن:
- تقرير التكامل الكامل (مخزون + محاسبة)
- تقرير انحرافات التكلفة
- تقرير الإنتاجية والجودة
- تقرير حركة المواد
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Avg, Count, Q, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import json

from production.models import (
    ProductionOrder, MaterialConsumption, ProductionTimeLog,
    ProductionQualityCheck, WorkerProductionEntry
)
from production.services import (
    ProductionAccountingService,
    ProductionInventoryService
)
from inventory.models import Issue, Product, Stock
from accounting.models import JournalEntry


@login_required
def production_integration_report(request):
    """
    تقرير التكامل الكامل للإنتاج
    يعرض العلاقة بين أوامر الإنتاج، المخزون، والمحاسبة
    """
    # تحديد الفترة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if not start_date:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    # أوامر الإنتاج في الفترة
    orders = ProductionOrder.objects.filter(
        order_date__range=[start_date, end_date]
    ).select_related('product', 'supervisor')
    
    # تحليل كل أمر
    orders_analysis = []
    
    for order in orders:
        # حركات المخزون المرتبطة
        issues = Issue.objects.filter(
            reference__icontains=str(order.id)
        )
        
        # فحص إذا تم استلام منتجات تامة
        has_finished_goods = order.produced_quantity > 0
        
        # القيود المحاسبية المرتبطة
        journal_entries = JournalEntry.objects.filter(
            reference__icontains=str(order.number)
        )
        
        # تحليل الانحرافات
        variance = ProductionAccountingService.calculate_cost_variance(order)
        
        orders_analysis.append({
            'order': order,
            'issues_count': issues.count(),
            'has_finished_goods': has_finished_goods,
            'journal_entries_count': journal_entries.count(),
            'variance': variance,
            'integration_complete': (
                issues.exists() and 
                has_finished_goods and 
                journal_entries.exists()
            ),
        })
    
    # إحصائيات عامة
    total_orders = orders.count()
    completed_orders = orders.filter(status='completed').count()
    
    total_material_cost = orders.aggregate(total=Sum('actual_material_cost'))['total'] or Decimal('0')
    total_labor_cost = orders.aggregate(total=Sum('actual_labor_cost'))['total'] or Decimal('0')
    total_overhead_cost = orders.aggregate(total=Sum('actual_overhead_cost'))['total'] or Decimal('0')
    
    total_issues = Issue.objects.filter(
        issue_date__range=[start_date, end_date]
    ).count()
    
    # عدد الأوامر التي لديها منتجات تامة
    orders_with_output = orders.filter(produced_quantity__gt=0).count()
    
    total_entries = JournalEntry.objects.filter(
        date__range=[start_date, end_date]
    ).count()
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'orders_analysis': orders_analysis,
        'stats': {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
            'total_material_cost': total_material_cost,
            'total_labor_cost': total_labor_cost,
            'total_overhead_cost': total_overhead_cost,
            'total_cost': total_material_cost + total_labor_cost + total_overhead_cost,
            'total_issues': total_issues,
            'orders_with_output': orders_with_output,
            'total_journal_entries': total_entries,
        }
    }
    
    return render(request, 'production/reports/integration_report.html', context)


@login_required
def cost_variance_report(request):
    """
    تقرير انحرافات التكلفة التفصيلي
    """
    # تحديد الفترة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if not start_date:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    # أوامر الإنتاج المكتملة في الفترة
    orders = ProductionOrder.objects.filter(
        status='completed',
        actual_end_date__range=[start_date, end_date]
    ).select_related('product')
    
    # تحليل الانحرافات
    variance_data = []
    
    total_favorable = 0
    total_unfavorable = 0
    
    for order in orders:
        variance = ProductionAccountingService.calculate_cost_variance(order)
        
        total_variance_amount = variance.get('total', {}).get('variance', 0)
        
        if total_variance_amount < 0:
            total_favorable += abs(total_variance_amount)
        else:
            total_unfavorable += total_variance_amount
        
        variance_data.append({
            'order': order,
            'variance': variance,
        })
    
    # ترتيب حسب الانحراف
    variance_data.sort(
        key=lambda x: abs(x['variance'].get('total', {}).get('variance', 0)),
        reverse=True
    )
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'variance_data': variance_data,
        'summary': {
            'total_orders': len(variance_data),
            'total_favorable': total_favorable,
            'total_unfavorable': total_unfavorable,
            'net_variance': total_unfavorable - total_favorable,
        }
    }
    
    return render(request, 'production/reports/cost_variance_report.html', context)


@login_required
def material_consumption_report(request):
    """
    تقرير استهلاك المواد التفصيلي
    """
    # تحديد الفترة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    product_id = request.GET.get('product_id')
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if not start_date:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    # استهلاك المواد
    consumptions = MaterialConsumption.objects.filter(
        consumption_date__range=[start_date, end_date]
    ).select_related('production_order', 'material', 'location')
    
    if product_id:
        consumptions = consumptions.filter(production_order__product_id=product_id)
    
    # تجميع حسب المادة
    materials_summary = consumptions.values(
        'material__name', 'material__sku'
    ).annotate(
        total_planned=Sum('planned_quantity'),
        total_consumed=Sum('consumed_quantity'),
        total_wastage=Sum('wastage_quantity'),
        total_cost=Sum('total_cost'),
        order_count=Count('production_order', distinct=True)
    ).order_by('-total_cost')
    
    # حساب نسب الهدر
    for item in materials_summary:
        total_used = item['total_consumed'] + item['total_wastage']
        if total_used > 0:
            item['wastage_percentage'] = (item['total_wastage'] / total_used) * 100
        else:
            item['wastage_percentage'] = 0
    
    # الإجماليات
    totals = consumptions.aggregate(
        total_planned=Sum('planned_quantity'),
        total_consumed=Sum('consumed_quantity'),
        total_wastage=Sum('wastage_quantity'),
        total_cost=Sum('total_cost')
    )
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'consumptions': consumptions[:100],  # آخر 100 حركة
        'materials_summary': materials_summary,
        'totals': totals,
        'products': Product.objects.filter(is_active=True).order_by('name')
    }
    
    return render(request, 'production/reports/material_consumption_report.html', context)


@login_required
def productivity_quality_report(request):
    """
    تقرير الإنتاجية والجودة
    """
    # تحديد الفترة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if not start_date:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    # بيانات الإنتاجية
    time_logs = ProductionTimeLog.objects.filter(
        start_time__date__range=[start_date, end_date]
    ).select_related('employee', 'production_order', 'work_center')
    
    # تجميع حسب العامل
    employee_productivity = time_logs.values(
        'employee__arabic_name', 'employee__id'
    ).annotate(
        total_hours=Sum(
            ExpressionWrapper(
                (F('end_time') - F('start_time')),
                output_field=DurationField()
            )
        ),
        total_quantity=Sum('quantity_produced'),
        total_scrap=Sum('quantity_scrapped'),
        avg_efficiency=Avg('efficiency_percentage'),
        avg_quality=Avg('quality_rating'),
        order_count=Count('production_order', distinct=True)
    ).order_by('-total_quantity')
    
    # حساب الإنتاجية
    for item in employee_productivity:
        if item['total_hours'] and item['total_hours'] > 0:
            item['productivity_rate'] = float(item['total_quantity']) / float(item['total_hours'])
        else:
            item['productivity_rate'] = 0
        
        total_produced = (item['total_quantity'] or 0) + (item['total_scrap'] or 0)
        if total_produced > 0:
            item['scrap_rate'] = (item['total_scrap'] / total_produced) * 100
        else:
            item['scrap_rate'] = 0
    
    # بيانات الجودة
    quality_checks = ProductionQualityCheck.objects.filter(
        check_date__date__range=[start_date, end_date]
    ).select_related('production_order', 'inspector')
    
    # تجميع الجودة
    quality_summary = quality_checks.aggregate(
        total_checked=Sum('quantity_checked'),
        total_passed=Sum('quantity_passed'),
        total_failed=Sum('quantity_failed'),
        total_rework=Sum('quantity_rework'),
        avg_quality_score=Avg('quality_score')
    )
    
    if quality_summary['total_checked'] and quality_summary['total_checked'] > 0:
        quality_summary['pass_rate'] = (
            quality_summary['total_passed'] / quality_summary['total_checked'] * 100
        )
        quality_summary['fail_rate'] = (
            quality_summary['total_failed'] / quality_summary['total_checked'] * 100
        )
        quality_summary['rework_rate'] = (
            quality_summary['total_rework'] / quality_summary['total_checked'] * 100
        )
    else:
        quality_summary['pass_rate'] = 0
        quality_summary['fail_rate'] = 0
        quality_summary['rework_rate'] = 0
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'employee_productivity': employee_productivity,
        'quality_summary': quality_summary,
        'quality_checks': quality_checks[:50],
    }
    
    return render(request, 'production/reports/productivity_quality_report.html', context)


@login_required
def export_integration_report_csv(request):
    """
    تصدير تقرير التكامل إلى CSV
    """
    # تحديد الفترة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if not start_date:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    # أوامر الإنتاج
    orders = ProductionOrder.objects.filter(
        order_date__range=[start_date, end_date]
    ).select_related('product')
    
    # إنشاء ملف CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="production_integration_{start_date}_{end_date}.csv"'
    
    writer = csv.writer(response)
    
    # العناوين
    writer.writerow([
        'رقم الأمر',
        'المنتج',
        'الحالة',
        'الكمية المخططة',
        'الكمية المنتجة',
        'تكلفة المواد',
        'تكلفة العمالة',
        'التكاليف الإضافية',
        'التكلفة الإجمالية',
        'تكلفة الوحدة',
        'عدد سندات الصرف',
        'عدد سندات الاستلام',
        'عدد القيود المحاسبية',
    ])
    
    # البيانات
    for order in orders:
        issues_count = Issue.objects.filter(
            reference_type='production_order',
            reference_id=order.id
        ).count()
        
        has_output = order.actual_quantity > 0
        
        entries_count = JournalEntry.objects.filter(
            reference_type='production_order',
            reference_id=order.id
        ).count()
        
        writer.writerow([
            order.number,
            order.product.name,
            order.get_status_display(),
            order.planned_quantity,
            order.produced_quantity,
            order.actual_material_cost,
            order.actual_labor_cost,
            order.actual_overhead_cost,
            order.actual_total_cost,
            order.unit_cost,
            issues_count,
            'نعم' if has_output else 'لا',
            entries_count,
        ])
    
    return response
