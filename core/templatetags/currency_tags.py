from django import template
from django.utils.safestring import mark_safe
from core.models import Currency

register = template.Library()


@register.simple_tag
def currency_symbol():
    """إرجاع رمز العملة الافتراضية"""
    currency = Currency.get_default()
    return currency.symbol if currency else 'ج.م'


@register.simple_tag 
def currency_name():
    """إرجاع اسم العملة الافتراضية"""
    currency = Currency.get_default()
    return currency.name if currency else 'جنيه مصري'


@register.filter
def currency_format(value, decimal_places=2):
    """تنسيق المبلغ مع العملة"""
    currency = Currency.get_default()
    symbol = currency.symbol if currency else 'ج.م'
    
    if not value:
        return f"0.00 {symbol}"
    
    try:
        # تحويل إلى float
        amount = float(value)
        # تنسيق الرقم بالفواصل
        formatted_number = f"{amount:,.{decimal_places}f}"
        # إضافة رمز العملة
        return mark_safe(f"{formatted_number} {symbol}")
    except (ValueError, TypeError):
        return f"0.00 {symbol}"


@register.filter(name='currency')
def currency_alias(value):
    """مرشح متوافق للاسم القديم {{ value|currency }} يعتمد على currency_format."""
    return currency_format(value)


@register.filter
def currency_format_short(value):
    """تنسيق المبلغ مع العملة (بدون منازل عشرية إذا كان رقم صحيح)"""
    currency = Currency.get_default()
    symbol = currency.symbol if currency else 'ج.م'
    
    if not value:
        return f"0 {symbol}"
    
    try:
        amount = float(value)
        if amount == int(amount):
            formatted_number = f"{int(amount):,}"
        else:
            formatted_number = f"{amount:,.2f}"
        return mark_safe(f"{formatted_number} {symbol}")
    except (ValueError, TypeError):
        return f"0 {symbol}"


@register.inclusion_tag('core/currency_selector.html')
def currency_selector():
    """سيلكتور لاختيار العملة"""
    return {
        'currencies': Currency.objects.filter(is_active=True),
        'current_currency': Currency.get_default()
    }


@register.filter(name='sub')
def subtract_simple(value, arg):
    """طرح رقمين داخل القوالب: {{ a|sub:b }}. يرجع 0 عند الخطأ."""
    try:
        return float(value) - float(arg)
    except (TypeError, ValueError):
        return 0


@register.filter(name='div')
def divide_simple(value, arg):
    """قسمة رقمين داخل القوالب: {{ a|div:b }}. يرجع 0 عند الخطأ أو القسمة على صفر."""
    try:
        denominator = float(arg)
        if denominator == 0:
            return 0
        return float(value) / denominator
    except (TypeError, ValueError):
        return 0