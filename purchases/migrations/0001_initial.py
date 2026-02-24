from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('partners', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='PurchaseBill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(blank=True, max_length=50)),
                ('date', models.DateField(blank=True, null=True)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='purchasebill', to='partners.supplier')),
            ],
        ),
    ]
