from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = "Create 'auditors' group and grant 'core.view_auditlog' permission."

    def handle(self, *args, **options):
        try:
            ct = ContentType.objects.get(app_label='core', model='auditlog')
            perm = Permission.objects.get(content_type=ct, codename='view_auditlog')
        except ContentType.DoesNotExist:
            self.stdout.write(self.style.WARNING("ContentType for core.AuditLog not found. Have you migrated?"))
            return
        except Permission.DoesNotExist:
            self.stdout.write(self.style.WARNING("Permission 'view_auditlog' not found. Have you migrated?"))
            return

        group, created = Group.objects.get_or_create(name='auditors')
        group.permissions.add(perm)
        self.stdout.write(self.style.SUCCESS("Auditors group is ready and has 'view_auditlog'."))
