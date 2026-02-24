"""
Core Security Package
نظام الأمان والصلاحيات الموحد
"""

from .permissions_service import (
    PermissionService,
    user_can,
    require_permission,
    check_approval_authority,
    get_user_max_approval_amount,
    get_user_max_discount_percentage,
)

from . import role_definitions as rd
from .role_definitions import *  # re-export all role constants and helpers

__all__ = [
    'PermissionService',
    'user_can',
    'require_permission',
    'check_approval_authority',
    'get_user_max_approval_amount',
    'get_user_max_discount_percentage',
]

# أضف كل الثوابت والدوال المساعدة من role_definitions إلى __all__
__all__ += [
    name for name in dir(rd)
    if name.isupper() or name.startswith(('get_', 'is_', 'can_'))
]



