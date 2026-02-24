from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_auditlog_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='appsettings',
            name='audit_retention_days',
            field=models.PositiveIntegerField(default=90),
        ),
        migrations.AddField(
            model_name='appsettings',
            name='audit_sensitive_fields',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='appsettings',
            name='audit_ignore_apps',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='appsettings',
            name='audit_ignore_models',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='appsettings',
            name='audit_alert_rules',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
