# Generated manually for new driver violation & advance models and expense links
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
from decimal import Decimal

class Migration(migrations.Migration):
    dependencies = [
        ('fleet', '0003_alter_driver_options_alter_trip_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DriverAdvance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='تاريخ العهدة')),
                ('amount', models.DecimalField(max_digits=12, decimal_places=2, verbose_name='قيمة العهدة')),
                ('description', models.CharField(blank=True, max_length=255, verbose_name='الوصف')),
                ('status', models.CharField(choices=[('open', 'مفتوحة'), ('settled', 'مُقفلة')], default='open', max_length=10, verbose_name='الحالة')),
                ('settlement_date', models.DateField(blank=True, null=True, verbose_name='تاريخ التصفية')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='advances', to='fleet.driver', verbose_name='السائق')),
            ],
            options={'verbose_name': 'عهدة سائق', 'verbose_name_plural': 'عهد السائقين', 'ordering': ['-date', '-id']},
        ),
        migrations.CreateModel(
            name='DriverViolation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('violation_type', models.CharField(max_length=120, verbose_name='نوع المخالفة')),
                ('date', models.DateField(verbose_name='التاريخ')),
                ('amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='قيمة المخالفة')),
                ('receipt', models.FileField(blank=True, null=True, upload_to='fleet/violations/', verbose_name='إيصال/مرفق')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('is_paid', models.BooleanField(default=False, verbose_name='مدفوعة')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='violations', to='fleet.driver', verbose_name='السائق')),
                ('vehicle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='violations', to='fleet.vehicle', verbose_name='المركبة')),
            ],
            options={'verbose_name': 'مخالفة سائق', 'verbose_name_plural': 'مخالفات السائقين', 'ordering': ['-date', '-id']},
        ),
        migrations.AddField(
            model_name='vehicleexpense',
            name='advance',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expenses', to='fleet.driveradvance', verbose_name='عهدة مرتبطة'),
        ),
        migrations.AddField(
            model_name='vehicleexpense',
            name='driver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expenses', to='fleet.driver', verbose_name='السائق (إن وجد)'),
        ),
    ]
