"""
تقارير التكاليف الصناعية — RITA ERP
Sprint 7
"""
from decimal import Decimal

from django.db.models import Sum, F, Q

from apps.production.models import ProductionOrder, MaterialConsumption
from apps.inventory.models import Product, BillOfMaterials, BOMLine, StockLevel
from apps.sales.models import SalesInvoiceLine


class CostReports:
    """تقارير التكاليف"""

    @classmethod
    def product_cost_report(cls, product=None):
        """
        تقرير تكلفة المنتج الفعلية (Gold Report)
        خامات + عمالة + overhead = تكلفة حقيقية vs سعر بيع
        """
        filters = Q(
            product_type__in=['finished', 'semi_finished'],
            is_active=True,
        )
        if product:
            filters &= Q(pk=product.pk)

        products = Product.objects.filter(filters)

        result = []
        for prod in products:
            # آخر أمر إنتاج مكتمل
            last_order = ProductionOrder.objects.filter(
                product=prod, status='completed'
            ).order_by('-actual_completion_date').first()

            if last_order:
                material_cost = last_order.material_cost
                labor_cost = last_order.labor_cost
                overhead_cost = last_order.overhead_cost
                total_cost = last_order.total_cost
                unit_cost = last_order.unit_cost
                qty_produced = last_order.quantity_produced
            else:
                # تقدير من BOM
                bom = BillOfMaterials.objects.filter(product=prod, is_default=True).first()
                material_cost = Decimal('0')
                if bom:
                    for line in bom.lines.all():
                        mat_cost = line.raw_material.cost_price * line.quantity * (1 + line.waste_percentage / 100)
                        material_cost += mat_cost
                labor_cost = Decimal('0')
                overhead_cost = Decimal('0')
                total_cost = material_cost
                unit_cost = material_cost  # لوحدة واحدة
                qty_produced = Decimal('0')

            retail_price = prod.retail_price or Decimal('0')
            margin = retail_price - unit_cost if unit_cost > 0 else Decimal('0')
            margin_pct = (
                (margin / retail_price * 100).quantize(Decimal('0.01'))
                if retail_price > 0 else Decimal('0')
            )

            if margin_pct > 25:
                status = '🟢 مربح'
                status_color = 'success'
            elif margin_pct > 10:
                status = '🟡 مقبول'
                status_color = 'warning'
            else:
                status = '🔴 ضعيف / خاسر'
                status_color = 'danger'

            result.append({
                'product_code': prod.code,
                'product_name': prod.name,
                'material_cost': material_cost,
                'labor_cost': labor_cost,
                'overhead_cost': overhead_cost,
                'total_cost': total_cost,
                'unit_cost': unit_cost,
                'retail_price': retail_price,
                'margin': margin,
                'margin_pct': margin_pct,
                'status': status,
                'status_color': status_color,
                'last_production': last_order.order_number if last_order else '-',
                'qty_produced': qty_produced,
            })

        result.sort(key=lambda x: float(x['margin_pct']))
        return result

    @classmethod
    def cost_variance_report(cls, start_date, end_date):
        """
        تقرير انحراف التكاليف
        فرق سعر خامات + فرق استهلاك + هالك
        """
        orders = ProductionOrder.objects.filter(
            status='completed',
            actual_completion_date__gte=start_date,
            actual_completion_date__lte=end_date,
        ).select_related('product', 'bom')

        result = []
        for order in orders:
            consumptions = order.material_consumptions.all().select_related('raw_material')

            material_variances = []
            total_variance = Decimal('0')

            for c in consumptions:
                planned_cost = c.planned_quantity * c.raw_material.cost_price
                actual_cost = c.total_cost or Decimal('0')
                variance = actual_cost - planned_cost
                total_variance += variance

                material_variances.append({
                    'material': c.raw_material.name,
                    'planned_qty': c.planned_quantity,
                    'actual_qty': c.actual_quantity,
                    'waste_qty': c.waste_quantity,
                    'planned_cost': planned_cost,
                    'actual_cost': actual_cost,
                    'variance': variance,
                    'variance_pct': (
                        (variance / planned_cost * 100).quantize(Decimal('0.01'))
                        if planned_cost > 0 else Decimal('0')
                    ),
                })

            variance_status = 'success' if total_variance <= 0 else (
                'warning' if total_variance < order.material_cost * Decimal('0.05') else 'danger'
            )

            result.append({
                'order_number': order.order_number,
                'product_name': order.product.name,
                'completion_date': order.actual_completion_date,
                'quantity_produced': order.quantity_produced,
                'material_cost': order.material_cost,
                'labor_cost': order.labor_cost,
                'overhead_cost': order.overhead_cost,
                'total_cost': order.total_cost,
                'total_variance': total_variance,
                'variance_status': variance_status,
                'material_variances': material_variances,
            })

        return result

    @classmethod
    def production_line_profitability(cls, start_date, end_date):
        """
        ربحية خطوط الإنتاج
        """
        orders = ProductionOrder.objects.filter(
            status='completed',
            actual_completion_date__gte=start_date,
            actual_completion_date__lte=end_date,
            production_line__isnull=False,
        ).select_related('product', 'production_line')

        lines_data = {}
        for order in orders:
            line_name = order.production_line.name
            if line_name not in lines_data:
                lines_data[line_name] = {
                    'line_name': line_name,
                    'order_count': 0,
                    'total_produced': Decimal('0'),
                    'total_cost': Decimal('0'),
                    'material_cost': Decimal('0'),
                    'labor_cost': Decimal('0'),
                    'overhead_cost': Decimal('0'),
                    'total_revenue': Decimal('0'),
                }

            data = lines_data[line_name]
            data['order_count'] += 1
            data['total_produced'] += order.quantity_produced
            data['total_cost'] += order.total_cost
            data['material_cost'] += order.material_cost
            data['labor_cost'] += order.labor_cost
            data['overhead_cost'] += order.overhead_cost

            # تقدير الإيراد من سعر التجزئة
            revenue = order.quantity_produced * (order.product.retail_price or Decimal('0'))
            data['total_revenue'] += revenue

        result = []
        for data in lines_data.values():
            profit = data['total_revenue'] - data['total_cost']
            margin = (
                (profit / data['total_revenue'] * 100).quantize(Decimal('0.01'))
                if data['total_revenue'] > 0 else Decimal('0')
            )
            result.append({
                **data,
                'profit': profit,
                'margin': margin,
                'margin_color': 'success' if margin >= 20 else ('warning' if margin >= 10 else 'danger'),
            })

        result.sort(key=lambda x: float(x.get('profit', 0)), reverse=True)
        return result
