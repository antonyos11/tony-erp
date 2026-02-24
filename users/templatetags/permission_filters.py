"""
Template filters for permissions matrix
فلاتر القوالب لمصفوفة الصلاحيات
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    الوصول لعنصر في قاموس
    
    الاستخدام:
        {{ my_dict|get_item:'key' }}
    """
    if dictionary is None:
        return None
    
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    
    return None


@register.filter
def get_attr(obj, attr_name):
    """
    الوصول لخاصية في كائن
    
    الاستخدام:
        {{ my_obj|get_attr:'attribute' }}
    """
    if obj is None:
        return None
    
    try:
        return getattr(obj, attr_name, None)
    except:
        return None


