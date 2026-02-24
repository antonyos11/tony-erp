from django.core.management.base import BaseCommand
from users.models import User, UserRole, ModulePermission

class Command(BaseCommand):
    help = 'إعداد صلاحيات الصيانة للأدوار'

    def handle(self, *args, **options):
        self.stdout.write('بدء إعداد صلاحيات الصيانة...')
        
        # الحصول على جميع الأدوار
        roles = UserRole.objects.all()
        
        if not roles.exists():
            # إنشاء دور افتراضي إذا لم توجد أدوار
            admin_role = UserRole.objects.create(
                name='مدير النظام',
                description='مدير عام للنظام',
                is_active=True
            )
            self.stdout.write(f'تم إنشاء دور: {admin_role.name}')
            roles = [admin_role]
            
            # تعيين هذا الدور للمستخدمين الإداريين
            admin_users = User.objects.filter(is_superuser=True, role__isnull=True)
            for user in admin_users:
                user.role = admin_role
                user.save()
                self.stdout.write(f'تم تعيين دور للمستخدم: {user.username}')
        
        # إنشاء صلاحيات الصيانة لكل دور
        actions = ['view', 'add', 'change', 'delete']
        
        for role in roles:
            for action in actions:
                permission, created = ModulePermission.objects.get_or_create(
                    role=role,
                    module='maintenance',
                    action=action,
                    defaults={'is_allowed': True}
                )
                
                if created:
                    self.stdout.write(f'تمت إضافة صلاحية {action} للصيانة للدور: {role.name}')
                else:
                    # تأكد من أن الصلاحية مفعلة
                    if not permission.is_allowed:
                        permission.is_allowed = True
                        permission.save()
                        self.stdout.write(f'تم تفعيل صلاحية {action} للصيانة للدور: {role.name}')
        
        self.stdout.write(self.style.SUCCESS('تم إعداد صلاحيات الصيانة بنجاح!'))