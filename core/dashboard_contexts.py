"""
Context builders for specialized dashboards
بناء البيانات للوحات التحكم المتخصصة
"""
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, Avg
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def get_distribution_context():
    """بيانات لوحة التوزيع والشحن"""
    ctx = {}
    today = timezone.now().date()

    # ── الفروع والمعارض ──
    try:
        from branches.models import Branch, BranchTransfer
        from showrooms.models import Showroom

        branches = Branch.objects.all()
        showrooms = Showroom.objects.all()
        active_branches = branches.filter(is_active=True).count() if hasattr(Branch, 'is_active') else branches.count()
        active_showrooms = showrooms.filter(is_active=True).count() if hasattr(Showroom, 'is_active') else showrooms.count()

        # التحويلات
        transfers = BranchTransfer.objects.all()
        total_transfers = transfers.count()
        pending_transfers = transfers.filter(status__in=['pending', 'draft', 'approved']).count()
        shipped_transfers = transfers.filter(status__in=['shipped', 'in_transit']).count()
        completed_transfers = transfers.filter(status__in=['received', 'completed']).count()

        # آخر التحويلات
        recent_transfers = transfers.order_by('-transfer_date')[:15]

        # بيانات حسب الفرع
        branch_stats = []
        for b in branches[:8]:
            outgoing = transfers.filter(from_branch=b).count()
            incoming = transfers.filter(to_branch=b).count()
            branch_stats.append({
                'name': b.name,
                'count': outgoing + incoming,
                'outgoing': outgoing,
                'incoming': incoming,
            })

        ctx.update({
            'active_branches': active_branches,
            'active_showrooms': active_showrooms,
            'total_locations': active_branches + active_showrooms,
            'total_transfers': total_transfers,
            'pending_transfers': pending_transfers,
            'shipped_transfers': shipped_transfers,
            'completed_transfers': completed_transfers,
            'recent_transfers': recent_transfers,
            'branch_stats': branch_stats,
        })
    except Exception as e:
        logger.debug("Distribution context - branches error: %s", e)
        ctx.update({
            'active_branches': 0, 'active_showrooms': 0, 'total_locations': 0,
            'total_transfers': 0, 'pending_transfers': 0, 'shipped_transfers': 0,
            'completed_transfers': 0, 'recent_transfers': [], 'branch_stats': [],
        })

    # ── المخزون بالفروع ──
    try:
        from inventory.models import Stock, StockTransfer
        stock_transfers = StockTransfer.objects.all()
        pending_stock_transfers = stock_transfers.filter(status__in=['pending', 'draft']).count()
        completed_stock_transfers = stock_transfers.filter(status__in=['completed', 'received']).count()

        # مخزون حسب الموقع
        from inventory.models import Location
        branch_inventory = []
        locations = Location.objects.annotate(
            total_stock=Sum('stocks__quantity'),
            product_count=Count('stocks__product', distinct=True),
        ).filter(total_stock__gt=0).order_by('-total_stock')[:8]
        for loc in locations:
            branch_inventory.append({
                'name': loc.name,
                'items': loc.product_count or 0,
                'total_stock': loc.total_stock or 0,
                'percentage': min(100, int((loc.total_stock or 0) / 50 * 100)) if loc.total_stock else 0,
            })

        ctx.update({
            'pending_stock_transfers': pending_stock_transfers,
            'completed_stock_transfers': completed_stock_transfers,
            'branch_inventory': branch_inventory,
        })
    except Exception as e:
        logger.debug("Distribution context - inventory error: %s", e)
        ctx.update({
            'pending_stock_transfers': 0, 'completed_stock_transfers': 0,
            'branch_inventory': [],
        })

    # ── الفواتير حسب الفرع ──
    try:
        from sales.models import Invoice
        total_invoices = Invoice.objects.count()
        today_invoices = Invoice.objects.filter(date=today).count()
        ctx.update({
            'total_invoices': total_invoices,
            'today_invoices': today_invoices,
        })
    except Exception as e:
        ctx.update({'total_invoices': 0, 'today_invoices': 0})

    # ── اتجاه التحويلات آخر 7 أيام ──
    transfer_trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_label = d.strftime('%m/%d')
        try:
            from branches.models import BranchTransfer
            day_count = BranchTransfer.objects.filter(transfer_date=d).count()
        except Exception:
            day_count = 0
        transfer_trend.append({'date': day_label, 'count': day_count})
    ctx['transfer_trend'] = transfer_trend

    return ctx


def get_costing_context():
    """بيانات لوحة التكاليف والتسعير"""
    ctx = {}

    # ── أوامر الإنتاج والتكاليف ──
    try:
        from production.models import ProductionOrder, BillOfMaterials, BOMItem, MaterialConsumption

        orders = ProductionOrder.objects.all()
        completed = orders.filter(status='completed')

        # تكاليف فعلية
        cost_agg = completed.aggregate(
            total_material=Sum('actual_material_cost'),
            total_labor=Sum('actual_labor_cost'),
            total_overhead=Sum('actual_overhead_cost'),
            est_material=Sum('estimated_material_cost'),
            est_labor=Sum('estimated_labor_cost'),
            est_overhead=Sum('estimated_overhead_cost'),
        )

        actual_material = float(cost_agg['total_material'] or 0)
        actual_labor = float(cost_agg['total_labor'] or 0)
        actual_overhead = float(cost_agg['total_overhead'] or 0)
        total_actual = actual_material + actual_labor + actual_overhead

        est_material = float(cost_agg['est_material'] or 0)
        est_labor = float(cost_agg['est_labor'] or 0)
        est_overhead = float(cost_agg['est_overhead'] or 0)
        total_estimated = est_material + est_labor + est_overhead

        # نسب التكاليف
        if total_actual > 0:
            material_pct = round(actual_material / total_actual * 100)
            labor_pct = round(actual_labor / total_actual * 100)
            overhead_pct = 100 - material_pct - labor_pct
        else:
            material_pct, labor_pct, overhead_pct = 45, 25, 30

        # انحراف التكلفة
        if total_estimated > 0:
            cost_variance = round((total_actual - total_estimated) / total_estimated * 100, 1)
        else:
            cost_variance = 0

        ctx.update({
            'total_production_cost': round(total_actual),
            'raw_material_cost': round(actual_material),
            'labor_cost': round(actual_labor),
            'overhead_cost': round(actual_overhead),
            'estimated_total': round(total_estimated),
            'material_percentage': material_pct,
            'labor_percentage': labor_pct,
            'overhead_percentage': overhead_pct,
            'cost_variance': cost_variance,
            'total_orders': orders.count(),
            'completed_orders': completed.count(),
        })
    except Exception as e:
        logger.debug("Costing context - production error: %s", e)
        ctx.update({
            'total_production_cost': 0, 'raw_material_cost': 0,
            'labor_cost': 0, 'overhead_cost': 0, 'estimated_total': 0,
            'material_percentage': 45, 'labor_percentage': 25, 'overhead_percentage': 30,
            'cost_variance': 0, 'total_orders': 0, 'completed_orders': 0,
        })

    # ── تكلفة المنتجات من BOM ──
    try:
        from production.models import BillOfMaterials, BOMItem
        from inventory.models import Product

        products_costing = []
        for bom in BillOfMaterials.objects.select_related('product').all()[:20]:
            product = bom.product
            items = BOMItem.objects.filter(bom=bom)
            material_cost = sum(float(i.unit_cost or 0) * float(i.quantity or 0) for i in items)
            mfg_cost = material_cost * 0.35  # تكلفة تصنيع تقديرية
            total_cost = material_cost + mfg_cost
            selling_price = float(getattr(product, 'price', 0) or getattr(product, 'selling_price', 0) or 0)
            margin = round(((selling_price - total_cost) / selling_price * 100), 1) if selling_price > 0 else 0

            products_costing.append({
                'name': getattr(product, 'name', str(product)),
                'bom_name': bom.name,
                'material_cost': round(material_cost),
                'manufacturing_cost': round(mfg_cost),
                'total_cost': round(total_cost),
                'selling_price': round(selling_price),
                'margin': margin,
                'items_count': items.count(),
            })

        # متوسط هامش الربح
        margins = [p['margin'] for p in products_costing if p['margin'] > 0]
        avg_profit_margin = round(sum(margins) / len(margins), 1) if margins else 0

        ctx.update({
            'products_costing': products_costing,
            'avg_profit_margin': avg_profit_margin,
            'bom_count': BillOfMaterials.objects.count(),
        })
    except Exception as e:
        logger.debug("Costing context - BOM error: %s", e)
        ctx.update({'products_costing': [], 'avg_profit_margin': 0, 'bom_count': 0})

    # ── استهلاك المواد ──
    try:
        from production.models import MaterialConsumption
        consumptions = MaterialConsumption.objects.all()
        total_consumed = consumptions.aggregate(t=Sum('total_cost'))['t'] or 0
        total_wastage = consumptions.aggregate(t=Sum('wastage_quantity'))['t'] or 0
        ctx.update({
            'total_material_consumed': round(float(total_consumed)),
            'total_wastage': round(float(total_wastage)),
            'consumption_count': consumptions.count(),
        })
    except Exception as e:
        ctx.update({'total_material_consumed': 0, 'total_wastage': 0, 'consumption_count': 0})

    return ctx


def get_mrp_context():
    """بيانات لوحة تخطيط موارد التصنيع MRP"""
    ctx = {}
    today = timezone.now().date()

    # ── أوامر الإنتاج ──
    try:
        from production.models import ProductionOrder

        all_orders = ProductionOrder.objects.all()
        active_orders = all_orders.filter(status__in=['in_progress', 'confirmed', 'quality_check'])
        planned_orders = all_orders.filter(status__in=['draft'])
        completed_orders = all_orders.filter(status='completed')
        on_hold = all_orders.filter(status='on_hold')
        cancelled = all_orders.filter(status='cancelled')

        # إحصائيات الحالات
        status_completed = completed_orders.count()
        status_in_progress = active_orders.count()
        status_planned = planned_orders.count()
        status_on_hold = on_hold.count()
        status_cancelled = cancelled.count()

        # الإنتاج هذا الشهر
        completed_this_month = completed_orders.filter(
            actual_end_date__month=today.month,
            actual_end_date__year=today.year,
        ).count()

        # كفاءة الإنتاج
        total = max(all_orders.count(), 1)
        production_efficiency = round((status_completed / total) * 100)

        # نسبة استغلال الطاقة
        capacity_usage = min(round((status_in_progress / max(total, 1)) * 100 + 20), 100)

        # قائمة الأوامر النشطة
        production_orders = []
        for po in all_orders.exclude(status__in=['completed', 'cancelled']).select_related('product').order_by('-order_date')[:12]:
            planned = float(po.planned_quantity or 0)
            produced = float(po.produced_quantity or 0)
            progress = round((produced / planned * 100)) if planned > 0 else 0

            production_orders.append({
                'id': po.id,
                'order_number': po.number,
                'product_name': str(po.product) if po.product else '—',
                'quantity': int(planned),
                'produced': int(produced),
                'progress': min(progress, 100),
                'status': po.status,
                'get_status_display': po.get_status_display(),
                'due_date': po.planned_end_date,
                'priority': po.priority,
                'get_priority_display': po.get_priority_display() if hasattr(po, 'get_priority_display') else po.priority,
            })

        ctx.update({
            'active_production_orders': status_in_progress,
            'planned_orders': status_planned,
            'completed_this_month': completed_this_month,
            'production_efficiency': production_efficiency,
            'capacity_usage': capacity_usage,
            'production_orders': production_orders,
            'status_completed': status_completed,
            'status_in_progress': status_in_progress,
            'status_planned': status_planned,
            'status_on_hold': status_on_hold,
            'status_cancelled': status_cancelled,
            'total_production_orders': all_orders.count(),
        })
    except Exception as e:
        logger.debug("MRP context - orders error: %s", e)
        ctx.update({
            'active_production_orders': 0, 'planned_orders': 0,
            'completed_this_month': 0, 'production_efficiency': 0,
            'capacity_usage': 0, 'production_orders': [],
            'status_completed': 0, 'status_in_progress': 0,
            'status_planned': 0, 'status_on_hold': 0, 'status_cancelled': 0,
            'total_production_orders': 0,
        })

    # ── المواد الخام ──
    try:
        from production.models import BOMItem
        from inventory.models import Product, Stock

        # كل المواد المستخدمة في BOM
        material_ids = BOMItem.objects.values_list('material_id', flat=True).distinct()
        materials_status = []

        for product in Product.objects.filter(id__in=material_ids).distinct()[:10]:
            total_stock = Stock.objects.filter(product=product).aggregate(s=Sum('quantity'))['s'] or 0
            # المطلوب من أوامر الإنتاج النشطة
            needed = BOMItem.objects.filter(
                material=product,
                bom__productionorder__status__in=['draft', 'confirmed', 'in_progress'],
            ).aggregate(s=Sum('quantity'))['s'] or 0

            max_needed = max(float(needed), float(total_stock), 1)
            pct = round(float(total_stock) / max_needed * 100) if max_needed > 0 else 0

            materials_status.append({
                'name': product.name,
                'quantity': int(total_stock),
                'needed': int(needed),
                'unit': getattr(product, 'unit', 'وحدة'),
                'percentage': min(pct, 100),
                'stock_level': 'critical' if pct < 20 else ('low' if pct < 50 else 'normal'),
            })

        low_stock_materials = sum(1 for m in materials_status if m['stock_level'] in ('critical', 'low'))
        ctx.update({
            'materials_status': materials_status,
            'low_stock_materials': low_stock_materials,
        })
    except Exception as e:
        logger.debug("MRP context - materials error: %s", e)
        ctx.update({'materials_status': [], 'low_stock_materials': 0})

    # ── مراكز العمل ──
    try:
        from production.models import ProductionWorkCenter
        work_centers = ProductionWorkCenter.objects.all()
        ctx['work_centers_count'] = work_centers.count()
        ctx['work_centers'] = [
            {'name': wc.name, 'id': wc.id}
            for wc in work_centers[:8]
        ]
    except Exception as e:
        ctx.update({'work_centers_count': 0, 'work_centers': []})

    # ── BOMs ──
    try:
        from production.models import BillOfMaterials
        ctx['bom_count'] = BillOfMaterials.objects.count()
    except Exception:
        ctx['bom_count'] = 0

    return ctx
