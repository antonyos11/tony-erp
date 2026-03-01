"""
محرك حركة المخزون
يتحكم في كل الحركات: وارد، صادر، تحويل، صرف إنتاج، تسوية
يحدّث أرصدة المخزون تلقائياً
يربط مع محرك المحاسبة لإنشاء القيود
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.inventory.models import StockMove, StockLevel, Product


def _parse_source_id(source_id):
    """تحويل معرف المصدر إلى عدد صحيح أو None"""
    if source_id is None or source_id == '':
        return None
    try:
        return int(source_id)
    except (ValueError, TypeError):
        return None


class StockEngine:
    """محرك المخزون"""

    @staticmethod
    def _generate_move_number(move_type):
        """توليد رقم حركة تلقائي"""
        today = timezone.now()
        prefix_map = {
            'in': 'IN',
            'out': 'OUT',
            'transfer': 'TRF',
            'production_in': 'PIN',
            'production_out': 'POUT',
            'adjustment': 'ADJ',
            'return_in': 'RIN',
            'return_out': 'ROUT',
            'waste': 'WST',
        }
        prefix = prefix_map.get(move_type, 'MOV')
        count = StockMove.objects.filter(
            date__year=today.year,
            date__month=today.month,
            move_type=move_type,
        ).count() + 1
        return f"{prefix}-{today.strftime('%Y%m')}-{count:04d}"

    @classmethod
    def _update_stock_level(cls, product, warehouse, quantity_change, unit_cost=None):
        """
        تحديث رصيد المخزون
        quantity_change: موجب = إضافة، سالب = خصم
        """
        stock_level, created = StockLevel.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            defaults={'quantity': 0, 'average_cost': unit_cost or Decimal('0')}
        )

        if quantity_change > 0 and unit_cost:
            # حساب المتوسط المرجح عند الإضافة
            if product.valuation_method == 'average':
                total_value = (stock_level.quantity * stock_level.average_cost) + (quantity_change * unit_cost)
                new_quantity = stock_level.quantity + quantity_change
                if new_quantity > 0:
                    stock_level.average_cost = (total_value / new_quantity).quantize(Decimal('0.01'))
            elif product.valuation_method == 'fifo':
                # FIFO: نحتفظ بالتكلفة كما هي — التكلفة تُحسب عند الصرف
                if created or stock_level.average_cost == 0:
                    stock_level.average_cost = unit_cost

        stock_level.quantity += quantity_change
        stock_level.save()

        # تحديث سعر التكلفة في المنتج
        if quantity_change > 0 and unit_cost:
            product.cost_price = stock_level.average_cost
            product.save(update_fields=['cost_price'])

        return stock_level

    @classmethod
    @transaction.atomic
    def receive_stock(cls, product, warehouse, quantity, unit_cost,
                      source_type='', source_id='', notes='', user=None):
        """
        استلام مخزون (وارد)
        - شراء خامات
        - استلام إنتاج تام
        - مرتجع من عميل
        """
        move = StockMove.objects.create(
            move_number=cls._generate_move_number('in'),
            date=timezone.now(),
            move_type='in',
            product=product,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            warehouse_to=warehouse,
            source_type=source_type,
            source_id=_parse_source_id(source_id),
            notes=notes,
            created_by=user,
            updated_by=user,
        )

        cls._update_stock_level(product, warehouse, quantity, unit_cost)
        return move

    @classmethod
    @transaction.atomic
    def issue_stock(cls, product, warehouse, quantity,
                    source_type='', source_id='', notes='', user=None):
        """
        صرف مخزون (صادر)
        - بيع
        - صرف للإنتاج
        """
        # التحقق من الرصيد
        stock_level = StockLevel.objects.filter(
            product=product, warehouse=warehouse
        ).first()

        if not stock_level or stock_level.quantity < quantity:
            available = stock_level.quantity if stock_level else 0
            raise ValueError(
                f"رصيد غير كافي! المطلوب: {quantity}، المتاح: {available} "
                f"من {product.name} في {warehouse.name}"
            )

        unit_cost = stock_level.average_cost
        total_cost = quantity * unit_cost

        move = StockMove.objects.create(
            move_number=cls._generate_move_number('out'),
            date=timezone.now(),
            move_type='out',
            product=product,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            warehouse_from=warehouse,
            source_type=source_type,
            source_id=_parse_source_id(source_id),
            notes=notes,
            created_by=user,
            updated_by=user,
        )

        cls._update_stock_level(product, warehouse, -quantity)
        return move

    @classmethod
    @transaction.atomic
    def transfer_stock(cls, product, from_warehouse, to_warehouse, quantity,
                       notes='', user=None):
        """
        تحويل مخزون بين مخازن
        """
        # التحقق من الرصيد
        stock_level = StockLevel.objects.filter(
            product=product, warehouse=from_warehouse
        ).first()

        if not stock_level or stock_level.quantity < quantity:
            available = stock_level.quantity if stock_level else 0
            raise ValueError(
                f"رصيد غير كافي للتحويل! المطلوب: {quantity}، المتاح: {available}"
            )

        unit_cost = stock_level.average_cost

        move = StockMove.objects.create(
            move_number=cls._generate_move_number('transfer'),
            date=timezone.now(),
            move_type='transfer',
            product=product,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            warehouse_from=from_warehouse,
            warehouse_to=to_warehouse,
            notes=notes,
            created_by=user,
            updated_by=user,
        )

        cls._update_stock_level(product, from_warehouse, -quantity)
        cls._update_stock_level(product, to_warehouse, quantity, unit_cost)

        return move

    @classmethod
    @transaction.atomic
    def production_issue(cls, product, warehouse, quantity, production_order,
                         user=None):
        """
        صرف خامات للإنتاج
        """
        stock_level = StockLevel.objects.filter(
            product=product, warehouse=warehouse
        ).first()

        if not stock_level or stock_level.quantity < quantity:
            available = stock_level.quantity if stock_level else 0
            raise ValueError(
                f"رصيد خامة غير كافي! {product.name}: المطلوب {quantity}، المتاح {available}"
            )

        unit_cost = stock_level.average_cost

        move = StockMove.objects.create(
            move_number=cls._generate_move_number('production_out'),
            date=timezone.now(),
            move_type='production_out',
            product=product,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            warehouse_from=warehouse,
            source_type='ProductionOrder',
            source_id=_parse_source_id(production_order.id),
            notes=f'صرف لأمر إنتاج {production_order.order_number}',
            created_by=user,
            updated_by=user,
        )

        cls._update_stock_level(product, warehouse, -quantity)
        return move

    @classmethod
    @transaction.atomic
    def production_receive(cls, product, warehouse, quantity, unit_cost,
                           production_order, user=None):
        """
        استلام منتج تام من الإنتاج
        """
        move = StockMove.objects.create(
            move_number=cls._generate_move_number('production_in'),
            date=timezone.now(),
            move_type='production_in',
            product=product,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            warehouse_to=warehouse,
            source_type='ProductionOrder',
            source_id=_parse_source_id(production_order.id),
            notes=f'استلام من أمر إنتاج {production_order.order_number}',
            created_by=user,
            updated_by=user,
        )

        cls._update_stock_level(product, warehouse, quantity, unit_cost)
        return move

    @classmethod
    @transaction.atomic
    def adjust_stock(cls, product, warehouse, new_quantity, reason='', user=None):
        """
        تسوية جرد
        """
        stock_level = StockLevel.objects.filter(
            product=product, warehouse=warehouse
        ).first()

        current_quantity = stock_level.quantity if stock_level else Decimal('0')
        difference = new_quantity - current_quantity

        if difference == 0:
            return None

        unit_cost = stock_level.average_cost if stock_level else product.cost_price

        move = StockMove.objects.create(
            move_number=cls._generate_move_number('adjustment'),
            date=timezone.now(),
            move_type='adjustment',
            product=product,
            quantity=abs(difference),
            unit_cost=unit_cost,
            total_cost=abs(difference) * unit_cost,
            warehouse_from=warehouse if difference < 0 else None,
            warehouse_to=warehouse if difference > 0 else None,
            notes=f'تسوية جرد: {reason}. الرصيد القديم: {current_quantity}، الجديد: {new_quantity}',
            created_by=user,
            updated_by=user,
        )

        cls._update_stock_level(product, warehouse, difference, unit_cost)
        return move

    @classmethod
    @transaction.atomic
    def record_waste(cls, product, warehouse, quantity, reason='', user=None):
        """
        تسجيل هالك
        """
        stock_level = StockLevel.objects.filter(
            product=product, warehouse=warehouse
        ).first()

        if not stock_level or stock_level.quantity < quantity:
            available = stock_level.quantity if stock_level else 0
            raise ValueError(f"رصيد غير كافي لتسجيل هالك! المتاح: {available}")

        unit_cost = stock_level.average_cost

        move = StockMove.objects.create(
            move_number=cls._generate_move_number('waste'),
            date=timezone.now(),
            move_type='waste',
            product=product,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            warehouse_from=warehouse,
            notes=f'هالك: {reason}',
            created_by=user,
            updated_by=user,
        )

        cls._update_stock_level(product, warehouse, -quantity)
        return move

    @classmethod
    def get_stock_level(cls, product, warehouse=None):
        """
        جلب رصيد منتج
        """
        if warehouse:
            stock = StockLevel.objects.filter(product=product, warehouse=warehouse).first()
            return stock.quantity if stock else Decimal('0')
        else:
            from django.db.models import Sum
            total = StockLevel.objects.filter(product=product).aggregate(
                total=Sum('quantity')
            )
            return total['total'] or Decimal('0')

    @classmethod
    def get_low_stock_products(cls):
        """
        المنتجات تحت حد إعادة الطلب
        """
        from django.db.models import Sum
        products = Product.objects.filter(
            is_active=True, reorder_level__gt=0
        )

        low_stock = []
        for product in products:
            total_qty = StockLevel.objects.filter(product=product).aggregate(
                total=Sum('quantity')
            )['total'] or Decimal('0')

            if total_qty <= product.reorder_level:
                low_stock.append({
                    'product': product,
                    'current_stock': total_qty,
                    'reorder_level': product.reorder_level,
                    'deficit': product.reorder_level - total_qty,
                })

        return low_stock
