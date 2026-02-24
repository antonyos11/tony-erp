"""
خدمة الصلاحيات الموحدة
Unified Permissions Service

هذه الطبقة توفر واجهة موحدة للتعامل مع الصلاحيات في كل أنحاء النظام.
استخدم هذه الطبقة بدلاً من التعامل المباشر مع Models أو Middleware.
"""

from typing import Optional, Any, Callable
from functools import wraps
from decimal import Decimal

from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.core.cache import cache

from .role_definitions import (
    get_default_approval_limit,
    get_default_discount_limit,
    get_approval_level,
)


class PermissionService:
    """
    خدمة مركزية للتعامل مع الصلاحيات
    
    أمثلة الاستخدام:
    
    # فحص صلاحية وحدة
    if PermissionService.can_view(user, 'sales'):
        # عرض البيانات
        
    # فحص صلاحية عملية
    if PermissionService.can_add(user, 'inventory'):
        # إضافة صنف جديد
        
    # فحص صلاحية مورد محدد
    if PermissionService.can_access_resource(user, 'sales', 'invoice_create', 'add'):
        # إنشاء فاتورة
        
    # فحص سلطة الموافقة على مبلغ
    if PermissionService.can_approve_amount(user, amount):
        # اعتماد العملية
    """
    
    # Cache timeout in seconds (5 minutes)
    CACHE_TIMEOUT = 300
    
    @staticmethod
    def _get_cache_key(user_id: int, cache_type: str, *args) -> str:
        """إنشاء مفتاح cache للصلاحيات"""
        args_str = '_'.join(str(arg) for arg in args)
        return f"perm_{cache_type}_{user_id}_{args_str}"
    
    @staticmethod
    def clear_user_cache(user: User) -> None:
        """مسح cache الصلاحيات لمستخدم معين"""
        # في حالة تغيير الأدوار أو الصلاحيات
        cache_pattern = f"perm_*_{user.id}_*"
        # Note: Django cache doesn't support pattern deletion directly
        # في بيئة إنتاج مع Redis، استخدم:
        # cache.delete_pattern(cache_pattern)
        pass
    
    @staticmethod
    def _get_user_profile(user: User):
        """الحصول على ملف تعريف المستخدم مع cache"""
        if not user or not user.is_authenticated:
            return None
        
        cache_key = PermissionService._get_cache_key(user.id, 'profile')
        profile = cache.get(cache_key)
        
        if profile is None:
            try:
                profile = user.profile
                cache.set(cache_key, profile, PermissionService.CACHE_TIMEOUT)
            except Exception:
                return None
        
        return profile
    
    # ========================================================================
    # Module-Level Permissions (صلاحيات على مستوى الوحدة)
    # ========================================================================
    
    @staticmethod
    def has_module_permission(user: User, module: str, action: str) -> bool:
        """
        فحص صلاحية على مستوى الوحدة
        
        Args:
            user: المستخدم
            module: الوحدة (مثل 'sales', 'inventory', 'accounting')
            action: العملية (مثل 'view', 'add', 'change', 'delete', 'approve')
        
        Returns:
            True إذا كان المستخدم لديه الصلاحية
        """
        if not user or not user.is_authenticated:
            return False
        
        # Super admin لديه كل الصلاحيات
        if user.is_superuser:
            return True
        
        # استخدام الدالة الموجودة في User model
        try:
            return user.has_module_permission(module, action)
        except Exception:
            return False
    
    @staticmethod
    def can_view(user: User, module: str) -> bool:
        """فحص صلاحية العرض"""
        return PermissionService.has_module_permission(user, module, 'view')
    
    @staticmethod
    def can_add(user: User, module: str) -> bool:
        """فحص صلاحية الإضافة"""
        return PermissionService.has_module_permission(user, module, 'add')
    
    @staticmethod
    def can_change(user: User, module: str) -> bool:
        """فحص صلاحية التعديل"""
        return PermissionService.has_module_permission(user, module, 'change')
    
    @staticmethod
    def can_delete(user: User, module: str) -> bool:
        """فحص صلاحية الحذف"""
        return PermissionService.has_module_permission(user, module, 'delete')
    
    @staticmethod
    def can_approve(user: User, module: str) -> bool:
        """فحص صلاحية الاعتماد"""
        return PermissionService.has_module_permission(user, module, 'approve')
    
    @staticmethod
    def can_print(user: User, module: str) -> bool:
        """فحص صلاحية الطباعة"""
        return PermissionService.has_module_permission(user, module, 'print')
    
    @staticmethod
    def can_export(user: User, module: str) -> bool:
        """فحص صلاحية التصدير"""
        return PermissionService.has_module_permission(user, module, 'export')
    
    # ========================================================================
    # Resource-Level Permissions (صلاحيات على مستوى المورد/الشاشة)
    # ========================================================================
    
    @staticmethod
    def has_resource_permission(user: User, module: str, resource: str, action: str) -> bool:
        """
        فحص صلاحية تفصيلية على مستوى مورد معين
        
        Args:
            user: المستخدم
            module: الوحدة
            resource: المورد/الشاشة (مثل 'invoice_create', 'product_list')
            action: العملية
        
        Returns:
            True إذا كان المستخدم لديه الصلاحية
        """
        if not user or not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        try:
            return user.has_resource_permission(module, resource, action)
        except Exception:
            # Fallback إلى صلاحية الوحدة
            return PermissionService.has_module_permission(user, module, action)
    
    @staticmethod
    def can_access_resource(user: User, module: str, resource: str, action: str = 'view') -> bool:
        """
        اختصار للوصول لمورد معين
        """
        return PermissionService.has_resource_permission(user, module, resource, action)
    
    # ========================================================================
    # Role Checking (فحص الأدوار)
    # ========================================================================
    
    @staticmethod
    def has_role(user: User, role_name: str) -> bool:
        """
        فحص إذا كان المستخدم لديه دور معين
        
        Args:
            user: المستخدم
            role_name: كود الدور (استخدم الثوابت من role_definitions)
        
        Returns:
            True إذا كان المستخدم لديه الدور
        """
        if not user or not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        profile = PermissionService._get_user_profile(user)
        if not profile:
            return False
        
        try:
            return profile.has_role(role_name)
        except Exception:
            return False
    
    @staticmethod
    def get_user_roles(user: User) -> list:
        """
        الحصول على جميع أدوار المستخدم
        
        Returns:
            قائمة بكائنات UserRole
        """
        if not user or not user.is_authenticated:
            return []
        
        profile = PermissionService._get_user_profile(user)
        if not profile:
            return []
        
        try:
            return profile.get_all_roles()
        except Exception:
            return []
    
    @staticmethod
    def is_manager(user: User) -> bool:
        """فحص إذا كان المستخدم في منصب إداري"""
        from .role_definitions import is_manager_role
        
        roles = PermissionService.get_user_roles(user)
        return any(is_manager_role(role.name) for role in roles)
    
    # ========================================================================
    # Approval Authority (سلطة الموافقة)
    # ========================================================================
    
    @staticmethod
    def can_approve_amount(user: User, amount: Decimal | float) -> bool:
        """
        فحص إذا كان المستخدم يستطيع الموافقة على مبلغ معين
        
        Args:
            user: المستخدم
            amount: المبلغ المطلوب الموافقة عليه
        
        Returns:
            True إذا كان المستخدم لديه السلطة للموافقة
        """
        if not user or not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        max_amount = PermissionService.get_max_approval_amount(user)
        
        # None تعني بدون حدود
        if max_amount is None:
            return True
        
        return Decimal(str(amount)) <= Decimal(str(max_amount))
    
    @staticmethod
    def get_max_approval_amount(user: User) -> Decimal | None:
        """
        الحصول على أقصى مبلغ يستطيع المستخدم اعتماده
        
        Returns:
            المبلغ أو None (بدون حدود)
        """
        if not user or not user.is_authenticated:
            return Decimal('0')
        
        if user.is_superuser:
            return None  # بدون حدود
        
        profile = PermissionService._get_user_profile(user)
        if not profile:
            return Decimal('0')
        
        try:
            roles = profile.get_all_roles()
            max_amount = Decimal('0')
            unlimited = False
            
            for role in roles:
                role_limit = role.max_approval_amount
                if role_limit is None or role_limit < 0:
                    unlimited = True
                    break
                if role_limit > max_amount:
                    max_amount = role_limit
            
            return None if unlimited else max_amount
        except Exception:
            return Decimal('0')
    
    @staticmethod
    def get_approval_level(user: User) -> int:
        """
        الحصول على مستوى الموافقة للمستخدم (للاستخدام في workflows)
        
        Returns:
            رقم المستوى (5 = أعلى مستوى، 0 = بدون سلطة موافقة)
        """
        if not user or not user.is_authenticated:
            return 0
        
        if user.is_superuser:
            return 5
        
        profile = PermissionService._get_user_profile(user)
        if not profile:
            return 0
        
        try:
            roles = profile.get_all_roles()
            max_level = 0
            
            for role in roles:
                level = role.approval_level or 0
                if level > max_level:
                    max_level = level
            
            return max_level
        except Exception:
            return 0
    
    # ========================================================================
    # Discount Authority (سلطة الخصم)
    # ========================================================================
    
    @staticmethod
    def can_give_discount(user: User, discount_percentage: float) -> bool:
        """
        فحص إذا كان المستخدم يستطيع إعطاء خصم بنسبة معينة
        
        Args:
            user: المستخدم
            discount_percentage: نسبة الخصم المطلوبة
        
        Returns:
            True إذا كان مسموحاً
        """
        if not user or not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        max_discount = PermissionService.get_max_discount_percentage(user)
        
        # None تعني بدون حدود
        if max_discount is None:
            return True
        
        return discount_percentage <= max_discount
    
    @staticmethod
    def get_max_discount_percentage(user: User) -> float | None:
        """
        الحصول على أقصى نسبة خصم يستطيع المستخدم إعطاءها
        
        Returns:
            النسبة أو None (بدون حدود)
        """
        from .role_definitions import get_default_discount_limit
        
        if not user or not user.is_authenticated:
            return 0
        
        if user.is_superuser:
            return None  # بدون حدود
        
        profile = PermissionService._get_user_profile(user)
        if not profile:
            return 0
        
        try:
            roles = profile.get_all_roles()
            max_discount = 0
            unlimited = False
            
            for role in roles:
                # استخدام الحد الافتراضي من التعريفات
                role_limit = get_default_discount_limit(role.name)
                if role_limit is None:
                    unlimited = True
                    break
                if role_limit > max_discount:
                    max_discount = role_limit
            
            return None if unlimited else max_discount
        except Exception:
            return 0
    
    # ========================================================================
    # Special Checks (فحوصات خاصة)
    # ========================================================================
    
    @staticmethod
    def can_cancel_approved_invoice(user: User) -> bool:
        """فحص إذا كان المستخدم يستطيع إلغاء فاتورة معتمدة"""
        from .role_definitions import ROLE_OWNER, ROLE_FIN_MANAGER
        
        if user.is_superuser:
            return True
        
        return (
            PermissionService.has_role(user, ROLE_OWNER) or
            PermissionService.has_role(user, ROLE_FIN_MANAGER)
        )
    
    @staticmethod
    def can_close_period(user: User) -> bool:
        """فحص إذا كان المستخدم يستطيع إقفال فترة محاسبية"""
        from .role_definitions import ROLE_OWNER, ROLE_FIN_MANAGER
        
        if user.is_superuser:
            return True
        
        return (
            PermissionService.has_role(user, ROLE_OWNER) or
            PermissionService.has_role(user, ROLE_FIN_MANAGER)
        )
    
    @staticmethod
    def can_post_journal_entries(user: User) -> bool:
        """فحص إذا كان المستخدم يستطيع ترحيل القيود"""
        from .role_definitions import ROLE_OWNER, ROLE_FIN_MANAGER
        
        if user.is_superuser:
            return True
        
        return (
            PermissionService.has_role(user, ROLE_OWNER) or
            PermissionService.has_role(user, ROLE_FIN_MANAGER)
        )
    
    @staticmethod
    def can_view_cost_prices(user: User) -> bool:
        """فحص إذا كان المستخدم يستطيع رؤية أسعار التكلفة"""
        from .role_definitions import (
            ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_ACCOUNTANT,
            ROLE_INV_MANAGER, ROLE_PROD_MANAGER
        )
        
        if user.is_superuser:
            return True
        
        allowed_roles = [
            ROLE_OWNER,
            ROLE_FIN_MANAGER,
            ROLE_ACCOUNTANT,
            ROLE_INV_MANAGER,
            ROLE_PROD_MANAGER,
        ]
        
        return any(PermissionService.has_role(user, role) for role in allowed_roles)
    
    @staticmethod
    def can_view_profit_reports(user: User) -> bool:
        """فحص إذا كان المستخدم يستطيع رؤية تقارير الأرباح"""
        from .role_definitions import ROLE_OWNER, ROLE_FIN_MANAGER
        
        if user.is_superuser:
            return True
        
        return (
            PermissionService.has_role(user, ROLE_OWNER) or
            PermissionService.has_role(user, ROLE_FIN_MANAGER)
        )
    
    @staticmethod
    def is_pos_only_user(user: User) -> bool:
        """فحص إذا كان المستخدم كاشير فقط (محصور في POS)"""
        from .role_definitions import ROLE_CASHIER
        
        if user.is_superuser:
            return False
        
        roles = PermissionService.get_user_roles(user)
        
        # إذا كان لديه دور واحد فقط وهو كاشير
        return len(roles) == 1 and roles[0].name == ROLE_CASHIER


# ============================================================================
# Shortcut Functions (دوال مختصرة)
# ============================================================================

def user_can(user: User, module: str, action: str = 'view') -> bool:
    """
    دالة مختصرة لفحص الصلاحيات
    
    أمثلة:
        if user_can(request.user, 'sales', 'add'):
            # create invoice
    """
    return PermissionService.has_module_permission(user, module, action)


def check_approval_authority(user: User, amount: Decimal | float) -> bool:
    """دالة مختصرة لفحص سلطة الموافقة"""
    return PermissionService.can_approve_amount(user, amount)


def get_user_max_approval_amount(user: User) -> Decimal | None:
    """دالة مختصرة للحصول على أقصى مبلغ موافقة"""
    return PermissionService.get_max_approval_amount(user)


def get_user_max_discount_percentage(user: User) -> float | None:
    """دالة مختصرة للحصول على أقصى نسبة خصم"""
    return PermissionService.get_max_discount_percentage(user)


# ============================================================================
# Decorator (ديكوريتر للـ Views)
# ============================================================================

def require_permission(module: str, action: str = 'view'):
    """
    ديكوريتر لحماية الـ Views بصلاحيات محددة
    
    أمثلة:
        @require_permission('sales', 'add')
        def create_invoice(request):
            # ...
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            user = getattr(request, 'user', None)
            
            if not user or not user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            if not PermissionService.has_module_permission(user, module, action):
                from django.http import HttpResponseForbidden, JsonResponse
                
                # إذا كان طلب API، إرجاع JSON
                if request.headers.get('accept') == 'application/json' or '/api/' in request.path:
                    return JsonResponse({
                        'error': 'غير مسموح لك بالوصول لهذه الصفحة',
                        'code': 'permission_denied'
                    }, status=403)
                
                # إرجاع صفحة خطأ عادية
                return HttpResponseForbidden('غير مسموح لك بالوصول لهذه الصفحة')
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped
    return decorator



