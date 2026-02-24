from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def money(value, places=2):
    try:
        if value is None:
            return ''
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        q = Decimal(10) ** -int(places)
        return f"{value.quantize(q):,.{places}f}".replace(',', '٬')
    except Exception:
        return value
