from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0016_location_min_stock_location_purchase_uom_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LowStockEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_notified_at', models.DateTimeField(auto_now=True)),
                ('last_quantity', models.IntegerField(default=0)),
                ('threshold', models.IntegerField(default=0)),
                ('notification_count', models.PositiveIntegerField(default=0)),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='low_stock_event', to='inventory.product')),
            ],
            options={
                'verbose_name': 'Low Stock Event',
                'verbose_name_plural': 'Low Stock Events',
            },
        ),
        migrations.AddIndex(
            model_name='lowstockevent',
            index=models.Index(fields=['last_notified_at'], name='inventory_l_last_no_abc123'),
        ),
    ]
