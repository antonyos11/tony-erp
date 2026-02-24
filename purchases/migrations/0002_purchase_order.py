from django.db import migrations, models
import django.utils.timezone
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
        ('partners', '0001_initial'),
        ('purchases', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=50, unique=True, verbose_name='رقم الأمر')),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='التاريخ')),
                ('expected_date', models.DateField(blank=True, null=True, verbose_name='تاريخ التوريد المتوقع')),
                ('status', models.CharField(choices=[('draft', 'مسودة'), ('confirmed', 'مؤكد'), ('cancelled', 'ملغى')], default='draft', max_length=20, verbose_name='الحالة')),
                ('discount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='الخصم')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_orders', to='partners.supplier')),
            ],
            options={'ordering': ['-id'], 'verbose_name': 'أمر شراء', 'verbose_name_plural': 'أوامر الشراء'},
        ),
        migrations.CreateModel(
            name='PurchaseOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('cost', models.DecimalField(decimal_places=2, max_digits=12)),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.location')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.product')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='purchases.purchaseorder')),
            ],
            options={'verbose_name': 'بند أمر شراء', 'verbose_name_plural': 'بنود أوامر الشراء'},
        ),
    ]
