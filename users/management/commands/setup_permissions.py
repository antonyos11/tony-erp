"""
أمر إدارة لإعداد النظام والصلاحيات
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserRole, UserProfile, ModulePermission


class Command(BaseCommand):
    help = 'إعداد نظام الصلاحيات والأدوار'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-roles',
            action='store_true',
            help='إنشاء الأدوار الأساسية',
        )
        parser.add_argument(
            '--create-permissions',
            action='store_true',
            help='إنشاء الصلاحيات الأساسية',
        )
        parser.add_argument(
            '--fix-admin',
            action='store_true',
            help='إصلاح مستخدم admin وإنشاء profile له',
        )
        parser.add_argument(
            '--create-demo-user',
            action='store_true',
            help='إنشاء مستخدم تجريبي مع صلاحيات محدودة',
        )

    def handle(self, *args, **options):
        if options['create_roles']:
            self.create_roles()
        
        if options['create_permissions']:
            self.create_permissions()
            
        if options['fix_admin']:
            self.fix_admin_user()
            
        if options['create_demo_user']:
            self.create_demo_user()

    def create_roles(self):
        """إنشاء الأدوار الأساسية"""
        roles_data = [
            ('super_admin', 'مدير عام', 'صلاحيات كاملة في النظام', True, 5, 1000000),
            ('accounting_manager', 'مدير محاسبة', 'إدارة شؤون المحاسبة', True, 3, 100000),
            ('inventory_manager', 'مدير مخزون', 'إدارة شؤون المخزون', True, 3, 50000),
            ('sales_manager', 'مدير مبيعات', 'إدارة شؤون المبيعات', True, 3, 75000),
            ('hr_manager', 'مدير موارد بشرية', 'إدارة شؤون الموظفين', True, 3, 30000),
            ('accounting_staff', 'موظف محاسبة', 'موظف في قسم المحاسبة', False, 2, 5000),
            ('inventory_staff', 'موظف مخزون', 'موظف في قسم المخزون', False, 2, 1000),
            ('sales_staff', 'موظف مبيعات', 'موظف في قسم المبيعات', False, 2, 10000),
            ('hr_staff', 'موظف موارد بشرية', 'موظف في قسم الموارد البشرية', False, 2, 2000),
            ('viewer', 'مستخدم عرض فقط', 'يمكنه عرض البيانات فقط', False, 1, 0),
        ]
        
        for role_data in roles_data:
            role, created = UserRole.objects.get_or_create(
                name=role_data[0],
                defaults={
                    'display_name': role_data[1],
                    'description': role_data[2],
                    'can_approve': role_data[3],
                    'approval_level': role_data[4],
                    'max_approval_amount': role_data[5],
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'تم إنشاء الدور: {role.display_name}')
                )

    def create_permissions(self):
        """إنشاء الصلاحيات الأساسية"""
        modules = ['accounting', 'inventory', 'sales', 'purchases', 'production', 
                  'hr', 'crm', 'reports', 'partners', 'core', 'maintenance']
        actions = ['view', 'add', 'change', 'delete', 'approve', 'print', 'export']
        
        # صلاحيات المدير العام
        super_admin = UserRole.objects.get(name='super_admin')
        for module in modules:
            for action in actions:
                ModulePermission.objects.get_or_create(
                    role=super_admin,
                    module=module,
                    action=action,
                    defaults={'is_allowed': True}
                )
        
        # صلاحيات مدير المحاسبة
        acc_manager = UserRole.objects.get(name='accounting_manager')
        acc_modules = ['accounting', 'reports', 'core']
        for module in acc_modules:
            for action in ['view', 'add', 'change', 'approve', 'print', 'export']:
                ModulePermission.objects.get_or_create(
                    role=acc_manager,
                    module=module,
                    action=action,
                    defaults={'is_allowed': True}
                )
        
        # صلاحيات موظف المحاسبة
        acc_staff = UserRole.objects.get(name='accounting_staff')
        for module in ['accounting']:
            for action in ['view', 'add', 'change', 'print']:
                ModulePermission.objects.get_or_create(
                    role=acc_staff,
                    module=module,
                    action=action,
                    defaults={'is_allowed': True}
                )
        
        # صلاحيات مدير المخزون
        inv_manager = UserRole.objects.get(name='inventory_manager')
        inv_modules = ['inventory', 'purchases', 'reports']
        for module in inv_modules:
            for action in ['view', 'add', 'change', 'approve', 'print', 'export']:
                ModulePermission.objects.get_or_create(
                    role=inv_manager,
                    module=module,
                    action=action,
                    defaults={'is_allowed': True}
                )
        
        # صلاحيات موظف المخزون
        inv_staff = UserRole.objects.get(name='inventory_staff')
        for module in ['inventory']:
            for action in ['view', 'add', 'change']:
                ModulePermission.objects.get_or_create(
                    role=inv_staff,
                    module=module,
                    action=action,
                    defaults={'is_allowed': True}
                )
        
        # صلاحيات مستخدم العرض فقط
        viewer = UserRole.objects.get(name='viewer')
        for module in modules:
            ModulePermission.objects.get_or_create(
                role=viewer,
                module=module,
                action='view',
                defaults={'is_allowed': True}
            )
        
        self.stdout.write(
            self.style.SUCCESS('تم إنشاء الصلاحيات الأساسية')
        )

    def fix_admin_user(self):
        """إصلاح مستخدم admin"""
        try:
            admin_user = User.objects.get(username='admin')
            
            # تأكد من أن admin ليس superuser
            admin_user.is_superuser = False
            admin_user.is_staff = True
            admin_user.save()
            
            # إنشاء profile إذا لم يكن موجوداً
            profile, created = UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={
                    'arabic_name': 'المدير العام',
                    'employee_id': 'EMP001',
                    'role': UserRole.objects.get(name='super_admin'),
                    'is_approved': True,
                    'must_change_password': False,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS('تم إنشاء profile لمستخدم admin')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('Profile موجود مسبقاً لمستخدم admin')
                )
                
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('مستخدم admin غير موجود')
            )

    def create_demo_user(self):
        """إنشاء مستخدم تجريبي"""
        demo_user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'first_name': 'Demo',
                'last_name': 'User',
                'email': 'demo@example.com',
                'is_staff': True,
                'is_superuser': False,
            }
        )
        
        if created:
            demo_user.set_password('demo123456')
            demo_user.save()
            
            # إنشاء profile
            UserProfile.objects.create(
                user=demo_user,
                arabic_name='مستخدم تجريبي',
                employee_id='DEMO001',
                role=UserRole.objects.get(name='accounting_staff'),
                is_approved=True,
                must_change_password=False,
            )
            
            self.stdout.write(
                self.style.SUCCESS('تم إنشاء المستخدم التجريبي: demo_user (كلمة المرور: demo123456)')
            )