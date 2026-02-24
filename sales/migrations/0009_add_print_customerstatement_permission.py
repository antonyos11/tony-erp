from django.db import migrations

def add_permission(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    try:
        ct = ContentType.objects.get(app_label='sales', model='invoice')
        Permission.objects.get_or_create(
            codename='print_customerstatement',
            defaults={'name': 'طباعة كشف حساب عميل', 'content_type': ct},
            content_type=ct,
            name='طباعة كشف حساب عميل'
        )
    except Exception:
        # لا نفشل الهجرة في حال عدم توفر المحتوى (بيئات اختبارية قديمة)
        pass

def remove_permission(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    try:
        Permission.objects.filter(codename='print_customerstatement', content_type__app_label='sales').delete()
    except Exception:
        pass

class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0008_invoicepayment_sequence'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(add_permission, remove_permission),
    ]
