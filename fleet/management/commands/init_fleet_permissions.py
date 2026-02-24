from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import UserRole, ModulePermission

FLEET_ACTIONS = ['view','add','change','delete','export']
TARGET_ROLES = [
    'super_admin', 'accounting_manager', 'inventory_manager', 'sales_manager', 'production_manager', 'hr_manager'
]

class Command(BaseCommand):
    help = 'تهيئة صلاحيات وحدة الأسطول للأدوار الأساسية إن لم تكن موجودة'

    def handle(self, *args, **options):
        created_count = 0
        with transaction.atomic():
            roles = UserRole.objects.filter(name__in=TARGET_ROLES)
            for role in roles:
                for action in FLEET_ACTIONS:
                    obj, created = ModulePermission.objects.get_or_create(
                        role=role,
                        module='fleet',
                        action=action,
                        defaults={'is_allowed': True}
                    )
                    if created:
                        created_count += 1
        self.stdout.write(self.style.SUCCESS(f'تم إنشاء {created_count} صلاحية أسطول جديدة'))
