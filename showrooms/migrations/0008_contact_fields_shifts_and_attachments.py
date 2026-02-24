from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('showrooms', '0007_showroom_showroomexpense_showroompurchase_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='showroom',
            name='contact_person',
            field=models.CharField(blank=True, max_length=120, verbose_name='اسم مسؤول التواصل'),
        ),
        migrations.AddField(
            model_name='showroom',
            name='contact_phone',
            field=models.CharField(blank=True, max_length=40, verbose_name='هاتف التواصل'),
        ),
        migrations.AddField(
            model_name='showroomexpense',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='showrooms/expenses/', verbose_name='مرفق/إيصال'),
        ),
        migrations.AddField(
            model_name='showroompurchase',
            name='invoice_file',
            field=models.FileField(blank=True, null=True, upload_to='showrooms/purchases/', verbose_name='فاتورة/مرفق'),
        ),
        migrations.CreateModel(
            name='ShowroomShift',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=80, verbose_name='اسم الشفت')),
                ('start_time', models.TimeField(verbose_name='بداية الشفت')),
                ('end_time', models.TimeField(verbose_name='نهاية الشفت')),
                ('break_minutes', models.PositiveIntegerField(default=0, verbose_name='دقائق الراحة')),
                ('is_active', models.BooleanField(default=True, verbose_name='نشط')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('showroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shifts', to='showrooms.showroom', verbose_name='المعرض')),
            ],
            options={
                'verbose_name': 'شفت معرض',
                'verbose_name_plural': 'شفتات المعارض',
                'ordering': ['showroom', 'start_time'],
            },
        ),
        migrations.CreateModel(
            name='ShowroomShiftAssignment',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('day_of_week', models.PositiveSmallIntegerField(choices=[(0, 'الاثنين'), (1, 'الثلاثاء'), (2, 'الأربعاء'), (3, 'الخميس'), (4, 'الجمعة'), (5, 'السبت'), (6, 'الأحد')], verbose_name='اليوم')),
                ('note', models.CharField(blank=True, max_length=200, verbose_name='ملاحظة')),
                ('active', models.BooleanField(default=True, verbose_name='نشط')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shift_assignments', to='showrooms.showroomemployee', verbose_name='الموظف')),
                ('shift', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='showrooms.showroomshift', verbose_name='الشفت')),
            ],
            options={
                'verbose_name': 'تعيين شفت لموظف معرض',
                'verbose_name_plural': 'تعيينات شفتات موظفي المعرض',
            },
        ),
        migrations.AddIndex(
            model_name='showroomshift',
            index=models.Index(fields=['showroom', 'is_active'], name='showrooms_sh_showroo_6e35af_idx'),
        ),
        migrations.AddConstraint(
            model_name='showroomshiftassignment',
            constraint=models.UniqueConstraint(fields=('shift', 'employee', 'day_of_week'), name='showroom_shift_employee_day_unique'),
        ),
        migrations.AddIndex(
            model_name='showroomshiftassignment',
            index=models.Index(fields=['employee', 'active'], name='showrooms_sh_employee_8fecb4_idx'),
        ),
        migrations.AddIndex(
            model_name='showroomshiftassignment',
            index=models.Index(fields=['shift', 'day_of_week'], name='showrooms_sh_shift_da_5c787a_idx'),
        ),
    ]
