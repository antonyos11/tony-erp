"""
محرك التفويض الهرمي
═══════════════════════════
المبدأ الذهبي:
  كل مدير يضيف موظفين تحته فقط
  داخل نطاق سلطته
  بصلاحيات أقل أو مساوية

3 قواعد لا تُكسر:
  1. لا تمنح صلاحية لا تملكها
  2. لا تمنح نطاق أوسع من نطاقك
  3. لا تمنح سقف اعتماد أعلى من سقفك
"""
from apps.authorization.models import SystemRole, UserRoleAssignment
from apps.authorization.services.permission_engine import PermissionEngine


class DelegationEngine:
    """
    يتحكم في:
    1. أي أدوار يمكن للمدير منحها
    2. أي فروع/مخازن/خطوط يمكنه التعيين فيها
    3. منع أي تجاوز
    """

    # ═══════════════════════════════════════
    # القاعدة 1: الأدوار المسموح منحها
    # ═══════════════════════════════════════

    # كل دور → الأدوار التي يمكنه منحها
    DELEGATION_MAP = {
        # ═══ Super Admin (owner + superuser) ═══
        'owner': ['ceo', 'cfo', 'internal_auditor', 'hr_manager',
                  'branch_manager', 'production_manager',
                  'accountant_manager'],

        'ceo': ['cfo', 'branch_manager', 'production_manager',
                'hr_manager', 'accountant_manager', 'internal_auditor'],

        # ═══ المالية ═══
        'cfo': ['accountant_manager', 'accountant_purchases', 'accountant_sales'],
        'accountant_manager': ['accountant_purchases', 'accountant_sales'],

        # ═══ الفروع ═══
        'branch_manager': ['salesperson', 'cashier', 'storekeeper', 'delivery_driver'],

        # ═══ الإنتاج ═══
        'production_manager': ['production_supervisor', 'production_planner', 'qc_inspector'],

        # ═══ باقي الأدوار — لا تمنح أحد ═══
        'salesperson': [],
        'cashier': [],
        'storekeeper': [],
        'delivery_driver': [],
        'accountant_purchases': [],
        'accountant_sales': [],
        'production_supervisor': [],
        'production_planner': [],
        'qc_inspector': [],
        'hr_manager': [],
        'internal_auditor': [],
    }

    @classmethod
    def get_grantable_roles(cls, user):
        """
        الأدوار التي يمكن لهذا المستخدم منحها
        Returns: QuerySet of SystemRole
        """
        if user.is_superuser:
            return SystemRole.objects.filter(is_active=True).order_by('sort_order')

        # جمع كل الأدوار المسموحة من كل أدوار المستخدم
        user_role_codes = UserRoleAssignment.objects.filter(
            user=user, is_active=True
        ).values_list('role__code', flat=True)

        grantable_codes = set()
        for code in user_role_codes:
            grantable_codes.update(cls.DELEGATION_MAP.get(code, []))

        if not grantable_codes:
            return SystemRole.objects.none()

        return SystemRole.objects.filter(
            code__in=grantable_codes, is_active=True
        ).order_by('sort_order')

    @classmethod
    def can_grant_role(cls, granting_user, role_to_grant):
        """هل المستخدم يقدر يمنح هذا الدور؟"""
        if granting_user.is_superuser:
            return True

        grantable = cls.get_grantable_roles(granting_user)
        return grantable.filter(pk=role_to_grant.pk).exists()

    # ═══════════════════════════════════════
    # القاعدة 2: النطاق المسموح
    # ═══════════════════════════════════════

    @classmethod
    def get_grantable_branches(cls, user):
        """
        الفروع التي يمكن للمستخدم تعيين موظفين فيها
        - مدير فرع = فرعه فقط
        - مدير عام = كل الفروع
        """
        from apps.core.models import Branch

        if user.is_superuser:
            return Branch.objects.filter(is_active=True)

        scope = PermissionEngine.get_user_scope(user)

        if scope.get('scope') == 'all':
            return Branch.objects.filter(is_active=True)

        if scope.get('branch_ids'):
            return Branch.objects.filter(id__in=scope['branch_ids'], is_active=True)

        return Branch.objects.none()

    @classmethod
    def get_grantable_warehouses(cls, user):
        """المخازن المسموحة"""
        from apps.core.models import Warehouse

        if user.is_superuser:
            return Warehouse.objects.filter(is_active=True)

        scope = PermissionEngine.get_user_scope(user)

        if scope.get('scope') == 'all':
            return Warehouse.objects.filter(is_active=True)

        if scope.get('warehouse_ids'):
            return Warehouse.objects.filter(id__in=scope['warehouse_ids'], is_active=True)

        # مدير فرع — مخازن فرعه
        if scope.get('branch_ids'):
            return Warehouse.objects.filter(
                branch_id__in=scope['branch_ids'], is_active=True
            )

        return Warehouse.objects.none()

    @classmethod
    def get_grantable_production_lines(cls, user):
        """خطوط الإنتاج المسموحة"""
        from apps.production.models import ProductionLine

        if user.is_superuser:
            return ProductionLine.objects.filter(is_active=True)

        scope = PermissionEngine.get_user_scope(user)

        if scope.get('scope') == 'all':
            return ProductionLine.objects.filter(is_active=True)

        if scope.get('production_line_ids'):
            return ProductionLine.objects.filter(
                id__in=scope['production_line_ids'], is_active=True
            )

        return ProductionLine.objects.none()

    # ═══════════════════════════════════════
    # القاعدة 3: التحقق الشامل
    # ═══════════════════════════════════════

    @classmethod
    def validate_assignment(cls, granting_user, role, branch=None, warehouse=None, production_line=None):
        """
        التحقق الشامل قبل تعيين أي دور
        Returns: (is_valid, error_message)
        """
        errors = []

        # 1. هل يملك حق منح هذا الدور؟
        if not cls.can_grant_role(granting_user, role):
            errors.append(f"ليس لديك صلاحية لمنح دور '{role.name}'")

        # 2. هل الفرع ضمن نطاقه؟
        if branch:
            allowed_branches = cls.get_grantable_branches(granting_user)
            if not allowed_branches.filter(pk=branch.pk).exists():
                errors.append(f"ليس لديك صلاحية في فرع '{branch.name}'")

        # 3. هل المخزن ضمن نطاقه؟
        if warehouse:
            allowed_warehouses = cls.get_grantable_warehouses(granting_user)
            if not allowed_warehouses.filter(pk=warehouse.pk).exists():
                errors.append(f"ليس لديك صلاحية في مخزن '{warehouse.name}'")

        # 4. هل خط الإنتاج ضمن نطاقه؟
        if production_line:
            allowed_lines = cls.get_grantable_production_lines(granting_user)
            if not allowed_lines.filter(pk=production_line.pk).exists():
                errors.append(f"ليس لديك صلاحية في خط '{production_line.name}'")

        # 5. التحقق من Scope المنطقي
        if role.scope == 'branch' and not branch:
            errors.append("هذا الدور يحتاج تحديد فرع")
        if role.scope == 'warehouse' and not warehouse:
            errors.append("هذا الدور يحتاج تحديد مخزن")
        if role.scope == 'production_line' and not production_line:
            errors.append("هذا الدور يحتاج تحديد خط إنتاج")

        if errors:
            return False, " | ".join(errors)

        return True, ""

    # ═══════════════════════════════════════
    # تقرير: من أضاف من
    # ═══════════════════════════════════════

    @classmethod
    def get_delegation_report(cls, manager=None):
        """
        تقرير التفويضات
        - من أضاف من
        - متى
        - أي دور
        """
        qs = UserRoleAssignment.objects.select_related(
            'user', 'role', 'branch', 'assigned_by'
        ).order_by('-assigned_at')

        if manager:
            qs = qs.filter(assigned_by=manager)

        return qs
