"""Billing / payment related template utilities.

Provided tags & filters:
  remaining_amount total paid -> numeric remaining (non-negative)
  tuple_pair paid total        -> helper to chain into paid_percent filter
  paid_percent (paid,total)    -> percent (0-100, rounded to 2)
  clamp_percent value          -> cap any numeric to [0,100]
  percent_display value[:d]    -> formatted string with %
  payment_status paid total    -> dict with {percent, remaining, overpaid, status}

Usage example in template:
  {% load billing_extras %}
  {% payment_status paid total as ps %}
  {{ ps.percent|percent_display }} ({{ ps.remaining }})
"""

from django import template
from django.utils.translation import gettext as _

register = template.Library()


def _to_float(val, default=0.0):  # internal helper
    try:
        if val in (None, ""):
            return float(default)
        return float(val)
    except (TypeError, ValueError):
        return float(default)


@register.simple_tag
def remaining_amount(total, paid):
    """Return remaining amount (total - paid). Always >= 0."""
    t = _to_float(total)
    p = _to_float(paid)
    rem = t - p
    return rem if rem > 0 else 0


@register.filter
def paid_percent(value_tuple):
    """Given (paid,total) return percentage paid (0-100).
    Example: {{ paid|tuple_pair:total|paid_percent }}
    """
    try:
        paid, total = value_tuple
    except Exception:
        return 0
    t = _to_float(total)
    if t <= 0:
        return 0
    p = _to_float(paid)
    percent = (p / t) * 100
    if percent < 0:
        percent = 0
    if percent > 100:
        percent = 100
    # Keep two decimals for accuracy; presentation handled elsewhere
    return round(percent, 2)


@register.filter
def tuple_pair(paid, total):
    """Helper to build a tuple in template: {{ paid|tuple_pair:total|paid_percent }}"""
    return (paid, total)


@register.filter
def clamp_percent(value):
    """Clamp any numeric to 0-100 (useful when user inputs can exceed range)."""
    v = _to_float(value)
    if v < 0:
        return 0
    if v > 100:
        return 100
    return v


@register.filter
def percent_display(value, decimals=0):
    """Format a numeric percent value (already 0-100) with % sign.
    decimals: number of decimal places to keep (default 0).
    """
    v = _to_float(value)
    d = 0
    try:
        d = int(decimals)
    except Exception:
        d = 0
    fmt = f"{v:.{d}f}"
    if d == 0:
        # Remove .0 if present
        if "." in fmt:
            fmt = fmt.split(".")[0]
    return f"{fmt}%"


@register.simple_tag
def payment_status(paid, total):
    """Return a dict summarizing payment status.

    Keys:
      percent   -> float 0..100
      remaining -> float >=0
      overpaid  -> float (amount over total, 0 if not over)
      status    -> one of: paid, partial, unpaid, overpaid
    """
    t = _to_float(total)
    p = _to_float(paid)
    if t <= 0:
        percent = 0 if p <= 0 else 100  # if no total defined but paid present, treat as fully paid
    else:
        percent = (p / t) * 100 if p >= 0 else 0
    if percent < 0:
        percent = 0
    status = "unpaid"
    if p > t and t > 0:
        status = "overpaid"
    elif percent >= 100 and p >= t > 0:
        status = "paid"
    elif 0 < percent < 100:
        status = "partial"
    remaining = t - p
    overpaid = 0.0
    if remaining < 0:
        overpaid = abs(remaining)
        remaining = 0.0
    return {
        "percent": round(clamp_percent(percent), 2),
        "remaining": round(remaining, 2),
        "overpaid": round(overpaid, 2),
        "status": status,
    }


@register.inclusion_tag("includes/payment_status_badge.html")
def payment_status_badge(paid, total, show_progress=True, show_remaining=True, show_percent=True):
        """Render a payment status badge with optional progress bar and remaining amount.

        Parameters:
            paid, total: numeric (or coercible) values
            show_progress (bool): include progress bar (default True)
            show_remaining (bool): show remaining/overpaid amount (default True)
            show_percent (bool): show percentage paid (default True)

        Usage:
            {% load billing_extras %}
            {% payment_status_badge invoice.paid invoice.total %}
            {% payment_status_badge paid total False False True %}  # only percent
        """
        ps = payment_status(paid, total)
        return {
                "ps": ps,
                "show_progress": show_progress,
                "show_remaining": show_remaining,
                "show_percent": show_percent,
                "paid": paid,
                "total": total,
        }
