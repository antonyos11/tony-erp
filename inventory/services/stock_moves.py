from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from inventory.models import Stock, StockBatch, Product, Location
from django.core.exceptions import ValidationError

@dataclass
class MovementResult:
    product_id: int
    location_id: int
    delta: int
    new_quantity: int
    batches: List[int]
    meta: Dict[str, str]

class StockIntegrityError(Exception):
    pass

@transaction.atomic
def increase_stock(product: Product, location: Location, qty: int, *, unit_cost=None, lot_number: str = '', expiry_date=None, reason: str = '', meta: Optional[Dict[str, str]] = None, supplier=None) -> MovementResult:
    """
    زيادة المخزون مع تتبع المورد

    Args:
        supplier: المورد الذي تم الشراء منه (اختياري)
    """
    if qty <= 0:
        raise ValidationError('Quantity must be positive')
    stock, _ = Stock.objects.select_for_update().get_or_create(product=product, location=location)
    stock.quantity = F('quantity') + qty
    stock.save(update_fields=['quantity'])
    stock.refresh_from_db(fields=['quantity'])

    # تحديد التكلفة: من المورد المحدد أو من سعر المنتج الافتراضي
    final_cost = unit_cost
    if final_cost is None and supplier:
        # محاولة الحصول على سعر المورد
        from inventory.models import SupplierProductPrice
        supplier_price = SupplierProductPrice.objects.filter(
            product=product,
            supplier=supplier,
            is_active=True
        ).order_by('-effective_date').first()

        if supplier_price:
            final_cost = supplier_price.cost

    if final_cost is None:
        final_cost = product.cost

    batch = StockBatch.objects.create(
        product=product,
        location=location,
        lot_number=lot_number or '',
        expiry_date=expiry_date,
        unit_cost=final_cost,
        quantity=qty,
        supplier=supplier,  # حفظ المورد
    )
    return MovementResult(product.id, location.id, qty, stock.quantity, [batch.id], meta or {'reason': reason})

@transaction.atomic
def decrease_stock(product: Product, location: Location, qty: int, *, method: str = 'fifo', reason: str = '', meta: Optional[Dict[str, str]] = None) -> MovementResult:
    if qty <= 0:
        raise ValidationError('Quantity must be positive')
    stock = Stock.objects.select_for_update().filter(product=product, location=location).first()
    if not stock or stock.quantity < qty:
        raise StockIntegrityError('Insufficient stock')
    if method.lower() == 'lifo':
        batches = list(StockBatch.objects.filter(product=product, location=location, quantity__gt=0).order_by('-received_at', '-id').select_for_update())
    else:
        batches = list(StockBatch.objects.filter(product=product, location=location, quantity__gt=0).order_by('received_at', 'id').select_for_update())
    remain = qty
    used_batches: List[int] = []
    for b in batches:
        if remain <= 0:
            break
        take = min(b.quantity, remain)
        if take > 0:
            b.quantity -= take
            b.save(update_fields=['quantity'])
            remain -= take
            used_batches.append(b.id)
    if remain > 0:
        raise StockIntegrityError('Batches inconsistent with stock balance')
    stock.quantity = F('quantity') - qty
    stock.save(update_fields=['quantity'])
    stock.refresh_from_db(fields=['quantity'])
    return MovementResult(product.id, location.id, -qty, stock.quantity, used_batches, meta or {'reason': reason})
