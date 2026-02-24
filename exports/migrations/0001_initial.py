from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BackupRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('backup_name', models.CharField(max_length=255, verbose_name='اسم النسخة الاحتياطية')),
                ('backup_type', models.CharField(choices=[('manual', 'يدوي'), ('scheduled', 'مجدول'), ('automatic', 'تلقائي')], max_length=20, verbose_name='نوع النسخة')),
                ('file_path', models.CharField(max_length=500, verbose_name='مسار الملف')),
                ('file_size', models.BigIntegerField(default=0, verbose_name='حجم الملف (بايت)')),
                ('status', models.CharField(choices=[('in_progress', 'جاري التنفيذ'), ('completed', 'مكتمل'), ('failed', 'فشل')], default='in_progress', max_length=20, verbose_name='الحالة')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='تاريخ الاكتمال')),
                ('error_message', models.TextField(blank=True, verbose_name='رسالة الخطأ')),
                ('includes_media', models.BooleanField(default=True, verbose_name='يتضمن الملفات')),
                ('includes_database', models.BooleanField(default=True, verbose_name='يتضمن قاعدة البيانات')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='أنشئ بواسطة')),
            ],
            options={'verbose_name': 'نسخة احتياطية', 'verbose_name_plural': 'النسخ الاحتياطية', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='DataExport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('export_name', models.CharField(max_length=255, verbose_name='اسم التصدير')),
                ('export_type', models.CharField(max_length=50, verbose_name='نوع البيانات')),
                ('export_format', models.CharField(choices=[('csv', 'CSV'), ('excel', 'Excel'), ('pdf', 'PDF'), ('json', 'JSON')], max_length=10, verbose_name='تنسيق التصدير')),
                ('parameters', models.JSONField(blank=True, default=dict, verbose_name='معايير التصدير')),
                ('file_path', models.CharField(blank=True, max_length=500, verbose_name='مسار الملف')),
                ('file_size', models.BigIntegerField(default=0, verbose_name='حجم الملف (بايت)')),
                ('status', models.CharField(choices=[('pending', 'معلق'), ('processing', 'جاري المعالجة'), ('completed', 'مكتمل'), ('failed', 'فشل')], default='pending', max_length=20, verbose_name='الحالة')),
                ('progress', models.IntegerField(default=0, verbose_name='نسبة التقدم %')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الطلب')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='تاريخ الاكتمال')),
                ('download_count', models.IntegerField(default=0, verbose_name='عدد مرات التحميل')),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='ينتهي في')),
                ('error_message', models.TextField(blank=True, verbose_name='رسالة الخطأ')),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='طلب بواسطة')),
            ],
            options={'verbose_name': 'تصدير بيانات', 'verbose_name_plural': 'تصدير البيانات', 'ordering': ['-created_at']},
        ),
    ]
