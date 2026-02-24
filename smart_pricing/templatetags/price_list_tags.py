"""
Template tags for Price List
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    if hasattr(dictionary, '__getitem__'):
        try:
            return dictionary[key]
        except (KeyError, IndexError):
            return None
    return None


@register.filter
def size_key(size):
    """Generate size key from size object"""
    if hasattr(size, 'width') and hasattr(size, 'length'):
        return f"{size.width}x{size.length}"
    return str(size)


@register.filter
def get_price(prices, size):
    """Get price from prices dict using size object"""
    if not prices:
        return None
    key = f"{size.width}x{size.length}"
    return prices.get(key)


@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """Divide value by arg"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Calculate percentage"""
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0


@register.filter
def format_price(value):
    """Format price with comma separator"""
    try:
        return "{:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return value


@register.simple_tag
def size_price(prices_dict, width, length):
    """Get price for a specific size"""
    size_key = f"{width}x{length}"
    if prices_dict and hasattr(prices_dict, 'get'):
        return prices_dict.get(size_key, {}).get('price', '-')
    return '-'
