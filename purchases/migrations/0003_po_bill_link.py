from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0002_purchase_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorder',
            name='bill',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='source_order', to='purchases.purchasebill'),
        ),
    ]
