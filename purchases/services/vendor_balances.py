from __future__ import annotations
from decimal import Decimal
from typing import Iterable, Dict, Any, List, Tuple, Optional
from collections import defaultdict
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from purchases.models import PurchaseBill, PurchaseItem
from partners.models import Supplier

ALLOWED_SORTS = {"remaining","total","paid","name","open_bills"}

Bucket = Tuple[Decimal, Optional[Decimal]]  # (min, max]
DEFAULT_BUCKETS: List[Bucket] = [
    (Decimal('0'), Decimal('0')),
    (Decimal('0'), Decimal('10000')),
    (Decimal('10000'), Decimal('50000')),
    (Decimal('50000'), None),
]

def compute_vendor_balances(
    *,
    q: str = "",
    show_all: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = "remaining",
    direction: str = "desc",
    bucket: str | None = None,
    use_orm_agg: bool = False,
) -> Dict[str, Any]:
    """Compute vendors balances with optional ORM aggregation.

    Parameters mirror view query params.
    bucket format examples:
      - "0" exact zero remaining
      - "0-10000" inclusive upper bound
      - "10000-50000"
      - "50000+" open ended
    """
    if sort not in ALLOWED_SORTS:
        sort = "remaining"
    if direction not in {"asc","desc"}:
        direction = "desc"

    bills = PurchaseBill.objects.filter(is_deleted=False).select_related("supplier")
    if q:
        bills = bills.filter(supplier__name__icontains=q)
    if date_from:
        bills = bills.filter(date__gte=date_from)
    if date_to:
        bills = bills.filter(date__lte=date_to)

    rows: List[Dict[str, Any]] = []

    if use_orm_agg:
        # Aggregate total of items minus discount using sub-aggregation
        # Sum(quantity * cost) per bill then group by supplier
        item_totals = (
            PurchaseItem.objects.filter(bill_id__in=bills.values_list('id', flat=True))
            .values('bill_id')
            .annotate(items_total=Sum(F('quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2)))
        )
        item_total_map = {it['bill_id']: it['items_total'] or Decimal('0') for it in item_totals}
        supplier_map: Dict[int, Dict[str, Any]] = {}
        for b in bills.only('id','supplier_id','discount','paid','supplier__name'):
            gross = item_total_map.get(b.id, Decimal('0')) - (b.discount or Decimal('0'))
            paid = b.paid or Decimal('0')
            remaining = gross - paid
            rec = supplier_map.setdefault(b.supplier_id, {
                'supplier_id': b.supplier_id,
                'name': b.supplier.name,
                'total': Decimal('0'),
                'paid': Decimal('0'),
                'remaining': Decimal('0'),
                'open_bills': 0,
            })
            rec['total'] += gross
            rec['paid'] += paid
            rec['remaining'] += remaining
            if remaining > 0:
                rec['open_bills'] += 1
        rows = list(supplier_map.values())
    else:
        bill_ids = list(bills.values_list('id', flat=True))
        items = PurchaseItem.objects.filter(bill_id__in=bill_ids).values('bill_id','quantity','cost')
        bill_totals = defaultdict(lambda: Decimal('0'))
        for it in items:
            bill_totals[it['bill_id']] += Decimal(it['quantity']) * Decimal(it['cost'])
        supplier_map: Dict[int, Dict[str, Any]] = {}
        for b in bills.only('id','supplier_id','discount','paid','supplier__name'):
            gross = bill_totals.get(b.id, Decimal('0')) - (b.discount or Decimal('0'))
            paid = b.paid or Decimal('0')
            remaining = gross - paid
            rec = supplier_map.setdefault(b.supplier_id, {
                'supplier_id': b.supplier_id,
                'name': b.supplier.name,
                'total': Decimal('0'),
                'paid': Decimal('0'),
                'remaining': Decimal('0'),
                'open_bills': 0,
            })
            rec['total'] += gross
            rec['paid'] += paid
            rec['remaining'] += remaining
            if remaining > 0:
                rec['open_bills'] += 1
        rows = list(supplier_map.values())

    supplier_ids_with_bills = {r['supplier_id'] for r in rows}

    if show_all:
        extras = Supplier.objects.exclude(id__in=supplier_ids_with_bills)
        if q:
            extras = extras.filter(name__icontains=q)
        for s in extras[:300]:
            rows.append({
                'supplier_id': s.id,
                'name': s.name,
                'total': Decimal('0'),
                'paid': Decimal('0'),
                'remaining': Decimal('0'),
                'open_bills': 0,
            })

    # Bucket filtering
    def parse_bucket(arg: str | None) -> Optional[Bucket]:
        if not arg:
            return None
        if arg == '0':
            return (Decimal('0'), Decimal('0'))
        if arg.endswith('+'):
            base = arg[:-1]
            try:
                return (Decimal(base), None)
            except Exception:
                return None
        if '-' in arg:
            a,b = arg.split('-',1)
            try:
                return (Decimal(a), Decimal(b))
            except Exception:
                return None
        return None

    bucket_range = parse_bucket(bucket)
    if bucket_range:
        lo, hi = bucket_range
        filtered = []
        for r in rows:
            rem = r['remaining']
            if lo == Decimal('0') and hi == Decimal('0'):
                if rem == 0:
                    filtered.append(r)
                continue
            if hi is None:
                if rem > lo:
                    filtered.append(r)
            else:
                if rem > lo and rem <= hi:
                    filtered.append(r)
        rows = filtered

    grand_total = sum(r['total'] for r in rows)
    grand_paid = sum(r['paid'] for r in rows)
    grand_remaining = sum(r['remaining'] for r in rows)
    open_bills_total = sum(r['open_bills'] for r in rows)
    suppliers_with_debt_count = sum(1 for r in rows if r['remaining'] > 0)

    # Sorting
    def sort_key(r):
        if sort == 'name':
            return (r['name'] or '').lower()
        return r.get(sort, 0)
    rows.sort(key=sort_key, reverse=(direction=='desc'))

    # Percent of grand remaining per row (for progress bars)
    if grand_remaining > 0:
        for r in rows:
            r['remaining_pct'] = float((r['remaining'] / grand_remaining) * 100)
    else:
        for r in rows:
            r['remaining_pct'] = 0.0

    # Top 5
    top5 = []
    if grand_remaining > 0:
        for r in rows[:5]:
            pct = (r['remaining'] / grand_remaining * 100) if grand_remaining else 0
            top5.append({
                'supplier_id': r['supplier_id'],
                'name': r['name'],
                'remaining': r['remaining'],
                'percent': round(pct,2),
            })

    return {
        'rows': rows,
        'q': q,
        'show_all': show_all,
        'date_from': date_from,
        'date_to': date_to,
        'grand_total': grand_total,
        'grand_paid': grand_paid,
        'grand_remaining': grand_remaining,
        'open_bills_total': open_bills_total,
        'suppliers_with_debt_count': suppliers_with_debt_count,
        'sort': sort,
        'direction': direction,
        'bucket': bucket,
        'top5': top5,
        'use_orm_agg': use_orm_agg,
    }
