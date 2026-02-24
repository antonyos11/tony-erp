"""Accounting reporting helpers (cash flow, etc.).

Separated from views to allow reuse by API layers and easier unit testing.
Currently provides compute_cash_flow which implements the simplified
direct-method operating/investing/financing classification used by the
HTML/JSON/XLSX exports.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, Any, Optional, List, TypedDict

from .models import JournalEntryItem

try:  # optional mapping model
    from .models import CashFlowAccountMapping
except Exception:  # pragma: no cover
    CashFlowAccountMapping = None  # type: ignore


@dataclass
class CashFlowParams:
    date_from: date
    date_to: date
    cost_center_id: Optional[int] = None
    account_prefix: str = ''
    include_breakdown: bool = False
    compare_previous: bool = False


def _bucket_for(account, mappings: Dict[int, str]) -> str:
    # mapping override
    b = mappings.get(account.id)
    if b:
        return b
    t = account.account_type
    if t in ['revenue', 'expense']:
        return 'operating'
    if t == 'asset':
        if (account.code or '').startswith(('15', '16')):  # long term assets heuristic
            return 'investing'
        return 'operating'
    if t in ['liability', 'equity']:
        return 'financing'
    return 'operating'


class _FlowBucket(TypedDict, total=False):
    inflows: Decimal
    outflows: Decimal
    net: Decimal


def compute_cash_flow(params: CashFlowParams) -> Dict[str, Any]:
    """Compute cash flow statement context dict.

    Returns a dict with keys: operating, investing, financing, net_change,
    prev_period (optional), breakdown (optional), and meta params.
    """
    qs = JournalEntryItem.objects.filter(
        journal_entry__is_posted=True,
        journal_entry__date__range=[params.date_from, params.date_to]
    ).select_related('account')
    if params.cost_center_id:
        qs = qs.filter(cost_center_id=params.cost_center_id)
    if params.account_prefix:
        qs = qs.filter(account__code__startswith=params.account_prefix)

    mappings: Dict[int, str] = {}
    if CashFlowAccountMapping is not None:
        try:
            mappings = {m.account.id: m.category for m in CashFlowAccountMapping.objects.all()}
        except Exception:  # pragma: no cover
            mappings = {}

    data = {
        'operating': {'inflows': Decimal('0'), 'outflows': Decimal('0')},
        'investing': {'inflows': Decimal('0'), 'outflows': Decimal('0')},
        'financing': {'inflows': Decimal('0'), 'outflows': Decimal('0')},
    }

    breakdown_list: List[Dict[str, Any]] | None = [] if params.include_breakdown else None

    for item in qs:
        bucket = _bucket_for(item.account, mappings)
        sign = Decimal('1') if item.type == 'debit' else Decimal('-1')
        flow_amount = item.amount * sign
        if flow_amount > 0:
            data[bucket]['inflows'] += flow_amount
        else:
            data[bucket]['outflows'] += abs(flow_amount)
        if breakdown_list is not None:
            breakdown_list.append({
                'account_code': item.account.code,
                'account_name': item.account.name,
                'bucket': bucket,
                'amount': flow_amount,
                'debit': item.type == 'debit',
            })

    for bucket in ('operating', 'investing', 'financing'):
        b = data[bucket]
        b['net'] = b['inflows'] - b['outflows']

    net_change = data['operating']['net'] + data['investing']['net'] + data['financing']['net']

    prev_period: Dict[str, Any] | None = None
    if params.compare_previous:
        try:
            span = (params.date_to - params.date_from).days + 1
            prev_end = params.date_from - timedelta(days=1)
            prev_start = prev_end - timedelta(days=span - 1)
            prev_qs = JournalEntryItem.objects.filter(
                journal_entry__is_posted=True,
                journal_entry__date__range=[prev_start, prev_end]
            ).select_related('account')
            p_data: Dict[str, _FlowBucket] = {
                'operating': {'inflows': Decimal('0'), 'outflows': Decimal('0')},
                'investing': {'inflows': Decimal('0'), 'outflows': Decimal('0')},
                'financing': {'inflows': Decimal('0'), 'outflows': Decimal('0')},
            }
            for pit in prev_qs:
                bkt = _bucket_for(pit.account, mappings)
                sign = Decimal('1') if pit.type == 'debit' else Decimal('-1')
                famt = pit.amount * sign
                if famt > 0:
                    p_data[bkt]['inflows'] += famt
                else:
                    p_data[bkt]['outflows'] += abs(famt)
            for bucket in ('operating', 'investing', 'financing'):
                p_data[bucket]['net'] = p_data[bucket]['inflows'] - p_data[bucket]['outflows']
            prev_period = dict(p_data)
            prev_period['date_from'] = prev_start
            prev_period['date_to'] = prev_end
            prev_period['net_change'] = p_data['operating']['net'] + p_data['investing']['net'] + p_data['financing']['net']
        except Exception:  # pragma: no cover
            prev_period = None

    context: Dict[str, Any] = {
        'date_from': params.date_from.strftime('%Y-%m-%d'),
        'date_to': params.date_to.strftime('%Y-%m-%d'),
        'cost_center_id': params.cost_center_id,
        'account_prefix': params.account_prefix,
        **data,
        'net_change': net_change,
        'prev_period': prev_period,
        'breakdown': breakdown_list,
    }
    if prev_period:
        try:
            context['operating_change'] = data['operating']['net'] - prev_period['operating']['net']
            context['investing_change'] = data['investing']['net'] - prev_period['investing']['net']
            context['financing_change'] = data['financing']['net'] - prev_period['financing']['net']
            context['net_change_diff'] = net_change - prev_period['net_change']
        except Exception:  # pragma: no cover
            pass
    return context


__all__ = ['CashFlowParams', 'compute_cash_flow']
