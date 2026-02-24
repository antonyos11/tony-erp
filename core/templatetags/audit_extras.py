import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='pretty_json')
def pretty_json(value):
    try:
        # value may be a dict or string; try to ensure dict first
        if isinstance(value, str):
            try:
                data = json.loads(value)
            except Exception:
                data = value
        else:
            data = value
        if isinstance(data, (dict, list)):
            return mark_safe(json.dumps(data, ensure_ascii=False, indent=2))
        return value
    except Exception:
        return value
