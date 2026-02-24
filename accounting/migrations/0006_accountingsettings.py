from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0005_alter_loan_created_by_alter_loanpayment_created_by'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountingSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enable_vat', models.BooleanField(default=False, verbose_name='تفعيل ضريبة القيمة المضافة VAT')),
                ('default_vat_rate', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=5, verbose_name='نسبة VAT الافتراضية %')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ap_account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounting.account', verbose_name='حساب الدائنين (الموردين)')),
                ('cash_account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounting.account', verbose_name='حساب النقدية/البنك')),
                ('inventory_account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounting.account', verbose_name='حساب المخزون')),
                ('vat_input_account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounting.account', verbose_name='حساب ضريبة مدخلات')),
                ('vat_output_account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounting.account', verbose_name='حساب ضريبة مخرجات (للمبيعات)')),
            ],
            options={
                'verbose_name': 'إعدادات المحاسبة',
                'verbose_name_plural': 'إعدادات المحاسبة',
            },
        ),
    ]
