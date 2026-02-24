"""
API Views للأنظمة الجديدة:
- MRP (تخطيط موارد الإنتاج)
- التكلفة الصناعية
- توزيع المعارض
- لوحة التحكم الموحدة
- تكامل المصنع-المعارض
"""

from decimal import Decimal
from datetime import date, timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone


# ==================== MRP APIs ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mrp_material_requirements(request):
    """
    حساب متطلبات المواد لمنتج
    GET /api/mrp/requirements/?product_id=1&quantity=100
    """
    from production.mrp import MRPService
    
    product_id = request.query_params.get('product_id')
    quantity = request.query_params.get('quantity', '1')
    location_id = request.query_params.get('location_id')
    
    if not product_id:
        return Response({'error': 'product_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = MRPService()
        requirements = service.calculate_material_requirements(
            product_id=int(product_id),
            quantity=Decimal(quantity),
            location_id=int(location_id) if location_id else None
        )
        
        return Response({
            'product_id': product_id,
            'quantity': quantity,
            'requirements': [
                {
                    'product_id': r.product_id,
                    'product_name': r.product_name,
                    'product_sku': r.product_sku,
                    'required_quantity': float(r.required_quantity),
                    'available_quantity': float(r.available_quantity),
                    'shortage': float(r.shortage),
                    'unit_cost': float(r.unit_cost),
                    'total_cost': float(r.total_cost),
                    'coverage_percentage': r.coverage_percentage,
                    'is_shortage': r.is_shortage,
                    'suggested_order_date': r.suggested_order_date.isoformat() if r.suggested_order_date else None,
                    'suppliers': r.suppliers
                }
                for r in requirements
            ],
            'total_cost': sum(float(r.total_cost) for r in requirements),
            'has_shortages': any(r.is_shortage for r in requirements)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mrp_production_schedule(request):
    """
    جدول الإنتاج المقترح
    GET /api/mrp/schedule/?from_date=2026-01-01&to_date=2026-01-31
    """
    from production.mrp import MRPService
    
    from_date_str = request.query_params.get('from_date')
    to_date_str = request.query_params.get('to_date')
    
    try:
        from_date = date.fromisoformat(from_date_str) if from_date_str else date.today()
        to_date = date.fromisoformat(to_date_str) if to_date_str else from_date + timedelta(days=30)
    except ValueError:
        return Response({'error': 'تنسيق التاريخ غير صحيح'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = MRPService()
        schedule = service.suggest_production_schedule(from_date, to_date)
        
        return Response({
            'from_date': from_date.isoformat(),
            'to_date': to_date.isoformat(),
            'schedule': [
                {
                    'order_id': item.order_id,
                    'order_number': item.order_number,
                    'product_id': item.product_id,
                    'product_name': item.product_name,
                    'quantity': float(item.quantity),
                    'scheduled_date': item.scheduled_date.isoformat(),
                    'work_center': item.work_center_name,
                    'estimated_hours': float(item.estimated_hours),
                    'priority': item.priority.name,
                    'status': item.status,
                    'materials_ready': item.materials_ready,
                    'capacity_available': item.capacity_available
                }
                for item in schedule
            ],
            'total_orders': len(schedule),
            'ready_to_start': sum(1 for i in schedule if i.materials_ready and i.capacity_available)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mrp_purchase_suggestions(request):
    """
    اقتراحات الشراء
    GET /api/mrp/purchase-suggestions/?days_ahead=30
    """
    from production.mrp import MRPService
    
    days_ahead = int(request.query_params.get('days_ahead', 30))
    
    try:
        service = MRPService()
        suggestions = service.generate_purchase_suggestions(days_ahead)
        
        return Response({
            'days_ahead': days_ahead,
            'suggestions': suggestions,
            'total_items': len(suggestions),
            'total_estimated_cost': sum(s['estimated_cost'] for s in suggestions),
            'urgent_count': sum(1 for s in suggestions if s['urgency'] == 'urgent')
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mrp_alerts(request):
    """
    تنبيهات الإنتاج
    GET /api/mrp/alerts/
    """
    from production.mrp import MRPService
    
    try:
        service = MRPService()
        alerts = service.get_production_alerts()
        
        return Response({
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mrp_capacity(request):
    """
    طاقة مراكز العمل
    GET /api/mrp/capacity/?work_center_id=1&from_date=2026-01-01&to_date=2026-01-07
    """
    from production.mrp import MRPService
    
    work_center_id = request.query_params.get('work_center_id')
    from_date_str = request.query_params.get('from_date')
    to_date_str = request.query_params.get('to_date')
    
    if not work_center_id:
        return Response({'error': 'work_center_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from_date = date.fromisoformat(from_date_str) if from_date_str else date.today()
        to_date = date.fromisoformat(to_date_str) if to_date_str else from_date + timedelta(days=7)
    except ValueError:
        return Response({'error': 'تنسيق التاريخ غير صحيح'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = MRPService()
        capacity = service.get_work_center_capacity(
            int(work_center_id), from_date, to_date
        )
        
        return Response({
            'work_center_id': work_center_id,
            'from_date': from_date.isoformat(),
            'to_date': to_date.isoformat(),
            'capacity': [
                {
                    'date': c.date.isoformat(),
                    'total_capacity_hours': float(c.total_capacity_hours),
                    'scheduled_hours': float(c.scheduled_hours),
                    'available_hours': float(c.available_hours),
                    'utilization_percentage': c.utilization_percentage,
                    'orders_count': c.orders_count
                }
                for c in capacity
            ],
            'avg_utilization': sum(c.utilization_percentage for c in capacity) / len(capacity) if capacity else 0
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== Costing APIs ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def costing_standard_cost(request):
    """
    التكلفة المعيارية لمنتج
    GET /api/costing/standard/?product_id=1
    """
    from production.costing import ManufacturingCostService
    
    product_id = request.query_params.get('product_id')
    
    if not product_id:
        return Response({'error': 'product_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = ManufacturingCostService()
        breakdown = service.calculate_standard_cost(int(product_id))
        
        return Response({
            'product_id': product_id,
            'cost_breakdown': {
                'material_cost': float(breakdown.material_cost),
                'labor_cost': float(breakdown.labor_cost),
                'overhead_cost': float(breakdown.overhead_cost),
                'total': float(breakdown.total)
            },
            'percentages': breakdown.percentage_breakdown
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def costing_actual_cost(request):
    """
    التكلفة الفعلية لأمر إنتاج
    GET /api/costing/actual/?order_id=1
    """
    from production.costing import ManufacturingCostService
    
    order_id = request.query_params.get('order_id')
    
    if not order_id:
        return Response({'error': 'order_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = ManufacturingCostService()
        breakdown = service.calculate_actual_cost(int(order_id))
        
        return Response({
            'order_id': order_id,
            'cost_breakdown': {
                'material_cost': float(breakdown.material_cost),
                'labor_cost': float(breakdown.labor_cost),
                'overhead_cost': float(breakdown.overhead_cost),
                'total': float(breakdown.total)
            },
            'percentages': breakdown.percentage_breakdown
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def costing_variances(request):
    """
    انحرافات التكلفة
    GET /api/costing/variances/?product_id=1&from_date=2026-01-01&to_date=2026-01-31
    """
    from production.costing import ManufacturingCostService
    
    product_id = request.query_params.get('product_id')
    from_date_str = request.query_params.get('from_date')
    to_date_str = request.query_params.get('to_date')
    
    if not product_id:
        return Response({'error': 'product_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from_date = date.fromisoformat(from_date_str) if from_date_str else date.today() - timedelta(days=30)
        to_date = date.fromisoformat(to_date_str) if to_date_str else date.today()
        
        service = ManufacturingCostService()
        variances = service.calculate_variances(int(product_id), from_date, to_date)
        
        return Response({
            'product_id': product_id,
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            },
            'variances': [
                {
                    'cost_type': v.cost_type,
                    'standard_cost': float(v.standard_cost),
                    'actual_cost': float(v.actual_cost),
                    'variance_amount': float(v.variance_amount),
                    'variance_percentage': v.variance_percentage,
                    'is_favorable': v.is_favorable
                }
                for v in variances
            ]
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def costing_product_margin(request):
    """
    هامش ربح المنتج
    GET /api/costing/margin/?product_id=1
    """
    from production.costing import ManufacturingCostService
    
    product_id = request.query_params.get('product_id')
    use_standard = request.query_params.get('use_standard', 'true').lower() == 'true'
    
    if not product_id:
        return Response({'error': 'product_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = ManufacturingCostService()
        margin = service.calculate_product_margin(int(product_id), use_standard)
        
        return Response(margin)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def costing_analysis_report(request):
    """
    تقرير تحليل التكلفة
    GET /api/costing/analysis/?from_date=2026-01-01&to_date=2026-01-31
    """
    from production.costing import ManufacturingCostService
    
    from_date_str = request.query_params.get('from_date')
    to_date_str = request.query_params.get('to_date')
    product_ids = request.query_params.getlist('product_id')
    
    try:
        from_date = date.fromisoformat(from_date_str) if from_date_str else None
        to_date = date.fromisoformat(to_date_str) if to_date_str else None
        
        service = ManufacturingCostService()
        analysis = service.get_cost_analysis_report(
            product_ids=[int(p) for p in product_ids] if product_ids else None,
            from_date=from_date,
            to_date=to_date
        )
        
        return Response({
            'period': {
                'from': from_date.isoformat() if from_date else None,
                'to': to_date.isoformat() if to_date else None
            },
            'products': [
                {
                    'product_id': a.product_id,
                    'product_name': a.product_name,
                    'standard_cost': float(a.standard_cost.total),
                    'actual_cost': float(a.actual_cost.total),
                    'selling_price': float(a.selling_price),
                    'margin_amount': float(a.margin_amount),
                    'margin_percentage': a.margin_percentage,
                    'production_quantity': float(a.production_quantity)
                }
                for a in analysis
            ]
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== Distribution APIs ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def distribution_stock_levels(request):
    """
    مستويات المخزون في فرع
    GET /api/distribution/stock-levels/?branch_id=1
    """
    from branches.distribution import ShowroomDistributionService
    
    branch_id = request.query_params.get('branch_id')
    
    if not branch_id:
        return Response({'error': 'branch_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = ShowroomDistributionService()
        levels = service.get_branch_stock_levels(int(branch_id))
        
        return Response({
            'branch_id': branch_id,
            'stock_levels': [
                {
                    'product_id': l.product_id,
                    'product_name': l.product_name,
                    'current_quantity': float(l.current_quantity),
                    'minimum_quantity': float(l.minimum_quantity),
                    'reorder_point': float(l.reorder_point),
                    'maximum_quantity': float(l.maximum_quantity),
                    'fill_rate': l.fill_rate,
                    'needs_replenishment': l.needs_replenishment,
                    'is_critical': l.is_critical
                }
                for l in levels
            ],
            'summary': {
                'total_items': len(levels),
                'critical': sum(1 for l in levels if l.is_critical),
                'needs_replenishment': sum(1 for l in levels if l.needs_replenishment)
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def distribution_replenishment_suggestions(request):
    """
    اقتراحات التموين
    GET /api/distribution/replenishment/?branch_id=1
    """
    from branches.distribution import ShowroomDistributionService
    
    branch_id = request.query_params.get('branch_id')
    
    try:
        service = ShowroomDistributionService()
        suggestions = service.get_replenishment_suggestions(
            branch_id=int(branch_id) if branch_id else None
        )
        
        return Response({
            'suggestions': [
                {
                    'branch_id': s.branch_id,
                    'branch_name': s.branch_name,
                    'product_id': s.product_id,
                    'product_name': s.product_name,
                    'product_sku': s.product_sku,
                    'current_stock': float(s.current_stock),
                    'suggested_quantity': float(s.suggested_quantity),
                    'source_branch_name': s.source_branch_name,
                    'source_available': float(s.source_available),
                    'priority': s.priority.value,
                    'estimated_days_until_stockout': s.estimated_days_until_stockout,
                    'total_cost': float(s.total_cost)
                }
                for s in suggestions
            ],
            'total_items': len(suggestions),
            'urgent_count': sum(1 for s in suggestions if s.priority.value == 'urgent'),
            'total_cost': sum(float(s.total_cost) for s in suggestions)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def distribution_create_replenishment(request):
    """
    إنشاء أوامر تموين
    POST /api/distribution/create-replenishment/
    """
    from branches.distribution import ShowroomDistributionService
    
    suggestion_ids = request.data.get('suggestion_ids', [])
    notes = request.data.get('notes', '')
    
    try:
        service = ShowroomDistributionService()
        suggestions = service.get_replenishment_suggestions()
        
        # فلترة الاقتراحات المحددة (إذا تم تحديدها)
        if suggestion_ids:
            suggestions = [s for i, s in enumerate(suggestions) if i in suggestion_ids]
        
        transfers = service.create_replenishment_order(
            suggestions, request.user, notes
        )
        
        return Response({
            'success': True,
            'transfers_created': len(transfers),
            'transfer_ids': list(transfers.keys())
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def distribution_dashboard(request):
    """
    لوحة معلومات التوزيع
    GET /api/distribution/dashboard/
    """
    from branches.distribution import ShowroomDistributionService
    
    try:
        service = ShowroomDistributionService()
        dashboard = service.get_distribution_dashboard()
        
        return Response(dashboard)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def distribution_movements(request):
    """
    حركة المخزون بين الفروع
    GET /api/distribution/movements/?from_date=2026-01-01&to_date=2026-01-31
    """
    from branches.distribution import ShowroomDistributionService
    
    from_date_str = request.query_params.get('from_date')
    to_date_str = request.query_params.get('to_date')
    branch_id = request.query_params.get('branch_id')
    
    try:
        from_date = date.fromisoformat(from_date_str) if from_date_str else date.today() - timedelta(days=30)
        to_date = date.fromisoformat(to_date_str) if to_date_str else date.today()
        
        service = ShowroomDistributionService()
        movements = service.get_inter_branch_movements(
            from_date, to_date,
            branch_id=int(branch_id) if branch_id else None
        )
        
        return Response({
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            },
            'movements': movements,
            'summary': {
                'total_transfers': len(movements),
                'total_value': sum(m['total_value'] for m in movements)
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== Unified Dashboard APIs ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unified_dashboard(request):
    """
    لوحة التحكم الموحدة الكاملة
    GET /api/dashboard/unified/
    """
    from core.unified_dashboard import UnifiedDashboardService
    
    try:
        service = UnifiedDashboardService()
        dashboard = service.get_full_dashboard()
        
        return Response(dashboard)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_company_overview(request):
    """
    نظرة عامة على الشركة
    GET /api/dashboard/company/
    """
    from core.unified_dashboard import UnifiedDashboardService
    
    try:
        service = UnifiedDashboardService()
        overview = service.get_company_overview()
        
        return Response(overview)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_branches_performance(request):
    """
    أداء الفروع
    GET /api/dashboard/branches/
    """
    from core.unified_dashboard import UnifiedDashboardService
    
    limit = int(request.query_params.get('limit', 10))
    
    try:
        service = UnifiedDashboardService()
        performance = service.get_branches_performance(limit)
        
        return Response({
            'branches': performance,
            'total': len(performance)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_production_status(request):
    """
    حالة الإنتاج
    GET /api/dashboard/production/
    """
    from core.unified_dashboard import UnifiedDashboardService
    
    try:
        service = UnifiedDashboardService()
        status_data = service.get_production_status()
        
        return Response(status_data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_inventory_overview(request):
    """
    نظرة عامة على المخزون
    GET /api/dashboard/inventory/
    """
    from core.unified_dashboard import UnifiedDashboardService
    
    try:
        service = UnifiedDashboardService()
        overview = service.get_inventory_overview()
        
        return Response(overview)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_alerts(request):
    """
    التنبيهات
    GET /api/dashboard/alerts/
    """
    from core.unified_dashboard import UnifiedDashboardService
    
    max_alerts = int(request.query_params.get('max', 20))
    
    try:
        service = UnifiedDashboardService()
        alerts = service.get_all_alerts(max_alerts)
        
        return Response({
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_charts(request):
    """
    بيانات الرسوم البيانية
    GET /api/dashboard/charts/
    """
    from core.unified_dashboard import UnifiedDashboardService
    
    try:
        service = UnifiedDashboardService()
        charts = service.get_charts_data()
        
        return Response(charts)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== Integration APIs ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def integration_demands(request):
    """
    جمع الطلبات من جميع المصادر
    GET /api/integration/demands/
    """
    from production.factory_showroom_integration import FactoryShowroomIntegration
    
    from_date_str = request.query_params.get('from_date')
    to_date_str = request.query_params.get('to_date')
    branch_ids = request.query_params.getlist('branch_id')
    
    try:
        from_date = date.fromisoformat(from_date_str) if from_date_str else None
        to_date = date.fromisoformat(to_date_str) if to_date_str else None
        
        service = FactoryShowroomIntegration()
        demands = service.collect_demands(
            from_date=from_date,
            to_date=to_date,
            branch_ids=[int(b) for b in branch_ids] if branch_ids else None
        )
        
        return Response({
            'demands': [
                {
                    'product_id': d.product_id,
                    'product_name': d.product_name,
                    'product_sku': d.product_sku,
                    'requested_quantity': float(d.requested_quantity),
                    'source': d.source.value,
                    'source_branch_name': d.source_branch_name,
                    'required_date': d.required_date.isoformat(),
                    'priority': d.priority,
                    'scheduled_quantity': float(d.scheduled_quantity),
                    'is_fully_scheduled': d.is_fully_scheduled
                }
                for d in demands
            ],
            'total': len(demands),
            'unscheduled': sum(1 for d in demands if not d.is_fully_scheduled)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def integration_create_production(request):
    """
    إنشاء أوامر إنتاج من الطلبات
    POST /api/integration/create-production/
    """
    from production.factory_showroom_integration import FactoryShowroomIntegration
    
    work_center_id = request.data.get('work_center_id')
    
    try:
        service = FactoryShowroomIntegration()
        demands = service.collect_demands()
        
        # فقط الطلبات غير المجدولة بالكامل
        unscheduled = [d for d in demands if not d.is_fully_scheduled]
        
        orders = service.create_production_from_demands(
            unscheduled,
            request.user,
            work_center_id=int(work_center_id) if work_center_id else None
        )
        
        return Response({
            'success': True,
            'orders_created': len(orders),
            'order_numbers': [o.order_number for o in orders]
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def integration_create_transfer(request):
    """
    إنشاء تحويل من أمر إنتاج مكتمل
    POST /api/integration/create-transfer/
    """
    from production.factory_showroom_integration import FactoryShowroomIntegration
    
    production_order_id = request.data.get('production_order_id')
    target_branch_id = request.data.get('target_branch_id')
    
    if not production_order_id or not target_branch_id:
        return Response({
            'error': 'production_order_id و target_branch_id مطلوبان'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = FactoryShowroomIntegration()
        transfer = service.create_transfer_from_production(
            int(production_order_id),
            int(target_branch_id),
            request.user
        )
        
        return Response({
            'success': True,
            'transfer_id': transfer.id,
            'transfer_number': transfer.transfer_number
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def integration_links(request):
    """
    روابط الإنتاج-المعارض
    GET /api/integration/links/
    """
    from production.factory_showroom_integration import FactoryShowroomIntegration
    
    branch_id = request.query_params.get('branch_id')
    status_filter = request.query_params.get('status')
    
    try:
        service = FactoryShowroomIntegration()
        links = service.get_production_showroom_links(
            branch_id=int(branch_id) if branch_id else None,
            status=status_filter
        )
        
        return Response({
            'links': [
                {
                    'production_order_id': l.production_order_id,
                    'production_order_number': l.production_order_number,
                    'target_branch_name': l.target_branch_name,
                    'product_name': l.product_name,
                    'quantity': float(l.quantity),
                    'status': l.status,
                    'production_status': l.production_status,
                    'transfer_status': l.transfer_status,
                    'transfer_id': l.transfer_id
                }
                for l in links
            ],
            'total': len(links)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def integration_dashboard(request):
    """
    لوحة معلومات التكامل
    GET /api/integration/dashboard/
    """
    from production.factory_showroom_integration import FactoryShowroomIntegration
    
    try:
        service = FactoryShowroomIntegration()
        dashboard = service.get_integration_dashboard()
        
        return Response(dashboard)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def integration_auto_process(request):
    """
    معالجة تلقائية للطلبات
    POST /api/integration/auto-process/
    """
    from production.factory_showroom_integration import FactoryShowroomIntegration
    
    try:
        service = FactoryShowroomIntegration()
        result = service.auto_process_demands(request.user)
        
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
