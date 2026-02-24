"""
Template tags إضافية للمستخدمين
"""
from django import template

register = template.Library()


@register.filter
def lookup(dict_obj, key):
    """البحث في القاموس باستخدام مفتاح"""
    if dict_obj is None:
        return None
    try:
        return dict_obj.get(key)
    except (AttributeError, KeyError):
        return None


@register.filter
def get_permission(permissions, role_module_action):
    """الحصول على صلاحية محددة"""
    try:
        role_id, module, action = role_module_action.split('|')
        return permissions.get(int(role_id), {}).get(module, {}).get(action, False)
    except (ValueError, AttributeError):
        return False


@register.simple_tag
def permission_class(is_allowed):
    """فئة CSS للصلاحية"""
    return 'permission-allowed' if is_allowed else 'permission-denied'


@register.simple_tag
def permission_icon(is_allowed):
    """أيقونة الصلاحية"""
    return 'bi-check-circle-fill text-success' if is_allowed else 'bi-x-circle-fill text-danger'


@register.filter
def count_role_permissions(permissions, role_id):
    """عد الصلاحيات المسموحة للدور"""
    try:
        role_perms = permissions.get(role_id, {})
        count = 0
        for module_perms in role_perms.values():
            for is_allowed in module_perms.values():
                if is_allowed:
                    count += 1
        return count
    except (AttributeError, KeyError):
        return 0


@register.filter
def percentage(value, total):
    """حساب النسبة المئوية"""
    try:
        if int(total) == 0:
            return 0
        return round((int(value) / int(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0