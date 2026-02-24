from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import UserRole, ModulePermission


class Command(BaseCommand):
    help = 'إعداد الأدوار والصلاحيات الافتراضية للنظام'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='إعادة تعيين جميع الأدوار والصلاحيات',
        )

    def handle(self, *args, **options):
        self.stdout.write('بدء إعداد الأدوار والصلاحيات...')
        
        if options['reset']:
            self.reset_data()
        
        self.create_roles()
        self.create_permissions()
        
        self.stdout.write(
            self.style.SUCCESS('تم إعداد النظام بنجاح!')
        )

    @transaction.atomic
    def reset_data(self):
        """إعادة تعيين البيانات"""
        self.stdout.write('إعادة تعيين البيانات الموجودة...')
        ModulePermission.objects.all().delete()
        UserRole.objects.all().delete()

    @transaction.atomic
    def create_roles(self):
        """إنشاء الأدوار الافتراضية"""
        self.stdout.write('إنشاء الأدوار...')
        
        roles_data = [
            {
                'name': 'super_admin',
                'display_name': 'مدير عام',
                'description': 'صلاحيات كاملة على جميع أجزاء النظام',
                'can_approve': True,
                'approval_level': 5,
                'max_approval_amount': 999999999.99,
            },
            {
                'name': 'accounting_manager',
                'display_name': 'مدير محاسبة',
                'description': 'إدارة النظام المحاسبي والتقارير المالية',
                'can_approve': True,
                'approval_level': 4,
                'max_approval_amount': 100000.00,
            },
            {
                'name': 'inventory_manager',
                'display_name': 'مدير مخزون',
                'description': 'إدارة المخزون والمشتريات',
                'can_approve': True,
                'approval_level': 3,
                'max_approval_amount': 50000.00,
            },
            {
                'name': 'sales_manager',
                'display_name': 'مدير مبيعات',
                'description': 'إدارة المبيعات والعملاء وإدارة علاقات العملاء',
                'can_approve': True,
                'approval_level': 3,
                'max_approval_amount': 50000.00,
            },
            {
                'name': 'production_manager',
                'display_name': 'مدير إنتاج',
                'description': 'إدارة عمليات الإنتاج والجودة',
                'can_approve': True,
                'approval_level': 3,
                'max_approval_amount': 30000.00,
            },
            {
                'name': 'hr_manager',
                'display_name': 'مدير موارد بشرية',
                'description': 'إدارة شؤون الموظفين والرواتب',
                'can_approve': True,
                'approval_level': 3,
                'max_approval_amount': 20000.00,
            },
            {
                'name': 'accounting_staff',
                'display_name': 'موظف محاسبة',
                'description': 'إدخال القيود المحاسبية والفواتير',
                'can_approve': False,
                'approval_level': 1,
                'max_approval_amount': 5000.00,
            },
            {
                'name': 'inventory_staff',
                'display_name': 'موظف مخزون',
                'description': 'إدارة حركة المخزون',
                'can_approve': False,
                'approval_level': 1,
                'max_approval_amount': 2000.00,
            },
            {
                'name': 'sales_staff',
                'display_name': 'موظف مبيعات',
                'description': 'إنشاء فواتير المبيعات وإدارة العملاء',
                'can_approve': False,
                'approval_level': 1,
                'max_approval_amount': 3000.00,
            },
            {
                'name': 'production_staff',
                'display_name': 'موظف إنتاج',
                'description': 'تسجيل عمليات الإنتاج',
                'can_approve': False,
                'approval_level': 1,
                'max_approval_amount': 1000.00,
            },
            {
                'name': 'hr_staff',
                'display_name': 'موظف موارد بشرية',
                'description': 'إدخال بيانات الموظفين',
                'can_approve': False,
                'approval_level': 1,
                'max_approval_amount': 1000.00,
            },
            {
                'name': 'viewer',
                'display_name': 'مستخدم عرض',
                'description': 'عرض التقارير فقط',
                'can_approve': False,
                'approval_level': 1,
                'max_approval_amount': 0.00,
            },
        ]
        
        for role_data in roles_data:
            role, created = UserRole.objects.get_or_create(
                name=role_data['name'],
                defaults=role_data
            )
            if created:
                self.stdout.write(f'  تم إنشاء الدور: {role.display_name}')
            else:
                self.stdout.write(f'  الدور موجود: {role.display_name}')

    @transaction.atomic
    def create_permissions(self):
        """إنشاء الصلاحيات الافتراضية"""
        self.stdout.write('إنشاء الصلاحيات...')
        
        # تعريف الصلاحيات لكل دور
        permissions_matrix = {
            'super_admin': {
                # صلاحيات كاملة على جميع الوحدات
                'all_modules': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export']
            },
            'accounting_manager': {
                'accounting': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export'],
                'reports': ['view', 'print', 'export'],
                'core': ['view', 'change'],
                'sales': ['view', 'approve'],
                'purchases': ['view', 'approve'],
                'partners': ['view', 'add', 'change'],
            },
            'inventory_manager': {
                'inventory': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export'],
                'purchases': ['view', 'add', 'change', 'delete', 'approve', 'print'],
                'production': ['view', 'approve'],
                'reports': ['view', 'print', 'export'],
                'partners': ['view', 'add', 'change'],
            },
            'sales_manager': {
                'sales': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export'],
                'crm': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export'],
                'inventory': ['view'],
                'reports': ['view', 'print', 'export'],
                'partners': ['view', 'add', 'change'],
            },
            'production_manager': {
                'production': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export'],
                'inventory': ['view', 'change'],
                'purchases': ['view', 'add'],
                'reports': ['view', 'print', 'export'],
            },
            'hr_manager': {
                'hr': ['view', 'add', 'change', 'delete', 'approve', 'print', 'export'],
                'reports': ['view', 'print', 'export'],
                'core': ['view'],
            },
            'accounting_staff': {
                'accounting': ['view', 'add', 'change'],
                'sales': ['view', 'add', 'change'],
                'purchases': ['view', 'add', 'change'],
                'reports': ['view'],
                'partners': ['view'],
            },
            'inventory_staff': {
                'inventory': ['view', 'add', 'change'],
                'purchases': ['view', 'add'],
                'production': ['view'],
                'reports': ['view'],
            },
            'sales_staff': {
                'sales': ['view', 'add', 'change', 'print'],
                'crm': ['view', 'add', 'change'],
                'inventory': ['view'],
                'reports': ['view'],
                'partners': ['view'],
            },
            'production_staff': {
                'production': ['view', 'add', 'change'],
                'inventory': ['view'],
                'reports': ['view'],
            },
            'hr_staff': {
                'hr': ['view', 'add', 'change'],
                'reports': ['view'],
            },
            'viewer': {
                'accounting': ['view'],
                'inventory': ['view'],
                'sales': ['view'],
                'purchases': ['view'],
                'production': ['view'],
                'hr': ['view'],
                'crm': ['view'],
                'reports': ['view'],
                'partners': ['view'],
                'core': ['view'],
            },
        }
        
        all_modules = ['accounting', 'inventory', 'sales', 'purchases', 
                      'production', 'hr', 'crm', 'reports', 'partners', 'core']
        
        for role_name, role_permissions in permissions_matrix.items():
            try:
                role = UserRole.objects.get(name=role_name)
                
                if 'all_modules' in role_permissions:
                    # صلاحيات كاملة على جميع الوحدات (للمدير العام)
                    for module in all_modules:
                        for action in role_permissions['all_modules']:
                            ModulePermission.objects.get_or_create(
                                role=role,
                                module=module,
                                action=action,
                                defaults={'is_allowed': True}
                            )
                else:
                    # صلاحيات محددة لكل وحدة
                    for module, actions in role_permissions.items():
                        for action in actions:
                            ModulePermission.objects.get_or_create(
                                role=role,
                                module=module,
                                action=action,
                                defaults={'is_allowed': True}
                            )
                
                self.stdout.write(f'  تم إعداد صلاحيات: {role.display_name}')
                
            except UserRole.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'  الدور غير موجود: {role_name}')
                )