"""
محرك BOM متعدد المستويات — RITA ERP Sprint 22C
═══════════════════════════════════════════════
يحل BOM بالكامل (يفكك المكوّنات النصف مصنعة)
"""
from decimal import Decimal
from collections import defaultdict


class BOMEngine:

    @classmethod
    def explode_bom(cls, bom, quantity=1, level=0, max_level=10):
        """
        تفكيك BOM متعدد المستويات
        يرجّع قائمة مسطحة بكل الخامات المطلوبة

        Returns: [
            {'level': 0, 'product': ..., 'quantity': ..., 'is_sub_assembly': True, 'sub_bom': ..., 'line_cost': Decimal},
            ...
        ]
        """
        if level > max_level:
            return []

        result = []
        for line in bom.lines.filter(is_alternative=False).select_related('raw_material'):
            effective_qty = line.effective_quantity * Decimal(str(quantity))

            if line.is_sub_assembly:
                # نصف مصنع — فكّكه
                sub_bom = line.component.boms.filter(is_active=True).first()
                result.append({
                    'level': level,
                    'product': line.component,
                    'quantity': effective_qty,
                    'is_sub_assembly': True,
                    'sub_bom': sub_bom,
                    'line_cost': Decimal('0'),  # التكلفة في المكوّنات الفرعية
                })
                # تفكيك المستوى التالي
                sub_items = cls.explode_bom(sub_bom, effective_qty, level + 1, max_level)
                result.extend(sub_items)
            else:
                # خامة أساسية
                cost_price = line.component.cost_price or Decimal('0')
                result.append({
                    'level': level,
                    'product': line.component,
                    'quantity': effective_qty,
                    'is_sub_assembly': False,
                    'sub_bom': None,
                    'line_cost': effective_qty * cost_price,
                })

        return result

    @classmethod
    def get_flat_materials(cls, bom, quantity=1):
        """
        قائمة مسطحة بالخامات الأساسية فقط (بدون نصف مصنع)
        يُستخدم لصرف الخامات في أمر الإنتاج
        """
        all_items = cls.explode_bom(bom, quantity)

        # تجميع الخامات المتكررة
        materials = defaultdict(lambda: {'product': None, 'quantity': Decimal('0'), 'cost': Decimal('0')})

        for item in all_items:
            if not item['is_sub_assembly']:
                prod_id = item['product'].id
                materials[prod_id]['product'] = item['product']
                materials[prod_id]['quantity'] += item['quantity']
                materials[prod_id]['cost'] += item['line_cost']

        return list(materials.values())

    @classmethod
    def check_material_availability(cls, bom, quantity, warehouse):
        """
        فحص توفر الخامات في المخزن
        Returns: {'materials': [...], 'all_available': bool, 'total_cost': Decimal}
        """
        from apps.inventory.services.stock_engine import StockEngine

        materials = cls.get_flat_materials(bom, quantity)
        result = []
        all_available = True

        for mat in materials:
            available = StockEngine.get_stock_level(mat['product'], warehouse)
            shortage = max(Decimal('0'), mat['quantity'] - available)

            result.append({
                'product': mat['product'],
                'required': mat['quantity'],
                'available': available,
                'shortage': shortage,
                'is_available': shortage == 0,
            })

            if shortage > 0:
                all_available = False

        return {
            'materials': result,
            'all_available': all_available,
            'total_cost': sum(m['cost'] for m in materials),
        }

    @classmethod
    def get_where_used(cls, product):
        """
        أين يُستخدم هذا المنتج (reverse BOM)
        يرجّع كل الـ BOMs اللي المنتج ده مكوّن فيها
        """
        from apps.inventory.models import BOMLine
        lines = BOMLine.objects.filter(
            raw_material=product, bom__is_active=True
        ).select_related('bom', 'bom__product')

        return [{
            'bom': line.bom,
            'parent_product': line.bom.product,
            'quantity': line.quantity,
        } for line in lines]
