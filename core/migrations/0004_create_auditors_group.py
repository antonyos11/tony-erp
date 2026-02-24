from django.db import migrations


def create_auditors_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    try:
        ct = ContentType.objects.get(app_label='core', model='auditlog')
        perm = Permission.objects.get(content_type=ct, codename='view_auditlog')
    except Exception:
        # If content type or permission isn't available, skip without failing.
        return
    group, _ = Group.objects.get_or_create(name='auditors')
    group.permissions.add(perm)


def remove_auditors_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='auditors').delete()


class Migration(migrations.Migration):
    dependencies = [
    ('core', '0002_auditlog'),
    ('core', '0003_appsettings'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(create_auditors_group, remove_auditors_group),
    ]
