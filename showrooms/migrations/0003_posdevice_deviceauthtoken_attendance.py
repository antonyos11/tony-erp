from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('showrooms', '0002_showroomemployee_extra_perms_and_more'),
        ('inventory', '0010_product_is_promo_active_product_promo_end_and_more'),  # location FK (already exists earlier)
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='POSDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='الاسم')),
                ('identifier', models.CharField(help_text='Serial / MAC / UUID', max_length=120, unique=True, verbose_name='المعرف')),
                ('api_key', models.CharField(max_length=64, unique=True, verbose_name='مفتاح API')),
                ('is_active', models.BooleanField(default=True, verbose_name='نشط')),
                ('last_seen', models.DateTimeField(blank=True, null=True, verbose_name='آخر ظهور')),
                ('registered_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ التسجيل')),
                ('showroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='devices', to='showrooms.showroom', verbose_name='المعرض')),
            ],
            options={
                'verbose_name': 'جهاز نقطة بيع',
                'verbose_name_plural': 'أجهزة نقاط البيع',
            },
        ),
        migrations.CreateModel(
            name='DeviceAuthToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=80, unique=True, verbose_name='التوكن')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='ينتهي في')),
                ('revoked', models.BooleanField(default=False, verbose_name='ملغي')),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to='showrooms.posdevice', verbose_name='الجهاز')),
            ],
            options={
                'verbose_name': 'توكن جهاز',
                'verbose_name_plural': 'توكنات الأجهزة',
            },
        ),
        migrations.CreateModel(
            name='AttendanceRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='التاريخ')),
                ('in_time', models.DateTimeField(blank=True, null=True, verbose_name='وقت الدخول')),
                ('out_time', models.DateTimeField(blank=True, null=True, verbose_name='وقت الخروج')),
                ('device_identifier', models.CharField(blank=True, max_length=120, verbose_name='معرف الجهاز')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='ملاحظة')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='أُنشئ في')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_records', to='showrooms.showroomemployee', verbose_name='الموظف')),
                ('showroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_records', to='showrooms.showroom', verbose_name='المعرض')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='showroom_attendance', to=settings.AUTH_USER_MODEL, verbose_name='المستخدم')),
            ],
            options={
                'verbose_name': 'سجل حضور',
                'verbose_name_plural': 'سجلات الحضور',
            },
        ),
        migrations.AddIndex(
            model_name='posdevice',
            index=models.Index(fields=['showroom', 'is_active'], name='showroom_posdevice_showroom_active_idx'),
        ),
        migrations.AddIndex(
            model_name='posdevice',
            index=models.Index(fields=['identifier'], name='showroom_posdevice_identifier_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['showroom', 'date'], name='showroom_attendance_showroom_date_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['employee', 'date'], name='showroom_attendance_employee_date_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='attendancerecord',
            unique_together={('showroom', 'employee', 'date')},
        ),
    ]
