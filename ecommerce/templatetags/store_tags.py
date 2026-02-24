"""
Template tags للمتجر الإلكتروني
"""
from django import template
from ecommerce.models import EcommerceSettings

register = template.Library()


@register.simple_tag
def get_store_settings():
    """الحصول على إعدادات المتجر"""
    return EcommerceSettings.get_settings()
