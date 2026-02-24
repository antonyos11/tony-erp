"""
Menu Template Tags
وسوم القوالب للقوائم الديناميكية
"""

from django import template
from django.contrib.auth.models import User

from core.navigation import MenuEngine

register = template.Library()


@register.simple_tag(takes_context=True)
def get_main_menu(context):
    """
    الحصول على القائمة الرئيسية للمستخدم الحالي
    
    الاستخدام:
        {% load menu_tags %}
        {% get_main_menu as main_menu %}
        
        {% for item in main_menu %}
            <li>{{ item.label }}</li>
        {% endfor %}
    """
    request = context.get('request')
    if not request or not request.user:
        return []
    
    return MenuEngine.get_menu_for_user(request.user)


@register.simple_tag(takes_context=True)
def get_quick_actions(context):
    """
    الحصول على الإجراءات السريعة للمستخدم
    
    الاستخدام:
        {% load menu_tags %}
        {% get_quick_actions as actions %}
    """
    request = context.get('request')
    if not request or not request.user:
        return []
    
    return MenuEngine.get_quick_actions(request.user)


@register.simple_tag(takes_context=True)
def get_breadcrumbs(context):
    """
    الحصول على breadcrumbs للصفحة الحالية
    
    الاستخدام:
        {% load menu_tags %}
        {% get_breadcrumbs as breadcrumbs %}
    """
    request = context.get('request')
    if not request or not request.user:
        return []
    
    current_path = request.path
    return MenuEngine.get_breadcrumbs(request.user, current_path)


@register.inclusion_tag('components/main_menu.html', takes_context=True)
def render_main_menu(context):
    """
    رندر القائمة الرئيسية كاملة
    
    الاستخدام:
        {% load menu_tags %}
        {% render_main_menu %}
    """
    request = context.get('request')
    menu = []
    
    if request and request.user:
        menu = MenuEngine.get_menu_for_user(request.user)
    
    return {
        'menu': menu,
        'request': request,
    }


@register.inclusion_tag('components/quick_actions.html', takes_context=True)
def render_quick_actions(context):
    """
    رندر الإجراءات السريعة
    
    الاستخدام:
        {% load menu_tags %}
        {% render_quick_actions %}
    """
    request = context.get('request')
    actions = []
    
    if request and request.user:
        actions = MenuEngine.get_quick_actions(request.user)
    
    return {
        'actions': actions,
        'request': request,
    }


@register.filter
def has_children(menu_item):
    """
    فحص إذا كان بند القائمة لديه بنود فرعية
    
    الاستخدام:
        {% if item|has_children %}
    """
    return 'children' in menu_item and len(menu_item.get('children', [])) > 0


@register.filter
def is_active(menu_item, current_path):
    """
    فحص إذا كان بند القائمة نشط (الصفحة الحالية)
    
    الاستخدام:
        {% if item|is_active:request.path %}
    """
    item_url = menu_item.get('url_resolved', '')
    
    if not item_url or item_url == '#':
        return False
    
    return current_path.startswith(item_url)


