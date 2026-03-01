"""
Template tags للصلاحيات — RITA ERP
"""
from django import template
from apps.authorization.services.permission_engine import PermissionEngine

register = template.Library()


@register.simple_tag(takes_context=True)
def has_perm(context, module, action):
    """التحقق من صلاحية في الـ template"""
    request = context.get('request')
    if not request or not request.user or not request.user.is_authenticated:
        return False
    return PermissionEngine.has_permission(request.user, module, action)


@register.simple_tag(takes_context=True)
def user_can_see_cost(context):
    """هل المستخدم يقدر يشوف التكلفة"""
    request = context.get('request')
    if not request or not request.user:
        return False
    return PermissionEngine.can_see_cost(request.user)


@register.simple_tag(takes_context=True)
def user_can_see_profit(context):
    """هل المستخدم يقدر يشوف الأرباح"""
    request = context.get('request')
    if not request or not request.user:
        return False
    return PermissionEngine.can_see_profit(request.user)


@register.simple_tag(takes_context=True)
def user_max_discount(context):
    """أقصى نسبة خصم"""
    request = context.get('request')
    if not request or not request.user:
        return 0
    return PermissionEngine.get_max_discount(request.user)
