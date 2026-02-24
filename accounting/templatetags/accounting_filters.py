"""
فلاتر Django بديلة لفلاتر Jinja2 (selectattr, rejectattr, groupby, إلخ)
تضمن التوافق مع القوالب المنقولة من Jinja2
"""
from django import template
from decimal import Decimal
from itertools import groupby as itertools_groupby

register = template.Library()


@register.filter(name='selectattr')
def selectattr_filter(value, args):
    """
    بديل Django لفلتر Jinja2 selectattr
    الاستخدام: {{ items|selectattr:"attr_name,value" }}
    أو: {{ items|selectattr:"attr_name" }}  (فلترة بناءً على truthiness)
    """
    if not value:
        return []

    try:
        parts = args.split(',', 1)
        attr_name = parts[0].strip()

        if len(parts) > 1:
            attr_value = parts[1].strip()
            result = []
            for item in value:
                item_val = getattr(item, attr_name, None)
                if item_val is None:
                    continue
                if str(item_val) == attr_value or item_val == attr_value:
                    result.append(item)
                elif attr_value.lower() in ('true', 'false'):
                    if bool(item_val) == (attr_value.lower() == 'true'):
                        result.append(item)
            return result
        else:
            return [item for item in value if getattr(item, attr_name, None)]
    except Exception:
        return list(value) if value else []


@register.filter(name='rejectattr')
def rejectattr_filter(value, args):
    """
    بديل Django لفلتر Jinja2 rejectattr
    الاستخدام: {{ items|rejectattr:"attr_name,value" }}
    """
    if not value:
        return []

    try:
        parts = args.split(',', 1)
        attr_name = parts[0].strip()

        if len(parts) > 1:
            attr_value = parts[1].strip()
            result = []
            for item in value:
                item_val = getattr(item, attr_name, None)
                if item_val is None or str(item_val) != attr_value:
                    result.append(item)
            return result
        else:
            return [item for item in value if not getattr(item, attr_name, None)]
    except Exception:
        return list(value) if value else []


@register.filter(name='map_attr')
def map_attr_filter(value, attr_name):
    """
    بديل Django لفلتر Jinja2 map(attribute=...)
    الاستخدام: {{ items|map_attr:"name" }}
    """
    if not value:
        return []
    return [getattr(item, attr_name, '') for item in value]


@register.filter(name='sum_attr')
def sum_attr_filter(value, attr_name):
    """
    جمع قيمة attribute معين من قائمة objects
    الاستخدام: {{ items|sum_attr:"amount" }}
    """
    if not value:
        return 0
    total = Decimal('0')
    for item in value:
        val = getattr(item, attr_name, 0)
        if val is not None:
            try:
                total += Decimal(str(val))
            except Exception:
                pass
    return total


@register.filter(name='groupby_attr')
def groupby_filter(value, attr_name):
    """
    بديل Django لفلتر Jinja2 groupby
    الاستخدام: {% for group in items|groupby_attr:"category" %}
    """
    if not value:
        return []

    sorted_items = sorted(value, key=lambda x: str(getattr(x, attr_name, '')))
    groups = []
    for key, group in itertools_groupby(sorted_items, key=lambda x: getattr(x, attr_name, '')):
        groups.append({
            'grouper': key,
            'list': list(group),
        })
    return groups


@register.filter(name='currency')
def currency_filter(value, symbol='ر.س'):
    """
    تنسيق المبالغ المالية
    الاستخدام: {{ amount|currency }} أو {{ amount|currency:"$" }}
    """
    try:
        val = Decimal(str(value))
        formatted = f'{val:,.2f}'
        return f'{formatted} {symbol}'
    except Exception:
        return f'0.00 {symbol}'


@register.filter(name='percentage')
def percentage_filter(value, decimals=1):
    """
    تنسيق كنسبة مئوية
    الاستخدام: {{ ratio|percentage }} أو {{ ratio|percentage:2 }}
    """
    try:
        val = float(value)
        return f'{val:.{int(decimals)}f}%'
    except Exception:
        return '0.0%'
