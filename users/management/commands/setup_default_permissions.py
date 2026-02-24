"""
Django Management Command: Setup Default Permissions
إعداد الصلاحيات الافتراضية لكل الأدوار (مستندة على التعريفات المحدثة)

الاستخدام:
    python manage.py setup_default_permissions
    python manage.py setup_default_permissions --reset  # إعادة تعيين كل شيء
"""

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from users.models import UserRole, ModulePermission
from core.security import role_definitions as rd


MODULES_ALL = [
    'accounting', 'inventory', 'sales', 'purchases', 'production', 'hr', 'crm', 'maintenance',
    'reports', 'partners', 'fleet', 'pos', 'core'
]

ACTIONS_MANAGER = ['view', 'add', 'change', 'delete', 'approve', 'print', 'export']
ACTIONS_SUPERVISOR = ['view', 'add', 'change', 'print']
ACTIONS_STAFF = ['view', 'add', 'print']
ACTIONS_VIEW_ONLY = ['view']


class Command(BaseCommand):
    help = 'إعداد الصلاحيات الافتراضية لكل الأدوار وفق الهيكل الجديد'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='حذف الصلاحيات القديمة وإعادة الإنشاء',
        )

    def handle(self, *args, **options):
        reset = options['reset']

        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('🔧 إعداد الصلاحيات الافتراضية'))
        self.stdout.write(self.style.WARNING('=' * 70))

        if reset:
            self.stdout.write(self.style.WARNING('⚠️  وضع إعادة التعيين - سيتم حذف كل الصلاحيات القديمة!'))
            confirm = input('هل أنت متأكد؟ (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('تم الإلغاء'))
                return

        try:
            with transaction.atomic():
                self._ensure_roles()
                created = self._setup_permissions(reset)

            self.stdout.write(self.style.SUCCESS(f'\n✅ تم إعداد الصلاحيات بنجاح! (إجمالي {created} صلاحية)'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ خطأ: {str(e)}'))

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    def _ensure_roles(self):
        """إنشاء الأدوار من التعريفات إذا كانت مفقودة"""
        self.stdout.write('\n📋 التحقق من الأدوار...')

        for role_code, display_name in rd.ROLE_DISPLAY_NAMES.items():
            approval_level = rd.get_approval_level(role_code)
            max_amount = rd.get_default_approval_limit(role_code) or 0
            can_approve = rd.can_approve_by_default(role_code)
            description = rd.get_role_description(role_code)

            role, created = UserRole.objects.get_or_create(
                name=role_code,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'approval_level': approval_level,
                    'can_approve': can_approve,
                    'max_approval_amount': max_amount or 0,
                    'is_active': True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'   ✓ تم إنشاء دور: {display_name}'))
            else:
                self.stdout.write(f'   • دور موجود: {display_name}')

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    def _setup_permissions(self, reset: bool) -> int:
        self.stdout.write('\n🔐 إعداد الصلاحيات...')

        if reset:
            deleted_count = ModulePermission.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'   🗑️  تم حذف {deleted_count} صلاحية قديمة'))

        templates = self._build_templates()
        total_created = 0

        for role in UserRole.objects.filter(is_active=True):
            permissions = templates.get(role.name)

            # أدوار قديمة أو غير معرفة في التعريفات تحصل على صلاحيات عرض للتقارير كافتراضي آمن
            if permissions is None:
                permissions = {'reports': ACTIONS_VIEW_ONLY}

            total_created += self._create_permissions_for_role(role, permissions)
            self.stdout.write(f'   ✓ {role.display_name}: {len(permissions)} وحدات')

        return total_created

    def _build_templates(self):
        """يبني قوالب بسيطة للصلاحيات حسب المجال ومستوى الدور"""
        domain_modules = self._domain_modules()
        templates = defaultdict(dict)

        for role_code in rd.ROLE_DISPLAY_NAMES.keys():
            modules = domain_modules.get(role_code, ['reports'])
            actions = self._actions_for_role(role_code)

            module_actions = {module: actions for module in modules}
            templates[role_code] = module_actions

        return templates

    def _create_permissions_for_role(self, role: UserRole, permissions: dict) -> int:
        count = 0
        for module, actions in permissions.items():
            for action in actions:
                ModulePermission.objects.get_or_create(
                    role=role,
                    module=module,
                    action=action,
                    defaults={'is_allowed': True},
                )
                count += 1
        return count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _actions_for_role(self, role_code: str):
        if role_code in {rd.ROLE_OWNER, rd.ROLE_GM, rd.ROLE_SYS_ADMIN}:
            return ACTIONS_MANAGER

        if rd.is_manager_role(role_code):
            return ACTIONS_MANAGER

        # أدوار إشرافية/قيادة فرعية
        supervisor_keywords = ['supervisor', 'lead', 'controller']
        if any(key in role_code for key in supervisor_keywords):
            return ACTIONS_SUPERVISOR

        # أدوار خدمية بسيطة أو أمن
        low_privilege = {rd.ROLE_PORTER, rd.ROLE_TEA_BOY, rd.ROLE_CLEANER, rd.ROLE_SECURITY_GUARD}
        if role_code in low_privilege:
            return ACTIONS_VIEW_ONLY

        return ACTIONS_STAFF

    def _domain_modules(self):
        """تحديد الوحدات المناسبة لكل دور"""
        branch_roles = {
            rd.ROLE_BRANCHES_MANAGER, rd.ROLE_BRANCH_MANAGER, rd.ROLE_BRANCH_VICE_MANAGER, rd.ROLE_BRANCH_SUPERVISOR,
            rd.ROLE_BRANCH_ACCOUNTANT, rd.ROLE_BRANCH_STORE_KEEPER, rd.ROLE_WAREHOUSE_WORKER,
            rd.ROLE_SALES_REP_INTERNAL, rd.ROLE_SALES_REP_EXTERNAL, rd.ROLE_CASHIER,
        }
        finance_roles = {
            rd.ROLE_FIN_MANAGER, rd.ROLE_SENIOR_ACCOUNTANT, rd.ROLE_ACCOUNTANT, rd.ROLE_COST_ACCOUNTANT,
            rd.ROLE_TREASURY_OFFICER, rd.ROLE_BRANCH_ACCOUNTANT, rd.ROLE_INTERNAL_AUDITOR,
        }
        hr_roles = {
            rd.ROLE_HR_MANAGER, rd.ROLE_HR_RECRUITER, rd.ROLE_HR_PAYROLL, rd.ROLE_HR_ATTENDANCE,
            rd.ROLE_HR_TRAINING, rd.ROLE_HR_GOV_RELATIONS, rd.ROLE_HR_STAFF,
        }
        procurement_roles = {
            rd.ROLE_PROCUREMENT_MANAGER, rd.ROLE_PROCUREMENT_LEAD, rd.ROLE_PROCUREMENT_OFFICER,
            rd.ROLE_PO_OFFICER, rd.ROLE_SUPPLIER_FOLLOWUP,
        }
        warehouse_roles = {
            rd.ROLE_WAREHOUSE_MANAGER, rd.ROLE_STORE_SUPERVISOR, rd.ROLE_STORE_KEEPER, rd.ROLE_BRANCH_STORE_KEEPER,
            rd.ROLE_INVENTORY_CONTROLLER, rd.ROLE_RAW_STORE_KEEPER, rd.ROLE_SEMI_STORE_KEEPER,
            rd.ROLE_FG_STORE_KEEPER, rd.ROLE_WAREHOUSE_WORKER,
        }
        it_roles = {rd.ROLE_IT_MANAGER, rd.ROLE_IT_DEVELOPER, rd.ROLE_IT_NETWORK, rd.ROLE_IT_SUPPORT}
        sales_roles = {
            rd.ROLE_SALES_MARKETING_MANAGER, rd.ROLE_MARKETING_MANAGER, rd.ROLE_CAMPAIGN_TEAM,
            rd.ROLE_GRAPHIC_DESIGNER, rd.ROLE_CONTENT_CREATOR, rd.ROLE_SOCIAL_MEDIA_SPECIALIST,
            rd.ROLE_SALES_MANAGER, rd.ROLE_SALES_SUPERVISOR, rd.ROLE_SALES_REP_INTERNAL,
            rd.ROLE_SALES_REP_EXTERNAL, rd.ROLE_CASHIER, rd.ROLE_PRICING_OFFICER,
        }
        quality_roles = {
            rd.ROLE_QUALITY_MANAGER, rd.ROLE_QUALITY_INSPECTOR, rd.ROLE_QA_LAB_CHEMIST, rd.ROLE_QA_RAW_TESTER,
            rd.ROLE_QA_FINAL_TESTER, rd.ROLE_QA_SPEC_MATCHER,
        }
        customer_service_roles = {
            rd.ROLE_CUSTOMER_CARE_LEAD, rd.ROLE_CUSTOMER_SERVICE_LEAD, rd.ROLE_CS_AGENT,
            rd.ROLE_CS_ORDER_FOLLOWUP, rd.ROLE_CS_COMPLAINTS,
        }
        operations_roles = {
            rd.ROLE_OPERATIONS_MANAGER, rd.ROLE_FACTORY_MANAGER, rd.ROLE_FACTORY_VICE_MANAGER, rd.ROLE_PROD_MANAGER,
            rd.ROLE_PRODUCTION_SUPERVISOR, rd.ROLE_FOAM_LINE_SUPERVISOR, rd.ROLE_SPRING_LINE_SUPERVISOR,
            rd.ROLE_UPHOLSTERY_SUPERVISOR, rd.ROLE_SHIFT_LEAD, rd.ROLE_PROD_TECHNICIAN, rd.ROLE_PROD_STAFF,
            rd.ROLE_PACKAGING_WORKER, rd.ROLE_DISPATCH_CONTROLLER, rd.ROLE_LABOR_CONTROLLER,
        }
        maintenance_roles = {
            rd.ROLE_MAINTENANCE_MANAGER, rd.ROLE_MECH_TECH, rd.ROLE_ELEC_TECH, rd.ROLE_LINE_MAINT_TECH,
            rd.ROLE_SPAREPARTS_CONTROLLER,
        }
        hse_roles = {rd.ROLE_HSE_OFFICER, rd.ROLE_HSE_SUPERVISOR, rd.ROLE_HSE_EMERGENCY, rd.ROLE_SECURITY_GUARD}

        domain = {}

        for code in branch_roles:
            domain[code] = ['sales', 'pos', 'inventory', 'accounting', 'reports']
        for code in finance_roles:
            domain[code] = ['accounting', 'reports']
        for code in hr_roles:
            domain[code] = ['hr', 'reports']
        for code in procurement_roles:
            domain[code] = ['purchases', 'inventory', 'reports']
        for code in warehouse_roles:
            domain[code] = ['inventory', 'purchases', 'reports']
        for code in it_roles:
            domain[code] = ['core', 'reports']
        for code in sales_roles:
            domain[code] = ['sales', 'pos', 'crm', 'reports']
        for code in quality_roles:
            domain[code] = ['production', 'inventory', 'sales', 'reports']
        for code in customer_service_roles:
            domain[code] = ['sales', 'crm', 'reports']
        for code in operations_roles:
            domain[code] = ['production', 'maintenance', 'inventory', 'reports']
        for code in maintenance_roles:
            domain[code] = ['maintenance', 'inventory', 'reports']
        for code in hse_roles:
            domain[code] = ['production', 'maintenance', 'reports']

        # أدوار عليا تحصل على كل الوحدات
        for code in {rd.ROLE_OWNER, rd.ROLE_GM, rd.ROLE_SYS_ADMIN}:
            domain[code] = MODULES_ALL

        # عرض فقط
        domain[rd.ROLE_VIEWER] = ['reports']

        return domain


