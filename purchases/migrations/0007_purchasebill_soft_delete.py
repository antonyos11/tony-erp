from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('purchases', '0006_purchaseorder_new_statuses'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchasebill',
            name='is_deleted',
            field=models.BooleanField(default=False, verbose_name='محذوف'),
        ),
        migrations.AddField(
            model_name='purchasebill',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='تاريخ الحذف'),
        ),
        migrations.AddField(
            model_name='purchasebill',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_purchase_bills', to='auth.user', verbose_name='محذوف بواسطة'),
        ),
        migrations.AddField(
            model_name='purchasebill',
            name='delete_reason',
            field=models.TextField(blank=True, verbose_name='سبب الحذف'),
        ),
    ]
