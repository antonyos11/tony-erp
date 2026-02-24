from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounting', '0008_cheque_accounting__number_b628ad_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CashFlowAccountMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('operating', 'تشغيلي'), ('investing', 'استثماري'), ('financing', 'تمويلي')], max_length=20, verbose_name='الفئة')),
                ('note', models.CharField(blank=True, max_length=200, verbose_name='ملاحظة')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cashflow_mapping', to='accounting.account', verbose_name='الحساب')),
            ],
            options={
                'verbose_name': 'تعيين فئة تدفق نقدي',
                'verbose_name_plural': 'تعيينات فئات التدفق النقدي',
                'ordering': ['account__code'],
            },
        ),
    ]
