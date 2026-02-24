from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, Callable, List
from django.db import OperationalError
from django.conf import settings
from django.db.models import Sum, Count, F, Avg, DecimalField, ExpressionWrapper, Max as DJMax
# توافق خلفي: بعض البايت كود القديم قد يشير إلى الاسم Max مباشرةً
Max = DJMax  # type: ignore
from django.db.models.functions import Coalesce
from inventory.models import Product, Location, StockBatch
from sales.models import Invoice, InvoiceItem
from purchases.models import PurchaseBill, PurchaseItem
from partners.models import Customer, Supplier
from django.utils.timezone import now as tz_now

# Optional imports (some apps may be partially installed during early setup)
try:  # CRM
    from crm.models import Opportunity, OpportunityStage, SupportTicket
except Exception:  # pragma: no cover - defensive
    Opportunity = OpportunityStage = SupportTicket = None  # type: ignore
try:  # HR
    from hr.models import Employee
except Exception:  # pragma: no cover
    Employee = None  # type: ignore
try:  # Accounting extended
    from accounting.models import (
        Account, JournalEntry, Revenue as LegacyRevenue, Expense as LegacyExpense,
        CostCenter, Loan
    )
except Exception:  # pragma: no cover
    Account = JournalEntry = LegacyRevenue = LegacyExpense = CostCenter = Loan = None  # type: ignore

# NOTE:
# Previous iterations used invoice/bill level expressions like F('items__quantity') which caused
# intermittent FieldError: Cannot resolve keyword 'items' inside service tests (likely due to stale
# bytecode referencing outdated annotations). To fully stabilize, all aggregations below use
# item-level querysets (InvoiceItem / PurchaseItem) and then derive invoice/bill counts separately.
# This removes every dependency on 'items__' joins inside ExpressionWrapper instances.
DecimalExpr = ExpressionWrapper

# ----------------- Utility -----------------

def parse_date(value: str, default: date) -> date:
    if not value:
        return default
    for fmt in ('%Y-%m-%d', '%Y/%m/%d'):
        try:
            return datetime.strptime(value, fmt).date()
        except Exception:
            continue
    return default

# ----------------- Overview -----------------

def get_overview_report() -> Dict[str, Any]:
    today = date.today()
    last_30 = today - timedelta(days=30)
    # Item-level expressions
    item_sales_expr = DecimalExpr(F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2))
    item_cost_expr = DecimalExpr(F('quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))

    sales_total_30 = (
        InvoiceItem.objects.filter(invoice__date__gte=last_30).aggregate(total=Sum(item_sales_expr))['total'] or 0
    )
    purchases_total_30 = (
        PurchaseItem.objects.filter(bill__date__gte=last_30).aggregate(total=Sum(item_cost_expr))['total'] or 0
    )
    stats = {
        'total_products': Product.objects.count(),
        'total_customers': Customer.objects.count(),
        'total_suppliers': Supplier.objects.count(),
        'total_locations': Location.objects.count(),
        'invoices_30_days': Invoice.objects.filter(date__gte=last_30).count(),
        'purchases_30_days': PurchaseBill.objects.filter(date__gte=last_30).count(),
        'sales_total_30_days': sales_total_30,
        'purchases_total_30_days': purchases_total_30,
        'low_stock_count': Product.objects.annotate(total_qty=Coalesce(Sum('stocks__quantity'), 0)).filter(total_qty__lt=F('min_stock')).count(),
    }
    top_products = [
        {
            'name': r['product__name'],
            'total_sold': r['total_sold'],
            'total_revenue': float(r['total_revenue'] or 0),
        }
        for r in (
            InvoiceItem.objects.values('product__name')
            .annotate(
                total_sold=Sum('quantity'),
                total_revenue=Sum(item_sales_expr),
            )
            .order_by('-total_sold')[:5]
        )
    ]
    recent_invoices = list(
        Invoice.objects.select_related('customer').order_by('-date').values('id', 'number', 'customer__name', 'date')[:5]
    )
    recent_purchases = list(
        PurchaseBill.objects.select_related('supplier').order_by('-date').values('id', 'number', 'supplier__name', 'date')[:5]
    )
    return {
        'stats': stats,
        'top_products': top_products,
        'recent_invoices': recent_invoices,
        'recent_purchases': recent_purchases,
        'charts': {
            'sales_vs_purchases': {
                'labels': ['Sales', 'Purchases'],
                'series': [float(stats['sales_total_30_days']), float(stats['purchases_total_30_days'])],
            }
        },
    }

# ----------------- Sales -----------------

def get_sales_report(date_from: date, date_to: date, customer_id: Optional[int] = None, product_id: Optional[int] = None) -> Dict[str, Any]:
    invoices = Invoice.objects.filter(date__range=[date_from, date_to])
    if customer_id:
        invoices = invoices.filter(customer_id=customer_id)
    items_qs = InvoiceItem.objects.filter(invoice__date__range=[date_from, date_to])
    if customer_id:
        items_qs = items_qs.filter(invoice__customer_id=customer_id)
    if product_id:
        items_qs = items_qs.filter(product_id=product_id)
    item_sales_expr = DecimalExpr(F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2))
    revenue_total = items_qs.aggregate(total=Sum(item_sales_expr))['total'] or 0
    # Average invoice total computed via item-level aggregation per invoice to avoid 'items__' joins in ExpressionWrapper
    if invoices.exists():
        per_invoice = items_qs.values('invoice_id').annotate(total=Sum(item_sales_expr))
        totals = [r['total'] or 0 for r in per_invoice]
        avg_invoice = (sum(totals) / len(totals)) if totals else 0
    else:
        avg_invoice = 0
    sales_summary = {
        'total_invoices': invoices.count(),
        'total_revenue': revenue_total,
        'total_discount': invoices.aggregate(total=Sum('discount'))['total'] or 0,
        'total_paid': invoices.aggregate(total=Sum('paid'))['total'] or 0,
        'average_invoice': avg_invoice,
    }
    # Aggregate by customer via item-level joining to reduce complexity; fall back to invoice counts
    top_customers = [
        {
            'name': r['invoice__customer__name'],
            'invoice_count': r['invoice_count'],
            'total_amount': float(r['total_amount'] or 0),
        }
        for r in (
            items_qs.values('invoice__customer__name')
            .annotate(
                total_amount=Sum(item_sales_expr),
                invoice_count=Count('invoice', distinct=True),
            )
            .order_by('-total_amount')[:10]
        )
    ]
    top_products = [
        {
            'name': r['product__name'],
            'quantity_sold': r['quantity_sold'],
            'total_revenue': float(r['total_revenue'] or 0),
        }
        for r in (
            items_qs.values('product__name')
            .annotate(
                quantity_sold=Sum('quantity'),
                total_revenue=Sum(item_sales_expr),
            )
            .order_by('-quantity_sold')[:10]
        )
    ]
    # Daily revenue series (item-level aggregated per invoice date)
    days = (date_to - date_from).days + 1
    daily_map = {
        r['invoice__date']: r['revenue']
        for r in (
            items_qs.values('invoice__date').annotate(revenue=Sum(item_sales_expr))
        )
    }
    labels, series_rev, series_cnt = [], [], []
    invoice_counts = {r['date']: r['count'] for r in invoices.values('date').annotate(count=Count('id'))}
    for i in range(days):
        d = date_from + timedelta(days=i)
        labels.append(d.strftime('%Y-%m-%d'))
        series_rev.append(float(daily_map.get(d, 0) or 0))
        series_cnt.append(invoice_counts.get(d, 0))
    return {
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d'),
        'sales_summary': sales_summary,
        'top_customers': top_customers,
        'top_products': top_products,
        'charts': {
            'daily_revenue': {'labels': labels, 'series': [series_rev]},
            'daily_invoice_count': {'labels': labels, 'series': [series_cnt]},
        },
    }

# ----------------- Inventory -----------------

def get_inventory_report() -> Dict[str, Any]:
    products_with_stock = Product.objects.annotate(
        total_stock=Coalesce(
            Sum('stocks__quantity', output_field=DecimalField(max_digits=18, decimal_places=2)),
            0,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        stock_value=Sum(DecimalExpr(F('stocks__quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))),
        locations_count=Count('stocks__location', distinct=True),
    )
    stock_analysis = {
        'total_products': products_with_stock.count(),
        'out_of_stock': products_with_stock.filter(total_stock=0).count(),
        'low_stock': products_with_stock.filter(total_stock__gt=0, total_stock__lt=F('min_stock')).count(),
        'good_stock': products_with_stock.filter(total_stock__gte=F('min_stock')).count(),
        'total_value': float(products_with_stock.aggregate(total=Sum('stock_value'))['total'] or 0),
    }
    locations_stock = list(
        Location.objects.annotate(
            products_count=Count('stocks__product', distinct=True),
            total_items=Sum('stocks__quantity', output_field=DecimalField(max_digits=18, decimal_places=2)),
            stock_value_total=Sum(DecimalExpr(F('stocks__quantity') * F('stocks__product__cost'), output_field=DecimalField(max_digits=18, decimal_places=2))),
        )
        .order_by('-stock_value_total')
        .values('code', 'name', 'products_count', 'total_items', 'stock_value_total')
    )
    return {
        'stock_analysis': stock_analysis,
        'out_of_stock_products': list(products_with_stock.filter(total_stock=0).values('id', 'name', 'total_stock')[:10]),
        'low_stock_products': list(products_with_stock.filter(total_stock__gt=0, total_stock__lt=F('min_stock')).values('id', 'name', 'total_stock', 'min_stock')[:10]),
        'high_value_products': list(products_with_stock.filter(stock_value__gt=0).order_by('-stock_value').values('id', 'name', 'stock_value', 'total_stock')[:10]),
        'locations_stock': locations_stock,
        'charts': {
            'stock_distribution': {
                'labels': [r['name'] or r['code'] for r in locations_stock[:8]],
                'series': [float(r['total_items'] or 0) for r in locations_stock[:8]],
            }
        },
    }

# ----------------- Purchases -----------------

def get_purchases_report(date_from: date, date_to: date, supplier_id: Optional[int] = None) -> Dict[str, Any]:
    bills = PurchaseBill.objects.filter(date__range=[date_from, date_to])
    if supplier_id:
        bills = bills.filter(supplier_id=supplier_id)
    items_qs = PurchaseItem.objects.filter(bill__date__range=[date_from, date_to])
    if supplier_id:
        items_qs = items_qs.filter(bill__supplier_id=supplier_id)
    item_cost_expr = DecimalExpr(F('quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
    total_amount = items_qs.aggregate(total=Sum(item_cost_expr))['total'] or 0
    # Average bill total computed via item-level aggregation per bill to avoid 'items__' expressions
    if bills.exists():
        per_bill = items_qs.values('bill_id').annotate(total=Sum(item_cost_expr))
        bill_totals = [r['total'] or 0 for r in per_bill]
        avg_bill = (sum(bill_totals) / len(bill_totals)) if bill_totals else 0
    else:
        avg_bill = 0
    purchases_summary = {
        'total_bills': bills.count(),
        'total_amount': total_amount,
        'total_discount': bills.aggregate(total=Sum('discount'))['total'] or 0,
        'total_paid': bills.aggregate(total=Sum('paid'))['total'] or 0,
        'average_bill': avg_bill,
    }
    top_suppliers = [
        {
            'name': r['bill__supplier__name'],
            'bill_count': r['bill_count'],
            'total_amount': float(r['total_amount'] or 0),
        }
        for r in (
            items_qs.values('bill__supplier__name')
            .annotate(
                total_amount=Sum(item_cost_expr),
                bill_count=Count('bill', distinct=True),
            )
            .order_by('-total_amount')[:10]
        )
    ]
    top_purchased = [
        {
            'name': r['product__name'],
            'quantity_purchased': r['quantity_purchased'],
            'total_cost': float(r['total_cost'] or 0),
        }
        for r in (
            items_qs.values('product__name')
            .annotate(
                quantity_purchased=Sum('quantity'),
                total_cost=Sum(item_cost_expr),
            )
            .order_by('-quantity_purchased')[:10]
        )
    ]
    return {
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d'),
        'purchases_summary': purchases_summary,
        'top_suppliers': top_suppliers,
        'top_purchased': top_purchased,
    }

# ----------------- Full System (Aggregated) -----------------

def get_full_system_report() -> Dict[str, Any]:
    """Return a broad, multi‑module snapshot intended for a single dashboard request.

    It intentionally keeps queries shallow (mostly counts + light aggregates) and
    encapsulates per-app failures so a missing app / migration never breaks the
    entire response.
    """
    today = date.today()
    last_30 = today - timedelta(days=30)

    def safe(name: str, fn: Callable[[], Any], default: Any = None) -> Any:
        try:
            return fn()
        except Exception:  # pragma: no cover - defensive: never block report
            return default

    # Reuse existing granular report functions where cheap
    overview = safe('overview', get_overview_report, {})
    inventory = safe('inventory', get_inventory_report, {})

    # Sales quick slice (avoid full sales report if large date span)
    sales_slice = safe('sales_slice', lambda: {
        'invoices_30_days': Invoice.objects.filter(date__gte=last_30).count(),
        'revenue_30_days': float(
            InvoiceItem.objects.filter(invoice__date__gte=last_30).aggregate(
                total=Sum(DecimalExpr(F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2)))
            )['total'] or 0
        ),
    }, {})

    purchases_slice = safe('purchases_slice', lambda: {
        'bills_30_days': PurchaseBill.objects.filter(date__gte=last_30).count(),
        'amount_30_days': float(
            PurchaseItem.objects.filter(bill__date__gte=last_30).aggregate(
                total=Sum(DecimalExpr(F('quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2)))
            )['total'] or 0
        ),
    }, {})

    accounting_slice = safe('accounting', lambda: {
        'accounts': Account.objects.count() if Account else 0,
        'journal_entries_30_days': JournalEntry.objects.filter(date__gte=last_30).count() if JournalEntry else 0,
        'revenues_30_days': float(LegacyRevenue.objects.filter(date__gte=last_30).aggregate(total=Sum('amount'))['total'] or 0) if LegacyRevenue else 0,
        'expenses_30_days': float(LegacyExpense.objects.filter(date__gte=last_30).aggregate(total=Sum('amount'))['total'] or 0) if LegacyExpense else 0,
        'cost_centers': CostCenter.objects.count() if CostCenter else 0,
        'loans': {
            'count': Loan.objects.count() if Loan else 0,
            'outstanding_total': float(Loan.objects.aggregate(total=Sum('outstanding_balance'))['total'] or 0) if Loan else 0,
        },
    }, {})
    if accounting_slice:
        accounting_slice['net_income_30_days'] = accounting_slice.get('revenues_30_days', 0) - accounting_slice.get('expenses_30_days', 0)

    crm_slice = safe('crm', lambda: {
        'customers_count': Customer.objects.count(),  # partners' customer model already imported
        'opportunities': None if not Opportunity else {
            'open': Opportunity.objects.exclude(stage__is_won=True).exclude(stage__is_lost=True).count(),
            'won': Opportunity.objects.filter(stage__is_won=True).count(),
            'lost': Opportunity.objects.filter(stage__is_lost=True).count(),
            'pipeline_value': float(Opportunity.objects.filter(stage__is_won=False, stage__is_lost=False).aggregate(total=Sum('estimated_value'))['total'] or 0),
        },
        'tickets_count': 0 if not SupportTicket else SupportTicket.objects.count(),
    }, {})

    hr_slice = safe('hr', lambda: {
        'employees_count': 0 if not Employee else Employee.objects.count(),
    }, {})

    return {
        'generated_at': tz_now().isoformat(),
        'overview': overview,
        'inventory': {
            'stock_analysis': inventory.get('stock_analysis'),
            'low_stock_products': inventory.get('low_stock_products', [])[:5],
        } if inventory else {},
        'sales': sales_slice,
        'purchases': purchases_slice,
        'accounting': accounting_slice,
        'crm': crm_slice,
        'hr': hr_slice,
    }

# ----------------- Profit & Loss -----------------

def get_profit_loss_report(
    date_from: date,
    date_to: date,
    cogs_method: str | None = None,
    compare_all: bool = False,
) -> Dict[str, Any]:
    """Enhanced P&L report with optional COGS costing strategies.

    cogs_method:
      - 'fifo'     -> force FIFO attempt (fallback to approx on exception)
      - 'weighted' -> force weighted attempt (fallback to approx on exception)
      - 'approx'   -> bypass advanced costing
      - None/auto  -> try FIFO, else weighted, else approx
    """
    items = InvoiceItem.objects.filter(invoice__date__range=[date_from, date_to])
    sales_expr = DecimalExpr(F('quantity') * F('price'), output_field=DecimalField(max_digits=18, decimal_places=2))
    cogs_expr = DecimalExpr(F('quantity') * F('product__cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
    gross_revenue = items.aggregate(total=Sum(sales_expr))['total'] or 0
    cogs_approx = items.aggregate(total=Sum(cogs_expr))['total'] or 0
    discounts = Invoice.objects.filter(date__range=[date_from, date_to]).aggregate(total=Sum('discount'))['total'] or 0
    net_revenue = gross_revenue - discounts
    expenses_total = 0
    if 'accounting' in globals() and LegacyExpense:
        expenses_total = LegacyExpense.objects.filter(date__range=[date_from, date_to]).aggregate(total=Sum('amount'))['total'] or 0
    gross_profit = net_revenue - cogs_approx
    operating_profit = gross_profit - expenses_total
    base: Dict[str, Any] = {
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d'),
        'revenue': float(gross_revenue),
        'discounts': float(discounts),
        'net_revenue': float(net_revenue),
        'cogs': float(cogs_approx),  # legacy key
        'cogs_approx': float(cogs_approx),
        'gross_profit': float(gross_profit),
        'expenses': float(expenses_total),
        'operating_profit': float(operating_profit),
        'margin_percent': float((gross_profit / net_revenue * 100) if net_revenue else 0),
        'cogs_method': 'approx',
    }

    requested = cogs_method

    def apply_weighted() -> bool:
        try:
            ctx = compute_weighted_cogs_context(date_from, date_to)
            if ctx.get('cogs_weighted', 0) <= 0 and ctx.get('sold_qty', 0) > 0:
                return False
            base['cogs_weighted'] = round(ctx['cogs_weighted'], 2)
            base['avg_unit_cost_weighted'] = round(ctx['avg_unit_cost_weighted'], 4)
            base['cogs_method'] = 'weighted'
            net_rev = base.get('net_revenue', 0)
            expenses = base.get('expenses', 0)
            gp_w = net_rev - ctx['cogs_weighted']
            op_w = gp_w - expenses
            base['gross_profit_weighted'] = round(gp_w, 2)
            base['operating_profit_weighted'] = round(op_w, 2)
            base['margin_percent_weighted'] = float((gp_w / net_rev * 100) if net_rev else 0)
            return True
        except Exception:
            base.setdefault('errors', []).append('weighted_failed')
            return False

    def apply_fifo() -> bool:
        try:
            fifo_cogs = compute_fifo_cogs_for_period(date_from, date_to)
            if fifo_cogs is None:
                return False
            base['cogs_fifo'] = round(float(fifo_cogs), 2)
            base['cogs_method'] = 'fifo'
            net_rev = base.get('net_revenue', 0)
            expenses = base.get('expenses', 0)
            gp_f = net_rev - float(fifo_cogs)
            op_f = gp_f - expenses
            base['gross_profit_fifo'] = round(gp_f, 2)
            base['operating_profit_fifo'] = round(op_f, 2)
            base['margin_percent_fifo'] = float((gp_f / net_rev * 100) if net_rev else 0)
            return True
        except Exception:
            base.setdefault('errors', []).append('fifo_failed')
            return False

    if requested == 'approx':
        pass
    elif requested == 'fifo':
        apply_fifo()
    elif requested == 'weighted':
        apply_weighted()
    else:  # auto
        chosen = None
        if apply_fifo():
            chosen = 'fifo'
        elif apply_weighted():
            chosen = 'weighted'
        if chosen:
            base['chosen_auto_method'] = chosen

    if compare_all:
        have_fifo = 'cogs_fifo' in base
        have_weighted = 'cogs_weighted' in base
        if not have_fifo:
            apply_fifo()
        if not have_weighted:
            apply_weighted()
        if 'cogs_fifo' in base and 'cogs_weighted' in base:
            fifo_v = float(base['cogs_fifo'])
            weighted_v = float(base['cogs_weighted'])
            diff = fifo_v - weighted_v
            base['fifo_vs_weighted_cogs_diff'] = round(diff, 2)
            denom = weighted_v if weighted_v else (fifo_v if fifo_v else 0)
            base['fifo_vs_weighted_cogs_percent'] = round((diff / denom * 100), 2) if denom else 0.0
            net_rev = float(base.get('net_revenue', 0))
            gp_fifo = net_rev - fifo_v
            gp_weighted = net_rev - weighted_v
            base['fifo_vs_weighted_gross_profit_diff'] = round(gp_fifo - gp_weighted, 2)
    return base

# ----------------- Accounts Receivable Aging -----------------

def get_ar_aging_report(as_of: date) -> Dict[str, Any]:
    buckets = {
        '0_30': 0.0,
        '31_60': 0.0,
        '61_90': 0.0,
        '90_plus': 0.0,
    }
    per_customer: Dict[int, Dict[str, Any]] = {}
    invoices = Invoice.objects.all()
    for inv in invoices.select_related('customer').prefetch_related('items'):
        outstanding = float(inv.total) - float(inv.paid or 0)
        if outstanding <= 0:
            continue
        due_base = inv.due_date or inv.date
        age_days = (as_of - due_base).days
        if age_days <= 30:
            key = '0_30'
        elif age_days <= 60:
            key = '31_60'
        elif age_days <= 90:
            key = '61_90'
        else:
            key = '90_plus'
        buckets[key] += outstanding
        cdict = per_customer.setdefault(inv.customer_id, {
            'customer_id': inv.customer_id,
            'customer_name': getattr(inv.customer, 'name', getattr(inv.customer, 'full_name', '')),  # partner model difference
            '0_30': 0.0, '31_60': 0.0, '61_90': 0.0, '90_plus': 0.0,
            'total_outstanding': 0.0,
        })
        cdict[key] += outstanding
        cdict['total_outstanding'] += outstanding
    rows = sorted(per_customer.values(), key=lambda r: r['total_outstanding'], reverse=True)
    grand_total = sum(r['total_outstanding'] for r in rows)
    return {
        'as_of': as_of.strftime('%Y-%m-%d'),
        'buckets': {k: float(v) for k,v in buckets.items()},
        'total_outstanding': float(grand_total),
        'customers': rows,
    }

# ----------------- CRM Pipeline -----------------

def get_crm_pipeline_report() -> Dict[str, Any]:
    if not Opportunity:
        return {'enabled': False}
    stages = OpportunityStage.objects.all() if OpportunityStage else []  # type: ignore
    by_stage = []
    total_open = 0
    expected_value = 0
    for st in stages:
        qs = Opportunity.objects.filter(stage=st)
        stage_total = qs.aggregate(total=Sum('estimated_value'))['total'] or 0
        won = getattr(st, 'is_won', False)
        lost = getattr(st, 'is_lost', False)
        if not won and not lost:
            total_open += stage_total
            # probability: prefer stage.probability else average of opportunities
            prob = float(getattr(st, 'probability', 0))
            expected_value += stage_total * (prob / 100 if prob else 0)
        by_stage.append({
            'stage': st.name,
            'order': getattr(st,'order',0),
            'is_won': won,
            'is_lost': lost,
            'value': float(stage_total),
            'count': qs.count(),
        })
    won_value = Opportunity.objects.filter(stage__is_won=True).aggregate(total=Sum('estimated_value'))['total'] or 0
    lost_value = Opportunity.objects.filter(stage__is_lost=True).aggregate(total=Sum('estimated_value'))['total'] or 0
    return {
        'enabled': True,
        'stages': sorted(by_stage, key=lambda r: r['order']),
        'total_open_value': float(total_open),
        'expected_value_open': float(expected_value),
        'won_value': float(won_value),
        'lost_value': float(lost_value),
        'win_rate_percent': float((won_value / (won_value + lost_value) * 100) if (won_value + lost_value) else 0),
    }

# ----------------- Accounts Payable Aging -----------------

def get_ap_aging_report(as_of: date) -> Dict[str, Any]:
    buckets = {'0_30':0.0,'31_60':0.0,'61_90':0.0,'90_plus':0.0}
    per_supplier: Dict[int, Dict[str, Any]] = {}
    bills = PurchaseBill.objects.all()
    for bill in bills.prefetch_related('items').select_related('supplier'):
        outstanding = float(bill.total) - float(bill.paid or 0)
        if outstanding <= 0:
            continue
        due_base = bill.date  # لاحقاً يمكن إضافة حقل due_date للمورد
        age_days = (as_of - due_base).days
        if age_days <= 30: key='0_30'
        elif age_days <= 60: key='31_60'
        elif age_days <= 90: key='61_90'
        else: key='90_plus'
        buckets[key]+=outstanding
        sd = per_supplier.setdefault(bill.supplier_id, {
            'supplier_id': bill.supplier_id,
            'supplier_name': getattr(bill.supplier,'name',''),
            '0_30':0.0,'31_60':0.0,'61_90':0.0,'90_plus':0.0,'total_outstanding':0.0,
        })
        sd[key]+=outstanding; sd['total_outstanding']+=outstanding
    rows = sorted(per_supplier.values(), key=lambda r:r['total_outstanding'], reverse=True)
    total = sum(r['total_outstanding'] for r in rows)
    return {
        'as_of': as_of.strftime('%Y-%m-%d'),
        'buckets': {k:float(v) for k,v in buckets.items()},
        'total_outstanding': float(total),
        'suppliers': rows,
    }

# ----------------- Balance Sheet (Simplified) -----------------

def get_balance_sheet(as_of: date) -> Dict[str, Any]:
    if not Account:
        return {'enabled': False}
    # تصنيف بسيط حسب نوع الحساب الحالي
    accounts = Account.objects.filter(is_active=True)
    # Each account dict contains strings (code,name) and a float (balance)
    from typing import TypedDict
    class AccountRow(TypedDict):
        code: str
        name: str
        balance: float
    grouped: Dict[str, list[AccountRow]] = {t: [] for t in ['asset','liability','equity','revenue','expense']}
    for acc in accounts:
        bal = acc.balance
        grouped.get(acc.account_type, []).append(AccountRow(code=acc.code, name=acc.name, balance=float(bal)))
    def total(t):
        return sum(a['balance'] for a in grouped.get(t, []))
    assets = total('asset')
    liabilities = total('liability')
    equity = total('equity')
    # أرباح محتجزة مبسطة: (الإيرادات - المصروفات)
    retained = total('revenue') - total('expense')
    equity_total = equity + retained
    diff = assets - (liabilities + equity_total)
    return {
        'as_of': as_of.strftime('%Y-%m-%d'),
        'assets': {'total': assets, 'accounts': grouped['asset']},
        'liabilities': {'total': liabilities, 'accounts': grouped['liability']},
        'equity': {'base_equity': equity, 'retained_earnings': retained, 'total_equity': equity_total, 'accounts': grouped['equity']},
        'check': diff,  # legacy key
        'is_balanced': abs(diff) < 0.01,
        'difference': diff,
    }

# ----------------- Cash Flow (Simplified) -----------------

def get_cash_flow_report(date_from: date, date_to: date) -> Dict[str, Any]:
    """Segmented cash flow (operating / investing / financing) مع الحفاظ على الشكل السابق.

    Operating inflows: invoice paid amounts + legacy revenues.
    Operating outflows: purchases paid + legacy expenses.
    Investing: (placeholder) يمكن لاحقاً ربطه بحركات أصول ثابتة / استثمارات.
    Financing: (placeholder) يمكن لاحقاً ربطه بسداد/استلام قروض أو توزيعات.
    تبقى المفاتيح القديمة (inflows/outflows/net_cash_flow) لضمان التوافق مع الواجهات الحالية.
    """
    invoices = Invoice.objects.filter(date__range=[date_from, date_to])
    inflow_invoices = invoices.aggregate(total=Sum('paid'))['total'] or 0
    inflow_other = 0
    if LegacyRevenue:
        inflow_other = LegacyRevenue.objects.filter(date__range=[date_from, date_to]).aggregate(total=Sum('amount'))['total'] or 0
    bills = PurchaseBill.objects.filter(date__range=[date_from, date_to])
    outflow_purchases = bills.aggregate(total=Sum('paid'))['total'] or 0
    outflow_expenses = 0
    if LegacyExpense:
        outflow_expenses = LegacyExpense.objects.filter(date__range=[date_from, date_to]).aggregate(total=Sum('amount'))['total'] or 0
    total_inflows = float(inflow_invoices + inflow_other)
    total_outflows = float(outflow_purchases + outflow_expenses)
    net = total_inflows - total_outflows
    operating = {
        'inflows': {
            'invoices_paid': float(inflow_invoices),
            'other_revenues': float(inflow_other),
            'total_inflows': total_inflows,
        },
        'outflows': {
            'purchases_paid': float(outflow_purchases),
            'expenses': float(outflow_expenses),
            'total_outflows': total_outflows,
        },
        'net_operating': net,
    }
    investing_inflows = 0.0
    investing_outflows = 0.0
    financing_inflows = 0.0
    financing_outflows = 0.0
    # دمج أولي مع القروض: اعتبر صرف القرض تدفق تمويلي داخلي وسداد الأصل تدفق تمويلي خارجي
    if Loan:
        try:
            loan_disbursements = Loan.objects.filter(disbursement_date__range=[date_from, date_to]).aggregate(
                total=Sum('principal_amount'))['total'] or 0
            financing_inflows += float(loan_disbursements)
        except Exception:
            pass
        # سداد القروض من LoanPayment (جزء أصل الدين فقط)
        try:
            from accounting.models import LoanPayment  # استيراد محلي لتفادي أخطاء زمن التحميل
            principal_paid = LoanPayment.objects.filter(payment_date__range=[date_from, date_to]).aggregate(
                total=Sum('principal_portion'))['total'] or 0
            financing_outflows += float(principal_paid)
        except Exception:
            pass
    # TODO: إضافة معاملات أصول ثابتة مستقبلية (شراء/بيع) لقسم الاستثمار
    investing = {
        'inflows': investing_inflows,
        'outflows': investing_outflows,
        'net_investing': investing_inflows - investing_outflows,
    }
    financing = {
        'inflows': financing_inflows,
        'outflows': financing_outflows,
        'net_financing': financing_inflows - financing_outflows,
    }
    net_total = operating['net_operating'] + investing['net_investing'] + financing['net_financing']
    return {
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d'),
        # الشكل القديم (توافق رجعي)
        'inflows': operating['inflows'],
        'outflows': operating['outflows'],
        'net_cash_flow': operating['net_operating'],
        # الشكل الجديد المقسّم
        'operating': operating,
        'investing': investing,
        'financing': financing,
        'net_total': net_total,
        'notes': 'Segmented cash flow; investing/financing placeholders until related transactions are implemented.'
    }

# ----------------- Inventory Turnover -----------------

def get_inventory_turnover_report(
    date_from: date,
    date_to: date,
    cogs_method: str | None = None,
    compare_all: bool = False,
) -> Dict[str, Any]:
    """Inventory turnover with optional costing methods.

    Base approximation uses current product.cost; advanced tries FIFO/weighted similar to P&L.
    """
    sold_items = InvoiceItem.objects.filter(invoice__date__range=[date_from, date_to])
    cogs_expr = DecimalExpr(F('quantity') * F('product__cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
    cogs_approx = sold_items.aggregate(total=Sum(cogs_expr))['total'] or 0
    stock_value_expr = DecimalExpr(F('stocks__quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
    current_inventory_value = Product.objects.aggregate(total=Sum(stock_value_expr))['total'] or 0
    avg_inventory_proxy = current_inventory_value
    turnover = float(cogs_approx) / float(avg_inventory_proxy) if avg_inventory_proxy else 0.0
    days = (date_to - date_from).days + 1
    days_per_turn = (days / turnover) if turnover else None
    rep: Dict[str, Any] = {
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d'),
        'cogs_approx': float(cogs_approx),
        'average_inventory_value_proxy': float(avg_inventory_proxy),
        'turnover_ratio': float(turnover),
        'days_in_period': days,
        'days_per_turn': float(days_per_turn) if days_per_turn else None,
        'notes': 'Average inventory approximated by current value; implement historical snapshots for accuracy.',
        'cogs_method': 'approx',
    }

    requested = cogs_method

    def apply_weighted() -> bool:
        try:
            ctx = compute_weighted_cogs_context(date_from, date_to)
            rep['cogs_weighted'] = round(ctx['cogs_weighted'], 2)
            rep['avg_unit_cost_weighted'] = round(ctx['avg_unit_cost_weighted'], 4)
            opening_value = ctx['opening_value_est']
            closing_value = ctx['closing_value']
            avg_inventory = (opening_value + closing_value) / 2 if (opening_value or closing_value) else 0
            turnover_weighted = ctx['cogs_weighted'] / avg_inventory if avg_inventory else 0
            rep['turnover_ratio_weighted'] = round(turnover_weighted, 4)
            rep['days_per_turn_weighted'] = round(days / turnover_weighted, 2) if turnover_weighted else None
            rep['opening_inventory_weighted_estimate'] = round(opening_value, 2)
            rep['average_inventory_weighted'] = round(avg_inventory, 2)
            rep['cogs_method'] = 'weighted'
            return True
        except Exception:
            rep.setdefault('errors', []).append('weighted_failed')
            return False

    def apply_fifo() -> bool:
        try:
            fifo_cogs = compute_fifo_cogs_for_period(date_from, date_to)
            if fifo_cogs is None:
                return False
            rep['cogs_fifo'] = round(float(fifo_cogs), 2)
            rep['cogs_method'] = 'fifo'
            purchase_items = PurchaseItem.objects.filter(bill__date__range=[date_from, date_to])
            purchase_value = purchase_items.aggregate(total=Sum(DecimalExpr(F('quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))))['total'] or 0
            closing_value = rep['average_inventory_value_proxy']
            opening_est = max(0.0, float(closing_value) + float(fifo_cogs) - float(purchase_value))
            avg_inventory = (opening_est + float(closing_value)) / 2 if closing_value is not None else opening_est
            turnover_fifo = float(fifo_cogs) / avg_inventory if avg_inventory else 0.0
            rep['opening_inventory_estimate'] = round(opening_est, 2)
            rep['average_inventory_fifo_based'] = round(avg_inventory, 2)
            rep['turnover_ratio_fifo'] = round(turnover_fifo, 4)
            rep['days_per_turn_fifo'] = round(days / turnover_fifo, 2) if turnover_fifo else None
            return True
        except Exception:
            rep.setdefault('errors', []).append('fifo_failed')
            return False

    if requested == 'approx':
        pass
    elif requested == 'fifo':
        apply_fifo()
    elif requested == 'weighted':
        apply_weighted()
    else:
        chosen = None
        if apply_fifo():
            chosen = 'fifo'
        elif apply_weighted():
            chosen = 'weighted'
        if chosen:
            rep['chosen_auto_method'] = chosen

    if compare_all:
        have_fifo = 'cogs_fifo' in rep
        have_weighted = 'cogs_weighted' in rep
        if not have_fifo:
            apply_fifo()
        if not have_weighted:
            apply_weighted()
        if 'cogs_fifo' in rep and 'cogs_weighted' in rep:
            diff = float(rep['cogs_fifo']) - float(rep['cogs_weighted'])
            rep['fifo_vs_weighted_cogs_diff'] = round(diff, 2)
            denom = float(rep['cogs_weighted']) or float(rep['cogs_fifo']) or 0
            rep['fifo_vs_weighted_cogs_percent'] = round((diff / denom * 100), 2) if denom else 0.0
    return rep

# ----------------- Stock Aging -----------------

def get_stock_aging_report(as_of: date, slice_limit: int | None = 300) -> Dict[str, Any]:
    """Categorize products by last movement age (sale or purchase) with fewer queries.

    Uses subqueries to fetch last sale/purchase dates instead of building large Python dicts.
    Limits returned products list to 300 (configurable via slice) for performance in UI.
    """
    from django.db.models import OuterRef, Subquery, DateField as DJDateField
    last_invoice_date_sq = Subquery(
        InvoiceItem.objects.filter(product_id=OuterRef('pk'))
        .order_by('-invoice__date')
        .values('invoice__date')[:1]
    )
    last_purchase_date_sq = Subquery(
        PurchaseItem.objects.filter(product_id=OuterRef('pk'))
        .order_by('-bill__date')
        .values('bill__date')[:1]
    )
    products = (
        Product.objects.annotate(
            total_stock=Coalesce(Sum('stocks__quantity'), 0),
            stock_value=Sum(DecimalExpr(F('stocks__quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))),
            last_sale_date=last_invoice_date_sq,
            last_purchase_date=last_purchase_date_sq,
        )
    )
    buckets = {
        '0_30': {'value':0.0,'qty':0},
        '31_60': {'value':0.0,'qty':0},
        '61_90': {'value':0.0,'qty':0},
        '90_plus': {'value':0.0,'qty':0},
        'no_movement': {'value':0.0,'qty':0},
    }
    rows = []
    for p in products.iterator():
        # determine last movement
        last_date = p.last_sale_date if p.last_sale_date else p.last_purchase_date
        if p.last_sale_date and p.last_purchase_date:
            last_date = p.last_sale_date if p.last_sale_date > p.last_purchase_date else p.last_purchase_date
        if not last_date:
            bucket_key = 'no_movement'
            age_days = None
        else:
            age_days = (as_of - last_date).days
            if age_days <= 30:
                bucket_key = '0_30'
            elif age_days <= 60:
                bucket_key = '31_60'
            elif age_days <= 90:
                bucket_key = '61_90'
            else:
                bucket_key = '90_plus'
        value = float(p.stock_value or 0)
        qty = float(p.total_stock or 0)
        buckets[bucket_key]['value'] += value
        buckets[bucket_key]['qty'] += qty
        rows.append({
            'product_id': p.id,
            'name': p.name,
            'total_stock': qty,
            'stock_value': value,
            'last_movement_date': last_date.strftime('%Y-%m-%d') if last_date else None,
            'age_days': age_days,
            'bucket': bucket_key,
        })
    summary = {k: {'value': round(v['value'],2), 'qty': v['qty']} for k,v in buckets.items()}
    total_value = sum(v['value'] for v in buckets.values())
    return {
        'as_of': as_of.strftime('%Y-%m-%d'),
        'summary': summary,
        'total_value': round(total_value,2),
        'products': rows if slice_limit is None else rows[:slice_limit],
    }

# ----------------- Enhanced Historical COGS Utilities (FIFO) -----------------
from django.db import transaction

def compute_fifo_cogs_for_period(date_from: date, date_to: date) -> float:
    """Compute COGS for sales in period using FIFO StockBatch layers.

    For each sold invoice item in the period, walk batches (by received_at,id) and simulate consumption.
    This does NOT mutate actual batch quantities (read-only); we clone remaining quantities in memory.
    If batches are insufficient (negative inventory scenarios), fallback to product.cost for residual.
    """
    # Build per (product, location) batch queues
    from collections import defaultdict, deque
    sales_items = InvoiceItem.objects.filter(invoice__date__range=[date_from, date_to]).select_related('product','location')
    if not sales_items.exists():
        return 0.0
    prod_loc_keys = {(it.product_id, it.location_id) for it in sales_items}
    batch_map: dict[tuple[int,int], deque] = {}
    for pid,lid in prod_loc_keys:
        batches = list(StockBatch.objects.filter(product_id=pid, location_id=lid, quantity__gt=0).order_by('received_at','id').values('unit_cost','quantity'))
        batch_map[(pid,lid)] = deque({'cost': float(b['unit_cost']), 'qty': int(b['quantity'])} for b in batches)
    total_cogs = 0.0
    for it in sales_items:
        remain = int(it.quantity)
        dq = batch_map.get((it.product_id, it.location_id))
        # If no batches snapshot, fallback fully
        if not dq or not dq:
            total_cogs += float(it.quantity) * float(getattr(it.product, 'cost', 0) or 0)
            continue
        while remain > 0 and dq:
            layer = dq[0]
            take = min(layer['qty'], remain)
            total_cogs += take * layer['cost']
            layer['qty'] -= take
            remain -= take
            if layer['qty'] <= 0:
                dq.popleft()
        if remain > 0:
            # shortage fallback
            total_cogs += remain * float(getattr(it.product,'cost',0) or 0)
    return total_cogs

def compute_weighted_cogs_context(date_from: date, date_to: date) -> dict[str, float]:
    """Compute weighted average cost context for a period.

    Approximates opening inventory value/qty using current closing snapshot plus flow reconciliation:
        opening_value ~= closing_value + cogs_approx - purchases_value
        opening_qty   ~= closing_qty + sold_qty - purchase_qty
    Then:
        avg_unit_cost = (opening_value + purchases_value) / (opening_qty + purchase_qty)
        cogs_weighted = sold_qty * avg_unit_cost
    Fallbacks: if any denominator <=0 we return zeros and let caller degrade gracefully.
    """
    # Sold items in period
    sales_items = InvoiceItem.objects.filter(invoice__date__range=[date_from, date_to])
    sold_qty = float(sales_items.aggregate(q=Sum('quantity'))['q'] or 0)
    # Approximate COGS already (quantity * product.cost)
    cogs_expr = DecimalExpr(F('quantity') * F('product__cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
    cogs_approx = float(sales_items.aggregate(total=Sum(cogs_expr))['total'] or 0)
    # Purchases in period
    purchase_items = PurchaseItem.objects.filter(bill__date__range=[date_from, date_to])
    purch_qty = float(purchase_items.aggregate(q=Sum('quantity'))['q'] or 0)
    purch_value_expr = DecimalExpr(F('quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
    purch_value = float(purchase_items.aggregate(total=Sum(purch_value_expr))['total'] or 0)
    # Closing snapshot (current values)
    stock_value_expr = DecimalExpr(F('stocks__quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
    closing_value = float(Product.objects.aggregate(total=Sum(stock_value_expr))['total'] or 0)
    closing_qty = float(Product.objects.aggregate(q=Sum('stocks__quantity'))['q'] or 0)
    # Reconstruct opening estimates (non-negative)
    opening_value_est = max(0.0, closing_value + cogs_approx - purch_value)
    opening_qty_est = max(0.0, closing_qty + sold_qty - purch_qty)
    pool_value = opening_value_est + purch_value
    pool_qty = opening_qty_est + purch_qty
    if pool_qty <= 0 or pool_value <= 0 or sold_qty <= 0:
        return {
            'cogs_weighted': 0.0,
            'avg_unit_cost_weighted': 0.0,
            'opening_value_est': opening_value_est,
            'opening_qty_est': opening_qty_est,
            'closing_value': closing_value,
            'closing_qty': closing_qty,
            'purchases_value': purch_value,
            'purchases_qty': purch_qty,
            'sold_qty': sold_qty,
            'cogs_approx': cogs_approx,
        }
    avg_unit_cost = pool_value / pool_qty
    cogs_weighted = sold_qty * avg_unit_cost
    # Guard: cannot exceed pool value materially (floating tolerance)
    cogs_weighted = min(cogs_weighted, pool_value * 1.001)
    return {
        'cogs_weighted': float(cogs_weighted),
        'avg_unit_cost_weighted': float(avg_unit_cost),
        'opening_value_est': opening_value_est,
        'opening_qty_est': opening_qty_est,
        'closing_value': closing_value,
        'closing_qty': closing_qty,
        'purchases_value': purch_value,
        'purchases_qty': purch_qty,
        'sold_qty': sold_qty,
        'cogs_approx': cogs_approx,
    }

# ----------------- Snapshot Utilities -----------------
from .models import ReportDailySnapshot
from . import alerts  # variance / other alerts utilities

def create_daily_snapshot(snapshot_date: date | None = None) -> 'ReportDailySnapshot':
    """Create or refresh a daily snapshot for snapshot_date (defaults to today).

    Uses existing profit & loss logic with compare_all to capture multiple COGS
    variants when available. The function is idempotent for a given date.
    """
    snapshot_date = snapshot_date or date.today()
    d_from = d_to = snapshot_date
    pl = get_profit_loss_report(d_from, d_to, cogs_method=None, compare_all=True)
    stock_value_expr = DecimalExpr(F('stocks__quantity') * F('cost'), output_field=DecimalField(max_digits=18, decimal_places=2))
    closing_inventory_value = Product.objects.aggregate(total=Sum(stock_value_expr))['total'] or 0
    obj, _created = ReportDailySnapshot.objects.update_or_create(
        date=snapshot_date,
        defaults={
            'net_revenue': pl.get('net_revenue', 0) or 0,
            'expenses': pl.get('expenses', 0) or 0,
            'cogs_approx': pl.get('cogs_approx', 0) or 0,
            'cogs_fifo': pl.get('cogs_fifo'),
            'cogs_weighted': pl.get('cogs_weighted'),
            'closing_inventory_value': closing_inventory_value,
        }
    )
    # Retention cleanup (best effort)
    try:
        retention_days = int(getattr(settings, 'REPORT_SNAPSHOT_RETENTION_DAYS', 365))
        if retention_days > 0:
            cutoff = date.today() - timedelta(days=retention_days)
            ReportDailySnapshot.objects.filter(date__lt=cutoff).delete()
    except Exception:
        pass
    return obj

def get_snapshot_series(days: int = 30) -> List[Dict[str, Any]]:
    try:
        qs = ReportDailySnapshot.objects.order_by('-date')[:days]
        rows: List[Dict[str, Any]] = []
        for snap in reversed(list(qs)):
            rows.append({
                'date': snap.date.strftime('%Y-%m-%d'),
                'net_revenue': float(snap.net_revenue),
                'expenses': float(snap.expenses),
                'cogs_approx': float(snap.cogs_approx),
                'cogs_fifo': float(snap.cogs_fifo) if snap.cogs_fifo is not None else None,
                'cogs_weighted': float(snap.cogs_weighted) if snap.cogs_weighted is not None else None,
                'closing_inventory_value': float(snap.closing_inventory_value),
                'gross_profit_approx': snap.gross_profit_approx,
                'gross_profit_fifo': snap.gross_profit_fifo,
                'gross_profit_weighted': snap.gross_profit_weighted,
            })
        return rows
    except OperationalError:
        # Table not yet migrated (e.g. test database reused with --keepdb). Return empty series gracefully.
        return []

# ----------------- Celery Integration Helper -----------------
try:
    from celery import shared_task  # type: ignore
except Exception:  # pragma: no cover
    shared_task = None  # type: ignore

if shared_task:
    @shared_task(name='reports.create_daily_snapshot_task')
    def create_daily_snapshot_task():  # pragma: no cover - invoked via scheduler
        """Celery task wrapper to create today's snapshot (idempotent)."""
        try:
            obj = create_daily_snapshot()
            return {'date': obj.date.isoformat(), 'id': obj.id}
        except Exception as exc:
            import logging
            logging.getLogger('reports.snapshot').error(f"Snapshot task failed: {exc}")
            raise

