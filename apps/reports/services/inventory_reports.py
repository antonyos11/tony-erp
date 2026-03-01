"""
تقارير المخزون — RITA ERP
Sprint 7
"""
from decimal import Decimal
from datetime import timedelta

from django.db.models import Sum, Q, F, Max
from django.utils import timezone

from apps.inventory.models import Product, StockLevel, StockMove


class InventoryReports:
    """تقارير المخزون"""

    @classmethod
    def stock_movement_report(cls, start_date, end_date, warehouse=None, product=None):
        """
        تقرير حركة المخزون التفصيلي
        """
        filters = Q(date__date__gte=start_date, date__date__lte=end_date)
        if warehouse:
            filters &= (Q(warehouse_from=warehouse) | Q(warehouse_to=warehouse))
        if product:
            filters &= Q(product=product)

        moves = StockMove.objects.filter(filters).select_related(
            'product', 'product__unit', 'warehouse_from', 'warehouse_to'
        ).order_by('-date')

        items = []
        total_in_value = Decimal('0')
        total_out_value = Decimal('0')

        for move in moves:
            is_in = move.move_type in ('in', 'production_in', 'return_in', 'adjustment')
            if move.move_type == 'adjustment' and move.warehouse_from:
                is_in = False

            if is_in:
                total_in_value += move.total_cost
            else:
                total_out_value += move.total_cost

            items.append({
                'date': move.date,
                'move_number': move.move_number,
                'move_type': move.get_move_type_display(),
                'product_code': move.product.code,
                'product_name': move.product.name,
                'quantity': move.quantity,
                'unit': move.product.unit.symbol if move.product.unit else '',
                'unit_cost': move.unit_cost,
                'total_cost': move.total_cost,
                'direction': 'وارد' if is_in else 'صادر',
                'direction_color': 'success' if is_in else 'danger',
                'warehouse_from': move.warehouse_from.name if move.warehouse_from else '-',
                'warehouse_to': move.warehouse_to.name if move.warehouse_to else '-',
                'notes': move.notes,
            })

        return {
            'items': items,
            'total_in_value': total_in_value,
            'total_out_value': total_out_value,
            'total_count': len(items),
        }

    @classmethod
    def dead_stock_report(cls, days=90):
        """
        تقرير المخزون الراكد
        منتجات لم تتحرك منذ 30/60/90 يوم
        """
        now = timezone.now()
        cutoff = now - timedelta(days=days)

        # المنتجات التي لديها رصيد > 0
        active_stocks = StockLevel.objects.filter(
            quantity__gt=0, product__is_active=True
        ).select_related('product', 'product__unit', 'product__category', 'warehouse')

        result = []
        for stock in active_stocks:
            # آخر حركة لهذا المنتج في هذا المخزن
            last_move = StockMove.objects.filter(
                product=stock.product,
            ).filter(
                Q(warehouse_from=stock.warehouse) | Q(warehouse_to=stock.warehouse)
            ).order_by('-date').first()

            last_move_date = last_move.date if last_move else None
            days_idle = (now - last_move_date).days if last_move_date else 999

            if days_idle >= 30:  # نعرض كل ما هو أكبر من 30 يوم
                if days_idle >= 90:
                    severity = 'danger'
                    severity_label = '🔴 راكد (+90 يوم)'
                elif days_idle >= 60:
                    severity = 'warning'
                    severity_label = '🟡 بطيء (60-90 يوم)'
                else:
                    severity = 'info'
                    severity_label = '🔵 تنبيه (30-60 يوم)'

                result.append({
                    'product_code': stock.product.code,
                    'product_name': stock.product.name,
                    'category': stock.product.category.name if stock.product.category else '-',
                    'warehouse': stock.warehouse.name,
                    'quantity': stock.quantity,
                    'unit': stock.product.unit.symbol if stock.product.unit else '',
                    'value': stock.quantity * stock.average_cost,
                    'average_cost': stock.average_cost,
                    'last_move_date': last_move_date,
                    'days_idle': days_idle,
                    'severity': severity,
                    'severity_label': severity_label,
                })

        # ترتيب: الأكثر ركوداً أولاً
        result.sort(key=lambda x: -x['days_idle'])
        return result

    @classmethod
    def stock_turnover_report(cls, start_date, end_date):
        """
        تقرير دوران المخزون
        Turnover Rate + Days on Hand
        """
        products = Product.objects.filter(
            is_active=True,
            product_type__in=['finished', 'semi_finished'],
        )

        result = []
        days_in_period = max((end_date - start_date).days, 1)

        for product in products:
            # متوسط المخزون
            total_stock = StockLevel.objects.filter(product=product).aggregate(
                total_qty=Sum('quantity'),
                total_value=Sum(F('quantity') * F('average_cost')),
            )
            avg_stock = total_stock['total_qty'] or Decimal('0')

            # تكلفة البضاعة المباعة (COGS) في الفترة
            from apps.sales.models import SalesInvoiceLine
            cogs = SalesInvoiceLine.objects.filter(
                invoice__date__date__gte=start_date,
                invoice__date__date__lte=end_date,
                invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
                product=product,
            ).aggregate(
                total_cost=Sum(F('cost_price') * F('quantity')),
                total_qty=Sum('quantity'),
            )

            cogs_value = cogs['total_cost'] or Decimal('0')
            sold_qty = cogs['total_qty'] or Decimal('0')

            # معدل الدوران
            turnover_rate = (
                (cogs_value / (total_stock['total_value'] or Decimal('1')))
                if total_stock['total_value'] and total_stock['total_value'] > 0
                else Decimal('0')
            )

            # أيام المخزون
            days_on_hand = (
                int(avg_stock / (sold_qty / days_in_period))
                if sold_qty > 0
                else 999
            )

            if avg_stock > 0 or sold_qty > 0:
                if turnover_rate >= 4:
                    health = '🟢 ممتاز'
                    health_color = 'success'
                elif turnover_rate >= 2:
                    health = '🟡 مقبول'
                    health_color = 'warning'
                else:
                    health = '🔴 بطيء'
                    health_color = 'danger'

                result.append({
                    'product_code': product.code,
                    'product_name': product.name,
                    'current_stock': avg_stock,
                    'stock_value': total_stock['total_value'] or Decimal('0'),
                    'sold_qty': sold_qty,
                    'cogs': cogs_value,
                    'turnover_rate': turnover_rate.quantize(Decimal('0.01')) if isinstance(turnover_rate, Decimal) else Decimal(str(turnover_rate)).quantize(Decimal('0.01')),
                    'days_on_hand': min(days_on_hand, 999),
                    'health': health,
                    'health_color': health_color,
                })

        result.sort(key=lambda x: x['turnover_rate'])
        return result

    @classmethod
    def reorder_report(cls):
        """
        تقرير إعادة الطلب
        كل المنتجات تحت الحد الأدنى
        """
        from apps.inventory.services.stock_engine import StockEngine
        low_stock = StockEngine.get_low_stock_products()

        result = []
        for item in low_stock:
            product = item['product']
            result.append({
                'product_code': product.code,
                'product_name': product.name,
                'product_type': product.get_product_type_display(),
                'current_stock': item['current_stock'],
                'reorder_level': item['reorder_level'],
                'deficit': item['deficit'],
                'unit': product.unit.symbol if product.unit else '',
                'estimated_cost': item['deficit'] * product.cost_price,
                'severity': 'danger' if item['current_stock'] == 0 else 'warning',
            })

        result.sort(key=lambda x: -float(x['deficit']))
        return result
