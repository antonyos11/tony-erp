from django.db import migrations


def seed_roles(apps, schema_editor):
    UserRole = apps.get_model('users', 'UserRole')
    from core.security import role_definitions as rd

    for code, display_name in rd.ROLE_DISPLAY_NAMES.items():
        # لاحظ أن بعض الأكواد تستخدم أسماء مختلفة في UserRole choices (القيمة هي code نفسه)
        obj, created = UserRole.objects.get_or_create(
            name=code,
            defaults={
                'display_name': display_name,
                'description': rd.ROLE_DESCRIPTIONS.get(code, ''),
                'is_active': True,
                'can_approve': rd.get_default_approval_limit(code) not in (0, None),
                'approval_level': rd.get_approval_level(code),
                'max_approval_amount': rd.get_default_approval_limit(code) or 0,
            },
        )
        if not created:
            # حدّث الحقول الأساسية فقط إذا كانت فارغة لتجنب الكتابة فوق تخصيصات لاحقة
            updated = False
            if not obj.display_name:
                obj.display_name = display_name
                updated = True
            if not obj.description:
                obj.description = rd.ROLE_DESCRIPTIONS.get(code, '')
                updated = True
            if updated:
                obj.save(update_fields=['display_name', 'description'])


def noop_reverse(apps, schema_editor):
    # لا نحذف الأدوار عند الرجوع لتجنب فقد البيانات
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_userprofile_managed_by'),
    ]

    operations = [
        migrations.RunPython(seed_roles, noop_reverse),
    ]
