"""
محرك الصلاحيات المؤسسي — RITA ERP
═══════════════════════════════════
Sprint 22A: محرك موحد يدعم النماذج القديمة والجديدة معاً

3 طبقات للنظام الجديد:
1. Permission Check — هل يملك الصلاحية؟
2. Scope Check — هل ضمن نطاقه؟
3. Limit Check — هل ضمن سقفه؟

backward_compat: يدعم UserRole/Permission القديم لضمان عمل الاختبارات القديمة
"""
from decimal import Decimal
from django.utils import timezone
from apps.authorization.models import (
    # نماذج قديمة (backward compat)
    Permission, UserRole, Delegation, Role,
    # نماذج جديدة Sprint 22A
    SystemPermission, SystemRole, UserRoleAssignment, SecurityViolationLog,
)


class PermissionEngine:
    """محرك الصلاحيات الموحد — يدعم النماذج القديمة والجديدة"""

    # ═══════════════════════════════════════════════════════════
    # Backward-compat: النماذج القديمة (UserRole/Permission)
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def get_user_roles(user):
        """استرجاع أدوار المستخدم القديمة — للتوافق مع الكود القديم"""
        if not user or not user.is_authenticated:
            return Role.objects.none()

        direct_roles = Role.objects.filter(
            user_roles__user=user,
            user_roles__is_active=True,
            is_active=True,
        )

        now = timezone.now()
        delegated_roles = Role.objects.filter(
            delegation__delegate=user,
            delegation__is_active=True,
            delegation__is_deleted=False,
            delegation__start_date__lte=now,
            delegation__end_date__gte=now,
        )

        return (direct_roles | delegated_roles).distinct()

    # ═══════════════════════════════════════════════════════════
    # الطبقة 1: فحص الصلاحية (يدعم النموذجين معاً)
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def has_permission(cls, user, module, action):
        """
        هل المستخدم يملك صلاحية معينة؟
        يفحص النماذج الجديدة أولاً ثم القديمة (backward compat)
        """
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        # فحص النموذج الجديد (UserRoleAssignment → SystemRole → SystemPermission)
        assignments = UserRoleAssignment.objects.filter(
            user=user, is_active=True, role__is_active=True
        ).select_related('role')

        for assignment in assignments:
            if assignment.role.has_permission(module, action):
                return True

        # fallback: فحص النموذج القديم (UserRole → Role → Permission)
        old_roles = cls.get_user_roles(user)
        if old_roles.exists():
            return Permission.objects.filter(
                role__in=old_roles,
                module=module,
                action=action,
                is_allowed=True,
            ).exists()

        return False

    @classmethod
    def has_any_module_access(cls, user, module):
        """هل المستخدم يملك أي صلاحية في هذا القسم؟"""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        assignments = UserRoleAssignment.objects.filter(
            user=user, is_active=True, role__is_active=True
        ).select_related('role')

        for assignment in assignments:
            if assignment.role.has_any_permission_in_module(module):
                return True

        old_roles = cls.get_user_roles(user)
        if old_roles.exists():
            return Permission.objects.filter(
                role__in=old_roles,
                module=module,
                is_allowed=True,
            ).exists()

        return False

    @classmethod
    def get_user_modules(cls, user):
        """قائمة الأقسام المتاحة للمستخدم"""
        if not user or not user.is_authenticated:
            return []
        if user.is_superuser:
            return [c[0] for c in SystemPermission._meta.get_field('module').choices]

        modules = set()
        assignments = UserRoleAssignment.objects.filter(
            user=user, is_active=True, role__is_active=True
        ).select_related('role')

        for assignment in assignments:
            modules.update(assignment.role.get_modules())

        return list(modules)

    @classmethod
    def get_user_permissions(cls, user):
        """
        كل صلاحيات المستخدم.
        - إذا كان superuser أو يستخدم النموذج القديم: يعيد dict (module -> action -> bool)
        - إذا كان يستخدم النموذج الجديد: يعيد set of permission codes
        """
        if not user or not user.is_authenticated:
            return {}

        if user.is_superuser:
            perms = {}
            for mod_code, _ in Permission.MODULES:
                perms[mod_code] = {
                    action_code: True
                    for action_code, _ in Permission.ACTIONS
                }
            return perms

        # النموذج الجديد أولاً
        new_assignments = UserRoleAssignment.objects.filter(
            user=user, is_active=True, role__is_active=True
        ).select_related('role')

        if new_assignments.exists():
            perm_codes = set()
            for assignment in new_assignments:
                codes = assignment.role.permissions.values_list('code', flat=True)
                perm_codes.update(codes)
            return perm_codes

        # fallback: النموذج القديم — يعيد dict
        old_roles = cls.get_user_roles(user)
        permissions = Permission.objects.filter(
            role__in=old_roles,
            is_allowed=True,
        ).values_list('module', 'action')

        perms = {}
        for module, action in permissions:
            if module not in perms:
                perms[module] = {}
            perms[module][action] = True

        return perms

    # ═══════════════════════════════════════════════════════════
    # الطبقة 2: فحص النطاق (Scope)
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def get_user_scope(cls, user):
        """
        نطاق المستخدم — يحدد ما يمكنه رؤيته
        Returns: {'scope': 'branch', 'branch_ids': [1,2], 'warehouse_ids': [3], ...}
        """
        if not user or not user.is_authenticated:
            return {'scope': 'none'}
        if user.is_superuser:
            return {'scope': 'all'}

        scope_data = {
            'scope': 'none',
            'branch_ids': set(),
            'warehouse_ids': set(),
            'production_line_ids': set(),
        }

        assignments = UserRoleAssignment.objects.filter(
            user=user, is_active=True, role__is_active=True
        ).select_related('role', 'branch', 'warehouse', 'production_line')

        for assignment in assignments:
            role_scope = assignment.role.scope

            if role_scope == 'all':
                return {'scope': 'all'}

            if role_scope == 'branch' and assignment.branch:
                scope_data['scope'] = 'filtered'
                scope_data['branch_ids'].add(assignment.branch_id)

            if role_scope == 'warehouse' and assignment.warehouse:
                scope_data['scope'] = 'filtered'
                scope_data['warehouse_ids'].add(assignment.warehouse_id)
                if assignment.warehouse.branch_id:
                    scope_data['branch_ids'].add(assignment.warehouse.branch_id)

            if role_scope == 'production_line' and assignment.production_line:
                scope_data['scope'] = 'filtered'
                scope_data['production_line_ids'].add(assignment.production_line_id)

        scope_data['branch_ids'] = list(scope_data['branch_ids'])
        scope_data['warehouse_ids'] = list(scope_data['warehouse_ids'])
        scope_data['production_line_ids'] = list(scope_data['production_line_ids'])

        return scope_data

    @classmethod
    def filter_queryset_by_scope(cls, user, queryset, branch_field='branch'):
        """
        فلترة أي QuerySet حسب نطاق المستخدم
        استخدام: qs = PermissionEngine.filter_queryset_by_scope(request.user, qs, 'branch')
        """
        scope = cls.get_user_scope(user)

        if scope['scope'] == 'all':
            return queryset
        if scope['scope'] == 'none':
            return queryset.none()
        if scope.get('branch_ids'):
            return queryset.filter(**{f'{branch_field}_id__in': scope['branch_ids']})

        return queryset.none()

    # ═══════════════════════════════════════════════════════════
    # الطبقة 3: فحص السقف (Limits)
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def check_approval_limit(cls, user, limit_type, amount):
        """
        هل المبلغ ضمن سقف اعتماد المستخدم؟
        limit_type: 'invoice' / 'expense' / 'return'
        Returns: (bool, max_limit)
        """
        if user.is_superuser:
            return True, Decimal('999999999')

        max_limit = Decimal('0')
        assignments = UserRoleAssignment.objects.filter(
            user=user, is_active=True, role__is_active=True
        ).select_related('role')

        for assignment in assignments:
            if limit_type == 'invoice':
                limit = assignment.role.invoice_approval_limit
            elif limit_type == 'expense':
                limit = assignment.role.expense_approval_limit
            elif limit_type == 'return':
                limit = assignment.role.return_approval_limit
            else:
                limit = Decimal('0')
            max_limit = max(max_limit, limit)

        return amount <= max_limit, max_limit

    @classmethod
    def get_max_discount(cls, user):
        """أقصى خصم مسموح للمستخدم — يدعم النموذجين"""
        if not user or not user.is_authenticated:
            return Decimal('0')
        if user.is_superuser:
            return Decimal('100')

        # النموذج الجديد أولاً
        new_assignments = UserRoleAssignment.objects.filter(
            user=user, is_active=True, role__is_active=True
        ).select_related('role')

        if new_assignments.exists():
            max_disc = Decimal('0')
            for assignment in new_assignments:
                max_disc = max(max_disc, assignment.role.max_discount_percentage)
            return max_disc

        # fallback: النموذج القديم
        old_roles = cls.get_user_roles(user)
        max_discount = old_roles.order_by('-max_discount_percentage').values_list(
            'max_discount_percentage', flat=True
        ).first()
        return max_discount or Decimal('0')

    # ═══════════════════════════════════════════════════════════
    # Backward-compat helpers (needed by existing tests & template tags)
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def can_user_discount(cls, user, percentage):
        """هل المستخدم يقدر يعمل خصم بالنسبة دي"""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return percentage <= cls.get_max_discount(user)

    @classmethod
    def has_role_level(cls, user, level):
        """التحقق من أن المستخدم عنده دور بمستوى معين (النموذج القديم)"""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        roles = cls.get_user_roles(user)
        return roles.filter(level=level).exists()

    @classmethod
    def can_see_cost(cls, user):
        """هل المستخدم يقدر يشوف التكلفة"""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if cls.has_permission(user, 'accounts', 'view_cost') or \
           cls.has_permission(user, 'inventory', 'view_cost'):
            return True
        roles = cls.get_user_roles(user)
        return roles.filter(can_see_cost=True).exists()

    @classmethod
    def can_see_profit(cls, user):
        """هل المستخدم يقدر يشوف الأرباح"""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if cls.has_permission(user, 'sales', 'view_profit'):
            return True
        roles = cls.get_user_roles(user)
        return roles.filter(can_see_profit=True).exists()

    @classmethod
    def can_see_other_branches(cls, user):
        """هل المستخدم يقدر يشوف فروع تانية"""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        scope = cls.get_user_scope(user)
        if scope.get('scope') == 'all':
            return True
        roles = cls.get_user_roles(user)
        return roles.filter(can_see_other_branches=True).exists()

    # ═══════════════════════════════════════════════════════════
    # فحص الحساسية (Separation of Duties)
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def check_separation_of_duties(cls, user, action_module, action_type):
        """فصل المهام — لا بيع + تحصيل، لا مخزن + محاسبة"""
        CONFLICTING_PERMISSIONS = [
            ('sales', 'create', 'treasury', 'collect'),
            ('inventory', 'adjust', 'accounts', 'post'),
            ('purchases', 'create', 'inventory', 'receive'),
        ]

        for mod1, act1, mod2, act2 in CONFLICTING_PERMISSIONS:
            if action_module == mod1 and action_type == act1:
                if cls.has_permission(user, mod2, act2):
                    return False, f"تعارض صلاحيات: لا يجوز الجمع بين {mod1}.{act1} و {mod2}.{act2}"
            if action_module == mod2 and action_type == act2:
                if cls.has_permission(user, mod1, act1):
                    return False, f"تعارض صلاحيات: لا يجوز الجمع بين {mod1}.{act1} و {mod2}.{act2}"

        return True, ""

    # ═══════════════════════════════════════════════════════════
    # تسجيل محاولات الوصول غير المصرح
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def log_violation(cls, user, url, module, action, request=None):
        """تسجيل محاولة وصول مرفوضة"""
        SecurityViolationLog.objects.create(
            user=user,
            attempted_url=url,
            attempted_module=module,
            attempted_action=action,
            ip_address=cls._get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
        )

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    # ═══════════════════════════════════════════════════════════
    # التفويض الهرمي
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def can_grant_role(cls, granting_user, role_to_grant):
        """
        هل المستخدم يقدر يمنح هذا الدور لشخص آخر؟
        المبدأ: لا أحد يمنح صلاحية لا يمتلكها
        """
        if granting_user.is_superuser:
            return True

        user_roles = UserRoleAssignment.objects.filter(
            user=granting_user, is_active=True
        ).values_list('role_id', flat=True)

        return role_to_grant.can_be_granted_by.filter(id__in=user_roles).exists()
