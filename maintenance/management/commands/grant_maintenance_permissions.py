from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from users.models import User, UserRole
from maintenance.models import Machine, SparePart, MaintenanceRequest

class Command(BaseCommand):
    help = 'منح صلاحيات الصيانة للمستخدمين'

    def handle(self, *args, **options):
        self.stdout.write('بدء منح صلاحيات الصيانة...')
        
        # إنشاء أو الحصول على مجموعة الصيانة
        maintenance_group, created = Group.objects.get_or_create(name='Maintenance Users')
        if created:
            self.stdout.write('تم إنشاء مجموعة مستخدمي الصيانة')
        
        # الحصول على ContentTypes للنماذج
        machine_ct = ContentType.objects.get_for_model(Machine)
        spare_part_ct = ContentType.objects.get_for_model(SparePart)
        request_ct = ContentType.objects.get_for_model(MaintenanceRequest)
        
        # قائمة الصلاحيات المطلوبة
        permissions = [
            # Machine permissions
            ('view_machine', machine_ct),
            ('add_machine', machine_ct),
            ('change_machine', machine_ct),
            
            # SparePart permissions
            ('view_sparepart', spare_part_ct),
            ('add_sparepart', spare_part_ct),
            ('change_sparepart', spare_part_ct),
            
            # MaintenanceRequest permissions
            ('view_maintenancerequest', request_ct),
            ('add_maintenancerequest', request_ct),
            ('change_maintenancerequest', request_ct),
        ]
        
        # إضافة الصلاحيات للمجموعة
        for perm_codename, content_type in permissions:
            try:
                permission = Permission.objects.get(
                    codename=perm_codename,
                    content_type=content_type
                )
                maintenance_group.permissions.add(permission)
                self.stdout.write(f'تمت إضافة صلاحية: {perm_codename}')
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'لا توجد صلاحية: {perm_codename}'))
        
        # إضافة جميع المستخدمين الإداريين للمجموعة
        admin_users = User.objects.filter(is_superuser=True)
        for user in admin_users:
            user.groups.add(maintenance_group)
            
            # منح صلاحية الوحدة في نظام الصلاحيات المخصص
            try:
                from users.models import UserModulePermission
                
                # صلاحيات عرض
                UserModulePermission.objects.get_or_create(
                    user=user,
                    module='maintenance',
                    action='view',
                    defaults={'granted': True}
                )
                
                # صلاحيات إضافة
                UserModulePermission.objects.get_or_create(
                    user=user,
                    module='maintenance',
                    action='add',
                    defaults={'granted': True}
                )
                
                # صلاحيات تعديل
                UserModulePermission.objects.get_or_create(
                    user=user,
                    module='maintenance',
                    action='change',
                    defaults={'granted': True}
                )
                
                self.stdout.write(f'تم منح صلاحيات الصيانة للمستخدم: {user.username}')
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'خطأ في منح الصلاحيات المخصصة: {e}'))
        
        self.stdout.write(self.style.SUCCESS('تم منح صلاحيات الصيانة بنجاح!'))