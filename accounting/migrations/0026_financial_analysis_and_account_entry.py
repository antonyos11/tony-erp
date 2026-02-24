# Generated manually for financial analysis and account entry models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounting', '0025_alter_journalentry_created_by'),
    ]

    operations = [
        # FinancialAnalysis1
        migrations.CreateModel(
            name='FinancialAnalysis1',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='الكود')),
                ('name', models.CharField(max_length=255, verbose_name='الاسم')),
                ('description', models.TextField(blank=True, verbose_name='الوصف')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'تحليل مالي 1',
                'verbose_name_plural': 'التحليلات المالية 1',
                'ordering': ['code'],
            },
        ),
        # FinancialAnalysis2
        migrations.CreateModel(
            name='FinancialAnalysis2',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='الكود')),
                ('name', models.CharField(max_length=255, verbose_name='الاسم')),
                ('description', models.TextField(blank=True, verbose_name='الوصف')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'تحليل مالي 2',
                'verbose_name_plural': 'التحليلات المالية 2',
                'ordering': ['code'],
            },
        ),
        # AccountEntry
        migrations.CreateModel(
            name='AccountEntry',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('entry_type', models.CharField(choices=[('revenue', 'إيراد'), ('expense', 'منصرف')], max_length=10, verbose_name='نوع القيد')),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='التاريخ')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='المبلغ')),
                ('description', models.TextField(verbose_name='البيان')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cost_center', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounting.costcenter', verbose_name='مركز التكلفة')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_account_entries', to=settings.AUTH_USER_MODEL, verbose_name='أنشئ بواسطة')),
                ('financial_analysis_1', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounting.financialanalysis1', verbose_name='تحليل مالي 1')),
                ('financial_analysis_2', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounting.financialanalysis2', verbose_name='تحليل مالي 2')),
                ('journal_entry', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='account_entries', to='accounting.journalentry', verbose_name='القيد المحاسبي')),
                ('ledger_account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='account_entries', to='accounting.account', verbose_name='حساب الأستاذ')),
            ],
            options={
                'verbose_name': 'قيد حساب',
                'verbose_name_plural': 'قيود الحسابات',
                'ordering': ['-date', '-created_at'],
            },
        ),
        # Indexes
        migrations.AddIndex(
            model_name='accountentry',
            index=models.Index(fields=['entry_type', 'date'], name='accounting__entry_t_abc123_idx'),
        ),
        migrations.AddIndex(
            model_name='accountentry',
            index=models.Index(fields=['ledger_account'], name='accounting__ledger__def456_idx'),
        ),
        migrations.AddIndex(
            model_name='accountentry',
            index=models.Index(fields=['financial_analysis_1'], name='accounting__financi_ghi789_idx'),
        ),
        migrations.AddIndex(
            model_name='accountentry',
            index=models.Index(fields=['financial_analysis_2'], name='accounting__financi_jkl012_idx'),
        ),
    ]
