from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
    ('contenttypes', '0002_remove_content_type_name'),
    ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', 'إنشاء'), ('update', 'تعديل'), ('delete', 'حذف'), ('login', 'تسجيل دخول'), ('logout', 'تسجيل خروج')], max_length=20, verbose_name='الإجراء')),
                ('object_id', models.CharField(blank=True, max_length=255, null=True)),
                ('model_name', models.CharField(blank=True, max_length=100, verbose_name='اسم النموذج')),
                ('app_label', models.CharField(blank=True, max_length=100, verbose_name='اسم التطبيق')),
                ('object_repr', models.CharField(blank=True, max_length=255, verbose_name='وصف الكائن')),
                ('changes', models.JSONField(blank=True, default=dict, verbose_name='التغييرات')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='عنوان IP')),
                ('user_agent', models.CharField(blank=True, max_length=255, verbose_name='المتصفح/العميل')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name='التاريخ')),
                ('content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='المستخدم')),
            ],
            options={
                'verbose_name': 'سجل النظام',
                'verbose_name_plural': 'سجلات النظام',
                'ordering': ['-created_at'],
            },
        ),
    ]
