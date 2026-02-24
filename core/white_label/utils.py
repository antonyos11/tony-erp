"""
White Label Utilities
أدوات نظام العلامة البيضاء

وظائف مساعدة للوصول للمستأجر الحالي
"""

import threading
from typing import Optional
from .models import Tenant, TenantDomain

# Thread-local storage
_thread_locals = threading.local()


def get_current_tenant() -> Optional[Tenant]:
    """
    الحصول على المستأجر الحالي
    
    Returns:
        المستأجر الحالي أو None
    """
    return getattr(_thread_locals, 'tenant', None)


def set_current_tenant(tenant: Tenant):
    """
    تعيين المستأجر الحالي
    
    Args:
        tenant: المستأجر المراد تعيينه
    """
    _thread_locals.tenant = tenant


def clear_current_tenant():
    """مسح المستأجر الحالي"""
    if hasattr(_thread_locals, 'tenant'):
        delattr(_thread_locals, 'tenant')


def get_tenant_from_domain(domain: str) -> Optional[Tenant]:
    """
    الحصول على المستأجر من النطاق
    
    Args:
        domain: النطاق
        
    Returns:
        المستأجر أو None
    """
    try:
        tenant_domain = TenantDomain.objects.select_related('tenant').get(
            domain=domain,
            is_active=True
        )
        return tenant_domain.tenant
    except TenantDomain.DoesNotExist:
        return None


def get_tenant_from_slug(slug: str) -> Optional[Tenant]:
    """
    الحصول على المستأجر من slug
    
    Args:
        slug: معرف المستأجر
        
    Returns:
        المستأجر أو None
    """
    try:
        return Tenant.objects.get(slug=slug, is_active=True)
    except Tenant.DoesNotExist:
        return None


def is_feature_enabled(feature_name: str) -> bool:
    """
    التحقق من تفعيل ميزة للمستأجر الحالي
    
    Args:
        feature_name: اسم الميزة
        
    Returns:
        True إذا كانت مفعلة
    """
    tenant = get_current_tenant()
    if not tenant:
        return False
    
    return tenant.is_module_enabled(feature_name)


def get_tenant_setting(key: str, default=None):
    """
    الحصول على إعداد للمستأجر الحالي
    
    Args:
        key: مفتاح الإعداد
        default: القيمة الافتراضية
        
    Returns:
        قيمة الإعداد
    """
    tenant = get_current_tenant()
    if not tenant:
        return default
    
    try:
        return tenant.settings.get_setting(key, default)
    except:
        return default


def get_branding():
    """
    الحصول على العلامة التجارية للمستأجر الحالي
    
    Returns:
        TenantBranding أو None
    """
    tenant = get_current_tenant()
    if not tenant:
        return None
    
    try:
        return tenant.branding
    except:
        return None


class TenantAwareQuerySet:
    """
    QuerySet يدعم عزل البيانات للمستأجر
    
    يمكن استخدامه كـ Manager مخصص للنماذج
    """
    
    def get_queryset(self):
        """تصفية حسب المستأجر الحالي"""
        qs = super().get_queryset()
        tenant = get_current_tenant()
        
        if tenant and hasattr(self.model, 'tenant'):
            qs = qs.filter(tenant=tenant)
        
        return qs


def tenant_context_processor(request):
    """
    Context processor للقوالب
    
    يضيف معلومات المستأجر والثيم للقوالب
    
    إضافته في settings.py:
    TEMPLATES[0]['OPTIONS']['context_processors'].append(
        'core.white_label.utils.tenant_context_processor'
    )
    """
    tenant = getattr(request, 'tenant', None)
    branding = getattr(request, 'branding', None)
    settings = getattr(request, 'tenant_settings', None)
    
    context = {
        'tenant': tenant,
        'branding': branding,
        'tenant_settings': settings,
    }
    
    # إضافة متغيرات الثيم
    if branding:
        context['theme'] = {
            'primary_color': branding.primary_color,
            'secondary_color': branding.secondary_color,
            'accent_color': branding.accent_color,
            'background_color': branding.background_color,
            'text_color': branding.text_color,
            'font_family': branding.font_family,
            'logo_url': branding.get_logo_url(),
            'app_title': branding.get_app_title(),
        }
    
    return context


def validate_tenant_limits(tenant: Tenant) -> dict:
    """
    التحقق من حدود الاستخدام للمستأجر
    
    Args:
        tenant: المستأجر
        
    Returns:
        dict مع معلومات الاستخدام والحدود
    """
    from django.contrib.auth.models import User
    from branches.models import Branch
    from inventory.models import Product
    
    usage = tenant.get_usage_stats()
    
    return {
        'users': {
            'current': usage['users'],
            'limit': tenant.max_users,
            'exceeded': usage['users'] >= tenant.max_users
        },
        'branches': {
            'current': usage['branches'],
            'limit': tenant.max_branches,
            'exceeded': usage['branches'] >= tenant.max_branches
        },
        'products': {
            'current': usage['products'],
            'limit': tenant.max_products,
            'exceeded': usage['products'] >= tenant.max_products
        }
    }


def can_add_user(tenant: Tenant) -> bool:
    """التحقق من إمكانية إضافة مستخدم"""
    limits = validate_tenant_limits(tenant)
    return not limits['users']['exceeded']


def can_add_branch(tenant: Tenant) -> bool:
    """التحقق من إمكانية إضافة فرع"""
    limits = validate_tenant_limits(tenant)
    return not limits['branches']['exceeded']


def can_add_product(tenant: Tenant) -> bool:
    """التحقق من إمكانية إضافة منتج"""
    limits = validate_tenant_limits(tenant)
    return not limits['products']['exceeded']
