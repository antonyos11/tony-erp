"""
White Label System
نظام العلامة البيضاء

يسمح بتخصيص كامل للنظام لكل عميل (SaaS)
"""

from .models import Tenant, TenantBranding, TenantSettings
from .middleware import TenantMiddleware
from .utils import get_current_tenant, get_tenant_from_domain

__all__ = [
    'Tenant',
    'TenantBranding',
    'TenantSettings',
    'TenantMiddleware',
    'get_current_tenant',
    'get_tenant_from_domain',
]
