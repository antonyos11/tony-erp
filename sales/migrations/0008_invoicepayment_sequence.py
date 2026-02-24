from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0007_invoicepayment_extra_constraints'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvoicePaymentSequence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year_month', models.CharField(help_text='تنسيق YYYYMM', max_length=6, unique=True)),
                ('last_number', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'تسلسل إيصالات المدفوعات',
                'verbose_name_plural': 'تسلسلات إيصالات المدفوعات',
            },
        ),
        # لا حاجة لترحيل بيانات؛ الجداول ستولد لاحقاً عند أول استخدام.
    ]
