from django.db import migrations

def cleanup_permission(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    try:
        ct = ContentType.objects.get(app_label='sales', model='invoice')
        perms = Permission.objects.filter(codename='print_customerstatement')
        keep = perms.filter(content_type=ct).first() or perms.first()
        if keep:
            perms.exclude(pk=keep.pk).delete()
    except Exception:
        pass

class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0010_alter_invoice_options_alter_invoicepayment_options_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(cleanup_permission, reverse_code=migrations.RunPython.noop),
    ]
