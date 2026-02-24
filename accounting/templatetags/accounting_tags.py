"""
Template tags وfilters للمحاسبة
"""
from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    الوصول إلى عنصر في قاموس باستخدام مفتاح
    الاستخدام: {{ my_dict|get_item:"key_name" }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter(name='has_badge')
def has_badge(badges, badge_key):
    """
    التحقق من وجود قيمة للشارة
    """
    if not badges or not badge_key:
        return False
    value = badges.get(badge_key)
    return value is not None and value > 0
