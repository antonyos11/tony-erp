from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('partners', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(blank=True, max_length=50, verbose_name='رقم الفاتورة')),
                ('date', models.DateField(blank=True, null=True, verbose_name='التاريخ')),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='الإجمالي')),
                ('description', models.TextField(blank=True, verbose_name='الوصف')),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoices', to='partners.customer')),
            ],
            options={
                'verbose_name': 'فاتورة',
                'verbose_name_plural': 'الفواتير',
            },
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(blank=True, max_length=200, verbose_name='الوصف')),
                ('quantity', models.DecimalField(decimal_places=2, default=1, max_digits=10, verbose_name='الكمية')),
                ('unit_price', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='سعر الوحدة')),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='الإجمالي')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='sales.invoice')),
            ],
            options={
                'app_label': 'sales',
            },
        ),
        migrations.CreateModel(
            name='InvoicePayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='المبلغ')),
                ('date', models.DateField(blank=True, null=True, verbose_name='التاريخ')),
                ('method', models.CharField(blank=True, max_length=50, verbose_name='طريقة الدفع')),
                ('note', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='sales.invoice')),
            ],
            options={
                'app_label': 'sales',
            },
        ),
    ]
