"""
Fine-Grained Permission Template Tags
وسوم القوالب للصلاحيات التفصيلية
"""

from django import template
from django.contrib.auth.models import User

from core.security.fine_grained_permissions import FineGrainedPermissionService

register = template.Library()


@register.simple_tag(takes_context=True)
def can_view_field(context, page_id, field_name):
    """
    فحص إذا المستخدم يستطيع رؤية حقل
    
    الاستخدام:
        {% can_view_field 'product_detail' 'cost_price' as can_view_cost %}
        {% if can_view_cost %}
            <div>السعر: {{ product.cost_price }}</div>
        {% endif %}
    """
    request = context.get('request')
    if not request or not request.user or not request.user.is_authenticated:
        return False
    
    return FineGrainedPermissionService.can_view_field(request.user, page_id, field_name)


@register.simple_tag(takes_context=True)
def can_edit_field(context, page_id, field_name):
    """
    فحص إذا المستخدم يستطيع تعديل حقل
    
    الاستخدام:
        {% can_edit_field 'product_detail' 'cost_price' as can_edit_cost %}
        {% if can_edit_cost %}
            <input name="cost_price" value="{{ product.cost_price }}">
        {% else %}
            <span>{{ product.cost_price }}</span>
        {% endif %}
    """
    request = context.get('request')
    if not request or not request.user or not request.user.is_authenticated:
        return False
    
    return FineGrainedPermissionService.can_edit_field(request.user, page_id, field_name)


@register.simple_tag(takes_context=True)
def can_view_section(context, page_id, section_id):
    """
    فحص إذا المستخدم يستطيع رؤية قسم
    
    الاستخدام:
        {% can_view_section 'product_detail' 'financial_info' as can_view_financial %}
        {% if can_view_financial %}
            <div class="financial-section">
                ...
            </div>
        {% endif %}
    """
    request = context.get('request')
    if not request or not request.user or not request.user.is_authenticated:
        return False
    
    return FineGrainedPermissionService.can_view_section(request.user, page_id, section_id)


@register.simple_tag(takes_context=True)
def can_execute_action(context, page_id, action_id):
    """
    فحص إذا المستخدم يستطيع تنفيذ عملية
    
    الاستخدام:
        {% can_execute_action 'invoice_detail' 'delete' as can_delete %}
        {% if can_delete %}
            <button class="btn-danger">حذف</button>
        {% endif %}
    """
    request = context.get('request')
    if not request or not request.user or not request.user.is_authenticated:
        return False
    
    can, _ = FineGrainedPermissionService.can_execute_action(request.user, page_id, action_id)
    return can


@register.inclusion_tag('components/conditional_field.html', takes_context=True)
def render_field(context, page_id, field_name, label, value, field_type='text'):
    """
    رندر حقل بناءً على الصلاحيات
    
    الاستخدام:
        {% render_field 'product_detail' 'cost_price' 'سعر التكلفة' product.cost_price 'currency' %}
    """
    request = context.get('request')
    can_view = False
    can_edit = False
    
    if request and request.user and request.user.is_authenticated:
        can_view = FineGrainedPermissionService.can_view_field(request.user, page_id, field_name)
        can_edit = FineGrainedPermissionService.can_edit_field(request.user, page_id, field_name)
    
    return {
        'can_view': can_view,
        'can_edit': can_edit,
        'field_name': field_name,
        'label': label,
        'value': value,
        'field_type': field_type,
    }


@register.inclusion_tag('components/conditional_section.html', takes_context=True)
def render_section(context, page_id, section_id, title):
    """
    رندر قسم بناءً على الصلاحيات
    
    الاستخدام:
        {% render_section 'product_detail' 'financial_info' 'المعلومات المالية' %}
            <div>المحتوى هنا</div>
        {% end_render_section %}
    """
    request = context.get('request')
    can_view = False
    
    if request and request.user and request.user.is_authenticated:
        can_view = FineGrainedPermissionService.can_view_section(request.user, page_id, section_id)
    
    return {
        'can_view': can_view,
        'section_id': section_id,
        'title': title,
    }


@register.inclusion_tag('components/action_button.html', takes_context=True)
def render_action_button(context, page_id, action_id, label, url='#', btn_class='btn-primary', icon=''):
    """
    رندر زر عملية بناءً على الصلاحيات
    
    الاستخدام:
        {% render_action_button 'invoice_detail' 'delete' 'حذف' invoice_delete_url 'btn-danger' 'fa-trash' %}
    """
    request = context.get('request')
    can_execute = False
    message = ''
    
    if request and request.user and request.user.is_authenticated:
        can_execute, message = FineGrainedPermissionService.can_execute_action(
            request.user, page_id, action_id
        )
    
    return {
        'can_execute': can_execute,
        'action_id': action_id,
        'label': label,
        'url': url,
        'btn_class': btn_class,
        'icon': icon,
        'message': message,
    }


@register.filter
def field_visible(page_id, field_name):
    """
    فلتر للفحص السريع
    
    الاستخدام:
        {% if 'product_detail'|field_visible:'cost_price' %}
    """
    # Note: لا يمكن الحصول على request في filter، استخدم simple_tag بدلاً منه
    return True


@register.simple_tag(takes_context=True)
def get_visible_fields(context, page_id):
    """
    الحصول على قائمة الحقول المرئية
    
    الاستخدام:
        {% get_visible_fields 'product_detail' as visible_fields %}
        {% for field in visible_fields %}
            {{ field }}
        {% endfor %}
    """
    request = context.get('request')
    if not request or not request.user or not request.user.is_authenticated:
        return []
    
    config = FineGrainedPermissionService.get_page_config(page_id)
    if not config:
        return []
    
    return config.get_visible_fields(request.user)


@register.simple_tag(takes_context=True)
def get_available_actions(context, page_id):
    """
    الحصول على العمليات المتاحة
    
    الاستخدام:
        {% get_available_actions 'invoice_detail' as available_actions %}
        {% for action in available_actions %}
            <button>{{ action.label }}</button>
        {% endfor %}
    """
    request = context.get('request')
    if not request or not request.user or not request.user.is_authenticated:
        return []
    
    config = FineGrainedPermissionService.get_page_config(page_id)
    if not config:
        return []
    
    return config.get_available_actions(request.user)


