from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0001_initial'),
        ('accounting', '0006_accountingsettings'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Cheque',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=50, verbose_name='رقم الشيك')),
                ('bank_name', models.CharField(blank=True, max_length=100, verbose_name='اسم البنك')),
                ('cheque_type', models.CharField(choices=[('incoming', 'وارد'), ('outgoing', 'صادر')], default='incoming', max_length=10, verbose_name='نوع الشيك')),
                ('status', models.CharField(choices=[('received', 'مستلم/صادر'), ('under_collection', 'قيد التحصيل'), ('deposited', 'مودع بالبنك'), ('cleared', 'محصل/مصروف'), ('bounced', 'مرتجع'), ('cancelled', 'ملغى')], default='received', max_length=20, verbose_name='الحالة')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='المبلغ')),
                ('issue_date', models.DateField(default=django.utils.timezone.now, verbose_name='تاريخ الإصدار')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='تاريخ الاستحقاق')),
                ('image', models.ImageField(blank=True, null=True, upload_to='cheques/', verbose_name='صورة الشيك')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='أنشئ بواسطة')),
                ('partner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='partners.partner', verbose_name='الشريك')),
            ],
            options={
                'verbose_name': 'شيك',
                'verbose_name_plural': 'حافظة الشيكات',
                'ordering': ['-created_at'],
            },
        ),
    ]
