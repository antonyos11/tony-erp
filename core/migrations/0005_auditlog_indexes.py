from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_create_auditors_group'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['created_at', 'action'], name='auditlog_created_action_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['app_label', 'model_name', 'created_at'], name='auditlog_model_created_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user', 'created_at'], name='auditlog_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['app_label', 'model_name', 'object_id'], name='auditlog_obj_lookup_idx'),
        ),
    ]
