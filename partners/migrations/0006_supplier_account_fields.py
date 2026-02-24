from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        ('accounting', '0002_fiscalyear_account_journalentry_and_more'),  # يحتوي على Account model
        ('partners', '0005_customer_partner'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplier',
            name='partner',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='supplier_profile', to='partners.partner', verbose_name='الشريك المرتبط'),
        ),
        migrations.AddField(
            model_name='supplier',
            name='account',
            field=models.ForeignKey(blank=True, help_text='اتركه فارغاً لاستخدام حساب الدائنين العام بالإعدادات', null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounting.account', verbose_name='حساب المورد (فرعي)'),
        ),
        migrations.AddField(
            model_name='supplier',
            name='opening_balance',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=15, verbose_name='رصيد افتتاحي دائن'),
        ),
        migrations.AddField(
            model_name='supplier',
            name='credit_limit',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=15, verbose_name='حد ائتماني'),
        ),
        migrations.AddField(
            model_name='supplier',
            name='payment_terms_days',
            field=models.PositiveIntegerField(default=0, verbose_name='أيام سماح السداد'),
        ),
    ]
