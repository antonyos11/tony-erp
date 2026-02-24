# -*- coding: utf-8 -*-
"""
Views لتقارير الأسعار والتكاليف
===============================
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, F, Q, Max, Min
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json


@login_required
def price_history_list(request):
    """
    عرض سجل تاريخ الأسعار
    """
    from .price_history import MaterialPriceHistory
    from .models import Product
    from partners.models import Supplier
    
    # الفلاتر
    product_id = request.GET.get('product')
    supplier_id = request.GET.get('supplier')
    change_type = request.GET.get('change_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    direction = request.GET.get('direction')  # increase, decrease
    
    # جلب السجلات
    history = MaterialPriceHistory.objects.select_related(
        'product', 'supplier', 'changed_by'
    ).order_by('-changed_at')
    
    # تطبيق الفلاتر
    if product_id:
        history = history.filter(product_id=product_id)
    if supplier_id:
        history = history.filter(supplier_id=supplier_id)
    if change_type:
        history = history.filter(change_type=change_type)
    if date_from:
        history = history.filter(changed_at__date__gte=date_from)
    if date_to:
        history = history.filter(changed_at__date__lte=date_to)
    if direction == 'increase':
        history = history.filter(price_change__gt=0)
    elif direction == 'decrease':
        history = history.filter(price_change__lt=0)
    
    # إحصائيات
    stats = history.aggregate(
        total_changes=Count('id'),
        avg_change_pct=Avg('change_percentage'),
        increases=Count('id', filter=Q(price_change__gt=0)),
        decreases=Count('id', filter=Q(price_change__lt=0)),
    )
    
    # المنتجات والموردين للفلاتر
    products = Product.objects.filter(product_type='raw_material', is_active=True).order_by('name')
    suppliers = Supplier.objects.order_by('name')
    
    context = {
        'title': 'سجل تاريخ الأسعار',
        'history': history[:100],  # أول 100 سجل
        'stats': stats,
        'products': products,
        'suppliers': suppliers,
        'change_types': MaterialPriceHistory.CHANGE_TYPES,
        'filters': {
            'product': product_id,
            'supplier': supplier_id,
            'change_type': change_type,
            'date_from': date_from,
            'date_to': date_to,
            'direction': direction,
        }
    }
    
    return render(request, 'inventory/reports/price_history.html', context)


@login_required
def price_impact_analysis(request):
    """
    تحليل تأثير تغيير السعر
    """
    from .price_history import MaterialPriceHistory, PriceChangeImpact
    from .models import Product
    from partners.models import Supplier
    
    # فترة التحليل
    period = request.GET.get('period', '30')  # أيام
    try:
        days = int(period)
    except ValueError:
        days = 30
    
    date_from = timezone.now() - timedelta(days=days)
    
    # تغييرات الأسعار في الفترة
    price_changes = MaterialPriceHistory.objects.filter(
        changed_at__gte=date_from
    ).select_related('product', 'supplier')
    
    # إحصائيات التغييرات
    stats = price_changes.aggregate(
        total_changes=Count('id'),
        avg_increase=Avg('change_percentage', filter=Q(price_change__gt=0)),
        avg_decrease=Avg('change_percentage', filter=Q(price_change__lt=0)),
        max_increase=Max('change_percentage', filter=Q(price_change__gt=0)),
        max_decrease=Min('change_percentage', filter=Q(price_change__lt=0)),
    )
    
    # المواد الأكثر تغيراً
    top_changed = price_changes.values(
        'product__id', 'product__name'
    ).annotate(
        change_count=Count('id'),
        avg_change=Avg('change_percentage'),
    ).order_by('-change_count')[:10]
    
    # التأثيرات على المنتجات
    impacts = PriceChangeImpact.objects.filter(
        created_at__gte=date_from
    ).select_related('affected_product', 'price_change', 'price_change__product')
    
    impact_stats = impacts.aggregate(
        total_affected=Count('affected_product', distinct=True),
        total_cost_impact=Sum('unit_cost_impact'),
        total_stock_impact=Sum('stock_value_impact'),
        avg_margin_change=Avg(F('new_profit_margin') - F('old_profit_margin')),
    )
    
    # المنتجات الأكثر تأثراً
    most_affected = impacts.values(
        'affected_product__id', 'affected_product__name'
    ).annotate(
        impact_count=Count('id'),
        total_impact=Sum('unit_cost_impact'),
    ).order_by('-total_impact')[:10]
    
    context = {
        'title': 'تحليل تأثير تغييرات الأسعار',
        'period': days,
        'date_from': date_from,
        'stats': stats,
        'impact_stats': impact_stats,
        'top_changed': top_changed,
        'most_affected': most_affected,
        'price_changes': price_changes[:20],
    }
    
    return render(request, 'inventory/reports/price_impact.html', context)


@login_required
def product_cost_breakdown(request, product_id):
    """
    تفصيل تكلفة منتج من قائمة المواد
    """
    from .models import Product
    from .cost_service import get_cost_service
    from production.models import BillOfMaterials
    
    product = get_object_or_404(Product, pk=product_id)
    
    # جلب قائمة المواد
    bom = BillOfMaterials.objects.filter(
        product=product,
        is_active=True,
        is_default=True
    ).first()
    
    # حساب التكلفة
    cost_service = get_cost_service(request.user)
    cost_result = cost_service.calculate_product_cost_from_bom(product_id)

    # حساب هامش الربح
    profit = None
    margin_pct = None
    if cost_result.get('success'):
        try:
            unit_cost = Decimal(str(cost_result.get('unit_cost', 0) or 0))
            selling_price = product.price or Decimal('0')
            profit = selling_price - unit_cost
            if selling_price > 0:
                margin_pct = (profit / selling_price * 100).quantize(Decimal('0.01'))
        except Exception:
            profit = None
            margin_pct = None
    
    # تاريخ التكاليف
    from .price_history import ProductCostHistory
    cost_history = ProductCostHistory.objects.filter(
        product=product
    ).order_by('-changed_at')[:20]
    
    context = {
        'title': f'تفصيل تكلفة: {product.name}',
        'product': product,
        'bom': bom,
        'cost_result': cost_result,
        'cost_history': cost_history,
        'profit': profit,
        'margin_pct': margin_pct,
    }
    
    return render(request, 'inventory/reports/cost_breakdown.html', context)


@login_required
def price_change_preview(request):
    """
    معاينة تأثير تغيير السعر قبل تطبيقه
    API endpoint
    """
    from .cost_service import get_cost_service
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        material_id = data.get('material_id')
        old_price = Decimal(str(data.get('old_price', 0)))
        new_price = Decimal(str(data.get('new_price', 0)))
        
        if not material_id:
            return JsonResponse({'error': 'material_id required'}, status=400)
        
        cost_service = get_cost_service(request.user)
        result = cost_service.calculate_price_change_impact(
            material_id=int(material_id),
            old_price=old_price,
            new_price=new_price
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def notifications_list(request):
    """
    قائمة إشعارات تغيير الأسعار
    """
    from .notifications import PriceChangeNotification
    
    # فلتر حسب الحالة
    status = request.GET.get('status', 'unread')
    
    notifications = PriceChangeNotification.objects.filter(
        recipient=request.user
    ).select_related('product', 'supplier').order_by('-created_at')
    
    if status and status != 'all':
        notifications = notifications.filter(status=status)
    
    # إحصائيات
    stats = PriceChangeNotification.objects.filter(
        recipient=request.user
    ).aggregate(
        total=Count('id'),
        unread=Count('id', filter=Q(status='unread')),
        critical=Count('id', filter=Q(severity='critical', status='unread')),
    )
    
    context = {
        'title': 'إشعارات الأسعار',
        'notifications': notifications[:50],
        'stats': stats,
        'current_status': status,
    }
    
    return render(request, 'inventory/reports/notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """
    تحديد إشعار كمقروء
    """
    from .notifications import PriceChangeNotification
    
    notification = get_object_or_404(
        PriceChangeNotification,
        pk=notification_id,
        recipient=request.user
    )
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('inventory:notifications_list')


@login_required
def cost_comparison_report(request):
    """
    تقرير مقارنة التكاليف
    """
    from .models import Product
    from production.models import BillOfMaterials
    from .price_history import ProductCostHistory
    
    # المنتجات مع BOM
    products = Product.objects.filter(
        product_type='finished',
        is_active=True,
        bom_list__is_active=True,
        bom_list__is_default=True
    ).distinct()
    
    comparison_data = []
    
    for product in products[:50]:  # أول 50 منتج
        bom = product.bom_list.filter(is_active=True, is_default=True).first()
        if not bom:
            continue
        
        # آخر تغيير في التكلفة
        last_change = ProductCostHistory.objects.filter(
            product=product
        ).order_by('-changed_at').first()
        
        # حساب هامش الربح
        cost = product.cost or Decimal('0')
        price = product.price or Decimal('0')
        margin = ((price - cost) / price * 100) if price > 0 else 0
        
        comparison_data.append({
            'product': product,
            'bom': bom,
            'current_cost': cost,
            'selling_price': price,
            'margin': margin,
            'last_change': last_change,
            'material_cost': bom.total_material_cost,
            'labor_cost': bom.total_labor_cost,
            'overhead_cost': bom.total_overhead_cost,
        })
    
    # ترتيب حسب هامش الربح
    comparison_data.sort(key=lambda x: x['margin'])
    
    context = {
        'title': 'تقرير مقارنة التكاليف',
        'comparison_data': comparison_data,
        'low_margin_products': [p for p in comparison_data if p['margin'] < 15],
    }
    
    return render(request, 'inventory/reports/cost_comparison.html', context)


@login_required
def supplier_price_trends(request, supplier_id=None):
    """
    تقرير اتجاهات أسعار الموردين
    """
    from .price_history import MaterialPriceHistory
    from .models import Product
    from partners.models import Supplier
    
    # الفترة
    period = request.GET.get('period', '90')
    try:
        days = int(period)
    except ValueError:
        days = 90
    
    date_from = timezone.now() - timedelta(days=days)
    
    # جلب المورد
    supplier = None
    if supplier_id:
        supplier = get_object_or_404(Supplier, pk=supplier_id)
    
    # تغييرات الأسعار
    changes = MaterialPriceHistory.objects.filter(
        changed_at__gte=date_from
    ).select_related('product', 'supplier')
    
    if supplier:
        changes = changes.filter(supplier=supplier)
    
    # تجميع حسب المورد
    supplier_stats = changes.values(
        'supplier__id', 'supplier__name'
    ).annotate(
        total_changes=Count('id'),
        avg_change=Avg('change_percentage'),
        increases=Count('id', filter=Q(price_change__gt=0)),
        decreases=Count('id', filter=Q(price_change__lt=0)),
    ).order_by('-total_changes')
    
    # بيانات للرسم البياني
    chart_data = []
    for record in changes.order_by('changed_at')[:100]:
        chart_data.append({
            'date': record.changed_at.strftime('%Y-%m-%d'),
            'product': record.product.name,
            'supplier': record.supplier.name if record.supplier else 'N/A',
            'change_percentage': float(record.change_percentage),
        })
    
    context = {
        'title': f'اتجاهات أسعار {"المورد: " + supplier.name if supplier else "الموردين"}',
        'supplier': supplier,
        'period': days,
        'supplier_stats': supplier_stats,
        'changes': changes[:50],
        'chart_data': json.dumps(chart_data),
        'suppliers': Supplier.objects.order_by('name'),
    }
    
    return render(request, 'inventory/reports/supplier_trends.html', context)


# API Endpoints

@login_required
def api_recalculate_all_costs(request):
    """
    API: إعادة حساب جميع التكاليف
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    from .cost_service import get_cost_service
    
    try:
        cost_service = get_cost_service(request.user)
        result = cost_service.recalculate_all_bom_costs()
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_get_material_price_history(request, material_id):
    """
    API: جلب تاريخ أسعار مادة خام
    """
    from .price_history import MaterialPriceHistory
    
    history = MaterialPriceHistory.objects.filter(
        product_id=material_id
    ).order_by('-changed_at')[:50]
    
    data = []
    for record in history:
        data.append({
            'id': record.id,
            'old_price': float(record.old_price),
            'new_price': float(record.new_price),
            'change': float(record.price_change),
            'change_percentage': float(record.change_percentage),
            'supplier': record.supplier.name if record.supplier else None,
            'change_type': record.change_type,
            'change_reason': record.change_reason,
            'changed_at': record.changed_at.isoformat(),
            'changed_by': record.changed_by.username if record.changed_by else None,
        })
    
    return JsonResponse({'history': data})


@login_required
def api_get_unread_notifications_count(request):
    """
    API: عدد الإشعارات غير المقروءة
    """
    from .notifications import PriceChangeNotification
    
    count = PriceChangeNotification.objects.filter(
        recipient=request.user,
        status='unread'
    ).count()
    
    critical_count = PriceChangeNotification.objects.filter(
        recipient=request.user,
        status='unread',
        severity='critical'
    ).count()
    
    return JsonResponse({
        'unread_count': count,
        'critical_count': critical_count,
    })
