"""
تقييم المخزون — FIFO و Average
"""
from decimal import Decimal
from django.db.models import Sum, F
from apps.inventory.models import Product, StockLevel, StockMove


class InventoryValuation:
    """تقييم المخزون"""

    @classmethod
    def get_total_inventory_value(cls, warehouse=None):
        """
        قيمة المخزون الإجمالية
        """
        filters = {}
        if warehouse:
            filters['warehouse'] = warehouse

        result = StockLevel.objects.filter(
            quantity__gt=0, **filters
        ).aggregate(
            total_value=Sum(F('quantity') * F('average_cost'))
        )
        return result['total_value'] or Decimal('0')

    @classmethod
    def get_product_valuation(cls, product, warehouse=None):
        """
        تقييم منتج معين
        """
        filters = {'product': product}
        if warehouse:
            filters['warehouse'] = warehouse

        stocks = StockLevel.objects.filter(**filters)

        total_qty = Decimal('0')
        total_value = Decimal('0')

        details = []
        for stock in stocks:
            value = stock.quantity * stock.average_cost
            total_qty += stock.quantity
            total_value += value
            details.append({
                'warehouse': stock.warehouse.name,
                'quantity': stock.quantity,
                'average_cost': stock.average_cost,
                'value': value,
            })

        return {
            'product': product.name,
            'total_quantity': total_qty,
            'total_value': total_value,
            'average_cost': (total_value / total_qty).quantize(Decimal('0.01')) if total_qty > 0 else Decimal('0'),
            'details': details,
        }

    @classmethod
    def get_inventory_report(cls, warehouse=None, product_type=None):
        """
        تقرير تقييم المخزون الكامل
        """
        filters = {'quantity__gt': 0}
        if warehouse:
            filters['warehouse'] = warehouse
        if product_type:
            filters['product__product_type'] = product_type

        stocks = StockLevel.objects.filter(**filters).select_related(
            'product', 'product__category', 'product__unit', 'warehouse'
        ).order_by('product__product_type', 'product__name')

        items = []
        total_value = Decimal('0')

        for stock in stocks:
            value = stock.quantity * stock.average_cost
            total_value += value
            items.append({
                'product_code': stock.product.code,
                'product_name': stock.product.name,
                'product_type': stock.product.get_product_type_display(),
                'category': stock.product.category.name if stock.product.category else '-',
                'warehouse': stock.warehouse.name,
                'quantity': stock.quantity,
                'unit': stock.product.unit.symbol if stock.product.unit else '',
                'average_cost': stock.average_cost,
                'value': value,
                'reorder_level': stock.product.reorder_level,
                'is_low': stock.quantity <= stock.product.reorder_level and stock.product.reorder_level > 0,
            })

        return {
            'items': items,
            'total_value': total_value,
            'total_items': len(items),
        }
