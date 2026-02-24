from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def has_mod_perm(context, module: str, action: str) -> bool:
    request = context.get('request')
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return False
    try:
        return user.has_module_permission(module, action)
    except Exception:
        return False


@register.simple_tag(takes_context=True)
def has_res_perm(context, module: str, resource: str, action: str) -> bool:
    request = context.get('request')
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return False
    try:
        return user.has_resource_permission(module, resource, action)
    except Exception:
        return False
