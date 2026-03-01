"""
محرك الصلاحيات — RITA ERP
يتحقق من صلاحيات المستخدم استناداً إلى أدواره وتفويضاته
"""
from django.utils import timezone
from apps.authorization.models import Permission, UserRole, Delegation, Role


class PermissionEngine:
    """محرك التحقق من الصلاحيات"""

    @staticmethod
    def get_user_roles(user):
        """استرجاع كل أدوار المستخدم النشطة (المباشرة + التفويضات)"""
        if not user or not user.is_authenticated:
            return Role.objects.none()

        # الأدوار المباشرة
        direct_roles = Role.objects.filter(
            user_roles__user=user,
            user_roles__is_active=True,
            is_active=True,
        )

        # التفويضات النشطة
        now = timezone.now()
        delegated_roles = Role.objects.filter(
            delegation__delegate=user,
            delegation__is_active=True,
            delegation__is_deleted=False,
            delegation__start_date__lte=now,
            delegation__end_date__gte=now,
        )

        return (direct_roles | delegated_roles).distinct()

    @staticmethod
    def has_permission(user, module, action):
        """التحقق من أن المستخدم لديه صلاحية معينة"""
        if not user or not user.is_authenticated:
            return False

        # المشرفون لديهم كل الصلاحيات
        if user.is_superuser:
            return True

        roles = PermissionEngine.get_user_roles(user)
        if not roles.exists():
            return False

        # التحقق من وجود صلاحية مفعلة في أي دور
        return Permission.objects.filter(
            role__in=roles,
            module=module,
            action=action,
            is_allowed=True,
        ).exists()

    @staticmethod
    def get_user_permissions(user):
        """استرجاع كل صلاحيات المستخدم"""
        if not user or not user.is_authenticated:
            return {}

        if user.is_superuser:
            # المشرف لديه كل الصلاحيات
            perms = {}
            for mod_code, mod_name in Permission.MODULES:
                perms[mod_code] = {
                    action_code: True
                    for action_code, action_name in Permission.ACTIONS
                }
            return perms

        roles = PermissionEngine.get_user_roles(user)
        permissions = Permission.objects.filter(
            role__in=roles,
            is_allowed=True,
        ).values_list('module', 'action')

        perms = {}
        for module, action in permissions:
            if module not in perms:
                perms[module] = {}
            perms[module][action] = True

        return perms

    @staticmethod
    def can_user_discount(user, percentage):
        """هل المستخدم يقدر يعمل خصم بالنسبة دي"""
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        roles = PermissionEngine.get_user_roles(user)
        max_discount = roles.order_by('-max_discount_percentage').values_list(
            'max_discount_percentage', flat=True
        ).first()

        if max_discount is None:
            return False

        return percentage <= max_discount

    @staticmethod
    def get_max_discount(user):
        """أقصى نسبة خصم يقدر المستخدم يعملها"""
        if not user or not user.is_authenticated:
            return 0

        if user.is_superuser:
            return 100

        roles = PermissionEngine.get_user_roles(user)
        max_discount = roles.order_by('-max_discount_percentage').values_list(
            'max_discount_percentage', flat=True
        ).first()

        return max_discount or 0

    @staticmethod
    def has_role_level(user, level):
        """التحقق من أن المستخدم عنده دور بمستوى معين"""
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        roles = PermissionEngine.get_user_roles(user)
        return roles.filter(level=level).exists()

    @staticmethod
    def can_see_cost(user):
        """هل المستخدم يقدر يشوف التكلفة"""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        roles = PermissionEngine.get_user_roles(user)
        return roles.filter(can_see_cost=True).exists()

    @staticmethod
    def can_see_profit(user):
        """هل المستخدم يقدر يشوف الأرباح"""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        roles = PermissionEngine.get_user_roles(user)
        return roles.filter(can_see_profit=True).exists()

    @staticmethod
    def can_see_other_branches(user):
        """هل المستخدم يقدر يشوف فروع تانية"""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        roles = PermissionEngine.get_user_roles(user)
        return roles.filter(can_see_other_branches=True).exists()
