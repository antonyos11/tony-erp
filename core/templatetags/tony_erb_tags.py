"""
Template tags خاصة بنظام Tony ERB
"""
from django import template
from django.urls import reverse, NoReverseMatch
from users.models import user_has_permission
from django.utils.html import format_html
from django.forms.boundfield import BoundField
from typing import Any, Dict

register = template.Library()


@register.simple_tag
def user_has_perm(user, module, action):
    """فحص صلاحيات المستخدم"""
    if not user:
        return False
    # Handle case where user might be a string representation
    if isinstance(user, str):
        return False
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    return user_has_permission(user, module, action)


@register.simple_tag(takes_context=True)
def user_can_access_url(context, url_name, *args, **kwargs):
    """فحص إذا كان المستخدم يستطيع الوصول لرابط معين"""
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    
    try:
        # محاولة الحصول على URL
        url = reverse(url_name, args=args, kwargs=kwargs)
        
        # استخراج اسم الوحدة من URL
        if ':' in url_name:
            module = url_name.split(':')[0]
            return user_has_permission(request.user, module, 'view')
        
        return True
    except (NoReverseMatch, AttributeError):
        return False


@register.filter
def get_user_role_name(user):
    """الحصول على اسم دور المستخدم"""
    try:
        profile = user.get_profile()
        if profile and profile.role:
            return profile.role.get_name_display() or profile.role.display_name
        return "مستخدم"
    except:
        return "مستخدم"


@register.filter
def get_user_arabic_name(user):
    """الحصول على الاسم العربي للمستخدم"""
    try:
        profile = user.get_profile()
        if profile and profile.arabic_name:
            return profile.arabic_name
        return user.username
    except:
        return user.username


@register.inclusion_tag('core/user_menu.html', takes_context=True)
def user_menu(context):
    """قائمة المستخدم في الشريط العلوي"""
    request = context.get('request')
    return {
        'user': request.user if request else None,
        'request': request,
    }


@register.simple_tag
def system_version():
    """إرجاع رقم إصدار النظام"""
    return "2.0"


@register.simple_tag
def system_name():
    """إرجاع اسم النظام"""
    return "Tony ERB"


@register.filter
def permission_badge_class(permission_level):
    """تحديد كلاس Bootstrap للصلاحية"""
    badge_classes = {
        1: 'bg-secondary',  # عرض فقط
        2: 'bg-info',       # موظف
        3: 'bg-warning',    # مدير
        4: 'bg-success',    # مدير عام
        5: 'bg-danger',     # مدير شامل
    }
    return badge_classes.get(permission_level, 'bg-light')


@register.simple_tag
def get_module_icon(module_key):
    """إرجاع أيقونة الوحدة"""
    icons = {
        'accounting': 'bi-calculator',
        'inventory': 'bi-boxes',
        'sales': 'bi-cart-check',
        'purchases': 'bi-bag-plus',
        'hr': 'bi-people',
        'crm': 'bi-person-hearts',
        'production': 'bi-gear-wide-connected',
        'reports': 'bi-graph-up-arrow',
        'core': 'bi-gear',
        'partners': 'bi-handshake',
    }
    return icons.get(module_key, 'bi-app')


@register.filter
def can_approve_amount(user, amount):
    """فحص إذا كان المستخدم يستطيع الموافقة على مبلغ معين"""
    try:
        profile = user.get_profile()
        if profile:
            return profile.can_approve_amount(float(amount))
        return False
    except:
        return False


@register.inclusion_tag('core/breadcrumb.html', takes_context=True)
def breadcrumb(context, *items):
    """إنشاء مسار التنقل (breadcrumb)"""
    breadcrumb_items = []
    
    # إضافة الصفحة الرئيسية
    breadcrumb_items.append({
        'name': 'الرئيسية',
        'url': '/',
        'active': False
    })
    
    # إضافة العناصر المرسلة
    for i, item in enumerate(items):
        if isinstance(item, dict):
            breadcrumb_items.append({
                'name': item.get('name', ''),
                'url': item.get('url', '#'),
                'active': i == len(items) - 1
            })
        else:
            breadcrumb_items.append({
                'name': str(item),
                'url': '#',
                'active': i == len(items) - 1
            })
    
    return {
        'breadcrumb_items': breadcrumb_items
    }


@register.filter
def multiply(value, arg):
    """ضرب قيمتين"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """حساب النسبة المئوية"""
    try:
        if float(total) == 0:
            return 0
        return round((float(value) / float(total)) * 100, 2)
    except (ValueError, TypeError):
        return 0


# Generic number formatter with thousand separators and optional decimals
@register.filter(name='numfmt')
def number_format(value, decimal_places=0):
    """Format numbers with thousand separators.
    Usage: {{ value|numfmt }} or {{ value|numfmt:2 }} for two decimals.
    Returns '0' or '0.00' when value is falsy or invalid.
    """
    try:
        if value is None or value == "":
            value = 0
        n = float(value)
        dp = int(decimal_places) if decimal_places is not None else 0
        fmt = f"{n:,.{dp}f}"
        # Drop decimals if dp=0
        if dp == 0:
            # convert to int-like string without .0
            return f"{int(round(n)):,}"
        return fmt
    except Exception:
        return "0" if not decimal_places else ("0." + ("0" * int(decimal_places)))

# Generic dict/object getter for templates: {{ mapping|get:key }}
@register.filter(name='get')
def get_item(value, arg):
    """Template filter to get a key from dict-like or attribute from object.
    Usage: {{ mydict|get:key }}
    Returns empty string if missing.
    """
    try:
        if value is None:
            return ''
        # dict-like with get method
        if hasattr(value, 'get'):
            return value.get(arg, '')
        # mapping by key
        try:
            return value[arg]
        except Exception:
            pass
        # object attribute access
        return getattr(value, str(arg), '')
    except Exception:
        return ''

# Alias for get_item filter - for backwards compatibility
@register.filter(name='get_item')
def get_item_alias(value, arg):
    """Alias for get filter - Template filter to get a key from dict-like or attribute from object.
    Usage: {{ mydict|get_item:key }}
    Returns empty string if missing.
    """
    try:
        if value is None:
            return ''
        # dict-like with get method
        if hasattr(value, 'get'):
            return value.get(arg, '')
        # mapping by key
        try:
            return value[arg]
        except Exception:
            pass
        # object attribute access
        return getattr(value, str(arg), '')
    except Exception:
        return ''

@register.simple_tag
def is_rtl_language():
    """فحص إذا كانت اللغة من اليمين لليسار"""
    return True


# ---------------------------
# Form helpers
# ---------------------------
def _build_widget_attrs(widget, extra_class=None, extra_attrs=None):
    attrs = widget.attrs.copy()
    if extra_class:
        existing = attrs.get('class', '')
        if existing:
            attrs['class'] = existing + ' ' + str(extra_class)
        else:
            attrs['class'] = str(extra_class)
    if extra_attrs:
        try:
            for k, v in extra_attrs.items():
                attrs[str(k)] = v
        except Exception:
            # ignore invalid extra_attrs
            pass
    return attrs


@register.filter(name='add_class')
def add_class(field, css_classes):
    """Render a form field adding CSS classes safely in templates.
    Usage: {{ form.field|add_class:"form-control is-invalid" }}
    """
    try:
        if isinstance(field, BoundField):
            attrs: Dict[str, Any] = _build_widget_attrs(field.field.widget, extra_class=css_classes)
            return field.as_widget(attrs=attrs)  # type: ignore[arg-type]
        return field
    except Exception:
        return field


@register.filter(name='attr')
def add_attr(field, arg):
    """Render a form field adding arbitrary attributes from a comma-separated "key=value" string.
    Usage: {{ form.field|attr:"placeholder=اكتب هنا,dir=rtl" }}
    """
    try:
        if not isinstance(field, BoundField):
            return field
        extra: Dict[str, Any] = {}
        for part in [p for p in str(arg).split(',') if p.strip()]:
            if '=' in part:
                k, v = part.split('=', 1)
                extra[k.strip()] = v.strip()
        attrs: Dict[str, Any] = _build_widget_attrs(field.field.widget, extra_attrs=extra)
        return field.as_widget(attrs=attrs)  # type: ignore[arg-type]
    except Exception:
        return field


# ==========================================
# Template Tags للتعامل الآمن مع JSON
# ==========================================

import json
from django.utils.safestring import mark_safe


@register.filter(name='json_script_safe')
def json_script_safe(value, element_id=None):
    """
    تحويل البيانات إلى JSON بشكل آمن للاستخدام في JavaScript.
    بديل آمن لـ |safe مع البيانات.
    
    Usage in template:
        {{ data|json_script_safe:"chart-data" }}
        
    Then in JS:
        const data = JSON.parse(document.getElementById('chart-data').textContent);
    """
    try:
        json_str = json.dumps(value, ensure_ascii=False)
        # تشفير الأحرف الخطرة
        json_str = json_str.replace('</script>', '<\\/script>')
        json_str = json_str.replace('<!--', '<\\!--')
        
        if element_id:
            return mark_safe(
                f'<script id="{element_id}" type="application/json">{json_str}</script>'
            )
        return mark_safe(json_str)
    except (TypeError, ValueError) as e:
        import logging
        logging.getLogger(__name__).warning(f"خطأ في تحويل JSON: {e}")
        if element_id:
            return mark_safe(f'<script id="{element_id}" type="application/json">null</script>')
        return 'null'


@register.filter(name='escapejs_json')
def escapejs_json(value):
    """
    تحويل آمن لـ JSON للاستخدام في سمات HTML أو JavaScript inline.
    يُشفّر كل الأحرف الخطرة.
    
    Usage:
        <div data-config='{{ config|escapejs_json }}'></div>
        const data = {{ data|escapejs_json }};
    """
    try:
        json_str = json.dumps(value, ensure_ascii=False)
        # تشفير الأحرف الخطرة لـ HTML و JavaScript
        replacements = [
            ('&', '\\u0026'),
            ('<', '\\u003c'),
            ('>', '\\u003e'),
            ("'", '\\u0027'),
            ('"', '\\u0022'),
            ('/', '\\u002f'),
        ]
        for old, new in replacements:
            json_str = json_str.replace(old, new)
        return mark_safe(json_str)
    except (TypeError, ValueError):
        return 'null'


@register.simple_tag
def json_data(value, var_name):
    """
    إنشاء متغير JavaScript آمن من بيانات Python.
    
    Usage:
        {% json_data chart_data "chartData" %}
        // Now you can use chartData in JavaScript
    """
    try:
        json_str = json.dumps(value, ensure_ascii=False)
        # تأمين من XSS
        json_str = json_str.replace('</script>', '<\\/script>')
        json_str = json_str.replace('<!--', '<\\!--')
        return mark_safe(f'const {var_name} = {json_str};')
    except (TypeError, ValueError) as e:
        import logging
        logging.getLogger(__name__).warning(f"خطأ في json_data: {e}")
        return mark_safe(f'const {var_name} = null;')