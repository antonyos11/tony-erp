"""
أمر إعداد الأدوار والصلاحيات الافتراضية — RITA ERP

الاستخدام:
    python manage.py setup_roles
"""
from django.core.management.base import BaseCommand
from apps.authorization.models import Role, Permission


# ═══════════════════════════════════════════════
# تعريف الأدوار الافتراضية
# ═══════════════════════════════════════════════

ALL_MODULES = ['accounts', 'inventory', 'production', 'sales', 'purchases', 'hr', 'reports', 'settings']
ALL_ACTIONS = ['view', 'create', 'edit', 'delete', 'approve', 'export']

DEFAULT_ROLES = [
    {
        'name': 'إدارة عليا',
        'level': 'owner',
        'description': 'صلاحيات كاملة على النظام بالكامل',
        'max_discount_percentage': 100,
        'can_see_cost': True,
        'can_see_profit': True,
        'can_see_other_branches': True,
        'can_delete': True,
        'can_modify_prices': True,
        'can_approve_entries': True,
        'can_create_users': True,
        'permissions': {mod: ALL_ACTIONS for mod in ALL_MODULES},
    },
    {
        'name': 'مدير عام',
        'level': 'ceo',
        'description': 'كل الصلاحيات ما عدا تعديل القيود',
        'max_discount_percentage': 100,
        'can_see_cost': True,
        'can_see_profit': True,
        'can_see_other_branches': True,
        'can_delete': True,
        'can_modify_prices': True,
        'can_approve_entries': False,
        'can_create_users': True,
        'permissions': {
            mod: [a for a in ALL_ACTIONS if a != 'approve'] if mod == 'accounts'
            else ALL_ACTIONS
            for mod in ALL_MODULES
        },
    },
    {
        'name': 'مدير مالي',
        'level': 'cfo',
        'description': 'محاسبة + تقارير + اعتماد',
        'max_discount_percentage': 50,
        'can_see_cost': True,
        'can_see_profit': True,
        'can_see_other_branches': True,
        'can_delete': False,
        'can_modify_prices': False,
        'can_approve_entries': True,
        'can_create_users': False,
        'permissions': {
            'accounts': ALL_ACTIONS,
            'reports': ALL_ACTIONS,
            'sales': ['view', 'export'],
            'purchases': ['view', 'export'],
            'inventory': ['view', 'export'],
            'production': ['view', 'export'],
        },
    },
    {
        'name': 'مدير حسابات',
        'level': 'account_manager',
        'description': 'محاسبة + تقارير',
        'max_discount_percentage': 30,
        'can_see_cost': True,
        'can_see_profit': True,
        'can_see_other_branches': True,
        'can_delete': False,
        'can_modify_prices': False,
        'can_approve_entries': False,
        'can_create_users': False,
        'permissions': {
            'accounts': ['view', 'create', 'edit', 'export'],
            'reports': ['view', 'export'],
            'sales': ['view'],
            'purchases': ['view'],
        },
    },
    {
        'name': 'محاسب',
        'level': 'accountant',
        'description': 'إدخال فقط',
        'max_discount_percentage': 0,
        'can_see_cost': True,
        'can_see_profit': False,
        'can_see_other_branches': False,
        'can_delete': False,
        'can_modify_prices': False,
        'can_approve_entries': False,
        'can_create_users': False,
        'permissions': {
            'accounts': ['view', 'create'],
            'reports': ['view'],
        },
    },
    {
        'name': 'مدير فرع',
        'level': 'branch_manager',
        'description': 'مبيعات + مخزون فرعه فقط',
        'max_discount_percentage': 20,
        'can_see_cost': True,
        'can_see_profit': True,
        'can_see_other_branches': False,
        'can_delete': False,
        'can_modify_prices': False,
        'can_approve_entries': False,
        'can_create_users': False,
        'permissions': {
            'sales': ['view', 'create', 'edit', 'approve', 'export'],
            'inventory': ['view', 'create', 'edit', 'export'],
            'reports': ['view', 'export'],
            'purchases': ['view', 'create'],
        },
    },
    {
        'name': 'بائع',
        'level': 'salesperson',
        'description': 'فواتير بيع فقط + خصم محدود (5%)',
        'max_discount_percentage': 5,
        'can_see_cost': False,
        'can_see_profit': False,
        'can_see_other_branches': False,
        'can_delete': False,
        'can_modify_prices': False,
        'can_approve_entries': False,
        'can_create_users': False,
        'permissions': {
            'sales': ['view', 'create'],
            'inventory': ['view'],
        },
    },
    {
        'name': 'كاشير',
        'level': 'cashier',
        'description': 'تحصيل فقط',
        'max_discount_percentage': 0,
        'can_see_cost': False,
        'can_see_profit': False,
        'can_see_other_branches': False,
        'can_delete': False,
        'can_modify_prices': False,
        'can_approve_entries': False,
        'can_create_users': False,
        'permissions': {
            'sales': ['view', 'create'],
        },
    },
    {
        'name': 'أمين مخزن',
        'level': 'storekeeper',
        'description': 'صرف واستلام فقط',
        'max_discount_percentage': 0,
        'can_see_cost': False,
        'can_see_profit': False,
        'can_see_other_branches': False,
        'can_delete': False,
        'can_modify_prices': False,
        'can_approve_entries': False,
        'can_create_users': False,
        'permissions': {
            'inventory': ['view', 'create', 'edit'],
        },
    },
    {
        'name': 'مدير إنتاج',
        'level': 'production_manager',
        'description': 'أوامر إنتاج',
        'max_discount_percentage': 0,
        'can_see_cost': True,
        'can_see_profit': False,
        'can_see_other_branches': False,
        'can_delete': False,
        'can_modify_prices': False,
        'can_approve_entries': False,
        'can_create_users': False,
        'permissions': {
            'production': ALL_ACTIONS,
            'inventory': ['view'],
            'reports': ['view'],
        },
    },
    {
        'name': 'مشرف خط إنتاج',
        'level': 'production_supervisor',
        'description': 'تسجيل كميات فقط',
        'max_discount_percentage': 0,
        'can_see_cost': False,
        'can_see_profit': False,
        'can_see_other_branches': False,
        'can_delete': False,
        'can_modify_prices': False,
        'can_approve_entries': False,
        'can_create_users': False,
        'permissions': {
            'production': ['view', 'edit'],
            'inventory': ['view'],
        },
    },
]


class Command(BaseCommand):
    help = 'إعداد الأدوار والصلاحيات الافتراضية'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('═' * 50))
        self.stdout.write(self.style.NOTICE('  إعداد الأدوار والصلاحيات الافتراضية'))
        self.stdout.write(self.style.NOTICE('═' * 50))

        created_roles = 0
        created_perms = 0

        for role_data in DEFAULT_ROLES:
            permissions_data = role_data.pop('permissions')

            role, created = Role.objects.get_or_create(
                level=role_data['level'],
                defaults={
                    'name': role_data['name'],
                    'description': role_data['description'],
                    'max_discount_percentage': role_data['max_discount_percentage'],
                    'can_see_cost': role_data['can_see_cost'],
                    'can_see_profit': role_data['can_see_profit'],
                    'can_see_other_branches': role_data['can_see_other_branches'],
                    'can_delete': role_data['can_delete'],
                    'can_modify_prices': role_data['can_modify_prices'],
                    'can_approve_entries': role_data['can_approve_entries'],
                    'can_create_users': role_data['can_create_users'],
                },
            )

            if created:
                created_roles += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ تم إنشاء الدور: {role.name}'))
            else:
                self.stdout.write(f'  - الدور موجود: {role.name}')

            # إعداد الصلاحيات
            for module, actions in permissions_data.items():
                for action in actions:
                    perm, perm_created = Permission.objects.get_or_create(
                        role=role,
                        module=module,
                        action=action,
                        defaults={'is_allowed': True},
                    )
                    if perm_created:
                        created_perms += 1

            # إعادة permissions_data للـ role_data (لو حبينا نعيد التشغيل)
            role_data['permissions'] = permissions_data

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'  تم إنشاء {created_roles} دور جديد'))
        self.stdout.write(self.style.SUCCESS(f'  تم إنشاء {created_perms} صلاحية جديدة'))
        self.stdout.write(self.style.NOTICE('═' * 50))
