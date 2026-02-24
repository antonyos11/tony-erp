from datetime import date as _date
from decimal import Decimal
from django.db.models import Sum
from django.core.cache import cache
from .models import Invoice, InvoicePayment

STATEMENT_CACHE_TTL = 120  # ثواني (يمكن تعديلها لاحقاً)

def _statement_version_key(customer_id):
    return f"cust_stmt_ver:{customer_id}"

def bump_customer_statement_version(customer_id):
    """Increment per-customer version used to namespace cached statements."""
    try:
        key = _statement_version_key(customer_id)
        val = cache.get(key, 0) + 1
        cache.set(key, val, STATEMENT_CACHE_TTL * 10)  # احتفظ بالنسخة فترة أطول من النتائج نفسها
    except Exception:
        pass

def _build_customer_statement(customer, date_from=None, date_to=None):
    """Internal builder (uncached)."""
    # ...existing logic moved from build_customer_statement...
    base_invoices_qs = Invoice.objects.filter(customer=customer).prefetch_related('items')
    base_payments_qs = InvoicePayment.objects.filter(customer=customer).select_related('invoice')
    opening_balance = Decimal('0')
    if date_from:
        inv_before_qs = base_invoices_qs.filter(date__lt=date_from)
        total_inv_before = sum((inv.total or Decimal('0')) for inv in inv_before_qs)
        pay_before_amount = base_payments_qs.filter(date__lt=date_from).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        opening_balance = (total_inv_before or Decimal('0')) - (pay_before_amount or Decimal('0'))
    invoices = base_invoices_qs
    payments = base_payments_qs
    if date_from:
        invoices = invoices.filter(date__gte=date_from)
        payments = payments.filter(date__date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)
        payments = payments.filter(date__date__lte=date_to)
    invoices = invoices.order_by('date', 'id')
    payments = payments.order_by('date', 'id')
    timeline = []
    for inv in invoices:
        timeline.append({
            'type': 'invoice',
            'date': inv.date,
            'id': inv.id,
            'number': inv.number,
            'debit': (inv.total or Decimal('0')),
            'credit': None,
            'description': f'فاتورة {inv.number}',
        })
    for p in payments:
        timeline.append({
            'type': 'payment',
            'date': p.date.date(),
            'id': p.id,
            'number': p.receipt_number,
            'debit': None,
            'credit': p.amount,
            'description': p.description or f'دفعة للفاتورة {p.invoice.number}',
        })
    timeline.sort(key=lambda x: (x['date'], x['type'] == 'payment', x['id']))
    balance = opening_balance
    for row in timeline:
        if row['debit']:
            balance += row['debit']
        if row['credit']:
            balance -= row['credit']
        row['balance'] = balance
    cutoff = date_to or _date.today()
    aging = {
        'bucket_0_30': Decimal('0'),
        'bucket_31_60': Decimal('0'),
        'bucket_61_90': Decimal('0'),
        'bucket_90_plus': Decimal('0'),
    }
    relevant_pays = base_payments_qs
    if cutoff:
        relevant_pays = relevant_pays.filter(date__date__lte=cutoff)
    pays_by_invoice = {row['invoice_id']: (row['total'] or Decimal('0')) for row in relevant_pays.values('invoice_id').annotate(total=Sum('amount'))}
    for inv in base_invoices_qs:
        if inv.date > cutoff:
            continue
        # استخدم Decimal بشكل متسق
        inv_total = (inv.total or Decimal('0'))
        paid_total = pays_by_invoice.get(inv.id, Decimal('0')) or Decimal('0')
        if not isinstance(paid_total, Decimal):
            try:
                paid_total = Decimal(str(paid_total))
            except Exception:
                paid_total = Decimal('0')
        remaining = inv_total - paid_total
        if remaining > 0:
            days = (cutoff - inv.date).days
            if days <= 30:
                aging['bucket_0_30'] += remaining
            elif days <= 60:
                aging['bucket_31_60'] += remaining
            elif days <= 90:
                aging['bucket_61_90'] += remaining
            else:
                aging['bucket_90_plus'] += remaining
    aging['total'] = Decimal(str(sum(aging.values())))
    return {
        'timeline': timeline,
        'opening_balance': opening_balance,
        'balance': balance,
        'aging': aging,
        'date_from': date_from,
        'date_to': date_to,
    }

def build_customer_statement(customer, date_from=None, date_to=None):
    """Cached wrapper. Returns same structure; caches per (customer, dates, version)."""
    version = cache.get(_statement_version_key(customer.id), 0)
    key = f"cust_stmt:{customer.id}:{date_from or '-'}:{date_to or '-'}:v{version}"
    try:
        cached = cache.get(key)
        if cached is not None:
            return cached
    except Exception:
        pass
    data = _build_customer_statement(customer, date_from=date_from, date_to=date_to)
    try:
        cache.set(key, data, STATEMENT_CACHE_TTL)
    except Exception:
        pass
    return data
