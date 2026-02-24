from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0005_invoicepayment'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicepayment',
            name='first_printed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='تاريخ أول طباعة'),
        ),
        migrations.AddField(
            model_name='invoicepayment',
            name='printed_count',
            field=models.PositiveIntegerField(default=0, verbose_name='عدد مرات الطباعة'),
        ),
        migrations.AddField(
            model_name='invoicepayment',
            name='locked',
            field=models.BooleanField(default=False, help_text='يمنع التعديل/الحذف بعد القفل', verbose_name='مقفول بعد الطباعة'),
        ),
        migrations.AlterModelOptions(
            name='invoicepayment',
            options={'ordering': ['-date', '-id'], 'permissions': [('lock_invoicepayment', 'قفل دفعة فاتورة')], 'verbose_name': 'دفعة فاتورة', 'verbose_name_plural': 'دفعات الفواتير'},
        ),
    ]
