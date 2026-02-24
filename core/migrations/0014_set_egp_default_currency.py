from django.db import migrations


def set_egp_default(apps, schema_editor):
    Currency = apps.get_model('core', 'Currency')
    Company = apps.get_model('core', 'Company')

    egp_defaults = {
        'name': 'الجنيه المصري',
        'symbol': 'ج.م',
        'is_active': True,
        'is_default': True,
        'exchange_rate': 1,
        'decimal_places': 2,
    }
    egp, created = Currency.objects.get_or_create(code='EGP', defaults=egp_defaults)
    changed = False
    for k, v in egp_defaults.items():
        if getattr(egp, k) != v:
            setattr(egp, k, v)
            changed = True
    if changed:
        egp.save()

    Currency.objects.exclude(pk=egp.pk).filter(is_default=True).update(is_default=False)

    for company in Company.objects.filter(default_currency__isnull=True):
        company.default_currency_id = egp.id
        company.save(update_fields=['default_currency'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0013_alter_currency_exchange_rate'),
    ]

    operations = [
        migrations.RunPython(set_egp_default, noop_reverse),
    ]
