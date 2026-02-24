from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Avg, Count, Min, Max
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json
import math
from decimal import Decimal
from django.db import transaction
from django.template.loader import render_to_string
import csv
from django.core.mail import send_mail

from .models import (
    ProductionOrder, ProductionOrderStage, ProductionWorkCenter,
    BillOfMaterials, ProductionStage, MaterialConsumption,
    ProductionTimeLog, ProductionQualityCheck, ProductionAlert,
    ProductionCostAnalysis, ProductionReport
)
from inventory.models import Product, Location, Stock
from hr.models import Employee, HSEIncident, HSEInspection, HSETraining, Department
from django.urls import reverse



@login_required
def production_dashboard(request):
    """لوحة تحكم الإنتاج"""
    
    # فلتر الفترة (أفضل توازن بين الأداء والمرونة)
    days_param = request.GET.get('days')
    period_is_all = (days_param == 'all')
    today = timezone.now().date()

    if period_is_all:
        # كل الأوامر - قد يكون أبطأ إذا كان الحجم كبيراً
        orders_qs = ProductionOrder.objects.all()
        days = None
        period_start = None
    else:
        # فترة تحليل افتراضية: آخر 90 يوم
        try:
            days = int(days_param or 90)
        except (TypeError, ValueError):
            days = 90
        days = max(7, min(days, 365))  # بين أسبوع وسنة كحد أقصى
        period_start = today - timedelta(days=days)
        orders_qs = ProductionOrder.objects.filter(order_date__gte=period_start)

    # إحصائيات عامة
    total_orders = orders_qs.count()
    active_orders = orders_qs.filter(status__in=['confirmed', 'in_progress']).count()
    completed_orders = orders_qs.filter(status='completed').count()
    overdue_orders = orders_qs.filter(
        planned_end_date__lt=today,
        status__in=['confirmed', 'in_progress']
    ).count()

    # إحصائيات الإنتاج والهالك للفترة
    production_agg = orders_qs.aggregate(
        total_planned_qty=Sum('planned_quantity'),
        total_produced_qty=Sum('produced_quantity'),
        total_scrap_qty=Sum('scrap_quantity'),
    )
    total_planned_qty = float(production_agg.get('total_planned_qty') or 0)
    total_produced_qty = float(production_agg.get('total_produced_qty') or 0)
    total_scrap_qty = float(production_agg.get('total_scrap_qty') or 0)
    produced_plus_scrap = (total_produced_qty + total_scrap_qty) or 0
    scrap_rate_pct = (
        (total_scrap_qty / produced_plus_scrap * 100)
        if produced_plus_scrap > 0 else 0
    )

    # بيانات الجراف: إنتاج فعلي مقابل مخطط حسب اليوم في الفترة
    chart_labels = []
    chart_actual_data = []
    chart_planned_data = []

    if orders_qs.exists():
        daily_stats = (
            orders_qs
            .values('order_date')
            .annotate(
                day_produced=Sum('produced_quantity'),
                day_planned=Sum('planned_quantity'),
            )
            .order_by('order_date')
        )

        for row in daily_stats:
            order_date = row['order_date']
            if order_date:
                chart_labels.append(order_date.strftime('%d/%m'))
                chart_actual_data.append(float(row.get('day_produced') or 0))
                chart_planned_data.append(float(row.get('day_planned') or 0))
    
    # أوامر الإنتاج اليوم
    today_orders = orders_qs.filter(order_date=today)
    
    # التنبيهات الحرجة (آخر 30 يوم فقط للحفاظ على الأداء)
    alerts_start = today - timedelta(days=30)
    critical_alerts = ProductionAlert.objects.filter(
        priority='critical',
        status__in=['new', 'acknowledged'],
        alert_date__date__gte=alerts_start
    ).order_by('-alert_date')[:5]
    
    # أوامر الإنتاج الحديثة
    recent_orders = orders_qs.select_related('product', 'supervisor').order_by('-created_at')[:10]
    
    # إحصائيات الجودة (خلال نفس الفترة إن وُجدت، أو لكل السجلات)
    quality_qs = ProductionQualityCheck.objects.all()
    if period_start is not None:
        quality_qs = quality_qs.filter(check_date__date__gte=period_start)
    quality_stats = quality_qs.aggregate(
        avg_quality_score=Avg('quality_score'),
        total_checks=Count('id')
    )
    
    # إحصائيات التكلفة (خلال نفس الفترة)
    cost_analysis = orders_qs.aggregate(
        total_estimated_material=Sum('estimated_material_cost'),
        total_estimated_labor=Sum('estimated_labor_cost'),
        total_estimated_overhead=Sum('estimated_overhead_cost'),
        total_actual_material=Sum('actual_material_cost'),
        total_actual_labor=Sum('actual_labor_cost'),
        total_actual_overhead=Sum('actual_overhead_cost')
    )
    
    # حساب الإجماليات
    estimated_total = (cost_analysis['total_estimated_material'] or 0) + \
                     (cost_analysis['total_estimated_labor'] or 0) + \
                     (cost_analysis['total_estimated_overhead'] or 0)
    
    actual_total = (cost_analysis['total_actual_material'] or 0) + \
                  (cost_analysis['total_actual_labor'] or 0) + \
                  (cost_analysis['total_actual_overhead'] or 0)
    
    cost_analysis['estimated_total'] = estimated_total
    cost_analysis['actual_total'] = actual_total
    
    # مراكز العمل النشطة
    active_work_centers = ProductionWorkCenter.objects.filter(is_active=True).count()
    
    context = {
        'total_orders': total_orders,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'overdue_orders': overdue_orders,
        'today_orders': today_orders,
        'critical_alerts': critical_alerts,
        'recent_orders': recent_orders,
        'quality_stats': quality_stats,
        'cost_analysis': cost_analysis,
        'active_work_centers': active_work_centers,
        'total_planned_qty': total_planned_qty,
        'total_produced_qty': total_produced_qty,
        'total_scrap_qty': total_scrap_qty,
        'scrap_rate_pct': scrap_rate_pct,
        'chart_labels': json.dumps(chart_labels, ensure_ascii=False),
        'chart_actual_data': json.dumps(chart_actual_data),
        'chart_planned_data': json.dumps(chart_planned_data),
        'period_days': days,
        'period_is_all': period_is_all,
    }
    
    return render(request, 'production/dashboard.html', context)


def _user_in_allowed_groups(user, allowed=(
    'HSE', 'Production', 'Production Managers', 'Supervisors'
)):
    try:
        if user.is_superuser:
            return True
        names = set(user.groups.values_list('name', flat=True))
        return any(g in names for g in allowed)
    except Exception:
        return False


@login_required
def waste_and_costs_dashboard(request):
    """
    لوحة حساب الهالك والتكلفة:
    - تحسب نسب الهالك على مستوى أوامر الإنتاج والمواد.
    - تعرض أكثر المواد/المنتجات هلاكاً.
    - تلخص تكلفة الوحدة شاملاً المواد+العمالة+الإضافية وفق القيود المسجلة.
    """
    # فترة اختيارية
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    # فلترة اختيارية بالمنتج
    product_id = request.GET.get('product')

    # المواد المستهلكة خلال الفترة
    mc_qs = MaterialConsumption.objects.filter(
        consumption_date__range=[start_date, end_date]
    )
    if product_id:
        mc_qs = mc_qs.filter(production_order__product_id=product_id)

    # إجماليات الهالك للمواد
    material_waste_agg = mc_qs.values('material__id', 'material__name').annotate(
        planned=Sum('planned_quantity'),
        consumed=Sum('consumed_quantity'),
        waste=Sum('wastage_quantity'),
        total_cost=Sum('total_cost'),
        count=Count('id')
    ).order_by('-waste')

    # تجهيز صفوف مع نسبة الهالك بالنسبة للمخطط أو المستهلك
    material_rows = []
    for row in material_waste_agg:
        planned = float(row.get('planned') or 0)
        consumed = float(row.get('consumed') or 0)
        waste = float(row.get('waste') or 0)
        base = consumed if consumed > 0 else (planned or 1)
        waste_pct = (waste / base * 100) if base else 0
        material_rows.append({
            'material_id': row['material__id'],
            'material_name': row['material__name'],
            'planned': planned,
            'consumed': consumed,
            'waste': waste,
            'waste_pct': waste_pct,
            'total_cost': float(row.get('total_cost') or 0),
            'count': row['count'],
        })

    # أكثر 5 مواد هلاكاً
    top_waste_materials = sorted(material_rows, key=lambda r: r['waste'], reverse=True)[:5]

    # أوامر الإنتاج وإجماليات التكلفة والهالك
    orders_qs = ProductionOrder.objects.filter(
        order_date__range=[start_date, end_date]
    )
    if product_id:
        orders_qs = orders_qs.filter(product_id=product_id)

    orders_stats = orders_qs.aggregate(
        total_planned=Sum('planned_quantity'),
        total_produced=Sum('produced_quantity'),
        total_scrap=Sum('scrap_quantity'),
        total_material_cost=Sum('actual_material_cost'),
        total_labor_cost=Sum('actual_labor_cost'),
        total_overhead_cost=Sum('actual_overhead_cost'),
        est_material_cost=Sum('estimated_material_cost'),
        est_labor_cost=Sum('estimated_labor_cost'),
        est_overhead_cost=Sum('estimated_overhead_cost'),
    )
    total_planned = float(orders_stats.get('total_planned') or 0)
    total_produced = float(orders_stats.get('total_produced') or 0)
    total_scrap = float(orders_stats.get('total_scrap') or 0)
    total_material_cost = float(orders_stats.get('total_material_cost') or 0)
    total_labor_cost = float(orders_stats.get('total_labor_cost') or 0)
    total_overhead_cost = float(orders_stats.get('total_overhead_cost') or 0)
    total_actual_cost = total_material_cost + total_labor_cost + total_overhead_cost
    est_material_cost = float(orders_stats.get('est_material_cost') or 0)
    est_labor_cost = float(orders_stats.get('est_labor_cost') or 0)
    est_overhead_cost = float(orders_stats.get('est_overhead_cost') or 0)
    estimated_total_cost = est_material_cost + est_labor_cost + est_overhead_cost
    cost_variance = total_actual_cost - estimated_total_cost if (estimated_total_cost or total_actual_cost) else 0

    # نسبة الهالك على مستوى أوامر الإنتاج: scrap من الكمية المنتجة+التالفة
    denom = (total_produced + total_scrap) or 1
    scrap_pct = (total_scrap / denom * 100) if denom else 0

    # تكلفة الوحدة (إجمالي فعلي / المنتج) مع بديل تقديري عند عدم توفر إنتاج فعلي
    if total_produced:
        unit_cost = total_actual_cost / total_produced if total_actual_cost else None
    elif total_planned:
        # إذا لا يوجد إنتاج فعلي لكن لدينا خطة نعرض التكلفة التقديرية للوحدة إن وجدت
        unit_cost = (estimated_total_cost / total_planned) if estimated_total_cost else None
    else:
        unit_cost = None

    # نسب إضافية: نسبة هدر المواد الإجمالية
    total_material_planned = sum(r['planned'] for r in material_rows) or 0
    total_material_consumed = sum(r['consumed'] for r in material_rows) or 0
    total_material_waste = sum(r['waste'] for r in material_rows) or 0
    material_waste_base = total_material_consumed if total_material_consumed > 0 else (total_material_planned or 1)
    material_waste_pct = (total_material_waste / material_waste_base * 100) if material_waste_base else 0

    has_material_data = bool(material_rows)
    has_orders_data = orders_qs.exists()

    # هدر حسب المنتج (المنتج النهائي)
    product_rows = []
    top_waste_products = []
    if has_orders_data:
        product_waste_agg = orders_qs.values('product__id', 'product__name').annotate(
            produced=Sum('produced_quantity'),
            scrap=Sum('scrap_quantity'),
            count=Count('id'),
        ).order_by('-scrap')
        for row in product_waste_agg:
            produced = float(row.get('produced') or 0)
            scrap = float(row.get('scrap') or 0)
            base = (produced + scrap) or 1
            scrap_pct_row = (scrap / base * 100) if base else 0
            product_rows.append({
                'product_id': row['product__id'],
                'product_name': row['product__name'],
                'produced': produced,
                'scrap': scrap,
                'scrap_pct': scrap_pct_row,
                'count': row['count'],
            })
        top_waste_products = sorted(product_rows, key=lambda r: r['scrap'], reverse=True)[:5]

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'material_rows': material_rows,
        'top_waste_materials': top_waste_materials,
        'product_rows': product_rows,
        'top_waste_products': top_waste_products,
        'total_planned': total_planned,
        'total_produced': total_produced,
        'total_scrap': total_scrap,
        'scrap_pct': scrap_pct,
        'total_material_cost': total_material_cost,
        'total_labor_cost': total_labor_cost,
        'total_overhead_cost': total_overhead_cost,
        'total_actual_cost': total_actual_cost,
        'estimated_total_cost': estimated_total_cost,
        'cost_variance': cost_variance,
        'unit_cost': unit_cost,
        'material_waste_pct': material_waste_pct,
        'total_material_waste': total_material_waste,
        'has_material_data': has_material_data,
        'has_orders_data': has_orders_data,
    'product_id': product_id,
    'products': Product.objects.all().order_by('name'),
    }

    return render(request, 'production/waste_and_costs.html', context)


@login_required
def waste_and_costs_csv(request):
    """تصدير تفاصيل المواد كهالك وتكلفة بصيغة CSV للفترة المحددة."""
    # نفس منطق التواريخ كما في الواجهة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    mc_qs = MaterialConsumption.objects.filter(
        consumption_date__range=[start_date, end_date]
    )

    material_waste_agg = mc_qs.values('material__id', 'material__name').annotate(
        planned=Sum('planned_quantity'),
        consumed=Sum('consumed_quantity'),
        waste=Sum('wastage_quantity'),
        total_cost=Sum('total_cost'),
        count=Count('id')
    ).order_by('material__name')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="waste_and_costs.csv"'
    writer = csv.writer(response)
    writer.writerow(['المادة', 'مخطط', 'مستهلك', 'هالك', '% الهالك', 'عدد السجلات', 'إجمالي التكلفة'])
    for row in material_waste_agg:
        planned = float(row.get('planned') or 0)
        consumed = float(row.get('consumed') or 0)
        waste = float(row.get('waste') or 0)
        base = consumed if consumed > 0 else (planned or 1)
        waste_pct = (waste / base * 100) if base else 0
        total_cost = float(row.get('total_cost') or 0)
        writer.writerow([
            row['material__name'],
            f"{planned:.3f}",
            f"{consumed:.3f}",
            f"{waste:.3f}",
            f"{waste_pct:.1f}",
            row['count'],
            f"{total_cost:.2f}",
        ])
    return response


@login_required
def product_costing_view(request):
    """
    حساب تكلفة المنتج: يجمع المواد الخام + العمالة + الإضافية + الهالك
    ويحسب تكلفة الوحدة لكل منتج خلال فترة محددة.
    """
    # فترة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    # أوامر الإنتاج حسب الفترة
    orders = ProductionOrder.objects.filter(order_date__range=[start_date, end_date])
    # إتاحة فلترة بمنتج معين
    product_id = request.GET.get('product')
    if product_id:
        orders = orders.filter(product_id=product_id)

    # إذا لم تكن هناك أوامر إنتاج، اعرض منتجات مع تكاليفها الأساسية
    if not orders.exists():
        # إنشاء صفوف من المنتجات مباشرة
        products_query = Product.objects.all()
        if product_id:
            products_query = products_query.filter(id=product_id)
        
        rows = []
        for product in products_query:
            rows.append({
                'product_id': product.id,
                'product_name': product.name,
                'produced': 0,
                'scrap': 0,
                'mat_cost': float(product.cost) if product.cost else 0.0,
                'labor_cost': 0.0,
                'overhead_cost': 0.0,
                'total_cost': float(product.cost) if product.cost else 0.0,
                'unit_cost': float(product.cost) if product.cost else 0.0,
                'mat_waste_pct': 0.0,
                'note': 'بناءً على التكلفة المحددة للمنتج (لا توجد أوامر إنتاج)'
            })
    else:
        # تجميع المعرفات
        order_ids = list(orders.values_list('id', flat=True))

        # تكاليف المواد المرتبطة بهذه الأوامر
        mc = MaterialConsumption.objects.filter(production_order_id__in=order_ids)
        mc_by_product = mc.values('production_order__product_id', 'production_order__product__name').annotate(
            materials_cost=Sum('total_cost'),
            material_waste=Sum('wastage_quantity'),
            material_consumed=Sum('consumed_quantity'),
        )

        # تكاليف العمالة بسجلات الوقت
        tl = ProductionTimeLog.objects.filter(production_order_id__in=order_ids)
        tl_by_product = tl.values('production_order__product_id').annotate(labor_cost=Sum('total_cost'))
        labor_map = {row['production_order__product_id']: float(row['labor_cost'] or 0) for row in tl_by_product}

        # تكاليف إضافية من تحليلات التكلفة
        ca = ProductionCostAnalysis.objects.filter(production_order_id__in=order_ids)
        ca_by_product = ca.values('production_order__product_id').annotate(overhead_cost=Sum('actual_amount'))
        overhead_map = {row['production_order__product_id']: float(row['overhead_cost'] or 0) for row in ca_by_product}

        # كميات الإنتاج والهالك على مستوى الأوامر
        qty_by_product = orders.values('product_id', 'product__name').annotate(
            produced=Sum('produced_quantity'),
            scrap=Sum('scrap_quantity'),
            estimated_mat_cost=Sum('estimated_material_cost'),
            estimated_labor_cost=Sum('estimated_labor_cost'),
            estimated_overhead_cost=Sum('estimated_overhead_cost'),
            actual_mat_cost=Sum('actual_material_cost'),
            actual_labor_cost=Sum('actual_labor_cost'),
            actual_overhead_cost=Sum('actual_overhead_cost'),
        )
        qty_map = {row['product_id']: row for row in qty_by_product}

        # بناء صفوف التقرير
        rows = []
        
        # إذا لم تكن هناك بيانات استهلاك مفصلة، استخدم بيانات أوامر الإنتاج
        if not mc_by_product:
            for row in qty_by_product:
                pid = row['product_id']
                name = row['product__name']
                produced = float(row.get('produced') or 0)
                scrap = float(row.get('scrap') or 0)
                
                # استخدام التكاليف الفعلية إن وجدت، وإلا المقدرة
                mat_cost = float(row.get('actual_mat_cost') or row.get('estimated_mat_cost') or 0)
                labor_cost = float(row.get('actual_labor_cost') or row.get('estimated_labor_cost') or 0)
                overhead_cost = float(row.get('actual_overhead_cost') or row.get('estimated_overhead_cost') or 0)
                
                total_cost = mat_cost + labor_cost + overhead_cost
                unit_cost = (total_cost / produced) if produced else 0

                rows.append({
                    'product_id': pid,
                    'product_name': name,
                    'produced': produced,
                    'scrap': scrap,
                    'mat_cost': mat_cost,
                    'labor_cost': labor_cost,
                    'overhead_cost': overhead_cost,
                    'total_cost': total_cost,
                    'unit_cost': unit_cost,
                    'mat_waste_pct': 0.0,  # لا توجد بيانات هالك مفصلة
                    'note': 'بناءً على تقديرات أمر الإنتاج'
                })
        else:
            # استخدام بيانات الاستهلاك المفصلة
            for row in mc_by_product:
                pid = row['production_order__product_id']
                name = row['production_order__product__name']
                produced = float((qty_map.get(pid) or {}).get('produced') or 0)
                scrap = float((qty_map.get(pid) or {}).get('scrap') or 0)
                mat_cost = float(row.get('materials_cost') or 0)
                labor_cost = labor_map.get(pid, 0.0)
                overhead_cost = overhead_map.get(pid, 0.0)
                total_cost = mat_cost + labor_cost + overhead_cost
                unit_cost = (total_cost / produced) if produced else 0
                
                # نسبة هدر المواد (من الاستهلاك)
                mat_waste = float(row.get('material_waste') or 0)
                mat_consumed = float(row.get('material_consumed') or 0)
                denom = (mat_consumed + mat_waste) or 1
                mat_waste_pct = (mat_waste / denom * 100) if denom else 0

                rows.append({
                    'product_id': pid,
                    'product_name': name,
                    'produced': produced,
                    'scrap': scrap,
                    'mat_cost': mat_cost,
                    'labor_cost': labor_cost,
                    'overhead_cost': overhead_cost,
                    'total_cost': total_cost,
                    'unit_cost': unit_cost,
                    'mat_waste_pct': mat_waste_pct,
                    'note': 'بناءً على بيانات الاستهلاك الفعلية'
                })

    # فرز بحسب أعلى تكلفة أو أعلى هالك
    sort = request.GET.get('sort', 'cost')
    if sort == 'waste':
        rows.sort(key=lambda r: r['mat_waste_pct'], reverse=True)
    else:
        rows.sort(key=lambda r: r['unit_cost'] or 0, reverse=True)

    products = Product.objects.all().order_by('name')
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'rows': rows,
        'products': products,
        'selected_product': int(product_id) if product_id else None,
        'sort': sort,
    }
    return render(request, 'production/product_costing.html', context)


@login_required
def product_costing_csv(request):
    """تصدير تقرير تكلفة المنتج بصيغة CSV وفق المرشحات الحالية."""
    # نفس التواريخ والمنطق
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    orders = ProductionOrder.objects.filter(order_date__range=[start_date, end_date])
    product_id = request.GET.get('product')
    if product_id:
        orders = orders.filter(product_id=product_id)

    order_ids = list(orders.values_list('id', flat=True))

    mc = MaterialConsumption.objects.filter(production_order_id__in=order_ids)
    mc_by_product = mc.values('production_order__product_id', 'production_order__product__name').annotate(
        materials_cost=Sum('total_cost'),
        material_waste=Sum('wastage_quantity'),
        material_consumed=Sum('consumed_quantity'),
    )

    tl = ProductionTimeLog.objects.filter(production_order_id__in=order_ids)
    tl_by_product = tl.values('production_order__product_id').annotate(labor_cost=Sum('total_cost'))
    labor_map = {row['production_order__product_id']: float(row['labor_cost'] or 0) for row in tl_by_product}

    ca = ProductionCostAnalysis.objects.filter(production_order_id__in=order_ids)
    ca_by_product = ca.values('production_order__product_id').annotate(overhead_cost=Sum('actual_amount'))
    overhead_map = {row['production_order__product_id']: float(row['overhead_cost'] or 0) for row in ca_by_product}

    qty_by_product = orders.values('product_id', 'product__name').annotate(
        produced=Sum('produced_quantity'),
        scrap=Sum('scrap_quantity'),
    )
    qty_map = {row['product_id']: row for row in qty_by_product}

    rows = []
    for row in mc_by_product:
        pid = row['production_order__product_id']
        name = row['production_order__product__name']
        produced = float((qty_map.get(pid) or {}).get('produced') or 0)
        scrap = float((qty_map.get(pid) or {}).get('scrap') or 0)
        mat_cost = float(row.get('materials_cost') or 0)
        labor_cost = labor_map.get(pid, 0.0)
        overhead_cost = overhead_map.get(pid, 0.0)
        total_cost = mat_cost + labor_cost + overhead_cost
        unit_cost = (total_cost / produced) if produced else None
        mat_waste = float(row.get('material_waste') or 0)
        mat_consumed = float(row.get('material_consumed') or 0)
        denom = (mat_consumed + mat_waste) or 1
        mat_waste_pct = (mat_waste / denom * 100) if denom else 0
        rows.append([
            name,
            f"{produced:.3f}",
            f"{scrap:.3f}",
            f"{mat_cost:.2f}",
            f"{labor_cost:.2f}",
            f"{overhead_cost:.2f}",
            f"{total_cost:.2f}",
            f"{(unit_cost or 0):.2f}" if unit_cost is not None else '—',
            f"{mat_waste_pct:.1f}",
        ])

    sort = request.GET.get('sort', 'cost')
    if sort == 'waste':
        rows.sort(key=lambda r: float(r[-1]), reverse=True)
    else:
        # تكلفة الوحدة بالعمود 7 إذا ليست —
        def unit_cost_key(r):
            try:
                return float(r[7]) if r[7] != '—' else 0.0
            except Exception:
                return 0.0
        rows.sort(key=unit_cost_key, reverse=True)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="product_costing.csv"'
    writer = csv.writer(response)
    writer.writerow(['المنتج', 'منتج', 'هالك', 'تكلفة المواد', 'تكلفة العمالة', 'تكاليف إضافية', 'الإجمالي', 'تكلفة الوحدة', '% هدر المواد'])
    for r in rows:
        writer.writerow(r)
    return response


@login_required
def material_issue_quick_create(request):
    """إنشاء إذن صرف خامات موجّه للإنتاج بسرعة ثم التحويل لشاشة تفاصيل الصرف بالمخازن.

    - يعتمد على نموذج مستند الصرف الموجود في وحدة المخازن (Issue/IssueItem).
    - يسمح بتمرير باراميترات اختيارية عبر GET:
        location: معرّف المخزن المراد الصرف منه. إن لم يحدد يستخدم الموقع الافتراضي إن وُجد.
        reference: مرجع نصي (مثلاً أمر تشغيل/دفتر)، يُحفظ في حقل reference.
        allocation: طريقة تخصيص الدُفعات fifo/lifo (افتراضي fifo).
        receiver: اسم المستلم في الإنتاج.
    - بعد الإنشاء يعاد التوجيه إلى شاشة تفاصيل الصرف لإضافة البنود مثل: ألواح إسفنج، غراء، خيوط...الخ.
    """
    from inventory.models import Issue, Location
    # اختيار موقع افتراضي إن لم يحدد
    loc = None
    try:
        loc_id = request.GET.get('location')
        if loc_id:
            loc = Location.objects.filter(pk=int(loc_id)).first()
    except Exception:
        loc = None
    if loc is None:
        loc = Location.objects.filter(is_default=True).first() or Location.objects.filter(is_active=True).order_by('id').first()
    if loc is None:
        messages.error(request, 'لا يوجد مخزن نشط لإنشاء إذن صرف.')
        return redirect('inventory:issue_list')

    reference = (request.GET.get('reference') or '').strip()
    allocation = (request.GET.get('allocation') or 'fifo').lower()
    allocation = allocation if allocation in {'fifo', 'lifo'} else 'fifo'
    receiver = (request.GET.get('receiver') or '').strip()

    obj = Issue.objects.create(
        location=loc,
        to_department='production',
        reference=reference,
        allocation_method=allocation,
        notes='',
        issued_by=getattr(request, 'user', None),
        received_by_name=receiver or None,
    )
    messages.success(request, f'تم إنشاء إذن صرف للإنتاج رقم {obj.number}. الرجاء إضافة الخامات المطلوبة.')
    return redirect('inventory:issue_detail', pk=obj.pk)


@login_required
def create_issue_for_order(request, order_id: int):
    """إنشاء إذن صرف خامات مرتبط بأمر إنتاج محدد مع تعبئة مبدئية اختيارية من الـ BOM.

    السلوك:
    - ينشئ مستند Issue في المخازن مرتبطاً بالإنتاج ويضع reference برقم أمر الإنتاج.
    - إذا تم تمرير ?prefill=bom يقوم بإضافة بنود للمواد من قائمة المواد الافتراضية بكمية متناسبة مع planned_quantity.
      لا يتم الترحيل هنا؛ فقط مسودة لإمكانية التعديل قبل التأكيد.
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    from inventory.models import Issue, IssueItem, Location

    # تحديد المخزن: إن كان لأحد مراكز العمل موقع مرفق استخدمه، وإلا الافتراضي.
    loc = None
    try:
        # حاول استخدام موقع مركز العمل لأول مرحلة في الـ BOM إن وجد
        first_stage = order.order_stages.select_related('stage__work_center').order_by('stage__sequence').first()
        if first_stage and first_stage.stage.work_center and first_stage.stage.work_center.location:
            loc = first_stage.stage.work_center.location
    except Exception:
        loc = None
    if loc is None:
        loc = Location.objects.filter(is_default=True).first() or Location.objects.filter(is_active=True).order_by('id').first()
    if loc is None:
        messages.error(request, 'لا يوجد مخزن نشط لإنشاء إذن صرف.')
        return redirect('production:order_detail', order_id=order.id)

    issue = Issue.objects.create(
        location=loc,
        to_department='production',
        reference=f"PO:{order.number}",
        allocation_method='fifo',
        notes=f'صرف خامات لأمر الإنتاج {order.number}',
        issued_by=request.user,
        received_by_name=None,
    )

    # تعبئة من BOM عند الطلب
    prefill = (request.GET.get('prefill') or '').lower()
    if prefill in {'1', 'true', 'yes', 'bom'}:
        try:
            bom = order.bom
            scale = float(order.planned_quantity or 1) / float(bom.base_quantity or 1)
            # عناصر المواد فقط
            for bi in bom.items.select_related('material').all():
                try:
                    from math import ceil
                    qty = bi.quantity_with_wastage * Decimal(str(scale))
                    # حفظ كعدد صحيح للوحدة الافتراضية للصرف (يمكن تعديله بالقالب لاحقاً)
                    qty_int = max(1, int(ceil(float(qty))))
                    IssueItem.objects.create(issue=issue, product=bi.material, quantity=qty_int)
                except Exception:
                    continue
            messages.success(request, 'تم نسخ مواد الـ BOM إلى إذن الصرف (قابلة للتعديل قبل التأكيد).')
        except Exception as e:
            messages.warning(request, f'تعذر التهيئة من قائمة المواد: {e}')

    # إعادة التوجيه لصفحة تفاصيل الصرف بالمخازن لاستكمال البنود والطباعة
    return redirect('inventory:issue_detail', pk=issue.pk)


@login_required
def create_requisition_for_order(request, order_id: int):
    """إنشاء إذن طلب خامات مرتبط بأمر إنتاج مع إمكانية تعبئة بنود من BOM كنقاط مرجعية.

    لا يخصم مخزون. ينشئ Requisition في المخازن ويربط مرجع PO:<order.number>.
    إن تم تمرير ?prefill=bom يضيف عناصر المواد بكميات تقريبية (مقربة لأقرب عدد صحيح).
    """
    # السماح بالإنشاء لمستخدمي الإنتاج: (superuser أو staff) أو امتلاك أي صلاحية إنتاج (view/change/add)
    allowed = getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_staff', False)
    if hasattr(request.user, 'has_module_permission'):
        try:
            allowed = allowed or request.user.has_module_permission('production', 'add') \
                               or request.user.has_module_permission('production', 'change') \
                               or request.user.has_module_permission('production', 'view')
        except Exception:
            pass
    if not allowed:
        messages.error(request, 'ليست لديك صلاحية إنشاء طلب خامات من الإنتاج')
        return redirect('production:orders_list')

    order = get_object_or_404(ProductionOrder, id=order_id)
    from inventory.models import Requisition, RequisitionItem

    req = Requisition.objects.create(
        from_department='production',
        reference=f"PO:{order.number}",
        notes=f'طلب خامات لأمر الإنتاج {order.number}',
        requested_by=request.user,
    )

    prefill = (request.GET.get('prefill') or '').lower()
    if prefill in {'1', 'true', 'yes', 'bom'} and getattr(order, 'bom', None):
        try:
            bom = order.bom
            scale = float(order.planned_quantity or 1) / float(bom.base_quantity or 1)
            from math import ceil
            for bi in bom.items.select_related('material').all():
                try:
                    qty = bi.quantity_with_wastage * Decimal(str(scale))
                    qty_int = max(1, int(ceil(float(qty))))
                    RequisitionItem.objects.create(requisition=req, product=bi.material, quantity=qty_int, production_order_id=order.id)
                except Exception:
                    continue
            messages.success(request, 'تم نسخ مواد الـ BOM إلى طلب الخامات (قابلة للتعديل).')
        except Exception as e:
            messages.warning(request, f'تعذر التهيئة من قائمة المواد: {e}')

    return redirect('inventory:requisition_detail', pk=req.pk)


@login_required
def material_requisition_quick_create(request):
        """إنشاء طلب خامات موجّه من الإنتاج بسرعة ثم التحويل لشاشة تفاصيل الطلب.

        باراميترات اختيارية عبر GET:
            - reference: مرجع نصي (مثلاً رقم أمر إنتاج)
            - notes: ملاحظات
        """
        # السماح بالإنشاء لمستخدمي الإنتاج: (superuser أو staff) أو امتلاك أي صلاحية إنتاج (view/change/add)
        allowed = getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_staff', False)
        if hasattr(request.user, 'has_module_permission'):
            try:
                allowed = allowed or request.user.has_module_permission('production', 'add') \
                                   or request.user.has_module_permission('production', 'change') \
                                   or request.user.has_module_permission('production', 'view')
            except Exception:
                pass
        if not allowed:
            messages.error(request, 'ليست لديك صلاحية إنشاء طلب خامات من الإنتاج')
            return redirect('production:orders_list')

        from inventory.models import Requisition
        reference = (request.GET.get('reference') or '').strip()
        notes = (request.GET.get('notes') or '').strip()
        req = Requisition.objects.create(
                from_department='production',
                reference=reference,
                notes=notes,
                requested_by=request.user,
        )
        messages.success(request, f'تم إنشاء طلب الخامات رقم {req.number}. الرجاء إضافة البنود المطلوبة.')
        return redirect('inventory:requisition_detail', pk=req.pk)


@login_required
def production_orders_list(request):
    """قائمة أوامر الإنتاج"""
    
    orders = ProductionOrder.objects.select_related('product', 'supervisor').order_by('-order_date')
    
    # الفلترة
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    priority_filter = request.GET.get('priority')
    if priority_filter:
        orders = orders.filter(priority=priority_filter)
    
    product_filter = request.GET.get('product')
    if product_filter:
        orders = orders.filter(product_id=product_filter)
    
    search = request.GET.get('search')
    if search:
        orders = orders.filter(
            Q(number__icontains=search) |
            Q(product__name__icontains=search) |
            Q(notes__icontains=search)
        )
    
    # التصفح
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # خيارات الفلتر
    products = Product.objects.all()
    status_choices = ProductionOrder.STATUS_CHOICES
    priority_choices = ProductionOrder.PRIORITY_CHOICES
    
    context = {
        'page_obj': page_obj,
        'products': products,
        'status_choices': status_choices,
        'priority_choices': priority_choices,
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
            'product': product_filter,
            'search': search,
        }
    }
    
    return render(request, 'production/orders_list.html', context)


@login_required
def production_order_detail(request, order_id):
    """تفاصيل أمر الإنتاج"""
    
    order = get_object_or_404(ProductionOrder, id=order_id)
    
    # مراحل الأمر
    order_stages = order.order_stages.select_related('stage', 'stage__work_center').order_by('stage__sequence')
    
    # استهلاك المواد
    material_consumptions = order.material_consumptions.select_related('material', 'location')
    
    # سجلات الوقت
    time_logs = order.time_logs.select_related('employee', 'work_center').order_by('-start_time')
    
    # فحوصات الجودة
    quality_checks = order.quality_checks.select_related('inspector').order_by('-check_date')
    
    # تحليل التكاليف
    cost_analysis = order.cost_analysis.order_by('-cost_date')
    
    # التنبيهات المرتبطة
    alerts = order.productionalert_set.order_by('-alert_date')
    
    # لواجهة الإضافة السريعة لاستهلاك المواد
    products = Product.objects.all().order_by('name')
    locations = Location.objects.filter(is_active=True).order_by('-is_default', 'name')
    default_location = locations.filter(is_default=True).first() if hasattr(locations, 'filter') else None
    
    context = {
        'order': order,
        'order_stages': order_stages,
        'material_consumptions': material_consumptions,
        'time_logs': time_logs,
        'quality_checks': quality_checks,
        'cost_analysis': cost_analysis,
        'alerts': alerts,
        'products': products,
        'locations': locations,
        'default_location': default_location,
    }
    
    return render(request, 'production/order_detail.html', context)


@login_required
def add_material_consumption(request, order_id):
    """إضافة استهلاك مواد سريع من صفحة أمر الإنتاج مع تحويل وحدات الشراء إلى وحدات الاستخدام عند الحاجة."""
    order = get_object_or_404(ProductionOrder, id=order_id)
    if request.method != 'POST':
        return redirect('production:order_detail', order_id=order_id)

    try:
        product_id = int(request.POST.get('material'))
        qty = float(request.POST.get('quantity') or 0)
        qty_unit = (request.POST.get('quantity_unit') or 'usage').strip()  # 'purchase' | 'usage'
        wastage = float(request.POST.get('wastage') or 0)
        unit_cost_override = request.POST.get('unit_cost')
        location_id = request.POST.get('location')
        stage_id = request.POST.get('stage')
        planned_quantity = request.POST.get('planned_quantity')

        product = get_object_or_404(Product, id=product_id)
        location = get_object_or_404(Location, id=int(location_id)) if location_id else Location.objects.filter(is_default=True).first()
        pos = get_object_or_404(ProductionOrderStage, id=int(stage_id)) if stage_id else None

        # تحويل الكمية للوحدة المستخدمة في الاستهلاك (usage)
        if qty_unit == 'purchase':
            consumed_usage = product.convert_qty_purchase_to_usage(qty)
            wastage_usage = product.convert_qty_purchase_to_usage(wastage) if wastage else 0
        else:
            consumed_usage = qty
            wastage_usage = wastage

        # تكلفة الوحدة بوحدة الاستهلاك
        if unit_cost_override not in (None, ""):
            unit_cost_usage = float(unit_cost_override)
        else:
            unit_cost_usage = product.convert_cost_per_usage_unit()

        planned_qty_val = float(planned_quantity) if planned_quantity else consumed_usage

        # ترحيل المخزون مع قفل السجل
        with transaction.atomic():
            stock, _ = Stock.objects.select_for_update().get_or_create(product=product, location=location)
            total_out = float(consumed_usage) + float(wastage_usage)
            required_units = int(math.ceil(total_out))
            if stock.quantity < required_units:
                raise ValueError(f'الكمية غير كافية في {location.name}. المتاح: {stock.quantity}, المطلوب: {required_units}')
            stock.quantity -= required_units
            stock.save()

            mc = MaterialConsumption.objects.create(
                production_order=order,
                stage=pos,
                material=product,
                planned_quantity=planned_qty_val,
                consumed_quantity=consumed_usage,
                wastage_quantity=wastage_usage,
                unit_cost=unit_cost_usage,
                location=location,
                issued_by=request.user,
            )

        # AJAX استجابة JSON بالتجزئة المولدة
        accepts_json = 'application/json' in (request.headers.get('Accept') or '') or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if accepts_json:
            item_html = render_to_string('production/_consumption_item.html', {'consumption': mc})
            return JsonResponse({'success': True, 'html': item_html})
        else:
            messages.success(request, 'تم إضافة استهلاك المواد بنجاح.')
    except Exception as e:
        accepts_json = 'application/json' in (request.headers.get('Accept') or '') or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if accepts_json:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, f'خطأ أثناء إضافة استهلاك المواد: {e}')

    return redirect('production:order_detail', order_id=order_id)


@login_required
def get_product_uom(request, product_id):
    """إرجاع معلومات وحدات المنتج وعامل التحويل وتكلفة وحدة الاستخدام للاستخدام في الواجهات."""
    p = get_object_or_404(Product, id=product_id)
    data = {
        'purchase_uom': p.purchase_uom,
        'usage_uom': p.usage_uom,
        'conversion_factor': float(p.conversion_factor or 1),
        'cost_per_usage_unit': p.convert_cost_per_usage_unit(),
    }
    return JsonResponse({'success': True, 'data': data})


@login_required
def create_production_order(request):
    """إنشاء أمر إنتاج جديد"""
    
    if request.method == 'POST':
        try:
            # استخراج البيانات العامة
            planned_start_date = request.POST.get('planned_start_date')
            planned_end_date = request.POST.get('planned_end_date')
            priority = request.POST.get('priority', 'normal')
            supervisor_id = request.POST.get('supervisor')
            notes = request.POST.get('notes', '')
            
            # دعم وضع متعدد المنتجات: أسماء الحقول المصفوفية item_product[], item_bom[], item_quantity[]
            item_products = request.POST.getlist('item_product[]')
            item_boms = request.POST.getlist('item_bom[]')
            item_quantities = request.POST.getlist('item_quantity[]')
            item_notes = request.POST.getlist('item_note[]')

            # تحقق من التواريخ العامة
            if not all([planned_start_date, planned_end_date]):
                messages.error(request, 'تواريخ البدء والانتهاء مطلوبة')
                return redirect('production:create_order')

            created_orders = []
            # إذا تم استخدام وضع متعدد المنتجات
            if item_products and item_boms and item_quantities:
                # تأكيد تطابق الأطوال
                row_count = min(len(item_products), len(item_boms), len(item_quantities), len(item_notes) or len(item_products))
                with transaction.atomic():
                    for i in range(row_count):
                        pid = (item_products[i] or '').strip()
                        bid = (item_boms[i] or '').strip()
                        qty = (item_quantities[i] or '').strip()
                        row_note = (item_notes[i] or '').strip() if i < len(item_notes) else ''
                        if not (pid and bid and qty):
                            continue
                        combined_notes = notes
                        if row_note:
                            prefix = f"\n[ملاحظة المنتج: #{pid}] " if notes else f"[ملاحظة المنتج: #{pid}] "
                            combined_notes = (notes or '') + prefix + row_note
                        order = ProductionOrder.objects.create(
                            product_id=int(pid),
                            bom_id=int(bid),
                            planned_quantity=Decimal(qty),
                            planned_start_date=planned_start_date,
                            planned_end_date=planned_end_date,
                            priority=priority,
                            supervisor_id=int(supervisor_id) if supervisor_id else None,
                            notes=combined_notes,
                            created_by=request.user
                        )
                        # إنشاء مراحل الأمر من قائمة المواد
                        for bom_stage in order.bom.stages.all():
                            ProductionOrderStage.objects.create(
                                production_order=order,
                                stage=bom_stage.stage,
                                planned_quantity=order.planned_quantity,
                                status='pending'
                            )
                        created_orders.append(order)

                if created_orders:
                    if len(created_orders) == 1:
                        messages.success(request, f'تم إنشاء أمر الإنتاج {created_orders[0].number} بنجاح')
                        return redirect('production:order_detail', order_id=created_orders[0].id)
                    else:
                        nums = ', '.join(o.number for o in created_orders[:5])
                        extra = '' if len(created_orders) <= 5 else f" ... (+{len(created_orders)-5})"
                        messages.success(request, f'تم إنشاء {len(created_orders)} أمر إنتاج: {nums}{extra}')
                        return redirect('production:orders_list')
                else:
                    messages.error(request, 'يرجى إضافة صف واحد على الأقل بمنتج وقائمة مواد وكمية صحيحة')
                    return redirect('production:create_order')

            # الوضع التقليدي (عنصر واحد)
            product_id = request.POST.get('product')
            bom_id = request.POST.get('bom')
            planned_quantity = request.POST.get('planned_quantity')
            if not all([product_id, bom_id, planned_quantity]):
                messages.error(request, 'جميع الحقول المطلوبة يجب تعبئتها')
                return redirect('production:create_order')

            # إنشاء أمر واحد كما بالسابق
            order = ProductionOrder.objects.create(
                product_id=product_id,
                bom_id=bom_id,
                planned_quantity=planned_quantity,
                planned_start_date=planned_start_date,
                planned_end_date=planned_end_date,
                priority=priority,
                supervisor_id=supervisor_id if supervisor_id else None,
                notes=notes,
                created_by=request.user
            )
            
            # إنشاء مراحل الأمر من قائمة المواد
            bom = order.bom
            for bom_stage in bom.stages.all():
                ProductionOrderStage.objects.create(
                    production_order=order,
                    stage=bom_stage.stage,
                    planned_quantity=order.planned_quantity,
                    status='pending'
                )
            
            messages.success(request, f'تم إنشاء أمر الإنتاج {order.number} بنجاح')
            return redirect('production:order_detail', order_id=order.id)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء الأمر: {str(e)}')
            return redirect('production:create_order')
    
    # GET request - عرض النموذج
    products = Product.objects.all()
    boms = BillOfMaterials.objects.filter(is_active=True)
    supervisors = Employee.objects.filter(status='active')
    
    context = {
        'products': products,
        'boms': boms,
        'supervisors': supervisors,
        'priority_choices': ProductionOrder.PRIORITY_CHOICES,
    }
    
    return render(request, 'production/order_form.html', context)


@login_required
def get_product_boms(request, product_id):
    """الحصول على قوائم المواد للمنتج - AJAX"""
    
    boms = BillOfMaterials.objects.filter(
        product_id=product_id,
        is_active=True
    ).values('id', 'version', 'name', 'base_quantity')
    
    return JsonResponse({'boms': list(boms)})


@login_required
def update_order_status(request, order_id):
    """تحديث حالة أمر الإنتاج"""
    
    if request.method == 'POST':
        order = get_object_or_404(ProductionOrder, id=order_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(ProductionOrder.STATUS_CHOICES):
            order.status = new_status
            
            # تحديث التواريخ حسب الحالة
            if new_status == 'in_progress' and not order.actual_start_date:
                order.actual_start_date = timezone.now().date()
            elif new_status == 'completed' and not order.actual_end_date:
                order.actual_end_date = timezone.now().date()
                order.produced_quantity = order.planned_quantity  # افتراضياً
            
            order.save()
            messages.success(request, f'تم تحديث حالة الأمر إلى {order.get_status_display()}')
        else:
            messages.error(request, 'حالة غير صحيحة')
    
    return redirect('production:order_detail', order_id=order_id)


@login_required
def work_centers_list(request):
    """قائمة مراكز العمل"""
    
    work_centers = ProductionWorkCenter.objects.select_related(
        'department', 'supervisor'
    ).order_by('code')
    
    # الفلترة
    type_filter = request.GET.get('type')
    if type_filter:
        work_centers = work_centers.filter(work_center_type=type_filter)
    
    active_filter = request.GET.get('active')
    if active_filter:
        work_centers = work_centers.filter(is_active=active_filter == 'true')
    
    search = request.GET.get('search')
    if search:
        work_centers = work_centers.filter(
            Q(code__icontains=search) |
            Q(name__icontains=search)
        )
    
    context = {
        'work_centers': work_centers,
        'type_choices': ProductionWorkCenter.WORK_CENTER_TYPES,
        'current_filters': {
            'type': type_filter,
            'active': active_filter,
            'search': search,
        }
    }
    
    return render(request, 'production/work_centers_list.html', context)


@login_required
def work_center_create(request):
    """إنشاء مركز عمل جديد"""
    
    if request.method == 'POST':
        try:
            # استخراج البيانات
            code = request.POST.get('code')
            name = request.POST.get('name')
            work_center_type = request.POST.get('work_center_type')
            department_id = request.POST.get('department')
            supervisor_id = request.POST.get('supervisor')
            capacity_per_hour = request.POST.get('capacity_per_hour')
            cost_per_hour = request.POST.get('cost_per_hour')
            setup_time = request.POST.get('setup_time', 0)
            description = request.POST.get('description', '')
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من صحة البيانات
            if not all([code, name, work_center_type]):
                messages.error(request, 'الحقول المطلوبة: الرمز، الاسم، نوع مركز العمل')
                return redirect('production:work_center_create')
            
            # التحقق من عدم تكرار الرمز
            if ProductionWorkCenter.objects.filter(code=code).exists():
                messages.error(request, 'رمز مركز العمل موجود مسبقاً')
                return redirect('production:work_center_create')
            
            # إنشاء مركز العمل
            work_center = ProductionWorkCenter.objects.create(
                code=code,
                name=name,
                work_center_type=work_center_type,
                department_id=department_id if department_id else None,
                supervisor_id=supervisor_id if supervisor_id else None,
                capacity_per_hour=capacity_per_hour or 1,
                cost_per_hour=cost_per_hour or 0,
                setup_time=setup_time or 0,
                description=description,
                is_active=is_active
            )
            
            messages.success(request, f'تم إنشاء مركز العمل {work_center.name} بنجاح')
            return redirect('production:work_center_detail', work_center_id=work_center.id)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء مركز العمل: {str(e)}')
            return redirect('production:work_center_create')
    
    # GET request - عرض النموذج
    from hr.models import Department
    
    departments = Department.objects.filter(is_active=True)
    supervisors = Employee.objects.filter(status='active')
    type_choices = ProductionWorkCenter.WORK_CENTER_TYPES
    
    context = {
        'departments': departments,
        'supervisors': supervisors,
        'type_choices': type_choices,
    }
    
    return render(request, 'production/work_center_form.html', context)


@login_required  
def work_center_detail(request, work_center_id):
    """تفاصيل مركز العمل"""
    
    work_center = get_object_or_404(ProductionWorkCenter, id=work_center_id)
    
    # أوامر الإنتاج في هذا المركز
    recent_orders = ProductionOrderStage.objects.filter(
        stage__work_center=work_center
    ).select_related('production_order', 'production_order__product').order_by('-created_at')[:10]
    
    # إحصائيات
    total_orders = ProductionOrderStage.objects.filter(stage__work_center=work_center).count()
    completed_orders = ProductionOrderStage.objects.filter(
        stage__work_center=work_center, 
        status='completed'
    ).count()
    
    # سجلات الوقت الحديثة
    time_logs = ProductionTimeLog.objects.filter(
        work_center=work_center
    ).select_related('employee', 'production_order').order_by('-start_time')[:10]
    
    context = {
        'work_center': work_center,
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'time_logs': time_logs,
    }
    
    return render(request, 'production/work_center_detail.html', context)


@login_required
def work_center_edit(request, work_center_id):
    """تعديل مركز العمل"""
    
    work_center = get_object_or_404(ProductionWorkCenter, id=work_center_id)
    
    if request.method == 'POST':
        try:
            # تحديث البيانات
            work_center.code = request.POST.get('code')
            work_center.name = request.POST.get('name')
            work_center.work_center_type = request.POST.get('work_center_type')
            
            department_id = request.POST.get('department')
            work_center.department_id = department_id if department_id else None
            
            supervisor_id = request.POST.get('supervisor')
            work_center.supervisor_id = supervisor_id if supervisor_id else None
            
            work_center.capacity_per_hour = request.POST.get('capacity_per_hour') or 1
            work_center.cost_per_hour = request.POST.get('cost_per_hour') or 0
            work_center.setup_time = request.POST.get('setup_time') or 0
            work_center.description = request.POST.get('description', '')
            work_center.is_active = request.POST.get('is_active') == 'on'
            
            work_center.save()
            
            messages.success(request, f'تم تحديث مركز العمل {work_center.name} بنجاح')
            return redirect('production:work_center_detail', work_center_id=work_center.id)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث مركز العمل: {str(e)}')
            return redirect('production:work_center_edit', work_center_id=work_center_id)
    
    # GET request - عرض النموذج
    from hr.models import Department
    
    departments = Department.objects.filter(is_active=True)
    supervisors = Employee.objects.filter(status='active')
    type_choices = ProductionWorkCenter.WORK_CENTER_TYPES
    
    context = {
        'work_center': work_center,
        'departments': departments,
        'supervisors': supervisors,
        'type_choices': type_choices,
    }
    
    return render(request, 'production/work_center_form.html', context)


@login_required
def production_calendar(request):
    """تقويم الإنتاج"""
    
    # الحصول على التاريخ المطلوب
    date_str = request.GET.get('date', timezone.now().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = timezone.now().date()
    
    # أوامر الإنتاج للشهر
    start_of_month = selected_date.replace(day=1)
    if selected_date.month == 12:
        end_of_month = selected_date.replace(year=selected_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = selected_date.replace(month=selected_date.month + 1, day=1) - timedelta(days=1)
    
    orders = ProductionOrder.objects.filter(
        Q(planned_start_date__range=[start_of_month, end_of_month]) |
        Q(planned_end_date__range=[start_of_month, end_of_month])
    ).select_related('product')
    
    # تجميع البيانات حسب التاريخ
    calendar_data = {}
    for order in orders:
        dates = []
        if start_of_month <= order.planned_start_date <= end_of_month:
            dates.append(order.planned_start_date)
        if start_of_month <= order.planned_end_date <= end_of_month:
            dates.append(order.planned_end_date)
        
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            if date_str not in calendar_data:
                calendar_data[date_str] = []
            calendar_data[date_str].append({
                'order_id': order.id,
                'order_number': order.number,
                'product_name': order.product.name,
                'status': order.status,
                'priority': order.priority,
                'type': 'start' if date == order.planned_start_date else 'end'
            })
    
    context = {
        'selected_date': selected_date,
        'calendar_data': json.dumps(calendar_data),
        'orders_count': orders.count(),
    }
    
    return render(request, 'production/calendar.html', context)


@login_required
def quality_dashboard(request):
    """لوحة تحكم الجودة"""
    
    # إحصائيات الجودة
    total_checks = ProductionQualityCheck.objects.count()
    passed_checks = ProductionQualityCheck.objects.filter(overall_result='passed').count()
    failed_checks = ProductionQualityCheck.objects.filter(overall_result='failed').count()
    pending_checks = ProductionQualityCheck.objects.filter(overall_result='pending').count()
    
    pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    # فحوصات اليوم
    today = timezone.now().date()
    today_checks = ProductionQualityCheck.objects.filter(check_date__date=today)
    
    # أحدث فحوصات الجودة
    recent_checks = ProductionQualityCheck.objects.select_related(
        'production_order', 'inspector'
    ).order_by('-check_date')[:10]
    
    # إحصائيات حسب المفتش
    inspector_stats = ProductionQualityCheck.objects.values(
        'inspector__arabic_name'
    ).annotate(
        total_checks=Count('id'),
        avg_quality_score=Avg('quality_score')
    ).order_by('-total_checks')
    
    context = {
        'total_checks': total_checks,
        'passed_checks': passed_checks,
        'failed_checks': failed_checks,
        'pending_checks': pending_checks,
        'pass_rate': pass_rate,
        'today_checks': today_checks,
        'recent_checks': recent_checks,
        'inspector_stats': inspector_stats,
    }
    
    return render(request, 'production/quality_dashboard.html', context)


@login_required
def cost_analysis_view(request):
    """تحليل تكاليف الإنتاج"""
    
    # فلترة التواريخ
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # تحليل التكاليف
    cost_analysis = ProductionCostAnalysis.objects.filter(
        cost_date__range=[start_date, end_date]
    ).select_related('production_order', 'cost_center')
    
    # إحصائيات حسب الفئة
    category_stats = cost_analysis.values('cost_category').annotate(
        total_budgeted=Sum('budgeted_amount'),
        total_actual=Sum('actual_amount'),
        count=Count('id')
    ).order_by('-total_actual')
    
    # إحصائيات حسب مركز التكلفة
    cost_center_stats = cost_analysis.filter(
        cost_center__isnull=False
    ).values('cost_center__name').annotate(
        total_actual=Sum('actual_amount'),
        count=Count('id')
    ).order_by('-total_actual')
    
    # إجمالي الإحصائيات
    total_stats = cost_analysis.aggregate(
        total_budgeted=Sum('budgeted_amount'),
        total_actual=Sum('actual_amount'),
        count=Count('id')
    )
    budgeted_total = total_stats.get('total_budgeted') or 0
    actual_total = total_stats.get('total_actual') or 0
    variance_total = actual_total - budgeted_total
    variance_pct = (variance_total / budgeted_total * 100) if budgeted_total else None

    # خريطة تسميات الفئات وأرقام مختصرة للفئات الأساسية
    category_labels = dict(ProductionCostAnalysis.COST_CATEGORIES)
    category_totals_map = {k: 0 for k, _ in ProductionCostAnalysis.COST_CATEGORIES}
    for row in category_stats:
        key = row['cost_category']
        total_actual_cat = row['total_actual'] or 0
        category_totals_map[key] = total_actual_cat

    # قائمة مرتبة سهلة للعرض في القالب
    category_rows = []
    for key, label in ProductionCostAnalysis.COST_CATEGORIES:
        category_rows.append({
            'key': key,
            'label': label,
            'total_actual': category_totals_map.get(key, 0),
        })

    # صفوف تفصيلية للسجلات مع الانحراف لكل سجل
    detailed_rows = []
    for ca in cost_analysis:
        budgeted = ca.budgeted_amount or 0
        actual = ca.actual_amount or 0
        detailed_rows.append({
            'cost_date': ca.cost_date,
            'category': ca.get_cost_category_display(),
            'description': ca.description,
            'budgeted_amount': budgeted,
            'actual_amount': actual,
            'variance': actual - budgeted,
        })
    
    context = {
        'cost_analysis': cost_analysis,
        'category_stats': category_stats,
        'cost_center_stats': cost_center_stats,
        'total_stats': total_stats,
    'start_date': start_date,
    'end_date': end_date,
    'budgeted_total': budgeted_total,
    'actual_total': actual_total,
    'variance_total': variance_total,
    'variance_pct': variance_pct,
    'category_labels': category_labels,
    'category_rows': category_rows,
    'detailed_rows': detailed_rows,
    }
    
    return render(request, 'production/cost_analysis.html', context)


@login_required
def production_alerts_list(request):
    """قائمة تنبيهات الإنتاج"""
    
    alerts = ProductionAlert.objects.select_related(
        'production_order', 'work_center', 'assigned_to'
    ).order_by('-priority', '-alert_date')
    
    # الفلترة
    status_filter = request.GET.get('status')
    if status_filter:
        alerts = alerts.filter(status=status_filter)
    
    priority_filter = request.GET.get('priority')
    if priority_filter:
        alerts = alerts.filter(priority=priority_filter)
    
    type_filter = request.GET.get('type')
    if type_filter:
        alerts = alerts.filter(alert_type=type_filter)
    
    # التصفح
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_choices': ProductionAlert.ALERT_STATUS,
        'priority_choices': ProductionAlert.PRIORITY_LEVELS,
        'type_choices': ProductionAlert.ALERT_TYPES,
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
            'type': type_filter,
        }
    }
    
    return render(request, 'production/alerts_list.html', context)


@login_required
def acknowledge_alert(request, alert_id):
    """إقرار التنبيه"""
    
    if request.method == 'POST':
        alert = get_object_or_404(ProductionAlert, id=alert_id)
        
        if request.user.employee_profile:
            alert.acknowledged_by = request.user.employee_profile
            alert.acknowledged_date = timezone.now()
            alert.status = 'acknowledged'
            alert.save()
            
            messages.success(request, 'تم إقرار التنبيه بنجاح')
        else:
            messages.error(request, 'يجب أن يكون لديك ملف موظف لإقرار التنبيهات')
    
    return redirect('production:alerts_list')


@login_required
def production_reports_list(request):
    """قائمة تقارير الإنتاج"""
    
    reports = ProductionReport.objects.select_related(
        'generated_by', 'approved_by'
    ).order_by('-created_at')
    
    # الفلترة
    type_filter = request.GET.get('type')
    if type_filter:
        reports = reports.filter(report_type=type_filter)
    
    status_filter = request.GET.get('status')
    if status_filter:
        reports = reports.filter(status=status_filter)
    
    context = {
        'reports': reports,
        'type_choices': ProductionReport.REPORT_TYPES,
        'status_choices': ProductionReport.REPORT_STATUS,
        'current_filters': {
            'type': type_filter,
            'status': status_filter,
        }
    }
    
    return render(request, 'production/reports_list.html', context)


@login_required
def worker_dashboard(request):
    """لوحة تحكم العامل"""
    
    # التأكد من وجود ملف موظف
    if not hasattr(request.user, 'employee_profile'):
        messages.error(request, 'يجب أن يكون لديك ملف موظف للوصول إلى لوحة العامل')
        return redirect('production:dashboard')
    
    worker = request.user.employee_profile
    today = timezone.now().date()
    
    # المهام المسندة للعامل
    assigned_tasks = []  # سيتم تطويرها لاحقاً مع نموذج المهام
    
    # إحصائيات اليوم (قيم وهمية للعرض)
    today_work_hours = 6.5
    today_completed_tasks = 3
    today_produced_units = 15
    today_efficiency = 85
    daily_progress = 70
    daily_progress_offset = 339.292 - (339.292 * daily_progress / 100)
    
    # حالة العمل الحالية
    is_working = False  # سيتم ربطها بنظام تتبع الوقت
    is_on_break = False
    current_work_time = "06:30:00"
    
    context = {
        'worker': worker,
        'assigned_tasks': assigned_tasks,
        'today_work_hours': today_work_hours,
        'today_completed_tasks': today_completed_tasks,
        'today_produced_units': today_produced_units,
        'today_efficiency': today_efficiency,
        'daily_progress': daily_progress,
        'daily_progress_offset': daily_progress_offset,
        'is_working': is_working,
        'is_on_break': is_on_break,
        'current_work_time': current_work_time,
    }
    
    return render(request, 'production/worker_dashboard.html', context)


@login_required
def safety_guidelines(request):
    """صفحة إرشادات السلامة المهنية في بيئة الإنتاج."""
    if not _user_in_allowed_groups(request.user):
        return HttpResponse(status=403)

    today = timezone.now().date()

    # مرشحات
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    department_id = request.GET.get('department')
    work_center_id = request.GET.get('work_center')

    # نطاق التاريخ الافتراضي: الشهر الحالي
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        end_date = today
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        start_date = end_date.replace(day=1)

    # حساب بداية الربع الحالي
    month = end_date.month
    quarter = (month - 1) // 3 + 1
    start_month = 3 * (quarter - 1) + 1
    start_of_quarter = end_date.replace(month=start_month, day=1)

    # مصادر البيانات مع المرشحات
    incidents_qs = HSEIncident.objects.filter(date__range=[start_date, end_date])
    if department_id:
        incidents_qs = incidents_qs.filter(department_id=department_id)
    kpi_incidents = incidents_qs.count()

    # 2) الأيام منذ آخر حادث
    last_incident = incidents_qs.order_by('-date').first() if (start_date_str or department_id) else HSEIncident.objects.order_by('-date').first()
    kpi_days_since_last = (today - last_incident.date).days if last_incident else None

    # 3) ساعات التدريب هذا الربع (افتراض: ساعة واحدة لكل مشاركة في تدريب سلامة مكتمل)
    # ملاحظة: لا يوجد حقل مدة في HSETraining؛ نفترض 1 ساعة لكل مشاركة.
    trainings_qs = HSETraining.objects.filter(date__range=[start_of_quarter, end_date], status='done')
    if department_id:
        trainings_qs = trainings_qs.filter(participants__department_id=department_id)
    trainings_participations = trainings_qs.aggregate(total_participations=Count('participants'))['total_participations'] or 0
    kpi_training_hours = trainings_participations  # ساعات تقديرية

    # 4) الإجراءات المفتوحة (افتراضي: حوادث غير مغلقة + تنبيهات سلامة غير محلولة)
    open_incidents_qs = HSEIncident.objects.filter(status__in=['open', 'investigating'])
    if department_id:
        open_incidents_qs = open_incidents_qs.filter(department_id=department_id)
    open_incidents = open_incidents_qs.count()

    safety_alerts_qs = ProductionAlert.objects.filter(alert_type='safety')
    if work_center_id:
        safety_alerts_qs = safety_alerts_qs.filter(work_center_id=work_center_id)
    if start_date_str or end_date_str:
        safety_alerts_qs = safety_alerts_qs.filter(alert_date__date__range=[start_date, end_date])
    open_safety_alerts = safety_alerts_qs.exclude(status__in=['resolved', 'closed']).count()
    kpi_open_actions = open_incidents + open_safety_alerts

    # تنبيه تلقائي عند تجاوز الحد الشهري
    # حد قابل للتخصيص من إعدادات التطبيق
    try:
        from core.models import AppSettings
        threshold = AppSettings.get().safety_incident_alert_threshold or 3
    except Exception:
        threshold = 3
    month_key = end_date.strftime('%Y-%m')
    threshold_exceeded = kpi_incidents >= threshold
    if threshold_exceeded:
        exists = ProductionAlert.objects.filter(
            alert_type='safety',
            title__icontains=f"High Safety Incidents {month_key}"
        ).exists()
        if not exists:
            ProductionAlert.objects.create(
                title=f"High Safety Incidents {month_key}",
                alert_type='safety',
                priority='high',
                status='new',
                description=f"Incidents in period {start_date} to {end_date}: {kpi_incidents} (threshold {threshold})",
                created_by=request.user,
            )
        # Toast notification for the UI
        try:
            messages.warning(request, f"تنبيه سلامة: عدد الحوادث تجاوز الحد ({kpi_incidents}/{threshold}).", extra_tags='toast')
        except Exception:
            pass
        # Optional email to HSE group members
        try:
            recipients = []
            hse_group = Group.objects.filter(name__in=['HSE','Production Managers']).first()
            if hse_group:
                recipients = list(hse_group.user_set.values_list('email', flat=True))
                recipients = [e for e in recipients if e]
            if not recipients:
                try:
                    from core.models import AppSettings as _AS
                    recipients = list(_AS.get().safety_alert_emails or [])
                except Exception:
                    recipients = []
            if recipients:
                subject = f"[Safety Alert] Incidents exceeded threshold ({kpi_incidents}/{threshold})"
                body = (
                    f"Period: {start_date} to {end_date}\n"
                    f"Incidents: {kpi_incidents}\n"
                    f"Threshold: {threshold}\n"
                    f"Triggered by: {request.user.username}"
                )
                send_mail(subject, body, None, recipients, fail_silently=True)
        except Exception:
            pass

    # تحضير بيانات الرسم البياني لآخر 6 أشهر
    labels = []
    values = []
    year = end_date.year
    for i in range(5, -1, -1):
        # حساب الشهر والسنة مع الرجوع للخلف i أشهر
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        # تسمية بسيطة بالشهر فقط
        labels.append(str(m))
        inc_q = HSEIncident.objects.filter(date__year=y, date__month=m)
        if department_id:
            inc_q = inc_q.filter(department_id=department_id)
        count_m = inc_q.count()
        values.append(count_m)

    # قوائم للاختيار
    departments = Department.objects.filter(is_active=True).order_by('name')
    work_centers = ProductionWorkCenter.objects.filter(is_active=True).order_by('name')

    context = {
        'kpi_incidents': kpi_incidents,
        'kpi_days_since_last': kpi_days_since_last,
        'kpi_training_hours': kpi_training_hours,
        'kpi_open_actions': kpi_open_actions,
    'safety_threshold': threshold,
    'safety_threshold_exceeded': threshold_exceeded,
        'chart_labels': labels,
        'chart_values': values,
        'start_date': start_date,
        'end_date': end_date,
        'departments': departments,
        'work_centers': work_centers,
        'selected_department': int(department_id) if department_id else None,
        'selected_work_center': int(work_center_id) if work_center_id else None,
    }
    return render(request, 'production/safety.html', context)


@login_required
def safety_export_csv(request):
    """تصدير مؤشرات السلامة إلى CSV"""
    if not _user_in_allowed_groups(request.user):
        return HttpResponse(status=403)
    # أعد استخدام المنطق بحساب سريع دون إنشاء تنبيه
    req = request
    # Build minimal context via calling safety_guidelines logic pieces
    # لإبقاء الأمور بسيطة سنكرر الاستخراج من GET
    today = timezone.now().date()
    end_date = datetime.strptime(req.GET.get('end_date'), '%Y-%m-%d').date() if req.GET.get('end_date') else today
    start_date = datetime.strptime(req.GET.get('start_date'), '%Y-%m-%d').date() if req.GET.get('start_date') else end_date.replace(day=1)
    department_id = req.GET.get('department')

    incidents_qs = HSEIncident.objects.filter(date__range=[start_date, end_date])
    if department_id:
        incidents_qs = incidents_qs.filter(department_id=department_id)
    kpi_incidents = incidents_qs.count()

    last_incident = incidents_qs.order_by('-date').first()
    kpi_days_since_last = (today - last_incident.date).days if last_incident else ''

    quarter = (end_date.month - 1) // 3 + 1
    start_of_quarter = end_date.replace(month=3 * (quarter - 1) + 1, day=1)
    trainings_qs = HSETraining.objects.filter(date__range=[start_of_quarter, end_date], status='done')
    if department_id:
        trainings_qs = trainings_qs.filter(participants__department_id=department_id)
    trainings_participations = trainings_qs.aggregate(total_participations=Count('participants'))['total_participations'] or 0
    kpi_training_hours = trainings_participations

    open_incidents = HSEIncident.objects.filter(status__in=['open', 'investigating'])
    if department_id:
        open_incidents = open_incidents.filter(department_id=department_id)
    open_safety_alerts = ProductionAlert.objects.filter(alert_type='safety').exclude(status__in=['resolved', 'closed']).count()
    kpi_open_actions = open_incidents.count() + open_safety_alerts

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="safety_kpis.csv"'
    writer = csv.writer(response)
    writer.writerow(['الفترة من', start_date, 'إلى', end_date])
    writer.writerow(['المؤشر', 'القيمة'])
    writer.writerow(['حوادث ضمن الفترة', kpi_incidents])
    writer.writerow(['أيام منذ آخر حادث', kpi_days_since_last])
    writer.writerow(['ساعات تدريب هذا الربع (تقديري)', kpi_training_hours])
    writer.writerow(['إجراءات مفتوحة', kpi_open_actions])
    return response


@login_required
def time_motion_guide(request):
    """صفحة مبادئ الوقت والحركة وتحسين العمليات."""
    if not _user_in_allowed_groups(request.user):
        return HttpResponse(status=403)
    # فترة افتراضية: آخر 14 يوماً
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = end_date - timedelta(days=13)
    except Exception:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=13)

    # مرشحات إضافية
    work_center_id = request.GET.get('work_center')
    product_id = request.GET.get('product')
    department_id = request.GET.get('department')

    logs = ProductionTimeLog.objects.filter(start_time__date__range=[start_date, end_date])
    if work_center_id:
        logs = logs.filter(work_center_id=work_center_id)
    if product_id:
        logs = logs.filter(production_order__product_id=product_id)
    if department_id:
        logs = logs.filter(work_center__department_id=department_id)

    # حساب الساعات والكمية
    productive_types = {'setup', 'operation', 'quality_check', 'cleanup'}
    downtime_types = {'waiting', 'maintenance', 'break'}
    total_hours = 0.0
    productive_hours = 0.0
    downtime_hours = 0.0
    total_quantity = 0.0
    for log in logs:
        dur = float(log.duration_hours or 0)
        total_hours += dur
        if log.activity_type in productive_types:
            productive_hours += dur
        if log.activity_type in downtime_types:
            downtime_hours += dur
        total_quantity += float(log.quantity_produced or 0)

    utilization = (productive_hours / total_hours * 100) if total_hours > 0 else 0
    avg_productivity = (total_quantity / productive_hours) if productive_hours > 0 else 0
    avg_cycle_time_hours = (productive_hours / total_quantity) if total_quantity > 0 else None

    # معدل الجودة من فحوصات الجودة في نفس الفترة
    qc = ProductionQualityCheck.objects.filter(check_date__date__range=[start_date, end_date])
    if product_id:
        qc = qc.filter(production_order__product_id=product_id)
    if work_center_id:
        qc = qc.filter(stage__stage__work_center_id=work_center_id)
    total_checked = qc.aggregate(s=Sum('quantity_checked'))['s'] or 0
    total_passed = qc.aggregate(s=Sum('quantity_passed'))['s'] or 0
    quality_rate = (float(total_passed) / float(total_checked) * 100) if total_checked else None

    # OEE مبسط
    availability = (productive_hours / total_hours) if total_hours > 0 else 0
    # الأداء من متوسط نسبة الكفاءة المسجلة
    eff_avg = logs.aggregate(e=Avg('efficiency_percentage'))['e'] or 100
    performance = float(eff_avg) / 100.0
    quality = (float(quality_rate) / 100.0) if quality_rate is not None else 1.0
    oee = availability * performance * quality * 100.0
    downtime_rate = (downtime_hours / total_hours * 100) if total_hours > 0 else 0

    # سلسلة يومية للإنتاج (وحدات/يوم)
    days = []
    values = []
    cur = start_date
    while cur <= end_date:
        days.append(cur.strftime('%m-%d'))
        day_qty = 0.0
        for log in logs:
            if log.start_time.date() == cur:
                day_qty += float(log.quantity_produced or 0)
        values.append(day_qty)
        cur += timedelta(days=1)

    # أفضل مراكز العمل/المنتجات حسب الإنتاج
    top_centers = (
        logs.values('work_center__name')
            .annotate(q=Sum('quantity_produced'))
            .order_by('-q')[:5]
    )
    top_products = (
        logs.values('production_order__product__name')
            .annotate(q=Sum('quantity_produced'))
            .order_by('-q')[:5]
    )

    from inventory.models import Product
    departments = Department.objects.filter(is_active=True).order_by('name')
    work_centers = ProductionWorkCenter.objects.filter(is_active=True).order_by('name')
    products = Product.objects.all().order_by('name')

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_hours': total_hours,
        'productive_hours': productive_hours,
        'downtime_hours': downtime_hours,
        'utilization': utilization,
        'total_quantity': total_quantity,
        'avg_productivity': avg_productivity,
        'avg_cycle_time_hours': avg_cycle_time_hours,
        'quality_rate': quality_rate,
        'oee': oee,
        'downtime_rate': downtime_rate,
        'tm_labels': days,
        'tm_values': values,
        'top_centers': top_centers,
        'top_products': top_products,
        'departments': departments,
        'work_centers': work_centers,
        'products': products,
        'selected_department': int(department_id) if department_id else None,
        'selected_work_center': int(work_center_id) if work_center_id else None,
        'selected_product': int(product_id) if product_id else None,
    }
    return render(request, 'production/time_motion.html', context)


@login_required
def time_motion_export_csv(request):
    """تصدير مؤشرات الوقت والحركة إلى CSV"""
    if not _user_in_allowed_groups(request.user):
        return HttpResponse(status=403)
    # سنعيد احتساب القيم الأساسية سريعاً (نفس منطق العرض بشكل مبسط)
    try:
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    except Exception:
        end_date = timezone.now().date()
    try:
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    except Exception:
        start_date = end_date - timedelta(days=13)

    logs = ProductionTimeLog.objects.filter(start_time__date__range=[start_date, end_date])
    total_hours = sum(float(l.duration_hours or 0) for l in logs)
    productive_hours = sum(float(l.duration_hours or 0) for l in logs if l.activity_type in {'setup','operation','quality_check','cleanup'})
    downtime_hours = sum(float(l.duration_hours or 0) for l in logs if l.activity_type in {'waiting','maintenance','break'})
    total_quantity = sum(float(l.quantity_produced or 0) for l in logs)
    utilization = (productive_hours / total_hours * 100) if total_hours > 0 else 0
    avg_productivity = (total_quantity / productive_hours) if productive_hours > 0 else 0
    avg_cycle_time_hours = (productive_hours / total_quantity) if total_quantity > 0 else ''
    qc = ProductionQualityCheck.objects.filter(check_date__date__range=[start_date, end_date])
    total_checked = qc.aggregate(s=Sum('quantity_checked'))['s'] or 0
    total_passed = qc.aggregate(s=Sum('quantity_passed'))['s'] or 0
    quality_rate = (float(total_passed) / float(total_checked) * 100) if total_checked else ''
    eff_avg = logs.aggregate(e=Avg('efficiency_percentage'))['e'] or 100
    availability = (productive_hours / total_hours) if total_hours > 0 else 0
    performance = float(eff_avg) / 100.0
    quality = (float(quality_rate) / 100.0) if quality_rate not in ('', None) else 1.0
    oee = availability * performance * quality * 100.0
    downtime_rate = (downtime_hours / total_hours * 100) if total_hours > 0 else 0

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="time_motion_kpis.csv"'
    writer = csv.writer(response)
    writer.writerow(['الفترة من', start_date, 'إلى', end_date])
    writer.writerow(['المؤشر', 'القيمة'])
    writer.writerow(['إجمالي ساعات العمل', f"{total_hours:.2f}"])
    writer.writerow(['ساعات منتجة', f"{productive_hours:.2f}"])
    writer.writerow(['نسبة الاستغلال %', f"{utilization:.1f}"])
    writer.writerow(['إجمالي الإنتاج', f"{total_quantity:.0f}"])
    writer.writerow(['إنتاجية متوسطة (وحدة/ساعة)', f"{avg_productivity:.2f}"])
    writer.writerow(['زمن دورة متوسط (ساعة/وحدة)', f"{avg_cycle_time_hours if avg_cycle_time_hours=='' else f'{avg_cycle_time_hours:.2f}'}"])
    writer.writerow(['معدل الجودة %', f"{quality_rate if quality_rate=='' else f'{quality_rate:.1f}'}"])
    writer.writerow(['OEE %', f"{oee:.1f}"])
    writer.writerow(['معدل التوقف %', f"{downtime_rate:.1f}"])
    return response


@login_required
def work_order_view(request, order_id):
    """
    صفحة تنفيذ أمر الشغل للعمال/المشرفين:
    - تعرض تفاصيل أمر الإنتاج ومراحله بكيفية مبسطة.
    - تتيح تغيير حالة الأمر أو كل مرحلة، وتسجيل ملاحظات/مشكلة كتنبيه.
    """
    order = get_object_or_404(ProductionOrder, id=order_id)
    stages = order.order_stages.select_related('stage', 'stage__work_center').order_by('stage__sequence')

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'update_order_status':
                new_status = request.POST.get('status')
                if new_status in dict(ProductionOrder.STATUS_CHOICES):
                    order.status = new_status
                    if new_status == 'in_progress' and not order.actual_start_date:
                        order.actual_start_date = timezone.now().date()
                    if new_status == 'completed' and not order.actual_end_date:
                        order.actual_end_date = timezone.now().date()
                    order.save()
                    messages.success(request, 'تم تحديث حالة أمر الإنتاج.')
                else:
                    messages.error(request, 'حالة غير صحيحة للأمر.')

            elif action == 'update_stage':
                stage_id = request.POST.get('stage_id')
                new_status = request.POST.get('stage_status')
                completed_qty = request.POST.get('completed_quantity')
                notes = request.POST.get('notes', '')
                pos = get_object_or_404(ProductionOrderStage, id=stage_id, production_order=order)
                if new_status in dict(ProductionOrderStage.STATUS_CHOICES):
                    pos.status = new_status
                if completed_qty:
                    try:
                        pos.completed_quantity = completed_qty
                    except Exception:
                        pass
                if notes:
                    pos.notes = (pos.notes or '') + f"\n{notes}"
                # Set actual dates
                if pos.status == 'in_progress' and not pos.actual_start_date:
                    pos.actual_start_date = timezone.now()
                if pos.status == 'completed' and not pos.actual_end_date:
                    pos.actual_end_date = timezone.now()
                pos.save()
                messages.success(request, 'تم تحديث حالة المرحلة.')

            elif action == 'report_issue':
                title = request.POST.get('title') or 'مشكلة أثناء التنفيذ'
                description = request.POST.get('description') or ''
                priority = request.POST.get('priority', 'medium')
                stage_id = request.POST.get('stage_id')
                work_center = None
                pos = None
                if stage_id:
                    pos = get_object_or_404(ProductionOrderStage, id=stage_id, production_order=order)
                    work_center = pos.stage.work_center
                ProductionAlert.objects.create(
                    title=title,
                    alert_type='delay',
                    priority=priority,
                    status='new',
                    production_order=order,
                    work_center=work_center,
                    description=description,
                    created_by=request.user,
                )
                messages.success(request, 'تم تسجيل المشكلة وإرسال تنبيه.')

            elif action == 'extra_material_issue':
                # صرف خامة إضافية (مثلاً إسفنج زائد) لتعديل منتج نهائي
                material_id = int(request.POST.get('material'))
                qty = float(request.POST.get('quantity') or 0)
                wastage = float(request.POST.get('wastage') or 0)
                unit_cost_override = request.POST.get('unit_cost')
                location_id = int(request.POST.get('location')) if request.POST.get('location') else None
                stage_id = request.POST.get('stage_id')
                pos = get_object_or_404(ProductionOrderStage, id=stage_id, production_order=order) if stage_id else None

                product = get_object_or_404(Product, id=material_id)
                location = get_object_or_404(Location, id=location_id) if location_id else Location.objects.filter(is_default=True).first()

                if qty <= 0:
                    raise ValueError('الكمية يجب أن تكون أكبر من صفر')

                unit_cost = float(unit_cost_override) if unit_cost_override not in (None, "") else product.convert_cost_per_usage_unit()

                with transaction.atomic():
                    from inventory.models import Stock
                    stock, _ = Stock.objects.select_for_update().get_or_create(product=product, location=location)
                    required_units = int(math.ceil(qty + wastage))
                    if stock.quantity < required_units:
                        raise ValueError(f'الكمية غير كافية في {location.name}. المتاح: {stock.quantity}, المطلوب: {required_units}')
                    stock.quantity -= required_units
                    stock.save()

                    MaterialConsumption.objects.create(
                        production_order=order,
                        stage=pos,
                        material=product,
                        planned_quantity=qty,
                        consumed_quantity=qty,
                        wastage_quantity=wastage,
                        unit_cost=unit_cost,
                        location=location,
                        issued_by=request.user,
                        notes=(request.POST.get('note') or 'صرف خامة إضافية من شاشة أمر الشغل')
                    )

                messages.success(request, 'تم صرف الخامة الإضافية وتحديث المخزون.')

            return redirect('production:order_work', order_id=order.id)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {e}')
            return redirect('production:order_work', order_id=order.id)

    # لواجهة صرف خامات إضافية سريعة
    from inventory.models import Product as _P
    products = _P.objects.all().order_by('name')
    locations = Location.objects.filter(is_active=True).order_by('-is_default', 'name')
    default_location = locations.filter(is_default=True).first() if hasattr(locations, 'filter') else None

    context = {
        'order': order,
        'stages': stages,
        'status_choices': ProductionOrder.STATUS_CHOICES,
        'stage_status_choices': ProductionOrderStage.STATUS_CHOICES,
        'priority_levels': ProductionAlert.PRIORITY_LEVELS,
        'products': products,
        'locations': locations,
        'default_location': default_location,
    }
    return render(request, 'production/order_work.html', context)


# ============================================================================
# بوابة العمال - Worker Portal
# ============================================================================

@login_required
def worker_portal(request):
    """بوابة الخدمة الذاتية للعمال"""
    try:
        employee = request.user.employee_profile
    except:
        messages.error(request, 'لا يوجد ملف موظف مرتبط بحسابك')
        return redirect('production:dashboard')
    
    from .models import WorkerProductionEntry
    from hr.models import LeaveRequest, LeaveType, AttendanceRecord
    
    today = timezone.now().date()
    current_month_start = today.replace(day=1)
    
    # إحصائيات
    today_production = WorkerProductionEntry.objects.filter(
        employee=employee,
        date=today
    ).aggregate(
        count=Count('id'),
        total_qty=Sum('quantity')
    )
    
    month_production = WorkerProductionEntry.objects.filter(
        employee=employee,
        date__gte=current_month_start
    ).aggregate(
        count=Count('id'),
        total_qty=Sum('quantity')
    )
    
    # رصيد الإجازات
    from hr.hr_utils import calculate_employee_leave_balance
    annual_leave_type = LeaveType.objects.filter(name__icontains='سنوي').first()
    leave_balance = 0
    if annual_leave_type:
        balance_info = calculate_employee_leave_balance(employee, annual_leave_type)
        leave_balance = balance_info.get('remaining_days', 0)
    
    pending_leaves = LeaveRequest.objects.filter(
        employee=employee,
        status='pending'
    ).count()
    
    # آخر التسجيلات الإنتاجية
    recent_production = WorkerProductionEntry.objects.filter(
        employee=employee
    ).select_related('product').order_by('-date', '-created_at')[:5]
    
    # آخر طلبات الإجازات
    recent_leaves = LeaveRequest.objects.filter(
        employee=employee
    ).select_related('leave_type').order_by('-created_at')[:5]
    
    # آخر سجلات الحضور (ملخص يومي)
    recent_attendance = AttendanceRecord.objects.filter(
        employee=employee
    ).values('date').annotate(
        check_in_time=Min('time', filter=Q(record_type='check_in')),
        check_out_time=Max('time', filter=Q(record_type='check_out'))
    ).order_by('-date')[:10]
    
    # حساب ساعات العمل
    for att in recent_attendance:
        if att['check_in_time'] and att['check_out_time']:
            from datetime import datetime, timedelta
            check_in = datetime.combine(att['date'], att['check_in_time'])
            check_out = datetime.combine(att['date'], att['check_out_time'])
            if check_out < check_in:
                check_out += timedelta(days=1)
            duration = check_out - check_in
            att['hours_worked'] = round(duration.total_seconds() / 3600, 2)
    
    context = {
        'employee': employee,
        'today': today,
        'today_production_count': today_production['count'] or 0,
        'month_production_count': month_production['count'] or 0,
        'leave_balance': leave_balance,
        'pending_leaves': pending_leaves,
        'recent_production': recent_production,
        'recent_leaves': recent_leaves,
        'recent_attendance': recent_attendance,
    }
    return render(request, 'production/worker_portal.html', context)


@login_required
def worker_production_entry(request):
    """تسجيل إنتاج العامل"""
    try:
        employee = request.user.employee_profile
    except:
        messages.error(request, 'لا يوجد ملف موظف مرتبط بحسابك')
        return redirect('production:worker_portal')
    
    from .forms import WorkerProductionEntrySimpleForm
    from .models import WorkerProductionEntry
    from users.models import UserActivity
    
    if request.method == 'POST':
        form = WorkerProductionEntrySimpleForm(request.POST, employee=employee)
        if form.is_valid():
            entry = form.save()
            
            # تسجيل النشاط
            UserActivity.objects.create(
                user=request.user,
                action='تسجيل إنتاج',
                module='الإنتاج',
                object_id=entry.id,
                description=f'تم تسجيل إنتاج: {entry.product.name} - {entry.quantity} {entry.unit_of_measure}',
                ip_address=request.META.get('REMOTE_ADDR'),
                success=True
            )
            
            messages.success(request, f'تم تسجيل إنتاجك بنجاح! {entry.product.name} - {entry.quantity} {entry.unit_of_measure}')
            return redirect('production:worker_portal')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = WorkerProductionEntrySimpleForm(employee=employee)
    
    # آخر 3 منتجات أنتجها العامل (للاقتراح)
    recent_products = WorkerProductionEntry.objects.filter(
        employee=employee
    ).values('product__id', 'product__name').annotate(
        count=Count('id')
    ).order_by('-count')[:3]

    # آخر تسجيل إنتاج لتخمين الماكينة / المرحلة الحالية
    last_entry = WorkerProductionEntry.objects.filter(
        employee=employee
    ).select_related('work_center').order_by('-date', '-created_at').first()
    current_work_center = last_entry.work_center if last_entry else None
    current_machine_code = last_entry.machine_code if last_entry else ''
    
    context = {
        'employee': employee,
        'form': form,
        'recent_products': recent_products,
        'current_work_center': current_work_center,
        'current_machine_code': current_machine_code,
    }
    return render(request, 'production/worker_production_entry.html', context)


@login_required
def worker_production_history(request):
    """تاريخ إنتاج العامل"""
    try:
        employee = request.user.employee_profile
    except:
        messages.error(request, 'لا يوجد ملف موظف مرتبط بحسابك')
        return redirect('production:worker_portal')
    
    from .models import WorkerProductionEntry
    
    # الفلترة حسب التاريخ والحالة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    
    entries = WorkerProductionEntry.objects.filter(
        employee=employee
    ).select_related('product', 'work_center')
    
    if start_date:
        entries = entries.filter(date__gte=start_date)
    if end_date:
        entries = entries.filter(date__lte=end_date)
    if status:
        entries = entries.filter(status=status)
    
    entries = entries.order_by('-date', '-created_at')
    
    # Pagination
    paginator = Paginator(entries, 20)
    page = request.GET.get('page')
    entries_page = paginator.get_page(page)
    
    # إحصائيات
    stats = entries.aggregate(
        total_count=Count('id'),
        approved_count=Count('id', filter=Q(status='approved')),
        total_quantity=Sum('quantity')
    )
    
    context = {
        'employee': employee,
        'entries': entries_page,
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date,
        'status': status,
    }
    return render(request, 'production/worker_production_history.html', context)


@login_required
def supervisor_production_approvals(request):
    """شاشة موافقات المشرف على تسجيلات الإنتاج"""
    from .models import WorkerProductionEntry
    from .forms import WorkerProductionApprovalForm
    
    # فقط المشرفين أو من لديهم صلاحية
    if not request.user.is_superuser:
        try:
            employee = request.user.employee_profile
            # التحقق من أن الموظف مشرف أو له صلاحية
            if not employee.is_supervisor:
                messages.error(request, 'هذه الصفحة للمشرفين فقط')
                return redirect('production:worker_portal')
        except:
            messages.error(request, 'لا يوجد ملف موظف مرتبط بحسابك')
            return redirect('production:dashboard')
    
    # التسجيلات المقدمة (بانتظار الموافقة)
    pending_entries = WorkerProductionEntry.objects.filter(
        status='submitted'
    ).select_related('employee', 'product', 'work_center').order_by('-date', '-created_at')
    
    if request.method == 'POST':
        entry_id = request.POST.get('entry_id')
        entry = get_object_or_404(WorkerProductionEntry, id=entry_id)
        
        form = WorkerProductionApprovalForm(request.POST, instance=entry)
        if form.is_valid():
            approve = form.cleaned_data.get('approve')
            
            if approve:
                entry.approve(request.user)
                messages.success(request, f'تم الموافقة على التسجيل لـ {entry.employee.arabic_name}')
            else:
                entry.reject(request.user, form.cleaned_data.get('rejection_reason'))
                messages.warning(request, f'تم رفض التسجيل لـ {entry.employee.arabic_name}')
            
            return redirect('production:supervisor_approvals')
    
    # Pagination
    paginator = Paginator(pending_entries, 20)
    page = request.GET.get('page')
    entries_page = paginator.get_page(page)
    
    context = {
        'entries': entries_page,
        'form': WorkerProductionApprovalForm(),
    }
    return render(request, 'production/supervisor_approvals.html', context)


# ===== الصفحات المتقدمة الإضافية =====
@login_required
def advanced_dashboard(request):
    """لوحة التحكم المتقدمة"""
    return render(request, 'production/advanced/dashboard.html')


@login_required
def work_orders_list(request):
    """قائمة أوامر العمل"""
    return render(request, 'production/work_orders/list.html')


@login_required
def production_stages_list(request):
    """مراحل الإنتاج"""
    # جلب جميع مراحل الإنتاج
    stages = ProductionStage.objects.all().order_by('sequence')
    
    # إحصائيات
    total_stages = stages.count()
    active_stages = stages.filter(is_active=True).count()
    
    # إحصائيات حسب النوع
    stages_by_type = {}
    for stage in stages:
        stage_type = stage.get_stage_type_display() if hasattr(stage, 'get_stage_type_display') else stage.stage_type
        if stage_type not in stages_by_type:
            stages_by_type[stage_type] = 0
        stages_by_type[stage_type] += 1
    
    context = {
        'stages': stages,
        'total_stages': total_stages,
        'active_stages': active_stages,
        'stages_by_type': stages_by_type,
    }
    return render(request, 'production/stages/list.html', context)


@login_required
def stage_create(request):
    """إنشاء مرحلة إنتاج جديدة"""
    from django.contrib import messages
    
    # جلب مراكز العمل لاختيارها في النموذج
    work_centers = ProductionWorkCenter.objects.filter(is_active=True)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()
        sequence = request.POST.get('order', 1)
        stage_type = request.POST.get('stage_type', 'other')
        work_center_id = request.POST.get('work_center')
        operation_time = request.POST.get('expected_time', 0)
        required_workers = request.POST.get('required_workers', 1)
        requires_quality_check = request.POST.get('requires_quality', False) == 'on'
        is_active = request.POST.get('status', 'active') == 'active'
        
        if not name:
            messages.error(request, 'يرجى إدخال اسم المرحلة')
            return render(request, 'production/stages/create.html', {
                'work_centers': work_centers,
            })
        
        try:
            # إنشاء المرحلة
            stage = ProductionStage.objects.create(
                name=name,
                code=code if code else None,  # سيتم توليده تلقائياً إذا كان فارغاً
                description=description,
                sequence=int(sequence) if sequence else 1,
                stage_type=stage_type,
                operation_time=Decimal(str(operation_time)) if operation_time else Decimal('0'),
                required_workers=int(required_workers) if required_workers else 1,
                requires_quality_check=requires_quality_check,
                is_active=is_active,
            )
            
            # ربط مركز العمل إذا تم اختياره
            if work_center_id:
                try:
                    work_center = ProductionWorkCenter.objects.get(pk=work_center_id)
                    stage.work_center = work_center
                    stage.save()
                except ProductionWorkCenter.DoesNotExist:
                    pass
            
            messages.success(request, f'تم إنشاء المرحلة "{name}" بنجاح')
            return redirect('production:stages_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
            return render(request, 'production/stages/create.html', {
                'work_centers': work_centers,
            })
    
    return render(request, 'production/stages/create.html', {
        'work_centers': work_centers,
    })


@login_required
def training_components_list(request):
    """مكونات التدريب"""
    return render(request, 'production/training/components.html')


@login_required
def quality_control_dashboard(request):
    """لوحة مراقبة الجودة"""
    return render(request, 'production/quality_control/dashboard.html')


@login_required
def production_optimization(request):
    """تحسين الإنتاج"""
    return render(request, 'production/optimization/dashboard.html')


# ===== تقارير إضافية =====
@login_required
def manufacturing_report(request):
    """تقرير التصنيع"""
    return render(request, 'production/reports/manufacturing.html')


@login_required
def production_cost_report(request):
    """تقرير تكلفة الإنتاج"""
    return render(request, 'production/reports/production_cost.html')


@login_required
def quantities_report(request):
    """تقرير الكميات"""
    return render(request, 'production/reports/quantities.html')


@login_required
def waste_report(request):
    """تقرير الهالك"""
    return render(request, 'production/reports/waste.html')


@login_required
def profitability_report(request):
    """تقرير الربحية"""
    return render(request, 'production/reports/profitability.html')


@login_required
def labor_report(request):
    """تقرير العمالة"""
    return render(request, 'production/reports/labor.html')


@login_required
def machine_efficiency_report(request):
    """تقرير كفاءة الآلات"""
    return render(request, 'production/reports/machine_efficiency.html')


@login_required
def indirect_costs_report(request):
    """تقرير التكاليف غير المباشرة"""
    return render(request, 'production/reports/indirect_costs.html')


# =============================
# Views إضافية للتوافق مع القوالب
# =============================

@login_required
def bom_list(request):
    """قائمة قوائم المواد (BOM)"""
    boms = BillOfMaterials.objects.select_related('product').all()
    
    # فلترة حسب البحث
    search = request.GET.get('search', '')
    if search:
        boms = boms.filter(
            Q(product__name__icontains=search) |
            Q(product__sku__icontains=search)
        )
    
    # ترقيم الصفحات
    paginator = Paginator(boms, 20)
    page = request.GET.get('page', 1)
    boms = paginator.get_page(page)
    
    context = {
        'boms': boms,
        'search': search,
        'page_title': 'قوائم المواد (BOM)',
    }
    return render(request, 'production/bom_list.html', context)


@login_required
def workers_list(request):
    """قائمة العمال في الإنتاج"""
    # الحصول على الموظفين المرتبطين بالإنتاج
    workers = Employee.objects.filter(
        Q(department__name__icontains='إنتاج') |
        Q(department__name__icontains='production') |
        Q(position__name__icontains='عامل') |
        Q(position__name__icontains='فني')
    ).filter(status='active')
    
    # إحصائيات
    stats = {
        'total': workers.count(),
        'active_today': workers.filter(
            attendance__check_in__date=timezone.now().date()
        ).distinct().count() if hasattr(Employee, 'attendance') else 0,
    }
    
    context = {
        'workers': workers,
        'stats': stats,
        'page_title': 'عمال الإنتاج',
    }
    return render(request, 'production/workers_list.html', context)


def production_tv_dashboard(request):
    """
    لوحة متابعة الإنتاج للمصنع — شاشة تلفزيون بتحديث لحظي عبر WebSocket.
    تعرض جميع أوامر الإنتاج المعلقة والجارية مع أشرطة تقدم مرئية.
    لا تتطلب تسجيل دخول — مصممة لشاشات المصنع (وضع الكشك).
    """

    orders = (
        ProductionOrder.objects.filter(
            status__in=['draft', 'confirmed', 'in_progress']
        )
        .select_related('product', 'bom')
        .prefetch_related('order_stages__stage__work_center')
        .order_by('-status', 'priority', 'planned_end_date')
    )

    today = timezone.now().date()

    order_list = []
    for order in orders:
        planned = float(order.planned_quantity or 0)
        produced = float(order.produced_quantity or 0)
        progress = round((produced / planned * 100) if planned > 0 else 0, 1)

        # Work center from the first BOM stage
        work_center_name = '—'
        first_stage = order.order_stages.select_related('stage__work_center').first()
        if first_stage and first_stage.stage and first_stage.stage.work_center:
            work_center_name = first_stage.stage.work_center.name

        order_list.append({
            'id': order.id,
            'number': order.number,
            'product_name': order.product.name if order.product else '—',
            'product_sku': order.product.sku if order.product else '—',
            'bom_name': order.bom.name if order.bom else '—',
            'work_center': work_center_name,
            'status': order.status,
            'status_display': order.get_status_display(),
            'priority': order.priority,
            'priority_display': order.get_priority_display(),
            'planned_quantity': planned,
            'produced_quantity': produced,
            'progress': progress,
            'planned_end': order.planned_end_date,
            'is_overdue': (
                order.planned_end_date is not None
                and order.planned_end_date < today
            ),
        })

    in_progress_count = sum(1 for o in order_list if o['status'] == 'in_progress')
    pending_count = len(order_list) - in_progress_count
    overdue_count = sum(1 for o in order_list if o['is_overdue'])

    context = {
        'orders': order_list,
        'total_active': len(order_list),
        'in_progress_count': in_progress_count,
        'pending_count': pending_count,
        'overdue_count': overdue_count,
        'now': timezone.now(),
    }

    return render(request, 'production/tv_dashboard.html', context)